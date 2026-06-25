#!/usr/bin/env python3
"""Headless smoke for W2 — 산책 중 HUD (#/walk).

DoD(12_W2_walking.md §8):
  1. #/walk 진입(데모) → 지도 + 상단 퀘스트 박스(≤2, 지도 가림 없음) + 좌하단 촬영 + 우하단 종료 렌더, 콘솔 0.
  2. 퀘스트 박스 탭 → #/camera?mission=...&quest=... 진입 단언. 좌하단 탭 → #/camera(mission 없음) 단언.
  3. (모킹) 카메라 복귀 후 해당 퀘스트가 완료 표시되는지 단언(store.walkClips 의 mission_id).
  4. 우하단 종료 → walk end API + POST /records(누적 clip_ids 포함) 201 → #/diary 진입 + 누적 클립 초기화 단언.

데모 모드(blip_demo_context)로 GPS 없이 구동. 콘솔 에러 0(외부 타일/WebGL 잡음 제외), 각 단계 스크린샷 저장.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:9012")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)
LAT, LNG = 37.5665, 126.9780

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

# 외부 리소스(타일/CDN)·WebGL 잡음은 우리 코드 버그가 아니므로 제외
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon")


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def upload_clip(token, mission_id):
    """카메라(W4) 클립 업로드를 API로 모킹 — 실제 소유 clip_id 확보(POST /records 201 위해 필요)."""
    boundary = "----w2b" + uuid.uuid4().hex

    def field(name, value):
        return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode()

    body = b""
    body += field("mission_id", mission_id)
    body += field("duration_ms", "2000")
    body += field("order", "0")
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"clip.webm\"\r\nContent-Type: video/webm\r\n\r\n").encode()
    body += b"\x1aE\xdf\xa3 fake-webm payload" + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/clips/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def make_user(nick, petname, breed):
    u = apicall("POST", "/auth/guest", body={"nickname": nick})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": petname, "breed": breed, "size": "small", "personality_tags": ["활발함"]})
    return u["user_id"], u["auth_token"], p["pet_id"]


def enter_walk(page):
    """#/walk 재진입 + HUD 렌더 대기."""
    page.evaluate("location.hash = '#/walk'")
    page.wait_for_selector(".map-screen", timeout=8000)
    page.wait_for_selector("#walk-map, #walk-fallback", timeout=8000, state="attached")
    page.wait_for_selector("#walk-end", timeout=8000)


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    records_calls = []  # (status, post_data)
    end_calls = []      # status

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    a_uid, a_tok, a_pet = make_user("산책이", "구름", "푸들")
    print(f"{DIM}  fixture: user={a_uid[:8]} pet={a_pet[:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896}, locale="ko-KR", timezone_id="UTC",
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)

        def on_response(r):
            try:
                if r.url.endswith("/api/records") and r.request.method == "POST":
                    records_calls.append((r.status, r.request.post_data))
                elif "/api/walks/" in r.url and r.url.endswith("/end"):
                    end_calls.append(r.status)
            except Exception:
                pass
        page.on("response", on_response)

        try:
            # 세션 + 데모 컨텍스트 주입 (GPS 없이 지도 구동), 누적상태 초기화
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p,lat,lng]) => {
                  localStorage.setItem('auth_token',t);
                  localStorage.setItem('user_id',u);
                  localStorage.setItem('pet_id',p);
                  localStorage.setItem('blip_demo_context', JSON.stringify({lat,lng}));
                  localStorage.removeItem('active_walk_session_id');
                  localStorage.removeItem('blip_walk_clips');
                  localStorage.removeItem('blip_walk_match');
                  localStorage.removeItem('blip_walk_started');
                }""",
                [a_tok, a_uid, a_pet, LAT, LNG],
            )

            # === DoD 1: #/walk 렌더 ===
            enter_walk(page)
            quests = page.query_selector_all(".walk-quest")
            assert 1 <= len(quests) <= 2, f"퀘스트 박스 개수가 1~2가 아님: {len(quests)}"
            assert page.query_selector("#walk-shoot"), "좌하단 촬영 버튼 없음"
            assert page.query_selector("#walk-end"), "우하단 통화종료 버튼 없음"
            mode = "지도(WebGL)" if page.query_selector("#me-marker") else "목록 fallback"
            # 지도 가림 없음: 상단 퀘스트 오버레이가 지도 상단 일부만 차지
            layout = page.evaluate(
                """() => {
                  const ms = document.querySelector('.map-screen').getBoundingClientRect();
                  const ov = document.querySelector('.walk-overlays-top').getBoundingClientRect();
                  return { coverRatio: (ov.bottom - ms.top) / ms.height, ovBottom: ov.bottom, msTop: ms.top, msH: ms.height };
                }"""
            )
            assert layout["coverRatio"] < 0.5, f"상단 퀘스트박스가 지도를 과하게 가림: {layout}"
            ok(page, f"#/walk → 지도({mode}) + 퀘스트박스 {len(quests)}개(지도 가림 {layout['coverRatio']*100:.0f}%) "
                     f"+ 촬영/종료 렌더", "w2_01_walk")

            # === DoD 2a: 퀘스트 박스 탭 → #/camera?mission=&quest= ===
            mid = page.get_attribute(".walk-quest", "data-mission")
            mtitle = page.get_attribute(".walk-quest", "data-quest")
            page.eval_on_selector(".walk-quest", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/camera')", timeout=8000)
            h = page.evaluate("location.hash")
            q = urllib.parse.parse_qs(h.split("?", 1)[1]) if "?" in h else {}
            assert q.get("mission", [None])[0] == mid, f"camera mission 쿼리 불일치: {h}"
            assert q.get("quest", [None])[0] == mtitle, f"camera quest 쿼리 불일치: {h}"
            ok(page, f"퀘스트 박스 탭 → #/camera?mission={mid[:6]}…&quest={mtitle}", "w2_02_camera_quest")

            # === DoD 2b: 좌하단 촬영 → #/camera (mission 없음) ===
            enter_walk(page)
            page.eval_on_selector("#walk-shoot", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/camera')", timeout=8000)
            h2 = page.evaluate("location.hash")
            assert "mission=" not in h2, f"일반 촬영인데 mission 쿼리가 있음: {h2}"
            ok(page, f"좌하단 촬영 탭 → #/camera (mission 없음: {h2})", "w2_03_camera_plain")

            # === DoD 3: 카메라 복귀(모킹) → 퀘스트 완료 표시 ===
            clip = upload_clip(a_tok, mid)  # 실제 소유 clip_id
            page.evaluate(
                "([cid, mid]) => localStorage.setItem('blip_walk_clips', JSON.stringify([{clip_id:cid, mission_id:mid, order:0}]))",
                [clip["clip_id"], mid],
            )
            enter_walk(page)
            done_box = page.query_selector(f'.walk-quest[data-mission="{mid}"]')
            assert done_box, "해당 미션 퀘스트 박스를 찾지 못함"
            cls = done_box.get_attribute("class") or ""
            assert "done" in cls, f"카메라 복귀 후에도 퀘스트가 완료표시되지 않음: class={cls}"
            ok(page, f"카메라 복귀(clip={clip['clip_id'][:6]}) → 해당 퀘스트 완료표시(.done)", "w2_04_quest_done")

            # === DoD 4: 우하단 종료 → end + POST /records(누적 clip) 201 → #/diary + 클립 초기화 ===
            page.eval_on_selector("#walk-end", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=10000)
            assert end_calls and end_calls[-1] == 200, f"walk end API 미관측/실패: {end_calls}"
            assert records_calls, "POST /records 가 관측되지 않음"
            rstatus, rbody = records_calls[-1]
            assert rstatus == 201, f"POST /records 상태가 201이 아님: {rstatus}"
            assert clip["clip_id"] in (rbody or ""), f"records 페이로드에 누적 clip_id 없음: {rbody}"
            cleared = page.evaluate(
                "() => ({clips: localStorage.getItem('blip_walk_clips'), walk: localStorage.getItem('active_walk_session_id')})"
            )
            assert not cleared["clips"], f"누적 클립이 초기화되지 않음: {cleared}"
            assert not cleared["walk"], f"walkId가 초기화되지 않음: {cleared}"
            ok(page, f"통화종료 → walk end {end_calls[-1]} + POST /records {rstatus}(clip 포함) → #/diary + 누적 초기화", "w2_05_saved")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "w2_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')} records={records_calls} end={end_calls}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W2 산책중 HUD 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
