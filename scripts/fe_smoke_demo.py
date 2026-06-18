#!/usr/bin/env python3
"""Headless smoke for R4 demo mode — one-device full flow.

Flow:
  - API fixture: guest + pet.
  - UI: home #demo-setup -> /api/demo/setup 200 -> #/walk.
  - Nearby mock marker -> preview -> request -> auto-accepted match session.
  - End session -> record editor -> fake 2s clip -> room visibility preset -> save.
  - Room tab feed shows the saved demo room record.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

LAT, LNG = 37.5009, 127.0398
GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
IGNORE = (
    "maplibre",
    "webgl",
    "tile.openstreetmap",
    "unpkg.com",
    "failed to load resource",
    "err_",
    "net::",
    "favicon",
)


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def make_user(nick, petname, breed):
    u = apicall("POST", "/auth/guest", body={"nickname": nick})
    p = apicall(
        "POST",
        "/pets",
        token=u["auth_token"],
        body={"name": petname, "breed": breed, "size": "small", "personality_tags": ["활발함"]},
    )
    return u, p["pet_id"]


def inject(page, user, pet_id):
    page.goto(BASE, wait_until="domcontentloaded")
    page.evaluate(
        """([t,u,p]) => {
          localStorage.setItem('auth_token', t);
          localStorage.setItem('user_id', u);
          localStorage.setItem('pet_id', p);
        }""",
        [user["auth_token"], user["user_id"], pet_id],
    )


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    uploads = []
    record_text = f"데모 방 공유 로그 {int(time.time())}"

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    user, pet_id = make_user("데모러", "초코", "푸들")
    print(f"{DIM}  fixture: user={user['user_id'][:8]} pet={pet_id[:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
            ],
        )
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896},
            locale="ko-KR",
            geolocation={"latitude": LAT, "longitude": LNG},
            permissions=["geolocation", "camera", "microphone"],
        )
        page = ctx.new_page()
        page.on(
            "console",
            lambda m: errors.append(f"{m.type}: {m.text}")
            if m.type == "error" and not any(k in m.text.lower() for k in IGNORE)
            else None,
        )
        page.on(
            "pageerror",
            lambda e: errors.append(f"pageerror: {e}") if not any(k in str(e).lower() for k in IGNORE) else None,
        )
        page.on("response", lambda r: uploads.append((r.status, r.url)) if "/api/clips/upload" in r.url else None)

        try:
            inject(page, user, pet_id)
            page.goto(BASE + "/#/home", wait_until="networkidle")
            page.wait_for_selector("#demo-setup", timeout=8000)
            ok(page, "게스트/펫 준비 → 홈 #demo-setup 노출", "demo_01_home")

            with page.expect_response(lambda r: "/api/demo/setup" in r.url and r.request.method == "POST") as resp_info:
                page.click("#demo-setup")
            setup_res = resp_info.value
            assert setup_res.status == 200, f"/api/demo/setup status={setup_res.status}"
            demo = setup_res.json()
            mock_ws = demo["mock_walk_session_id"]
            room_id = demo["room_id"]
            assert demo["location"]["label"] == "강남 테헤란로 큰길타워", "demo location label mismatch"

            page.wait_for_function("location.hash.startsWith('#/walk')", timeout=8000)
            page.wait_for_selector(".map-screen", timeout=8000)
            page.wait_for_selector(f'.demo-peer-marker[data-ws="{mock_ws}"]', timeout=5000)
            marker_box = page.locator(f'.demo-peer-marker[data-ws="{mock_ws}"]').bounding_box()
            assert marker_box, "데모 상대 UI 핀이 화면에 렌더링되지 않음"
            assert marker_box["x"] >= 0 and marker_box["y"] >= 0, f"데모 상대 UI 핀이 viewport 밖에 있음: {marker_box}"
            ok(page, f"/api/demo/setup 200 → #/walk 진입(mock_ws={mock_ws[:8]})", "demo_02_walk")

            page.wait_for_selector(f'[data-ws="{mock_ws}"]', timeout=15000)
            assert "망고" in page.inner_text(f'[data-ws="{mock_ws}"]'), "목업 마커에 펫 이름이 없음"
            ok(page, "nearby 폴링 → 데모 목업 마커 노출", "demo_03_marker")

            page.eval_on_selector(f'[data-ws="{mock_ws}"]', "e => e.click()")
            page.wait_for_selector("#preview-sheet", timeout=5000)
            page.wait_for_selector("#send-request")
            ok(page, "목업 마커 탭 → 바텀시트 → 같이 산책하기 CTA", "demo_04_preview")

            page.click("#send-request")
            page.wait_for_function(
                "location.hash.startsWith('#/request/') || location.hash.startsWith('#/session/')",
                timeout=8000,
            )
            current_hash = page.evaluate("location.hash")
            if current_hash.startswith("#/request/"):
                try:
                    page.wait_for_selector("#request-wait", timeout=1000)
                except Exception:
                    pass
                req_id = current_hash.split("/request/", 1)[1]
                ok(page, f"매칭 요청 전송 → 대기 화면(req={req_id[:8]})", "demo_05_request")
            else:
                ok(page, "매칭 요청 전송 → 목업 자동 수락으로 세션 즉시 전환", "demo_05_request")

            page.wait_for_function("location.hash.startsWith('#/session/')", timeout=10000)
            page.wait_for_selector("#session-timer", timeout=5000)
            assert "테헤란로 망고" in page.inner_text(".session-hud"), "자동 수락 세션 파트너가 목업 유저가 아님"
            ok(page, "목업 receiver 자동 수락 → SCR-14 매칭 세션 전환", "demo_06_session")

            page.click("#end-session")
            page.wait_for_function("location.hash.startsWith('#/record')", timeout=8000)
            page.wait_for_selector("#cam-video", timeout=10000)
            ok(page, "산책 종료 → 기록 에디터 + 가짜 카메라 활성", "demo_07_record")

            assert "sel" in (page.get_attribute("#vis-seg .opt[data-val='room']", "class") or ""), "방 공유 프리셋 아님"
            assert page.eval_on_selector("#room-select", "e => e.value") == room_id, "데모 방이 선택되지 않음"
            page.click("#rec-ring")
            page.wait_for_selector("[data-clip-id]", timeout=12000)
            assert uploads and uploads[-1][0] == 201, f"clip upload status={uploads[-1][0] if uploads else 'missing'}"
            page.fill("#record-text", record_text)
            ok(page, "2초 클립 녹화 201 + 방 공유 프리셋 확인", "demo_08_clip")

            page.click("#save-record")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=10000)
            ok(page, "방 공유 기록 저장 → 다이어리 이동", "demo_09_saved")

            page.goto(BASE + "/#/rooms", wait_until="networkidle")
            page.wait_for_selector("#room-feed [data-rid]", timeout=10000)
            assert record_text in page.inner_text("#room-feed"), "방 탭 로그 피드에 방금 저장한 기록이 없음"
            assert page.query_selector('#tabbar a[data-tab="room"].active'), "방 탭 active가 아님"
            ok(page, "방 탭 로그 피드에 데모 기록 노출", "demo_10_room_feed")

            page.click(f'#room-feed [data-room-id="{room_id}"]')
            page.wait_for_function("location.hash.startsWith('#/room/')", timeout=8000)
            page.wait_for_selector("#room-timeline [data-rid]", timeout=8000)
            assert record_text in page.inner_text("#room-timeline"), "데모 방 상세 타임라인에 기록이 없음"
            ok(page, "데모 방 상세 타임라인에도 기록 노출", "demo_11_room_detail")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "demo_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            try:
                print(f"  {DIM}hash={page.evaluate('location.hash')} uploads={uploads}{RESET}")
            except Exception:
                pass
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 R4 데모 모드 헤드리스 스모크 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
