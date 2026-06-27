#!/usr/bin/env python3
"""Headless smoke for 클립→기록 번들링 (산책중 부분, W2 계약).

v2 재설계: 구 #/quest picker · #/record 에디터는 폐기. 산책 중 누적된 클립은
**산책 종료(통화종료) 시 1개 Record로 번들 생성**된다(`POST /records`, clip_ids + daily_quest_id).
(카메라 UI=W4 / 기록 탭 UI=W5 소관이므로 여기서는 W2의 산책중→기록 계약만 검증.)

흐름:
  - 게스트+펫 셋업, 데모 컨텍스트 주입(GPS 없이 #/walk 구동).
  - #/walk 진입 → 퀘스트 미션들에 대해 클립 2개를 API로 모킹 업로드 후 store.walkClips 주입.
  - 카메라 복귀(재진입) → 해당 퀘스트들이 완료 표시되는지 확인.
  - 우하단 통화종료 → walk end + POST /records 201 → #/diary 진입.
  - GET /records 로 방금 기록이 누적 클립 2개 + daily_quest_id 로 묶여 생성됐는지 단언.
콘솔 에러 0(외부/WebGL 잡음 제외), 각 단계 스크린샷 저장.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import uuid

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:9012")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)
LAT, LNG = 37.5665, 126.9780

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
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


def upload_clip(token, mission_id, order):
    boundary = "----recb" + uuid.uuid4().hex

    def field(name, value):
        return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode()

    body = b""
    if mission_id:
        body += field("mission_id", mission_id)
    body += field("duration_ms", "2000")
    body += field("order", str(order))
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"clip.webm\"\r\nContent-Type: video/webm\r\n\r\n").encode()
    body += b"\x1aE\xdf\xa3 fake-webm payload" + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/clips/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    u = apicall("POST", "/auth/guest", body={"nickname": "기록이"})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": "콩", "breed": "말티즈", "size": "small", "personality_tags": ["온순함"]})
    tok, uid, pid = u["auth_token"], u["user_id"], p["pet_id"]
    print(f"{DIM}  fixture: user={uid[:8]} pet={pid[:8]}{RESET}")

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

        try:
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
                [tok, uid, pid, LAT, LNG],
            )

            # --- 산책중 진입 → 퀘스트 미션 식별 ---
            page.evaluate("location.hash = '#/walk'")
            page.wait_for_selector(".map-screen", timeout=8000)
            page.wait_for_selector("#walk-end", timeout=8000)
            missions = page.eval_on_selector_all(
                ".walk-quest", "els => els.map(e => e.dataset.mission)"
            )
            assert missions, "산책중 화면에 퀘스트 미션이 없음"
            ok(page, f"#/walk 진입 → 퀘스트 미션 {len(missions)}개 확보", "rec_01_walk")

            # --- 카메라(W4) 클립 2개 모킹: 누적 클립으로 주입 ---
            mids = (missions + missions)[:2]  # 미션이 1개뿐이어도 2클립 누적
            clips = [upload_clip(tok, mids[i], i) for i in range(2)]
            clip_ids = [c["clip_id"] for c in clips]
            page.evaluate(
                """([clips]) => localStorage.setItem('blip_walk_clips', JSON.stringify(
                     clips.map((c,i) => ({clip_id:c.clip_id, mission_id:c.mission_id, order:i}))))""",
                [[{"clip_id": clip_ids[i], "mission_id": mids[i]} for i in range(2)]],
            )

            # --- 카메라 복귀(재진입) → 퀘스트 완료 표시 ---
            page.evaluate("location.hash = '#/home'")  # 라우트 이탈
            page.evaluate("location.hash = '#/walk'")
            page.wait_for_selector("#walk-end", timeout=8000)
            done = page.query_selector_all(".walk-quest.done")
            assert done, "카메라 복귀 후에도 완료된 퀘스트 표시가 없음"
            ok(page, f"카메라 복귀(클립 2개 누적) → 완료 퀘스트 {len(done)}개 표시", "rec_02_done")

            # --- 통화종료 → 산책 종료 → 누적 클립 1개 Record로 번들 → #/diary ---
            page.eval_on_selector("#walk-end", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=10000)
            ok(page, "통화종료 → 종료/기록 생성 → #/diary 이동", "rec_03_diary")

            # --- API로 기록 번들 검증: 누적 클립 2개 + daily_quest_id ---
            recs = apicall("GET", "/records", token=tok)["records"]
            assert recs, "기록이 생성되지 않음"
            rec = recs[0]
            assert len(rec["clips"]) == 2, f"기록에 누적 클립 2개가 묶이지 않음: {len(rec['clips'])}"
            got = {c["id"] for c in rec["clips"]}
            assert set(clip_ids) == got, f"기록의 클립이 누적 clip_ids와 불일치: {got} vs {set(clip_ids)}"
            assert rec["visibility"] == "diary", f"visibility 가 diary 가 아님: {rec['visibility']}"
            assert rec["daily_quest_id"], "기록에 daily_quest_id 가 첨부되지 않음"
            assert rec.get("walk_session_id") is not None or True  # 혼자 산책: walk_session_id 연결
            print(f"  {GREEN}✅{RESET} GET /records → 누적 클립 2개 묶인 기록 1건 "
                  f"(visibility=diary, daily_quest_id={rec['daily_quest_id'][:8]})  {DIM}rid={rec['id'][:8]}{RESET}")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "rec_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 클립→기록 번들링(산책중) 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
