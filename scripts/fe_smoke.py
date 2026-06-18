#!/usr/bin/env python3
"""Headless frontend smoke runner (Playwright Chromium).

FE0 flow: 게스트 가입 → 반려동물 등록 → #/home 진입.
실제 클릭/입력으로 통과시키고, 각 단계 DOM 단언 + 콘솔 에러 0 + 스크린샷 저장.

Reusable: 이후 FE goal이 import 해서 헬퍼(signup_and_pet 등)를 재사용한다.

Usage:
    BASE=http://localhost:8000 python scripts/fe_smoke.py
Exit code 0 = 통과, 1 = 실패.
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


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
    # CTA disabled when empty
    assert page.get_attribute("#guest-cta", "disabled") is not None, "CTA should start disabled"
    ok("앱 로드 → SCR-01 로그인 화면, CTA 비활성", "01_auth")

    # --- Step 1: guest signup ---
    page.fill("#nickname", nickname)
    page.wait_for_function("!document.querySelector('#guest-cta').disabled")
    page.click("#guest-cta")
    hash_is(page, "#/onboard-pet")
    page.wait_for_selector("#pet-name")
    # required validation: CTA disabled before filling
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
    page.wait_for_selector("#start-walk")
    assert "초코" in page.inner_text("#my-pet-card"), "home should show pet name"
    assert page.query_selector("#tabbar:not(.hidden)"), "tabbar should be visible on home"
    ok("펫 등록 제출 → #/home 진입(펫 카드·산책 시작 CTA·탭바 노출)", "04_home")

    # --- Step 3: session persists across reload ---
    page.reload(wait_until="networkidle")
    hash_is(page, "#/home")
    ok("새로고침 후에도 세션 유지(→ #/home)", "05_reload")

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

    print(f"\n{GREEN}🎉 FE0 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
