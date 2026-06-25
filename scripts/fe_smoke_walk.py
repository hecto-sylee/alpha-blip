#!/usr/bin/env python3
"""Headless smoke for v2 산책 통합 — 홈(W1) · 산책중(W2) · 매칭(W3).

세 화면(home_map/walking/matching)이 한 통합 브랜치에 모였으므로 한 러너에서
세 플로우를 차례로(각자 격리된 브라우저 컨텍스트로) 검증한다.
  flow_home     (11_W1 §7): #/home 빨강 중앙 마커 · 강아지핀(메타 0) · centerModal → 매칭/산책
  flow_walk     (12_W2 §8): #/walk 투명 퀘스트박스(≤2) · 촬영/종료 · 누적클립 → 기록(#/diary)
  flow_matching (13_W3 §7): #/matching 본인+상대 둘만 · 발자국 누적 · 매칭성공/거절
콘솔 에러 0(외부 타일/WebGL/CDN 잡음 제외), 각 단계 스크린샷 저장.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:9010")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)
LAT, LNG = 37.5009, 127.0398  # 데모 원점(강남 테헤란로) — 매칭 거절 경로 geolocation

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

# 외부 리소스(타일/CDN)·WebGL 잡음은 우리 코드 버그가 아니므로 제외
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon")

LAUNCH_ARGS = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]


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
    """카메라(W4) 클립 업로드를 API로 모킹 — 실제 소유 clip_id 확보(POST /records 201 위해)."""
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


def demo_fixture(nick, petname, breed):
    """유저 + /demo/setup(목업 강아지 + active walk session) → (uid, tok, pet, demo_ctx, mock_ws)."""
    uid, tok, pet = make_user(nick, petname, breed)
    demo = apicall("POST", "/demo/setup", token=tok, body={})
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
    return uid, tok, pet, demo_ctx, demo["mock_walk_session_id"]


def new_page(browser, geo):
    """플로우별 격리 컨텍스트 + 콘솔/페이지 에러 수집 리스트를 함께 반환."""
    errors = []
    ctx = browser.new_context(
        viewport={"width": 414, "height": 896}, locale="ko-KR", timezone_id="UTC",
        geolocation=geo, permissions=["geolocation"],
    )
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
            if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
            if not any(k in str(e).lower() for k in IGNORE) else None)
    return ctx, page, errors


def shot(page, msg, name):
    path = os.path.join(SHOTS, f"{name}.png")
    page.screenshot(path=path)
    print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")


def settle_modal(page):
    # 스크림(.center-modal)은 opacity 0→1 CSS 트랜지션, 카드(.center-modal-card)는 springMotion.
    # 부모 opacity는 곱해지므로 둘 다 ~1이어야 보인다.
    page.wait_for_function(
        "() => { const s=document.querySelector('.center-modal');"
        " const c=document.querySelector('.center-modal-card');"
        " return s && c && parseFloat(getComputedStyle(s).opacity) >= 0.99"
        " && parseFloat(getComputedStyle(c).opacity) >= 0.99; }",
        timeout=3000,
    )


def enter_walk(page):
    """#/walk 재진입 + HUD 렌더 대기."""
    page.evaluate("location.hash = '#/walk'")
    page.wait_for_selector(".map-screen", timeout=8000)
    page.wait_for_selector("#walk-map, #walk-fallback", timeout=8000, state="attached")
    page.wait_for_selector("#walk-end", timeout=8000)


# ----------------------------------------------------------------------------
# flow_home — 홈 idle 지도 (W1, 11_W1_home_map.md §7)
# ----------------------------------------------------------------------------
def flow_home(browser):
    print(f"{DIM}— flow_home (W1 #/home){RESET}")
    uid, tok, pet, demo_ctx, mock_ws = demo_fixture("초코아빠", "초코", "푸들")
    ctx, page, errors = new_page(browser, {"latitude": demo_ctx["lat"], "longitude": demo_ctx["lng"]})
    api_calls = []  # (method, path, status)

    def on_resp(r):
        try:
            if "/api/" in r.url and r.request.method in ("POST", "PATCH", "DELETE"):
                api_calls.append((r.request.method, r.url.split("/api", 1)[1].split("?")[0], r.status))
        except Exception:
            pass
    page.on("response", on_resp)

    def calls(method, path):
        return [c for c in api_calls if c[0] == method and c[1] == path]

    try:
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
            [tok, uid, pet, demo_ctx],
        )

        # (1) #/home: 지도 + 본인 빨간 마커(중앙)
        page.goto(BASE + "/#/home", wait_until="networkidle")
        page.wait_for_function("location.hash.startsWith('#/home')", timeout=8000)
        page.wait_for_selector(".map-screen", timeout=8000)
        page.wait_for_selector("#me-marker, #walk-fallback", timeout=10000, state="attached")
        if not page.query_selector("#me-marker"):
            raise AssertionError("WebGL 지도/본인 마커가 렌더되지 않음(fallback 모드) — 빨강 중앙 마커 단언 불가")
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
        shot(page, f"#/home 지도 + 본인 빨강 마커 중앙 (dx={dx:.0f},dy={dy:.0f})", "home_01_map_red_center")

        # (2) 주변 마커 = 강아지 캐릭터 핀만(메타 칩 없음)
        page.wait_for_selector(f'.dog-pin[data-ws="{mock_ws}"]', timeout=12000)
        audit = page.evaluate(
            """(ws) => {
              const pin = document.querySelector(`.dog-pin[data-ws="${ws}"]`);
              const anyMeta = document.querySelectorAll('.dog-pin .meta, .dog-pin .nm, .dog-pin .ds').length;
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
        shot(page, f"주변 마커 = 강아지 캐릭터 핀만 ({audit['pins']}개, 메타 0)", "home_02_dog_pins")

        # (3) 타 강아지 탭 → centerModal → [같이 산책하기] → 매칭
        page.eval_on_selector(f'.dog-pin[data-ws="{mock_ws}"]', "e => e.click()")
        page.wait_for_selector("#cm-profile", timeout=5000)
        page.wait_for_selector("#peer-walk-together", timeout=5000)
        settle_modal(page)
        shot(page, "타 강아지 탭 → centerModal(프로필 + [같이 산책하기])", "home_03a_peer_modal")
        page.eval_on_selector("#peer-walk-together", "e => e.click()")
        page.wait_for_function("location.hash.startsWith('#/matching/')", timeout=8000)
        ws_starts = calls("POST", "/walks/start")
        mreqs = calls("POST", "/match-requests")
        assert ws_starts and ws_starts[-1][2] in (200, 201), f"본인 walk session 보장(POST /walks/start) 누락/실패: {ws_starts}"
        assert mreqs and mreqs[-1][2] in (200, 201), f"POST /match-requests 2xx 아님: {mreqs}"
        match_id = page.evaluate("location.hash.split('/matching/')[1]")
        shot(page, f"[같이 산책하기] → walks/start({ws_starts[-1][2]}) + match-requests({mreqs[-1][2]}) → #/matching/{match_id[:8]}", "home_03b_matching")

        # (4) 본인 마커 탭 → [산책하기] → 산책 세션 생성 → #/walk
        page.evaluate("() => localStorage.removeItem('active_walk_session_id')")
        before = len(calls("POST", "/walks/start"))
        page.goto(BASE + "/#/home", wait_until="networkidle")
        page.wait_for_selector("#me-marker", timeout=10000)
        page.eval_on_selector("#me-marker", "e => e.click()")
        page.wait_for_selector("#mine-start-walk", timeout=5000)
        settle_modal(page)
        shot(page, "본인 마커 탭 → centerModal([산책하기])", "home_04a_mine_modal")
        page.eval_on_selector("#mine-start-walk", "e => e.click()")
        page.wait_for_function("location.hash.startsWith('#/walk')", timeout=8000)
        after = calls("POST", "/walks/start")
        assert len(after) > before and after[-1][2] in (200, 201), f"산책 세션 생성(POST /walks/start) 누락/실패: {after}"
        walk_id = page.evaluate("() => localStorage.getItem('active_walk_session_id')")
        assert walk_id, "산책 세션 id가 store에 저장되지 않음"
        shot(page, f"[산책하기] → walks/start({after[-1][2]}) 세션 생성({walk_id[:8]}) → #/walk", "home_04b_walk")
    except Exception as e:
        page.screenshot(path=os.path.join(SHOTS, "home_FAIL.png"))
        print(f"  {RED}❌ flow_home 실패: {e}{RESET}")
        print(f"  {DIM}hash={page.evaluate('location.hash')} api={api_calls}{RESET}")
        ctx.close()
        raise
    ctx.close()
    return errors


# ----------------------------------------------------------------------------
# flow_walk — 산책 중 HUD (W2, 12_W2_walking.md §8)
# ----------------------------------------------------------------------------
def flow_walk(browser):
    print(f"{DIM}— flow_walk (W2 #/walk){RESET}")
    uid, tok, pet = make_user("산책이", "구름", "푸들")
    ctx, page, errors = new_page(browser, {"latitude": LAT, "longitude": LNG})
    records_calls = []  # (status, post_data)
    end_calls = []      # status

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
            [tok, uid, pet, LAT, LNG],
        )

        # DoD 1: #/walk 렌더
        enter_walk(page)
        quests = page.query_selector_all(".walk-quest")
        assert 1 <= len(quests) <= 2, f"퀘스트 박스 개수가 1~2가 아님: {len(quests)}"
        assert page.query_selector("#walk-shoot"), "좌하단 촬영 버튼 없음"
        assert page.query_selector("#walk-end"), "우하단 통화종료 버튼 없음"
        mode = "지도(WebGL)" if page.query_selector("#me-marker") else "목록 fallback"
        layout = page.evaluate(
            """() => {
              const ms = document.querySelector('.map-screen').getBoundingClientRect();
              const ov = document.querySelector('.walk-overlays-top').getBoundingClientRect();
              return { coverRatio: (ov.bottom - ms.top) / ms.height, ovBottom: ov.bottom, msTop: ms.top, msH: ms.height };
            }"""
        )
        assert layout["coverRatio"] < 0.5, f"상단 퀘스트박스가 지도를 과하게 가림: {layout}"
        shot(page, f"#/walk → 지도({mode}) + 퀘스트박스 {len(quests)}개(지도 가림 {layout['coverRatio']*100:.0f}%) + 촬영/종료", "w2_01_walk")

        # DoD 2a: 퀘스트 박스 탭 → #/camera?mission=&quest=
        mid = page.get_attribute(".walk-quest", "data-mission")
        mtitle = page.get_attribute(".walk-quest", "data-quest")
        page.eval_on_selector(".walk-quest", "e => e.click()")
        page.wait_for_function("location.hash.startsWith('#/camera')", timeout=8000)
        h = page.evaluate("location.hash")
        q = urllib.parse.parse_qs(h.split("?", 1)[1]) if "?" in h else {}
        assert q.get("mission", [None])[0] == mid, f"camera mission 쿼리 불일치: {h}"
        assert q.get("quest", [None])[0] == mtitle, f"camera quest 쿼리 불일치: {h}"
        shot(page, f"퀘스트 박스 탭 → #/camera?mission={mid[:6]}…&quest={mtitle}", "w2_02_camera_quest")

        # DoD 2b: 좌하단 촬영 → #/camera (mission 없음)
        enter_walk(page)
        page.eval_on_selector("#walk-shoot", "e => e.click()")
        page.wait_for_function("location.hash.startsWith('#/camera')", timeout=8000)
        h2 = page.evaluate("location.hash")
        assert "mission=" not in h2, f"일반 촬영인데 mission 쿼리가 있음: {h2}"
        shot(page, f"좌하단 촬영 탭 → #/camera (mission 없음: {h2})", "w2_03_camera_plain")

        # DoD 3: 카메라 복귀(모킹) → 퀘스트 완료 표시
        clip = upload_clip(tok, mid)
        page.evaluate(
            "([cid, mid]) => localStorage.setItem('blip_walk_clips', JSON.stringify([{clip_id:cid, mission_id:mid, order:0}]))",
            [clip["clip_id"], mid],
        )
        enter_walk(page)
        done_box = page.query_selector(f'.walk-quest[data-mission="{mid}"]')
        assert done_box, "해당 미션 퀘스트 박스를 찾지 못함"
        cls = done_box.get_attribute("class") or ""
        assert "done" in cls, f"카메라 복귀 후에도 퀘스트가 완료표시되지 않음: class={cls}"
        shot(page, f"카메라 복귀(clip={clip['clip_id'][:6]}) → 해당 퀘스트 완료표시(.done)", "w2_04_quest_done")

        # DoD 4: 우하단 종료 → end + POST /records(누적 clip) 201 → #/diary + 클립 초기화
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
        shot(page, f"통화종료 → walk end {end_calls[-1]} + POST /records {rstatus}(clip 포함) → #/diary + 누적 초기화", "w2_05_saved")
    except Exception as e:
        page.screenshot(path=os.path.join(SHOTS, "w2_FAIL.png"))
        print(f"  {RED}❌ flow_walk 실패: {e}{RESET}")
        print(f"  {DIM}hash={page.evaluate('location.hash')} records={records_calls} end={end_calls}{RESET}")
        ctx.close()
        raise
    ctx.close()
    return errors


# ----------------------------------------------------------------------------
# flow_matching — 산책 매칭중 + 발자국 (W3, 13_W3_matching.md §7)
# ----------------------------------------------------------------------------
def flow_matching(browser):
    print(f"{DIM}— flow_matching (W3 #/matching){RESET}")
    a_uid, a_tok, a_pet, demo_ctx, mock_ws = demo_fixture("초코아빠", "초코", "푸들")
    # 거절 경로용 실제 상대 B
    b_uid, b_tok, b_pet = make_user("보리엄마", "보리", "비숑")
    b_walk = apicall("POST", "/walks/start", token=b_tok,
                     body={"pet_id": b_pet, "latitude": LAT - 0.0006, "longitude": LNG - 0.0003})
    b_ws = b_walk["walk_session_id"]
    ctx, page, errors = new_page(browser, {"latitude": LAT, "longitude": LNG})

    try:
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

        # (1)(2)(3) 데모 매칭 경로 — 자동수락
        req = apicall("POST", "/match-requests", token=a_tok, body={"receiver_walk_session_id": mock_ws})
        req_id = req["match_request_id"]
        page.goto(BASE + f"/#/matching/{req_id}", wait_until="networkidle")
        page.wait_for_function("location.hash.startsWith('#/matching/')", timeout=8000)
        page.wait_for_selector("#w3-me", timeout=8000)
        page.wait_for_selector("#w3-partner", timeout=8000)

        # (1) 본인+상대 둘만, 주변 nearby 마커 없음
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
        shot(page, f"데모 매칭 진입 → 본인+상대 둘만 표시(주변 마커 0) {counts}", "w3_01_only_two")

        # (2) 발자국 누적 — 폴링 틱마다 .w3-foot 증가
        page.wait_for_selector(".w3-foot", timeout=8000)
        c1 = page.evaluate("() => document.querySelectorAll('.w3-foot').length")
        page.wait_for_timeout(4200)
        c2 = page.evaluate("() => document.querySelectorAll('.w3-foot').length")
        assert c2 > c1, f"발자국이 누적되지 않음: {c1} → {c2}"
        shot(page, f"발자국 트래킹 누적: {c1} → {c2} 개", "w3_02_footprints")

        # (3) 세션확정 → [매칭 성공] → #/walk?match=...
        page.wait_for_selector("#w3-cta:not([disabled])", timeout=8000)
        assert page.inner_text("#w3-cta").strip() == "매칭 성공", "CTA 라벨이 '매칭 성공'이 아님"
        page.click("#w3-cta")
        page.wait_for_function(
            "location.hash.startsWith('#/walk') && location.hash.includes('match=')", timeout=8000
        )
        walk_hash = page.evaluate("location.hash")
        assert "match=" in walk_hash and len(walk_hash.split("match=")[1]) > 0, f"match 세션 누락: {walk_hash}"
        shot(page, f"매칭 성공 → 산책중 인계 ({walk_hash})", "w3_03_success_to_walk")

        # (4) 거절 경로 — 토스트 + #/home
        page.evaluate("() => localStorage.removeItem('blip_demo_context')")
        req2 = apicall("POST", "/match-requests", token=a_tok, body={"receiver_walk_session_id": b_ws})
        rid2 = req2["match_request_id"]
        page.goto(BASE + f"/#/matching/{rid2}", wait_until="networkidle")
        page.wait_for_selector("#w3-me", timeout=8000)
        assert page.query_selector("#w3-partner") is None, "보류 상태인데 상대 마커가 떴음"
        apicall("PATCH", f"/match-requests/{rid2}/reject", token=b_tok)
        page.wait_for_function("location.hash.startsWith('#/home')", timeout=10000)
        toasted = page.evaluate(
            "() => !!Array.from(document.querySelectorAll('.toast')).find(t => /거절/.test(t.textContent))"
        )
        assert toasted, "거절 토스트가 보이지 않음"
        shot(page, "거절 경로 → 토스트 + #/home 복귀", "w3_04_reject_home")
    except Exception as e:
        page.screenshot(path=os.path.join(SHOTS, "w3_FAIL.png"))
        print(f"  {RED}❌ flow_matching 실패: {e}{RESET}")
        print(f"  {DIM}hash={page.evaluate('location.hash')}{RESET}")
        ctx.close()
        raise
    ctx.close()
    return errors


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    all_errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=LAUNCH_ARGS)
        try:
            for label, flow in (("home", flow_home), ("walk", flow_walk), ("matching", flow_matching)):
                all_errors += flow(browser)
        except Exception:
            browser.close()
            return 1
        browser.close()

    if all_errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(all_errors)}건:{RESET}")
        for e in all_errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 v2 산책 통합(홈+산책중+매칭) 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
