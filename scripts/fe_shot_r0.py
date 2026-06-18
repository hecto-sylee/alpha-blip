#!/usr/bin/env python3
"""R0 design-system screenshot runner.

Walks the main screens (auth → onboard-pet → home → diary → rooms → my),
captures screenshots into scripts/.fe_shots_r0/<TAG>/, asserts console errors 0,
and verifies that a primary button visually depresses on :active (translateY).

Usage:
    BASE=http://127.0.0.1:8011 TAG=before python scripts/fe_shot_r0.py
Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8011")
TAG = os.environ.get("TAG", "after")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "scripts", ".fe_shots_r0", TAG)
os.makedirs(SHOTS, exist_ok=True)

G, R, D, X = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def shot(page, name):
    p = os.path.join(SHOTS, f"{name}.png")
    page.screenshot(path=p)
    print(f"  {G}📸{X} {name}  {D}{p}{X}")
    return p


def hash_is(page, expected, timeout=8000):
    page.wait_for_function("h => location.hash.startsWith(h)", arg=expected, timeout=timeout)


def main():
    print(f"{D}BASE={BASE} TAG={TAG}{X}")
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        try:
            # auth
            page.goto(BASE, wait_until="networkidle")
            hash_is(page, "#/auth")
            page.wait_for_selector("#nickname")
            shot(page, "01_auth")

            # --- :active depress check on the guest CTA (mouse down→measure→up=click) ---
            page.fill("#nickname", "초코아빠")
            page.wait_for_function("!document.querySelector('#guest-cta').disabled")
            rest = page.eval_on_selector("#guest-cta", "el => getComputedStyle(el).transform")
            page.hover("#guest-cta")
            page.mouse.down()
            page.wait_for_timeout(120)
            pressed = page.eval_on_selector("#guest-cta", "el => getComputedStyle(el).transform")
            depressed = rest != pressed and pressed not in ("none", "")
            print(f"  {'✅' if depressed else '⚠️ '} CTA :active transform  rest={rest!r} pressed={pressed!r}")
            if not depressed:
                errors.append(f"CTA did not depress on :active (rest={rest}, pressed={pressed})")
            page.mouse.up()  # completes the click → guest signup

            # onboard-pet
            hash_is(page, "#/onboard-pet")
            page.wait_for_selector("#pet-name")
            shot(page, "02_onboard_pet")
            # fill so seg/tags selected states are visible in the shot
            page.fill("#pet-name", "초코")
            page.fill("#pet-breed", "푸들")
            page.click("#pet-size .opt[data-val='small']")
            page.click("#pet-tags .tag >> nth=0")
            shot(page, "02b_onboard_pet_filled")
            page.click("#pet-cta")

            # home
            hash_is(page, "#/home")
            page.wait_for_selector("#start-walk")
            shot(page, "03_home")

            # diary / rooms / my via tab nav
            for route, sel, name in [
                ("#/diary", "#view", "04_diary"),
                ("#/rooms", "#view", "05_rooms"),
                ("#/my", "#view", "06_my"),
            ]:
                page.evaluate("h => location.hash = h", route)
                hash_is(page, route)
                page.wait_for_timeout(450)
                shot(page, name)
        except Exception as e:
            shot(page, "FAIL")
            print(f"  {R}❌ {e}{X}  hash={page.url}")
            browser.close()
            return 1
        browser.close()

    if errors:
        print(f"\n{R}❌ 이슈 {len(errors)}건:{X}")
        for e in errors:
            print("   -", e)
        return 1
    print(f"\n{G}🎉 R0 스크린샷 러너 통과 (콘솔 에러 0, CTA 눌림 확인){X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
