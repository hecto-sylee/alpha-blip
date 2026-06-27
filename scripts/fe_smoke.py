#!/usr/bin/env python3
"""Headless frontend smoke runner (Playwright Chromium).

W0(기반/공통) 플로우: 게스트 가입 → 반려동물 등록 → #/home(W1 스텁) 진입.
이어서 W0 DoD 단언:
  (1) 하단 탭 정확히 3개(data-tab=diary/home/my), 방/랭킹 탭 부재
  (2) 신규 라우트 6종 직접 이동 시 스텁 렌더 + 콘솔 에러 0
  (3) 마이에 업적/내 방 링크 부재 + 로그아웃 정상
  (4) centerModal 중앙 팝업 등장/닫힘 1회

실제 클릭/입력으로 통과시키고, 각 단계 DOM 단언 + 콘솔 에러 0 + 스크린샷 저장.
Reusable: 이후 FE goal이 import 해서 헬퍼(run_fe0 등)를 재사용한다.

Usage:
    BASE=http://localhost:9010 python scripts/fe_smoke.py
Exit code 0 = 통과, 1 = 실패.
"""
from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

STUB_RE = "/준비 중/.test(document.querySelector('#view .h1')?.textContent || '')"


def shot(page, name):
    path = os.path.join(SHOTS, f"{name}.png")
    page.screenshot(path=path)
    return path


def attach_console_guard(page, errors):
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))


def hash_is(page, expected, timeout=8000):
    page.wait_for_function(
        "h => location.hash.startsWith(h)", arg=expected, timeout=timeout
    )


def run_fe0(page, errors, nickname="초코아빠"):
    """가입 → 펫 등록 → #/home(W1 스텁). 인증·펫 보유 상태를 만들어 반환(다른 러너가 재사용)."""
    steps = []

    def ok(msg, name):
        path = shot(page, name)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")
        steps.append(msg)

    # --- Step 0: load app, expect auth screen ---
    page.goto(BASE, wait_until="networkidle")
    hash_is(page, "#/auth")
    page.wait_for_selector("#nickname")
    assert page.query_selector("#guest-cta"), "guest CTA missing"
    assert page.get_attribute("#guest-cta", "disabled") is not None, "CTA should start disabled"
    ok("앱 로드 → SCR-01 로그인 화면, CTA 비활성", "01_auth")

    # --- Step 1: guest signup ---
    page.fill("#nickname", nickname)
    page.wait_for_function("!document.querySelector('#guest-cta').disabled")
    page.click("#guest-cta")
    hash_is(page, "#/onboard-pet")
    page.wait_for_selector("#pet-name")
    assert page.get_attribute("#pet-cta", "disabled") is not None, "pet CTA should start disabled"
    ok(f"게스트 가입('{nickname}') → SCR-02 펫 등록, 필수 미입력이라 CTA 비활성", "02_onboard_pet")

    # --- Step 2: fill required fields, submit ---
    page.fill("#pet-name", "초코")
    page.fill("#pet-breed", "푸들")
    page.click("#pet-size .opt[data-val='small']")
    page.click("#pet-tags .tag >> nth=0")
    page.wait_for_function("!document.querySelector('#pet-cta').disabled")
    ok("필수항목(이름·견종·크기·성격) 입력 → CTA 활성화", "03_pet_filled")

    page.click("#pet-cta")
    hash_is(page, "#/home")
    # 새 홈은 W1 스텁(지도는 W1에서 구현). 스텁 렌더 + 탭바 노출 확인.
    page.wait_for_selector("#tabbar:not(.hidden)")
    page.wait_for_function(STUB_RE)
    assert page.query_selector("#tabbar:not(.hidden)"), "tabbar should be visible on home"
    ok("펫 등록 제출 → #/home 진입(W1 스텁 렌더·탭바 노출)", "04_home")

    # --- Step 3: session persists across reload ---
    page.reload(wait_until="networkidle")
    hash_is(page, "#/home")
    page.wait_for_function(STUB_RE)
    ok("새로고침 후에도 세션 유지(→ #/home)", "05_reload")

    return steps


def run_w0_dod(page, errors):
    """W0 완료 조건(DoD) 1~4 단언."""
    steps = []

    def ok(msg, name):
        path = shot(page, name)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")
        steps.append(msg)

    # --- DoD#1: 하단 탭 정확히 3개(diary/home/my), 방/랭킹 부재 ---
    tabs = page.eval_on_selector_all("#tabbar a", "els => els.map(e => e.dataset.tab)")
    assert tabs == ["diary", "home", "my"], f"탭바 data-tab 예상[diary,home,my] != {tabs}"
    labels = page.eval_on_selector_all("#tabbar a span:last-child", "els => els.map(e => e.textContent)")
    assert "방" not in labels, f"'방' 탭이 남아있음: {labels}"
    assert "랭킹" not in labels, f"'랭킹' 탭이 남아있음: {labels}"
    ok(f"하단 탭 정확히 3개 {tabs} · 방/랭킹 부재 ({labels})", "06_tabbar")

    # --- DoD#2: 신규 라우트 직접 이동 → 스텁 렌더 + 콘솔 에러 0 ---
    routes = ["/home", "/walk", "/matching/x", "/camera", "/diary", "/pet-diary/new"]
    for r in routes:
        before = len(errors)
        page.evaluate("p => window.blip.navigate(p)", r)
        hash_is(page, "#" + r)
        page.wait_for_function(STUB_RE)
        assert len(errors) == before, f"{r} 이동 중 콘솔 에러: {errors[before:]}"
    shot(page, "07_stub_routes")
    ok(f"신규 라우트 6종 직접 이동 → 스텁 렌더·콘솔 에러 0 ({', '.join(routes)})", "07_stub_routes")

    # --- DoD#3: 마이에 업적/내 방 링크 부재 + 로그아웃 정상 ---
    page.evaluate("() => window.blip.navigate('/my')")
    hash_is(page, "#/my")
    page.wait_for_function("() => document.querySelector('#view .h1')?.textContent === '마이'")
    body = page.inner_text("#view")
    assert "업적" not in body, "마이에 '업적' 링크/카드가 남아있음"
    assert "내 방" not in body, "마이에 '내 방' 링크가 남아있음"
    assert page.query_selector("#logout"), "로그아웃 버튼이 없음"
    assert "개인정보 보호 설정" in body, "개인정보 보호 설정 링크가 사라짐(유지 대상)"
    ok("마이 — 업적/내 방 링크 부재 · 개인정보/로그아웃 유지", "08_my")

    # --- DoD#4: centerModal 등장/닫힘 1회 ---
    page.evaluate(
        """() => {
            window.__cm = window.blip.centerModal((close) => {
                const d = document.createElement('div');
                d.className = 'cm-demo';
                const h = document.createElement('div');
                h.className = 'h2';
                h.textContent = 'W1 프로필 데모';
                d.appendChild(h);
                return d;
            });
        }"""
    )
    page.wait_for_selector(".center-modal", state="visible")
    assert page.query_selector(".center-modal-card .cm-demo"), "centerModal 본문이 렌더되지 않음"
    shot(page, "09_center_modal_open")  # 모달 떠 있는 상태 보존
    page.evaluate("() => window.__cm.close()")
    page.wait_for_selector(".center-modal", state="detached")
    ok("centerModal 중앙 팝업 등장 → 닫힘 1회", "10_center_modal_closed")

    return steps


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        attach_console_guard(page, errors)
        try:
            run_fe0(page, errors)
            run_w0_dod(page, errors)
        except Exception as e:
            shot(page, "FAIL")
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.url}{RESET}")
            browser.close()
            return 1
        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 W0 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
