#!/usr/bin/env python3
"""Headless smoke for v2-W1 — 홈 idle 지도 (#/home).

v2 재설계로 산책/매칭은 W2(#/walk)·W3(#/matching)로 분리됐다. 이 러너는 **홈 idle 지도**의
DoD(11_W1_home_map.md §7)만 검증한다. (산책중/매칭중 상세는 W2/W3 러너 소관 — 여기선 진입만 단언.)

흐름(데모 컨텍스트):
  - A(초코아빠)를 API로 셋업(guest+pet) 후 /demo/setup으로 목업 강아지(망고) 1마리 확보.
  - 브라우저에 auth + blip_demo_context 주입 → #/home.
  - (1) 지도 + 본인 빨간 마커(.me-marker.red)가 화면 중앙 렌더 + 콘솔 에러 0.
  - (2) 주변 마커가 강아지 캐릭터 핀(.dog-pin)만 — 이름/거리 메타 칩 없음.
  - (3) 타 강아지 탭 → centerModal → [같이 산책하기] → 본인 walk session 보장(POST /walks/start)
        → POST /match-requests(2xx) → #/matching/:id 진입.
  - (4) 본인 마커 탭 → [산책하기] → walk session 생성(POST /walks/start) → #/walk 진입.
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
    api_calls = []  # (method, path, status)

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")
        steps.append(msg)

    def calls(method, path):
        return [c for c in api_calls if c[0] == method and c[1] == path]

    def settle_modal(page):
        # 스크림(.center-modal)은 opacity 0→1 CSS 트랜지션(240ms), 카드(.center-modal-card)는
        # springMotion이 opacity를 1로 올린다. 부모 opacity는 곱해지므로 둘 다 ~1이어야 보인다.
        page.wait_for_function(
            "() => { const s=document.querySelector('.center-modal');"
            " const c=document.querySelector('.center-modal-card');"
            " return s && c && parseFloat(getComputedStyle(s).opacity) >= 0.99"
            " && parseFloat(getComputedStyle(c).opacity) >= 0.99; }",
            timeout=3000,
        )

    # --- API 픽스처: A + 데모 목업(망고) ---
    a_uid, a_tok, a_pet = make_user("초코아빠", "초코", "푸들")
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
    print(f"{DIM}  fixture: A={a_uid[:8]} mock_ws={mock_ws[:8]} @ {demo_ctx['lat']},{demo_ctx['lng']}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896}, locale="ko-KR",
            geolocation={"latitude": demo_ctx["lat"], "longitude": demo_ctx["lng"]}, permissions=["geolocation"],
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)

        def on_resp(r):
            try:
                if "/api/" in r.url and r.request.method in ("POST", "PATCH", "DELETE"):
                    api_calls.append((r.request.method, r.url.split("/api", 1)[1].split("?")[0], r.status))
            except Exception:
                pass
        page.on("response", on_resp)

        try:
            # A 세션 + 데모 컨텍스트 주입
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p,demo]) => {
                  localStorage.setItem('auth_token',t);
                  localStorage.setItem('user_id',u);
                  localStorage.setItem('pet_id',p);
                  localStorage.setItem('blip_demo_context', JSON.stringify(demo));
                  localStorage.removeItem('active_walk_session_id');
                  localStorage.removeItem('blip_walk_clips');
                }""",
                [a_tok, a_uid, a_pet, demo_ctx],
            )

            # ---- (1) #/home: 지도 + 본인 빨간 마커(중앙) ----
            page.goto(BASE + "/#/home", wait_until="networkidle")
            page.wait_for_function("location.hash.startsWith('#/home')", timeout=8000)
            page.wait_for_selector(".map-screen", timeout=8000)
            page.wait_for_selector("#me-marker, #walk-fallback", timeout=10000, state="attached")
            if not page.query_selector("#me-marker"):
                raise AssertionError("WebGL 지도/본인 마커가 렌더되지 않음(fallback 모드) — 빨강 중앙 마커 단언 불가")
            # 빨강 변형 + 화면 중앙
            cls = page.get_attribute("#me-marker", "class") or ""
            assert "red" in cls.split(), f"본인 마커가 빨강 변형(.red)이 아님: class={cls!r}"
            geom = page.evaluate(
                """() => {
                  const m = document.querySelector('#me-marker').getBoundingClientRect();
                  const s = document.querySelector('.map-screen').getBoundingClientRect();
                  return { mcx:m.x+m.width/2, mcy:m.y+m.height/2,
                           scx:s.x+s.width/2, scy:s.y+s.height/2,
                           sw:s.width, sh:s.height,
                           top:s.top, bottom:s.bottom, vp:window.innerHeight,
                           docScroll: document.scrollingElement.scrollHeight - document.scrollingElement.clientHeight };
                }"""
            )
            dx, dy = abs(geom["mcx"] - geom["scx"]), abs(geom["mcy"] - geom["scy"])
            assert dx < 70 and dy < 90, f"본인 마커가 지도 중앙이 아님: dx={dx:.0f} dy={dy:.0f}"
            assert geom["top"] >= -1 and geom["bottom"] <= geom["vp"] + 1, f"지도가 viewport 밖: {geom}"
            assert geom["docScroll"] <= 1, f"문서 스크롤이 생김: {geom['docScroll']}"
            ok(page, f"#/home 지도 + 본인 빨강 마커 중앙 렌더 (dx={dx:.0f},dy={dy:.0f}, 한 화면)", "home_01_map_red_center")

            # ---- (2) 주변 마커 = 강아지 캐릭터 핀만(메타 칩 없음) ----
            page.wait_for_selector(f'.dog-pin[data-ws="{mock_ws}"]', timeout=12000)
            audit = page.evaluate(
                """(ws) => {
                  const pin = document.querySelector(`.dog-pin[data-ws="${ws}"]`);
                  const anyMeta = document.querySelectorAll('.dog-pin .meta, .dog-pin .nm, .dog-pin .ds').length;
                  // 보이는 텍스트만 측정: 캐릭터 SVG(접근성 <title> 포함)를 제거한 뒤 남는 텍스트.
                  const clone = pin.cloneNode(true);
                  clone.querySelectorAll('svg').forEach((s) => s.remove());
                  return {
                    pins: document.querySelectorAll('.dog-pin').length,
                    hasChar: !!pin.querySelector('svg'),
                    visibleText: clone.textContent.trim(),
                    anyMeta,
                  };
                }""",
                mock_ws,
            )
            assert audit["hasChar"], "강아지 핀에 캐릭터(svg)가 없음"
            assert audit["anyMeta"] == 0, f"강아지 핀에 이름/거리 메타 칩이 남아 있음({audit['anyMeta']}개)"
            assert audit["visibleText"] == "", f"강아지 핀에 보이는 텍스트(이름/거리)가 노출됨: {audit['visibleText']!r}"
            ok(page, f"주변 마커 = 강아지 캐릭터 핀만 ({audit['pins']}개, 메타 0)", "home_02_dog_pins")

            # ---- (3) 타 강아지 탭 → centerModal → [같이 산책하기] → 매칭 ----
            page.eval_on_selector(f'.dog-pin[data-ws="{mock_ws}"]', "e => e.click()")
            page.wait_for_selector("#cm-profile", timeout=5000)
            page.wait_for_selector("#peer-walk-together", timeout=5000)
            settle_modal(page)
            ok(page, "타 강아지 탭 → centerModal(프로필 + [같이 산책하기])", "home_03a_peer_modal")
            page.eval_on_selector("#peer-walk-together", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/matching/')", timeout=8000)
            ws_starts = calls("POST", "/walks/start")
            mreqs = calls("POST", "/match-requests")
            assert ws_starts and ws_starts[-1][2] in (200, 201), f"본인 walk session 보장(POST /walks/start) 누락/실패: {ws_starts}"
            assert mreqs and mreqs[-1][2] in (200, 201), f"POST /match-requests 2xx 아님: {mreqs}"
            match_id = page.evaluate("location.hash.split('/matching/')[1]")
            ok(page, f"[같이 산책하기] → walks/start({ws_starts[-1][2]}) + match-requests({mreqs[-1][2]}) → #/matching/{match_id[:8]}", "home_03b_matching")

            # ---- (4) 본인 마커 탭 → [산책하기] → 산책 세션 생성 → #/walk ----
            page.evaluate("() => localStorage.removeItem('active_walk_session_id')")  # 새 산책 세션 생성 확인용
            before = len(calls("POST", "/walks/start"))
            page.goto(BASE + "/#/home", wait_until="networkidle")
            page.wait_for_selector("#me-marker", timeout=10000)
            page.eval_on_selector("#me-marker", "e => e.click()")
            page.wait_for_selector("#mine-start-walk", timeout=5000)
            settle_modal(page)
            ok(page, "본인 마커 탭 → centerModal([산책하기])", "home_04a_mine_modal")
            page.eval_on_selector("#mine-start-walk", "e => e.click()")
            page.wait_for_function("location.hash.startsWith('#/walk')", timeout=8000)
            after = calls("POST", "/walks/start")
            assert len(after) > before and after[-1][2] in (200, 201), f"산책 세션 생성(POST /walks/start) 누락/실패: {after}"
            walk_id = page.evaluate("() => localStorage.getItem('active_walk_session_id')")
            assert walk_id, "산책 세션 id가 store에 저장되지 않음"
            ok(page, f"[산책하기] → walks/start({after[-1][2]}) 세션 생성({walk_id[:8]}) → #/walk", "home_04b_walk")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "home_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')}{RESET}")
            print(f"  {DIM}api_calls={api_calls}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W1 홈 지도 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
