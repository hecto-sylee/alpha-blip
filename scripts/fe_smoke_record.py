#!/usr/bin/env python3
"""Headless smoke for W5 — 기록 탭 재설계 (#/diary): 영상기록 + 매칭 상대기록 + 펫일기 + 캘린더/스와이프.

흐름(데모 매칭 산책 1회를 API로 구성한 뒤 브라우저로 검증):
  - 게스트+펫 → demo/setup(목 동행자) → 내 산책 시작 → 매칭요청(목이면 자동 수락) → match_session.
  - 내 클립/상대 클립 업로드 → 각각 match_session 연결 record 생성(오늘).
  - 어제: 혼자 산책 record(클립 1개, match 없음) — 상대영역 미표시/펫일기 빈상태 검증용.
  - 오늘: 펫일기 1개 생성 — 카드/상세 진입 검증용.
검증(DoD):
  (1) #/diary 에 [기록] 칩 + 영상 섹션 + 펫일기 섹션 렌더, 방 버튼/공유옵션 부재, 콘솔 0.
  (2) [기록] 칩 → 캘린더/공유 토글. 캘린더로 날짜 선택 → 해당 날짜 이동. 공유 비활성.
  (3) 매칭 record: 내 영상 + 상대 영상 썸네일 둘 다(신규 API 200 + 상대 클립 stream 200). 혼자 산책은 상대 영역 미표시.
  (4) 펫일기 0개 → "일기가 없어요."+작성 진입 / 1개 이상 → 카드 + 상세 진입.
  (5) 좌우 스와이프 → 날짜 변경 시 영상 + 펫일기 동시 갱신.
콘솔 에러 0(외부 타일/WebGL/더미 미디어 디코드 잡음 제외), 각 단계 스크린샷.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
# 외부 타일/WebGL + 더미 webm(테스트 픽스처) 디코드 잡음은 무시. 앱 로직 에러만 집계.
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon", "webm", "demuxer", "media resource", "no supported source",
          "decode", "pipeline_error", "media element")

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

# 최소 webm 헤더 흉내(EBML magic) — stream 200 + <video> 요소 생성만 확인하면 충분.
DUMMY_WEBM = b"\x1a\x45\xdf\xa3" + b"blip-w5-smoke-clip\x00" * 8


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def upload_clip(token, order=0, content=DUMMY_WEBM):
    boundary = "----blipW5Smoke"
    body = b""
    for name, value in (("order", str(order)), ("duration_ms", "2000")):
        body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{name}"\r\n\r\n{value}\r\n').encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="file"; filename="clip.webm"\r\nContent-Type: video/webm\r\n\r\n').encode()
    body += content + b"\r\n" + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/clips/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def setup_matching_walk():
    """오늘=매칭 산책(내/상대 클립), 어제=혼자 산책, 오늘 펫일기 1개를 API로 구성."""
    u = apicall("POST", "/auth/guest", body={"nickname": "기록이"})
    tok = u["auth_token"]
    p = apicall("POST", "/pets", token=tok,
                body={"name": "콩", "breed": "말티즈", "size": "small", "personality_tags": ["온순함"]})
    pet_id = p["pet_id"]

    demo = apicall("POST", "/demo/setup", token=tok, body={})
    mock_walk = demo["mock_walk_session_id"]
    mock_token = f"demo-mock:{u['user_id']}"

    apicall("POST", "/walks/start", token=tok,
            body={"pet_id": pet_id, "latitude": demo["location"]["latitude"],
                  "longitude": demo["location"]["longitude"]})

    req = apicall("POST", "/match-requests", token=tok,
                  body={"receiver_walk_session_id": mock_walk})
    info = apicall("GET", f"/match-requests/{req['match_request_id']}", token=tok)
    session_id = info["match_session_id"]
    assert session_id, f"match_session 미생성: {info}"

    clip_mine = upload_clip(tok, order=0)["clip_id"]
    apicall("POST", "/records", token=tok,
            body={"visibility": "diary", "walked_at": TODAY, "clip_ids": [clip_mine],
                  "match_session_id": session_id})

    clip_partner = upload_clip(mock_token, order=0)["clip_id"]
    apicall("POST", "/records", token=mock_token,
            body={"visibility": "diary", "walked_at": TODAY, "clip_ids": [clip_partner],
                  "match_session_id": session_id})

    # 어제: 혼자 산책 (match 없음)
    clip_solo = upload_clip(tok, order=0)["clip_id"]
    apicall("POST", "/records", token=tok,
            body={"visibility": "diary", "walked_at": YESTERDAY, "clip_ids": [clip_solo]})

    # 오늘: 펫일기 1개
    apicall("POST", "/pet-diary", token=tok,
            body={"pet_id": pet_id, "diary_date": TODAY, "mood": "happy",
                  "activity_tags": ["move:walk", "people:friend"], "text": "매칭 산책 즐거웠다 🐾"})

    return u, pet_id, session_id, clip_partner


def main():
    print(f"{DIM}BASE={BASE}  today={TODAY} yesterday={YESTERDAY}{RESET}")
    errors = []
    match_api = []   # (status, url) for /match-sessions/{id}/records
    streams = []     # (status, url) for /api/clips/{id}/stream

    u, pet_id, session_id, clip_partner = setup_matching_walk()
    print(f"{DIM}  fixture: user={u['user_id'][:8]} session={session_id[:8]} partnerClip={clip_partner[:8]}{RESET}")

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    def swipe(page, dx):
        box = page.eval_on_selector("#record-tab", "el => { const r=el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
        cy = box["y"] + box["h"] * 0.5
        x0 = box["x"] + box["w"] * 0.5
        page.mouse.move(x0, cy)
        page.mouse.down()
        page.mouse.move(x0 + dx, cy, steps=10)
        page.mouse.up()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)
        page.on("response", lambda r: (
            match_api.append((r.status, r.url)) if "/match-sessions/" in r.url and r.url.endswith("/records")
            else streams.append((r.status, r.url)) if "/api/clips/" in r.url and "/stream" in r.url
            else None))

        try:
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
                [u["auth_token"], u["user_id"], pet_id],
            )

            # ── (1) 렌더 + 방버튼/공유옵션 부재 ──────────────────────────
            page.goto(BASE + f"/#/diary?date={TODAY}", wait_until="networkidle")
            page.wait_for_selector("#record-pill", timeout=8000)
            page.wait_for_selector("#record-videos", timeout=8000)
            page.wait_for_selector("#record-diary", timeout=8000)
            room_btns = [b for b in page.query_selector_all("#record-tab button")
                         if "방" in (b.inner_text() or "")]
            assert not room_btns, f"방 버튼이 존재함: {[b.inner_text() for b in room_btns]}"
            assert page.query_selector("#record-tab >> text=방 공유") is None, "공유(방) 옵션이 존재함"
            ok(page, "(1) #/diary: [기록] 칩 + 영상 섹션 + 펫일기 섹션 렌더 · 방 버튼/공유옵션 부재", "f5_01_render")

            # ── (3) 매칭: 내 영상 + 상대 영상 둘 다 (신규 API 200 + 상대 stream 200) ──
            # 주: 캘린더/스와이프 날짜 이동은 URL을 바꾸지 않고 화면을 제자리 갱신(스펙).
            #     따라서 "오늘"에서 먼저 스와이프 검증을 끝낸 뒤, 마지막에 캘린더를 검증한다.
            page.wait_for_selector("#my-clips video", timeout=10000)
            page.wait_for_selector("#partner-clips video", timeout=10000)
            assert any(s == 200 for s, _ in match_api), f"match-records API 200 미관측: {match_api}"
            assert any(s in (200, 206) and clip_partner in url for s, url in streams), \
                f"상대 클립 stream 200 미관측: {streams}"
            ok(page, "(3) 매칭 record: 내 영상 + 상대 영상 썸네일 둘 다 표시 (신규 API 200 · 상대 stream 200)", "f5_02_matching")

            # ── (5) 스와이프 + (3-혼자) + (4-빈상태): 오늘→어제 동시 갱신 ──
            swipe(page, 120)  # 오른쪽으로 밀기 → 이전 날(어제)
            page.wait_for_function("d => document.getElementById('record-body').dataset.date === d", arg=YESTERDAY, timeout=8000)
            assert page.eval_on_selector("#record-videos", "el => el.dataset.date") == YESTERDAY, "영상 섹션이 어제로 안 바뀜"
            assert page.eval_on_selector("#record-diary", "el => el.dataset.date") == YESTERDAY, "펫일기 섹션이 어제로 안 바뀜"
            assert page.query_selector("#partner-clips") is None, "혼자 산책인데 상대 영역이 표시됨"
            page.wait_for_selector("#my-clips video", timeout=8000)
            assert page.query_selector(".record-diary-empty") and page.query_selector("#diary-write"), \
                "어제 펫일기 빈 상태(작성 진입)가 없음"
            ok(page, "(5)/(3-혼자)/(4-빈) 스와이프→어제: 영상+펫일기 동시 갱신 · 상대영역 미표시 · 펫일기 빈상태+작성진입", "f5_03_swipe_solo")

            # ── (4) 펫일기 카드 + 상세 진입: 어제→오늘 스와이프 ──
            swipe(page, -120)  # 왼쪽으로 밀기 → 다음 날(오늘)
            page.wait_for_function("d => document.getElementById('record-body').dataset.date === d", arg=TODAY, timeout=8000)
            page.wait_for_selector("#partner-clips video", timeout=10000)
            page.wait_for_selector(".pet-diary-card", timeout=8000)
            ok(page, "(4) 스와이프→오늘: 펫일기 카드 표시 (상대영역 복귀)", "f5_04_diary_card")
            page.click(".pet-diary-card")
            page.wait_for_function("location.hash.startsWith('#/pet-diary/')", timeout=8000)
            page.wait_for_selector("#diary-detail", timeout=8000)
            ok(page, "(4) 펫일기 카드 탭 → 상세 진입(#/pet-diary/:id)", "f5_05_diary_detail")

            # ── (2) [기록] 칩 → 캘린더/공유 토글 → 날짜 점프 + 공유 비활성 ──
            # 상세(#/pet-diary/:id)에서 진짜 네비게이션으로 기록 탭 복귀(해시가 달라 재진입됨).
            page.goto(BASE + f"/#/diary?date={TODAY}", wait_until="networkidle")
            page.wait_for_selector("#record-pill", timeout=8000)
            page.click("#record-pill")
            page.wait_for_selector("#record-toggle:not(.hidden)", timeout=5000)
            share = page.query_selector('[data-toggle="share"]')
            assert share and (share.get_attribute("disabled") is not None
                              or share.get_attribute("aria-disabled") == "true"), "공유 토글이 비활성이 아님"
            page.click('[data-toggle="calendar"]')
            page.wait_for_selector(".record-cal", timeout=5000)
            cell = page.query_selector(".record-cal-cell[data-date]:not(.is-selected):not(.is-empty)")
            jump = cell.get_attribute("data-date")
            cell.click()
            page.wait_for_function("d => document.getElementById('record-body').dataset.date === d", arg=jump, timeout=8000)
            assert page.inner_text("#record-date"), "날짜 라벨 비어있음"
            ok(page, f"(2) [기록] 칩 → 캘린더/공유 토글 · 공유 비활성 · 캘린더로 {jump} 이동", "f5_06_calendar")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "f5_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')}{RESET}")
            print(f"  {DIM}match_api={match_api}{RESET}")
            print(f"  {DIM}streams={streams[-6:]}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W5 기록 탭 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
