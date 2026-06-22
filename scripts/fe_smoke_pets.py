#!/usr/bin/env python3
"""FE smoke: 반려동물 리스트 + 펫별 고정 캐릭터.

FE0(가입+첫 펫) 재사용 → API로 견종/크기/성격이 다른 펫 3마리 추가 →
#/pets 진입해 .pet-row N개 + 각 행의 캐릭터 SVG 렌더 확인 + 홈 펫 카드 캐릭터 확인.
콘솔 에러 0 단언.

Usage: BASE=http://127.0.0.1:8011 python scripts/fe_smoke_pets.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright  # noqa: E402

from fe_smoke import BASE, attach_console_guard, hash_is, run_fe0, shot  # noqa: E402

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

EXTRA_PETS = [
    {"name": "망고", "breed": "시바", "size": "medium", "personality_tags": ["차분함"]},
    {"name": "보리", "breed": "비숑", "size": "large", "personality_tags": ["온순함", "사람좋아"]},
    {"name": "콩이", "breed": "웰시코기", "size": "small", "personality_tags": ["겁많음", "호기심"]},
]


def main() -> int:
    print(f"{DIM}BASE={BASE}{RESET}")
    errors: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        page = ctx.new_page()
        attach_console_guard(page, errors)
        try:
            # FE0: 가입 + 첫 펫(초코·푸들·소형·활발함)
            run_fe0(page, errors, nickname="펫집사")

            # 견종/크기/성격이 다른 펫 추가 (API)
            page.evaluate(
                """async (pets) => { for (const p of pets) { await window.blip.api.post('/pets', p); } }""",
                EXTRA_PETS,
            )

            # 마이 → 반려동물 관리(=/pets) 링크 동작도 함께 확인
            page.evaluate("window.blip.navigate('/my')")
            hash_is(page, "#/my")
            page.wait_for_selector(".list-link")
            page.evaluate("window.blip.navigate('/pets')")
            hash_is(page, "#/pets")

            page.wait_for_selector(".pet-row")
            rows = page.eval_on_selector_all(".pet-row", "els => els.length")
            svgs = page.eval_on_selector_all(".pet-row .bp-char svg", "els => els.length")
            names = page.eval_on_selector_all(
                ".pet-row-name", "els => els.map(e => e.textContent)"
            )
            assert rows == 4, f"expected 4 pet rows, got {rows}"
            assert svgs == 4, f"expected 4 character SVGs, got {svgs}"
            p = shot(page, "pets_10_list")
            print(f"  {GREEN}✅{RESET} /pets 4행 + 캐릭터 SVG 4개 렌더  names={names}  {DIM}{p}{RESET}")

            # tap → 수정 화면 진입
            page.click(".pet-row >> nth=0")
            hash_is(page, "#/pet/")
            page.wait_for_selector("#pet-name")
            print(f"  {GREEN}✅{RESET} 펫 행 탭 → 수정 화면(/pet/:id) 진입")

            # 홈 펫 카드의 캐릭터
            page.evaluate("window.blip.navigate('/home')")
            hash_is(page, "#/home")
            page.wait_for_selector("#my-pet-card .bp-char svg")
            p = shot(page, "pets_11_home_card")
            print(f"  {GREEN}✅{RESET} 홈 펫 카드 캐릭터 렌더  {DIM}{p}{RESET}")

            # 프로필(/my) 헤드 캐릭터
            page.evaluate("window.blip.navigate('/my')")
            hash_is(page, "#/my")
            page.wait_for_selector(".my-head .bp-char svg")
            print(f"  {GREEN}✅{RESET} 프로필 헤드 캐릭터 렌더")

            # 일관성: 같은 펫(초코)이 /pets와 홈에서 동일 SVG로 렌더(=고정)
            page.evaluate("window.blip.navigate('/pets')")
            hash_is(page, "#/pets")
            page.wait_for_selector(".pet-row .bp-char svg")
            pets_svg = page.eval_on_selector(".pet-row .bp-char svg", "e => e.innerHTML")
            page.evaluate("window.blip.navigate('/home')")
            hash_is(page, "#/home")
            page.wait_for_selector("#my-pet-card .bp-char svg")
            home_svg = page.eval_on_selector("#my-pet-card .bp-char svg", "e => e.innerHTML")
            assert pets_svg == home_svg, "same pet must render identical character (fixed)"
            print(f"  {GREEN}✅{RESET} 동일 펫 → 동일 캐릭터(고정) 일관성 확인")

            # 방: 생성 후 멤버 칩 캐릭터
            rid = page.evaluate(
                "async () => (await window.blip.api.post('/rooms', {name:'캐릭터방', mode:'walk_friend'})).room_id"
            )
            page.evaluate("(id) => window.blip.navigate('/room/' + id)", rid)
            hash_is(page, "#/room/")
            page.wait_for_selector(".member-chip .bp-char svg")
            p = shot(page, "pets_12_room")
            print(f"  {GREEN}✅{RESET} 방 멤버 칩 캐릭터 렌더  {DIM}{p}{RESET}")

            # 데모 산책: 지도 마커(상대 강아지) 캐릭터
            page.evaluate("window.blip.navigate('/home')")
            hash_is(page, "#/home")
            page.click("#demo-setup")
            hash_is(page, "#/walk")
            page.wait_for_selector(".dog-marker .bp-char svg", timeout=12000)
            p = shot(page, "pets_13_walk")
            print(f"  {GREEN}✅{RESET} 산책 지도 마커 캐릭터 렌더  {DIM}{p}{RESET}")

        except Exception as e:
            shot(page, "pets_FAIL")
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}url={page.url}{RESET}")
            browser.close()
            return 1
        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 펫 리스트 + 캐릭터 스모크 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
