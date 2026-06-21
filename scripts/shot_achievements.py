#!/usr/bin/env python3
"""Headless screenshot + console-error check for the achievements screens."""
from __future__ import annotations

import asyncio, json, os, time, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8000").rstrip("/")
OUT = Path(os.environ.get("OUT", "/tmp/alpha-blip-ach")); OUT.mkdir(parents=True, exist_ok=True)
TODAY = time.strftime("%Y-%m-%d")


def api(method, path, token=None, body=None):
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def seed():
    import datetime as dt
    u = api("POST", "/api/auth/guest", body={"nickname": f"뱃지-{str(int(time.time()))[-5:]}"})
    p = api("POST", "/api/pets", token=u["auth_token"], body={"name": "콩", "size": "small"})
    # distance + 3-day streak
    for i, d_off in enumerate([0, 1, 2]):
        d = (dt.date.today() - dt.timedelta(days=d_off)).isoformat()
        api("POST", "/api/records", token=u["auth_token"],
            body={"visibility": "diary", "walked_at": d, "distance_meters": 6000 if i == 0 else 400, "clip_ids": []})
    return u, p


async def main():
    u, p = seed()
    errors = []
    async with async_playwright() as pw:
        chrome = "/usr/bin/chromium-browser"
        browser = await pw.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        await ctx.add_init_script(
            f"localStorage.setItem('auth_token',{json.dumps(u['auth_token'])});"
            f"localStorage.setItem('user_id',{json.dumps(u['user_id'])});"
            f"localStorage.setItem('pet_id',{json.dumps(p['pet_id'])});"
        )
        page = await ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto(f"{BASE}/#/my")
        await page.wait_for_selector(".ach-card")
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(OUT / "my_with_ach_card.png"), full_page=True)

        await page.goto(f"{BASE}/#/achievements")
        await page.wait_for_selector(".ach-grid .ach-tile")
        await page.wait_for_timeout(900)
        unlocked = await page.locator(".ach-tile.unlocked").count()
        locked = await page.locator(".ach-tile.locked").count()
        await page.screenshot(path=str(OUT / "achievements_grid.png"), full_page=True)

        print(f"unlocked tiles={unlocked} locked tiles={locked} console_errors={len(errors)}")
        if errors:
            print("ERRORS:", errors)
        assert unlocked >= 2, f"expected >=2 unlocked tiles, got {unlocked}"
        assert not errors, "console errors present"
        print("PASS: achievements screens render, 0 console errors")
        await ctx.close(); await browser.close()


asyncio.run(main())
