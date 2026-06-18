#!/usr/bin/env python3
"""Headless smoke for FE1 — 산책 지도 · 근처 · 매칭 (SCR-10~14).

흐름:
  - B(보리엄마)를 API로 셋업: guest+pet+walk+근처 위치.
  - A(초코아빠)를 API로 셋업 후 브라우저 세션에 주입(geolocation 주입+권한 grant).
  - A: 홈에서 [산책 시작] 클릭 → 지도/내 위치(또는 fallback) 렌더 확인.
  - A 화면의 nearby 폴링이 B 마커를 띄우는지 단언 → 마커 탭 → 바텀시트 노출.
  - [같이 산책하기] → 요청 전송(SCR-13) → B가 API로 accept →
    A 화면이 세션(SCR-14)으로 전환 → 동행 타이머 → [산책 종료].
콘솔 에러 0(외부 리소스/WebGL/타일 잡음 제외), 각 단계 스크린샷 저장.
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


def make_user(nick, petname, breed):
    u = apicall("POST", "/auth/guest", body={"nickname": nick})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": petname, "breed": breed, "size": "small", "personality_tags": ["활발함"]})
    return u["user_id"], u["auth_token"], p["pet_id"]


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    steps = []

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")
        steps.append(msg)

    # --- API 픽스처 ---
    a_uid, a_tok, a_pet = make_user("초코아빠", "초코", "푸들")
    b_uid, b_tok, b_pet = make_user("보리엄마", "보리", "비숑")
    # B를 화면 중앙 아래(남쪽)에 배치 → 상단 상태바/헤더와 겹치지 않게
    b_walk = apicall("POST", "/walks/start", token=b_tok,
                     body={"pet_id": b_pet, "latitude": LAT - 0.0006, "longitude": LNG - 0.0003})
    b_ws = b_walk["walk_session_id"]
    print(f"{DIM}  fixture: A={a_uid[:8]} B={b_uid[:8]} B_walk={b_ws[:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896}, locale="ko-KR",
            geolocation={"latitude": LAT, "longitude": LNG}, permissions=["geolocation"],
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)

        try:
            # A 세션 주입
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
                [a_tok, a_uid, a_pet],
            )
            page.goto(BASE + "/#/home", wait_until="networkidle")
            page.wait_for_selector("#start-walk")
            ok(page, "A 홈 진입 (산책 시작 CTA 노출)", "f1_01_home")

            # 산책 시작
            page.click("#start-walk")
            page.wait_for_function("location.hash.startsWith('#/walk')", timeout=8000)
            page.wait_for_selector(".map-screen", timeout=8000)
            # 지도(me-marker) 또는 fallback 중 하나는 떠야 함
            page.wait_for_selector("#me-marker, #walk-fallback", timeout=8000, state="attached")
            page.wait_for_selector("#walk-coord", timeout=8000)
            fit = page.evaluate(
                """() => {
                  const r = document.querySelector('.map-screen').getBoundingClientRect();
                  const doc = document.scrollingElement;
                  return {
                    top: r.top,
                    bottom: r.bottom,
                    height: r.height,
                    viewport: window.innerHeight,
                    scrollHeight: doc.scrollHeight,
                    clientHeight: doc.clientHeight
                  };
                }"""
            )
            assert fit["top"] >= -1 and fit["bottom"] <= fit["viewport"] + 1, f"지도 화면이 viewport를 벗어남: {fit}"
            assert fit["scrollHeight"] <= fit["clientHeight"] + 1, f"산책 화면에 문서 스크롤이 생김: {fit}"
            mode = "지도(WebGL)" if page.query_selector("#me-marker") else "목록 fallback"
            ok(page, f"산책 시작 → SCR-11 지도 렌더 + 내 위치 + 한 화면 높이 ({mode})", "f1_02_walk")

            # nearby 폴링이 B 마커를 띄움
            page.wait_for_selector(f'[data-ws="{b_ws}"]', timeout=15000)
            assert "보리" in page.inner_text(f'[data-ws="{b_ws}"]'), "B 마커에 펫 이름이 없음"
            ok(page, "nearby 폴링 → B(보리) 입체 칩 마커 노출", "f1_03_nearby")

            # 마커 탭 → 미리보기 시트 (겹친 마커/상단바 간섭 없이 해당 마커의 핸들러 직접 실행)
            page.eval_on_selector(f'[data-ws="{b_ws}"]', "e => e.click()")
            page.wait_for_selector("#preview-sheet", timeout=5000)
            page.wait_for_selector("#send-request")
            ok(page, "마커 탭 → SCR-12 바텀시트(상대 프로필) 노출", "f1_04_preview")

            # 같이 산책하기 → 요청 대기
            page.click("#send-request")
            page.wait_for_function("location.hash.startsWith('#/request/')", timeout=8000)
            page.wait_for_selector("#request-wait")
            req_id = page.evaluate("location.hash.split('/request/')[1]")
            ok(page, f"요청 전송 → SCR-13 대기 화면 (req={req_id[:8]})", "f1_05_request")

            # B가 수락 (API)
            sess = apicall("PATCH", f"/match-requests/{req_id}/accept", token=b_tok)
            sid = sess["match_session_id"]

            # A 폴링이 수락 감지 → 세션 화면
            page.wait_for_function("location.hash.startsWith('#/session/')", timeout=8000)
            page.wait_for_selector("#session-timer", timeout=5000)
            assert "보리엄마" in page.inner_text(".session-hud"), "세션에 파트너 닉네임 없음"
            # 동행 타이머가 0부터 시작(서버 UTC 시각 오해석으로 540:00 등 큰 값이면 실패)
            tmm = int(page.inner_text("#session-timer").split(":")[0])
            assert tmm < 5, f"동행 타이머 시작값 이상: {page.inner_text('#session-timer')}"
            ok(page, f"B 수락 → SCR-14 매칭 세션 전환(파트너·동행 타이머 {page.inner_text('#session-timer')})", "f1_06_session")

            # 산책 종료 → 기록 에디터(SCR-20)로 (spec: 종료 → SCR-20)
            page.click("#end-session")
            page.wait_for_function("location.hash.startsWith('#/record')", timeout=8000)
            ok(page, "산책 종료 → 로그 저장 후 기록 에디터(SCR-20) 진입", "f1_07_end")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "f1_FAIL.png"))
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

    print(f"\n{GREEN}🎉 FE1 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
