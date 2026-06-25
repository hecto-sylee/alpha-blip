#!/usr/bin/env python3
"""Headless smoke for W4 — 가로 카메라 촬영 (docs/v2_redesign/14_W4_camera.md).

촬영 부분(구 FE2 기록 에디터)을 v2 W4 카메라 플로우로 교체.
DoD:
  (1) #/camera?quest=테스트 진입 → 가로(landscape) 레이아웃 + 상단 퀘스트 텍스트 표시, 콘솔 0.
  (2) #/camera (쿼리 없음) → 퀘스트 텍스트 미표시.
  (3) 촬영 버튼 → POST /clips/upload 201 → store.walkClips 길이 증가 → #/walk 복귀.
  (4) 퀘스트 진입 촬영 시 업로드 폼(multipart)에 mission_id 포함.
콘솔 에러 0(외부 타일/WebGL 잡음 제외), 각 단계 스크린샷 저장.

카메라: --use-fake-device-for-media-stream --use-fake-ui-for-media-stream + camera/microphone 권한 grant.
가로 레이아웃 검증을 위해 landscape 뷰포트(896x414) 사용. #/walk 복귀가 콘솔 깨끗하도록 geolocation도 grant.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon", "geolocation")

MISSION_ID = "m-w4-smoke-1"  # 임의 미션 id — 업로드 폼 태깅 검증용 (BE는 free-form 허용)


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    uploads = []        # (status, url)

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    u = apicall("POST", "/auth/guest", body={"nickname": "촬영이"})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": "콩", "breed": "말티즈", "size": "small", "personality_tags": ["온순함"]})
    print(f"{DIM}  fixture: user={u['user_id'][:8]} pet={p['pet_id'][:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-fake-device-for-media-stream",
                  "--use-fake-ui-for-media-stream", "--use-gl=angle",
                  "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        # 가로(landscape) 뷰포트 — 전체화면 카메라가 실제 가로 프레임이 되도록.
        ctx = browser.new_context(
            viewport={"width": 896, "height": 414}, locale="ko-KR",
            geolocation={"latitude": 37.5665, "longitude": 126.9780}, permissions=[],
        )
        ctx.grant_permissions(["camera", "microphone", "geolocation"])
        # 업로드 폼 필드 캡처: FormData.append 를 감싸 [name, value(문자열만)] 기록 → DoD(4) 직접 단언.
        ctx.add_init_script(
            """
            window.__clipFormFields = [];
            const _ap = FormData.prototype.append;
            FormData.prototype.append = function(name, value, ...rest) {
              try { window.__clipFormFields.push([name, (typeof value === 'string') ? value : '[blob]']); } catch (e) {}
              return _ap.call(this, name, value, ...rest);
            };
            """
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)
        page.on("response", lambda r: uploads.append((r.status, r.url))
                if "/api/clips/upload" in r.url else None)

        try:
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => {
                    localStorage.setItem('auth_token',t);
                    localStorage.setItem('user_id',u);
                    localStorage.setItem('pet_id',p);
                    localStorage.removeItem('blip_walk_clips');  // 클립 누적 초기화
                }""",
                [u["auth_token"], u["user_id"], p["pet_id"]],
            )

            # --- DoD (1): 퀘스트 진입 → 가로 레이아웃 + 상단 퀘스트 텍스트 ---
            page.goto(BASE + f"/#/camera?quest=테스트&mission={MISSION_ID}", wait_until="domcontentloaded")
            page.wait_for_selector("#camera-screen.landscape", timeout=8000)
            page.wait_for_selector("#cam-video", timeout=8000)  # 카메라 스트림 활성
            box = page.eval_on_selector("#camera-screen", "el => el.getBoundingClientRect()")
            assert box["width"] > box["height"], f"가로 레이아웃이 아님: {box['width']}x{box['height']}"
            assert page.query_selector("#cam-quest"), "상단 퀘스트 박스가 없음"
            assert page.is_visible("#cam-quest"), "퀘스트 박스가 보이지 않음"
            qtext = page.inner_text("#cam-quest")
            assert "테스트" in qtext, f"상단 퀘스트 텍스트가 표시되지 않음: {qtext!r}"
            ok(page, f"#/camera?quest= 진입 → 가로 {int(box['width'])}x{int(box['height'])} + 퀘스트 '{qtext.strip()}'", "w4_01_quest")

            # --- DoD (3)+(4): 촬영 → upload 201 → walkClips 증가 → #/walk 복귀, 폼에 mission_id ---
            before = page.evaluate("JSON.parse(localStorage.getItem('blip_walk_clips')||'[]').length")
            page.click("#cam-shoot")
            page.wait_for_function("location.hash.startsWith('#/walk')", timeout=15000)
            assert uploads, "clips/upload 응답이 관측되지 않음"
            up_status = uploads[-1][0]
            assert up_status == 201, f"clip 업로드 상태가 201이 아님: {up_status}"
            after = page.evaluate("JSON.parse(localStorage.getItem('blip_walk_clips')||'[]').length")
            assert after == before + 1, f"store.walkClips 길이가 증가하지 않음: {before} → {after}"
            last = page.evaluate("JSON.parse(localStorage.getItem('blip_walk_clips')||'[]').slice(-1)[0]")
            assert last and last.get("mission_id") == MISSION_ID, f"누적 클립 mission_id 불일치: {last}"
            # DoD (4): 업로드 폼에 mission_id 필드 포함 단언 (FormData.append 캡처)
            fields = page.evaluate("window.__clipFormFields || []")
            names = [f[0] for f in fields]
            assert "file" in names and "duration_ms" in names and "order" in names, f"업로드 폼 필수 필드 누락: {names}"
            assert ["mission_id", MISSION_ID] in [list(f) for f in fields], f"업로드 폼에 mission_id가 없음: {fields}"
            # 서버 라운드트립 — 업로드된 클립이 서버에 mission_id로 저장됐는지 확인(end-to-end).
            clip_id = last["clip_id"]
            rec = apicall("POST", "/records", token=u["auth_token"], body={"clip_ids": [clip_id]})
            detail = apicall("GET", f"/records/{rec['record_id']}", token=u["auth_token"])
            srv_mid = next((c.get("mission_id") for c in detail.get("clips", []) if c.get("id") == clip_id), None)
            assert srv_mid == MISSION_ID, f"서버 저장 mission_id 불일치: {srv_mid}"
            ok(page, f"촬영 → /clips/upload {up_status} → walkClips {before}→{after} → #/walk 복귀 (폼·서버 mission_id={srv_mid})", "w4_02_shoot")

            # --- DoD (2): 쿼리 없는 진입 → 퀘스트 텍스트 미표시 ---
            page.goto(BASE + "/#/camera", wait_until="domcontentloaded")
            page.wait_for_selector("#camera-screen.landscape", timeout=8000)
            page.wait_for_selector("#cam-video", timeout=8000)
            assert page.query_selector("#cam-quest") is None, "쿼리 없이 진입했는데 퀘스트 박스가 표시됨"
            ok(page, "#/camera (쿼리 없음) → 퀘스트 텍스트 미표시", "w4_03_noquest")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "w4_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')} uploads={uploads}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W4 카메라 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
