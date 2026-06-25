#!/usr/bin/env python3
"""Headless smoke for W6 — 펫일기 (작성 / 상세·편집·삭제 / 표시카드 규약).

흐름:
  - 게스트+펫 API 셋업 후 브라우저 세션 주입.
  - #/pet-diary/new?date=오늘 → 기분 선택 + 활동 칩 다중 선택 + 텍스트 → 저장 201 → #/diary 이동 단언.
  - 저장 후 GET /pet-diary?date= 1건 단언 → #/pet-diary/:id 상세 표시 단언.
  - 상세에서 편집(PATCH 200) → 삭제(DELETE 200 → #/diary) 단언.
  - petDiaryCard(d,{onClick}) 가 이미지4 형태(기분 이모지 + 활동 아이콘 줄 + 텍스트)로 렌더되는지 단언(W5 인수인계용).
콘솔 에러 0(외부/WebGL 잡음 제외), 각 단계 before/after 스크린샷 저장.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:9016")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)
TODAY = datetime.date.today().isoformat()

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


def main():
    print(f"{DIM}BASE={BASE}  date={TODAY}{RESET}")
    errors = []
    api_calls = []  # (method, status, url)

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    u = apicall("POST", "/auth/guest", body={"nickname": "일기쟁이"})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": "콩", "breed": "푸들", "size": "small", "personality_tags": ["온순함"]})
    print(f"{DIM}  fixture: user={u['user_id'][:8]} pet={p['pet_id'][:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)
        page.on("response", lambda r: api_calls.append((r.request.method, r.status, r.url))
                if "/api/pet-diary" in r.url else None)

        def last(method):
            for m, s, _u in reversed(api_calls):
                if m == method:
                    return s
            return None

        try:
            # 세션 주입
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
                [u["auth_token"], u["user_id"], p["pet_id"]],
            )

            # ── (2) 작성: #/pet-diary/new?date=오늘 ──
            page.goto(f"{BASE}/#/pet-diary/new?date={TODAY}", wait_until="networkidle")
            page.wait_for_selector("#mood-row")
            assert len(page.query_selector_all(".mood-opt")) == 5, "기분 5단계가 아님"
            ok(page, "작성 화면 진입(기분 5단계 + 활동 카탈로그)", "w6_01_new_before")

            # 기분 1개 선택
            page.click('.mood-opt[data-mood="happy"]')
            assert page.query_selector('.mood-opt[data-mood="happy"].sel'), "기분 선택 표시(.sel) 안됨"
            # 활동 칩 다중 선택(서로 다른 카테고리)
            for code in ("weather:sunny", "people:friend", "meal:lunch"):
                page.click(f'.diary-chip[data-code="{code}"]')
            sel_cnt = len(page.query_selector_all(".diary-chip.sel"))
            assert sel_cnt == 3, f"활동 칩 다중선택 수 불일치: {sel_cnt}"
            page.fill("#diary-text", "콩이랑 동네 한 바퀴 돌고 친구도 만난 좋은 하루 ☀️")
            ok(page, f"기분 선택 + 활동 칩 {sel_cnt}개 + 텍스트 입력", "w6_02_filled")

            # 저장 → 201 → #/diary 이동
            page.click("#diary-save")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=8000)
            post_status = last("POST")
            assert post_status == 201, f"POST /pet-diary 상태가 201이 아님: {post_status}"
            assert page.evaluate("location.hash").startswith("#/diary"), "저장 후 #/diary 이동 실패"
            ok(page, f"저장 POST {post_status} → #/diary 이동", "w6_03_saved")

            # ── (3) 저장 후 GET ?date= 1건 + 상세 ──
            lst = apicall("GET", f"/pet-diary?date={TODAY}", token=u["auth_token"])
            assert len(lst["diaries"]) == 1, f"GET ?date= 가 1건이 아님: {len(lst['diaries'])}"
            did = lst["diaries"][0]["id"]
            assert lst["diaries"][0]["activity_tags"] == ["weather:sunny", "people:friend", "meal:lunch"], \
                f"저장된 activity_tags 불일치: {lst['diaries'][0]['activity_tags']}"
            print(f"{DIM}  GET ?date={TODAY} → 1건 (id={did[:8]} tags={lst['diaries'][0]['activity_tags']}){RESET}")

            page.goto(f"{BASE}/#/pet-diary/{did}", wait_until="networkidle")
            page.wait_for_selector("#diary-detail")
            assert page.query_selector("#diary-detail .mood-face-lg .ic"), "상세에 기분 아이콘 없음"
            assert page.query_selector_all(".diary-act"), "상세에 활동 아이콘 줄 없음"
            assert "좋은 하루" in page.inner_text(".diary-detail-text"), "상세 텍스트 표시 안됨"
            ok(page, "상세: 기분 아이콘 + 활동 줄 + 텍스트 표시", "w6_04_detail")

            # ── 편집(PATCH) ──
            page.click("#diary-edit")
            page.wait_for_selector("#mood-row")
            page.click('.mood-opt[data-mood="good"]')
            page.click("#diary-save")
            page.wait_for_selector("#diary-detail", timeout=8000)
            patch_status = last("PATCH")
            assert patch_status == 200, f"PATCH 상태가 200이 아님: {patch_status}"
            assert "좋음" in page.inner_text(".diary-detail-mood"), "편집된 기분(좋음)이 반영 안됨"
            ok(page, f"편집 PATCH {patch_status} → 기분 '좋음' 반영", "w6_05_edited")

            # ── 삭제(DELETE) ──
            page.click("#diary-delete")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=8000)
            del_status = last("DELETE")
            assert del_status == 200, f"DELETE 상태가 200이 아님: {del_status}"
            gone = apicall("GET", f"/pet-diary?date={TODAY}", token=u["auth_token"])
            assert len(gone["diaries"]) == 0, "삭제 후에도 일기가 남아있음"
            ok(page, f"삭제 DELETE {del_status} → #/diary, 목록 0건", "w6_06_deleted")

            # ── (4) petDiaryCard 표시 규약(이미지4) ──
            card = page.evaluate(
                """async () => {
                    const mod = await import('/static/js/screens/pet_diary.js');
                    const d = { id:'demo-card', mood:'happy', diary_date:'%s',
                        activity_tags:['weather:sunny','people:friend','meal:lunch'],
                        text:'콩이랑 산책 다녀온 좋은 하루' };
                    let clicked = null;
                    const node = mod.petDiaryCard(d, { onClick: (x)=>{ clicked = x.id; } });
                    const view = document.getElementById('view');
                    view.innerHTML = '';
                    const wrap = document.createElement('div'); wrap.className = 'screen';
                    wrap.appendChild(node); view.appendChild(wrap);
                    node.click();
                    return {
                        isCard: node.classList.contains('pet-diary-card') && node.classList.contains('card'),
                        moodIcons: node.querySelectorAll('.pet-diary-mood .ic').length,
                        actIcons: node.querySelectorAll('.pet-diary-act .ic').length,
                        text: (node.querySelector('.pet-diary-text')||{}).textContent || '',
                        diaryId: node.dataset.diaryId,
                        clicked,
                    };
                }""" % TODAY
            )
            assert card["isCard"], "petDiaryCard 가 입체 카드(.card.pet-diary-card)가 아님"
            assert card["moodIcons"] == 1, f"기분 이모지(아이콘) 1개가 아님: {card['moodIcons']}"
            assert card["actIcons"] >= 2, f"활동 아이콘 줄이 2개 미만: {card['actIcons']}"
            assert "좋은 하루" in card["text"], "카드 텍스트 미표시"
            assert card["diaryId"] == "demo-card" and card["clicked"] == "demo-card", "onClick 콜백 미동작"
            ok(page, f"petDiaryCard 이미지4 형태(기분{card['moodIcons']}+활동{card['actIcons']}+텍스트+onClick)", "w6_07_card")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "w6_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')} api={api_calls}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W6 펫일기 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
