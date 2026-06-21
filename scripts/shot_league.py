#!/usr/bin/env python3
"""Headless screenshot + console check for the 랭킹 tab (league + achievements)."""
from __future__ import annotations

import asyncio, json, os, time, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8000").rstrip("/")
OUT = Path(os.environ.get("OUT", "/tmp/alpha-blip-league")); OUT.mkdir(parents=True, exist_ok=True)
TODAY = time.strftime("%Y-%m-%d")


def api(method, path, token=None, body=None):
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode(); return json.loads(raw) if raw else {}


def seed():
    u = api("POST", "/api/auth/guest", body={"nickname": f"랭킹-{str(int(time.time()))[-5:]}"})
    p = api("POST", "/api/pets", token=u["auth_token"], body={"name": "콩", "size": "small"})
    for _ in range(5):  # 점수 적립 → 보드 중상위에 위치
        api("POST", "/api/records", token=u["auth_token"],
            body={"visibility": "diary", "walked_at": TODAY, "distance_meters": 800, "clip_ids": []})
    return u, p


async def main():
    u, p = seed()
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path="/usr/bin/chromium-browser", headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        await ctx.add_init_script(
            f"localStorage.setItem('auth_token',{json.dumps(u['auth_token'])});"
            f"localStorage.setItem('user_id',{json.dumps(u['user_id'])});"
            f"localStorage.setItem('pet_id',{json.dumps(p['pet_id'])});"
        )
        page = await ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 탭바의 랭킹 탭이 존재하는지 + 클릭 진입
        await page.goto(f"{BASE}/#/home")
        await page.wait_for_selector('#tabbar a[data-tab="league"]')
        await page.click('#tabbar a[data-tab="league"]')
        await page.wait_for_selector(".league-board .lb-row")
        await page.wait_for_timeout(800)
        rows = await page.locator(".lb-row").count()
        me = await page.locator(".lb-row.me").count()
        tab_active = await page.locator('#tabbar a[data-tab="league"].active').count()
        see_all = await page.locator("#see-all-ach").count()
        await page.screenshot(path=str(OUT / "league_tab.png"), full_page=True)

        # "모든 업적 보기" → 그리드
        await page.click("#see-all-ach")
        await page.wait_for_selector(".ach-grid .ach-tile")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "league_to_achievements.png"), full_page=True)

        print(f"lb_rows={rows} me_rows={me} tab_active={tab_active} see_all_btn={see_all} console_errors={len(errors)}")
        if errors: print("ERRORS:", errors)
        assert rows == 30, f"expected 30 board rows, got {rows}"
        assert me == 1, f"expected exactly 1 me-row, got {me}"
        assert tab_active == 1, "league tab not marked active"
        assert see_all == 1, "see-all-achievements button missing"
        assert not errors, "console errors present"
        print("PASS: 랭킹 tab renders (30-row board, me highlighted), view-all works, 0 console errors")
        await ctx.close(); await browser.close()


asyncio.run(main())
