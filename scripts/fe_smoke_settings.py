#!/usr/bin/env python3
"""Headless smoke for FE4 — 마이 · 설정/개인정보 · 전역 폴링 배너 · 마감 (SCR-30~32).

(1) 설정 토글(위치공유/대략위치) 끄고 새로고침 → store.settings 유지 단언.
(2) 차단 목록 추가 → 해제가 UI에서 동작 + API 2xx 단언.
(3) B가 API로 A에게 매칭 요청 → A가 임의 화면(마이)에서 전역 배너 노출 → 수락 UI 동작 단언.
(4) prefers-reduced-motion=reduce 에뮬레이션에서 축하/스프링 모션 대체 전환(콘솔 에러 0) 확인.
각 단계 스크린샷 저장.
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
        return r.status, json.loads(r.read().decode() or "{}")


def make_user(nick, petname):
    _, u = apicall("POST", "/auth/guest", body={"nickname": nick})
    _, p = apicall("POST", "/pets", token=u["auth_token"],
                   body={"name": petname, "breed": "푸들", "size": "small", "personality_tags": ["활발함"]})
    return u, p["pet_id"]


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    a, a_pet = make_user("설정러A", "초코")
    b, b_pet = make_user("요청자B", "보리")
    # A의 활성 산책 세션(수신자 walk session) — B가 여기로 요청
    _, a_walk = apicall("POST", "/walks/start", token=a["auth_token"],
                        body={"pet_id": a_pet, "latitude": LAT, "longitude": LNG})
    a_ws = a_walk["walk_session_id"]
    print(f"{DIM}  fixture: A={a['user_id'][:8]} B={b['user_id'][:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)

        try:
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
                [a["auth_token"], a["user_id"], a_pet],
            )

            # --- 마이페이지 ---
            page.goto(BASE + "/#/my", wait_until="networkidle")
            page.wait_for_selector("#logout")
            ok(page, "마이페이지(SCR-30) 렌더 (펫 요약·스탯·메뉴·로그아웃)", "f4_01_my")

            # --- (1) 설정 토글 끄고 새로고침 유지 ---
            page.goto(BASE + "/#/settings", wait_until="networkidle")
            page.wait_for_selector("#set-locationVisible", state="attached")
            # 스위치 UI라 input은 display:none → 보이는 라벨을 클릭해 토글 (기본 on → 끔)
            assert page.is_checked("#set-locationVisible") is True, "기본값이 on이 아님"
            page.click("label.switch:has(#set-locationVisible)")
            page.click("label.switch:has(#set-approximate)")
            ok(page, "설정 토글 끔 (위치공유/대략위치)", "f4_02_toggle_off")
            page.reload(wait_until="networkidle")
            page.wait_for_selector("#set-locationVisible", state="attached")
            assert page.is_checked("#set-locationVisible") is False, "새로고침 후 위치공유 토글이 유지 안 됨"
            assert page.is_checked("#set-approximate") is False, "새로고침 후 대략위치 토글이 유지 안 됨"
            persisted = page.evaluate("JSON.parse(localStorage.getItem('settings')||'{}')")
            assert persisted.get("locationVisible") is False and persisted.get("approximate") is False, f"store.settings 미반영: {persisted}"
            ok(page, f"새로고침 후 토글 유지(store.settings={{locationVisible:false, approximate:false}})", "f4_03_persist")

            # --- (2) 차단 추가 → 해제 (API 2xx) ---
            block_resps = []
            page.on("response", lambda r: block_resps.append((r.request.method, r.status, r.url)) if "/api/privacy/block" in r.url else None)
            page.fill("#block-input", b["user_id"])
            page.click("#block-add")
            page.wait_for_selector(f'.block-row[data-uid="{b["user_id"]}"]', timeout=6000)
            ok(page, "차단 목록에 대상 추가 (UI 노출)", "f4_04_block_add")
            page.click(f'.block-row[data-uid="{b["user_id"]}"] button')
            page.wait_for_selector(f'.block-row[data-uid="{b["user_id"]}"]', state="detached", timeout=6000)
            # API 2xx 확인 (POST 201, DELETE 200)
            assert any(m == "POST" and 200 <= s < 300 for m, s, _ in block_resps), f"block POST 2xx 아님: {block_resps}"
            assert any(m == "DELETE" and 200 <= s < 300 for m, s, _ in block_resps), f"unblock DELETE 2xx 아님: {block_resps}"
            ok(page, f"차단 해제 (UI 제거 + block POST/DELETE 모두 2xx)", "f4_05_block_remove")

            # --- (3) 전역 매칭 폴링 배너 → 수락 ---
            # B가 A에게 매칭 요청 (A의 walk session으로)
            _, req = apicall("POST", "/match-requests", token=b["auth_token"], body={"receiver_walk_session_id": a_ws})
            # A는 임의 화면(마이)에 있음
            page.goto(BASE + "/#/my", wait_until="networkidle")
            page.wait_for_selector("#incoming-banner.show #incoming-accept", timeout=8000)
            assert "요청자B" in page.inner_text("#incoming-banner"), "배너에 요청자 닉네임 없음"
            ok(page, "임의 화면(마이)에서 전역 매칭 요청 배너 노출", "f4_06_banner")
            page.click("#incoming-accept")
            page.wait_for_function("location.hash.startsWith('#/session/')", timeout=8000)
            page.wait_for_selector("#session-timer")
            ok(page, "배너 수락 → 매칭 세션 전환", "f4_07_accept")

            # --- (4) prefers-reduced-motion ---
            page2 = ctx.new_page()
            page2.emulate_media(reduced_motion="reduce")
            rm_errors = []
            page2.on("console", lambda m: rm_errors.append(m.text) if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
            page2.on("pageerror", lambda e: rm_errors.append(str(e)) if not any(k in str(e).lower() for k in IGNORE) else None)
            page2.goto(BASE + "/#/my", wait_until="networkidle")
            page2.wait_for_selector("#logout")
            reduced = page2.evaluate("window.matchMedia('(prefers-reduced-motion: reduce)').matches")
            assert reduced is True, "reduced-motion 에뮬레이션 미적용"
            # 화면 전환들이 콘솔 에러 없이 동작
            page2.goto(BASE + "/#/diary", wait_until="networkidle")
            page2.wait_for_selector(".stat")
            assert not rm_errors, f"reduced-motion 콘솔 에러: {rm_errors}"
            ok(page2, "prefers-reduced-motion=reduce 에뮬: 화면 전환 정상(콘솔 에러 0)", "f4_08_reduced_motion")
            page2.close()

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "f4_FAIL.png"))
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

    print(f"\n{GREEN}🎉 FE4 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
