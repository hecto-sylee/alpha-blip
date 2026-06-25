#!/usr/bin/env python3
"""Headless smoke for v2 W3 — 산책 매칭중(#/matching/:id) + 발자국 트래킹.

v2 재설계로 홈(W1)·산책중(W2)이 분리됐고, 이 러너의 "매칭 부분"을 W3 화면 기준으로
갱신한다. W1/W2가 아직 스텁인 워크트리에서도 W3(matching.js)를 단독 검증할 수 있도록,
W1의 "같이 산책하기" 진입은 API로 match-request 를 만든 뒤 `#/matching/:id` 로 직접
진입해 시뮬레이션한다(데모 목업은 matches.py 가 자동 수락).

검증(13_W3_matching.md DoD):
  (1) 데모 매칭 진입 → 본인(빨강)+상대(강아지 핀) **둘만** 표시, 주변 마커 없음, 콘솔 0.
  (2) 폴링으로 발자국 마커(.w3-foot)가 누적(틱마다 증가).
  (3) 자동수락 세션확정 → [매칭 성공] → `#/walk?match=...` 진입.
  (4) 거절 경로 → 토스트 + `#/home` 복귀.
각 단계 스크린샷 저장, 콘솔 에러 0(외부 타일/WebGL 잡음 제외).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:9013")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)
# 데모 원점(강남 테헤란로 큰길타워) — 거절 경로의 geolocation 주입에도 사용.
LAT, LNG = 37.5009, 127.0398

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
    # 데모 셋업: A 전용 목업(망고) + 목업 active walk session (자동수락 대상)
    demo = apicall("POST", "/demo/setup", token=a_tok, body={})
    mock_ws = demo["mock_walk_session_id"]
    demo_ctx = {
        "lat": demo["location"]["latitude"],
        "lng": demo["location"]["longitude"],
        "label": demo["location"]["label"],
        "mockLat": demo["mock_location"]["latitude"],
        "mockLng": demo["mock_location"]["longitude"],
        "mockSessionId": demo["mock_walk_session_id"],
        "mockPet": demo["mock_pet"],
        "roomId": demo["room_id"],
        "roomJoinCode": demo["room_join_code"],
    }
    # 거절 경로용 실제 상대 B
    b_uid, b_tok, b_pet = make_user("보리엄마", "보리", "비숑")
    b_walk = apicall("POST", "/walks/start", token=b_tok,
                     body={"pet_id": b_pet, "latitude": LAT - 0.0006, "longitude": LNG - 0.0003})
    b_ws = b_walk["walk_session_id"]
    print(f"{DIM}  fixture: A={a_uid[:8]} mock_ws={mock_ws[:8]} B={b_uid[:8]} B_walk={b_ws[:8]}{RESET}")

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
            # A 세션 + 데모 컨텍스트 주입 (W1 home_map 이 store.demo 를 세팅하는 것을 대체)
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p,demo]) => {
                  localStorage.setItem('auth_token',t);
                  localStorage.setItem('user_id',u);
                  localStorage.setItem('pet_id',p);
                  localStorage.setItem('blip_demo_context', JSON.stringify(demo));
                }""",
                [a_tok, a_uid, a_pet, demo_ctx],
            )

            # === (1)(2)(3) 데모 매칭 경로 — 자동수락 ===
            # W1: 타 강아지 [같이 산책하기] 에 해당 → API 로 목업에 요청(자동 accept).
            req = apicall("POST", "/match-requests", token=a_tok, body={"receiver_walk_session_id": mock_ws})
            req_id = req["match_request_id"]
            page.goto(BASE + f"/#/matching/{req_id}", wait_until="networkidle")
            page.wait_for_function("location.hash.startsWith('#/matching/')", timeout=8000)
            page.wait_for_selector("#w3-me", timeout=8000)
            # 자동수락 → 상대 마커 확보(세션 확정)
            page.wait_for_selector("#w3-partner", timeout=8000)

            # (1) 본인+상대 둘만, 주변 nearby 마커(.dog-marker) 없음
            counts = page.evaluate(
                """() => ({
                  me: document.querySelectorAll('#w3-me').length,
                  partner: document.querySelectorAll('#w3-partner').length,
                  nearby: document.querySelectorAll('.dog-marker').length,
                })"""
            )
            assert counts["me"] == 1, f"본인 마커 개수 이상: {counts}"
            assert counts["partner"] == 1, f"상대 마커 개수 이상: {counts}"
            assert counts["nearby"] == 0, f"주변 마커가 존재함(매칭중엔 둘만): {counts}"
            ok(page, f"데모 매칭 진입 → 본인+상대 둘만 표시(주변 마커 0) {counts}", "w3_01_only_two")

            # (2) 발자국 누적 — 폴링 틱마다 .w3-foot 증가
            page.wait_for_selector(".w3-foot", timeout=8000)
            c1 = page.evaluate("() => document.querySelectorAll('.w3-foot').length")
            page.wait_for_timeout(4200)  # 폴링 3틱 이상 경과
            c2 = page.evaluate("() => document.querySelectorAll('.w3-foot').length")
            assert c2 > c1, f"발자국이 누적되지 않음: {c1} → {c2}"
            ok(page, f"발자국 트래킹 누적: {c1} → {c2} 개", "w3_02_footprints")

            # (3) 세션확정 → [매칭 성공] → #/walk?match=...
            page.wait_for_selector("#w3-cta:not([disabled])", timeout=8000)
            assert page.inner_text("#w3-cta").strip() == "매칭 성공", "CTA 라벨이 '매칭 성공'이 아님"
            page.click("#w3-cta")
            page.wait_for_function(
                "location.hash.startsWith('#/walk') && location.hash.includes('match=')", timeout=8000
            )
            walk_hash = page.evaluate("location.hash")
            assert "match=" in walk_hash and len(walk_hash.split("match=")[1]) > 0, f"match 세션 누락: {walk_hash}"
            ok(page, f"매칭 성공 → 산책중 인계 ({walk_hash})", "w3_03_success_to_walk")

            # === (4) 거절 경로 — 토스트 + #/home ===
            # 데모 컨텍스트 제거(실제 상대 B 와 일반 매칭) 후 보류 요청 생성
            page.evaluate("() => localStorage.removeItem('blip_demo_context')")
            req2 = apicall("POST", "/match-requests", token=a_tok, body={"receiver_walk_session_id": b_ws})
            rid2 = req2["match_request_id"]
            page.goto(BASE + f"/#/matching/{rid2}", wait_until="networkidle")
            page.wait_for_selector("#w3-me", timeout=8000)
            # 보류 상태이므로 상대 마커는 아직 없음
            assert page.query_selector("#w3-partner") is None, "보류 상태인데 상대 마커가 떴음"
            # B 가 거절 → 폴링이 감지 → 토스트 + #/home
            apicall("PATCH", f"/match-requests/{rid2}/reject", token=b_tok)
            page.wait_for_function("location.hash.startsWith('#/home')", timeout=10000)
            toasted = page.evaluate(
                "() => !!Array.from(document.querySelectorAll('.toast')).find(t => /거절/.test(t.textContent))"
            )
            assert toasted, "거절 토스트가 보이지 않음"
            ok(page, "거절 경로 → 토스트 + #/home 복귀", "w3_04_reject_home")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "w3_FAIL.png"))
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

    print(f"\n{GREEN}🎉 W3 매칭 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
