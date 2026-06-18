#!/usr/bin/env python3
"""Headless Playwright verification for docs/mvp_refactor/03_motion_spec.md."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, expect


BASE = os.environ.get("BASE", "http://127.0.0.1:8000").rstrip("/")
OUT_DIR = Path(os.environ.get("MOTION_OUT", "/tmp/alpha-blip-motion"))
TODAY = dt.date.today().isoformat()


def api(method: str, path: str, token: str | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {raw}") from exc


def make_user(label: str) -> dict[str, str]:
    suffix = str(int(time.time() * 1000))[-7:]
    user = api("POST", "/api/auth/guest", body={"nickname": f"{label}-{suffix}"})
    pet = api(
        "POST",
        "/api/pets",
        token=user["auth_token"],
        body={
            "name": f"{label}Dog",
            "breed": "Poodle",
            "size": "small",
            "personality_tags": ["active"],
            "walk_style": "normal",
        },
    )
    return {"user_id": user["user_id"], "token": user["auth_token"], "pet_id": pet["pet_id"]}


def prepare_normal_data() -> dict[str, Any]:
    a = make_user("motionA")
    b = make_user("motionB")

    walk_a = api(
        "POST",
        "/api/walks/start",
        token=a["token"],
        body={"pet_id": a["pet_id"], "latitude": 37.5665, "longitude": 126.9780},
    )["walk_session_id"]
    walk_b = api(
        "POST",
        "/api/walks/start",
        token=b["token"],
        body={"pet_id": b["pet_id"], "latitude": 37.5678, "longitude": 126.9785},
    )["walk_session_id"]
    req = api(
        "POST",
        "/api/match-requests",
        token=a["token"],
        body={"receiver_walk_session_id": walk_b},
    )["match_request_id"]
    session = api("PATCH", f"/api/match-requests/{req}/accept", token=b["token"])["match_session_id"]

    room = api("POST", "/api/rooms", token=a["token"], body={"name": "Motion Feed", "mode": "walk_friend"})
    api("POST", f"/api/rooms/{room['room_id']}/join", token=b["token"])
    api(
        "POST",
        "/api/records",
        token=b["token"],
        body={
            "visibility": "room",
            "room_id": room["room_id"],
            "walked_at": TODAY,
            "duration_minutes": 18,
            "distance_meters": 900,
            "text": "Room feed stagger source",
            "clip_ids": [],
        },
    )
    return {"a": a, "b": b, "walk_a": walk_a, "walk_b": walk_b, "session": session, "room": room}


class Watch:
    def __init__(self, label: str) -> None:
        self.label = label
        self.errors: list[str] = []

    def attach(self, page) -> None:
        page.on("console", self._console)
        page.on("pageerror", lambda exc: self.errors.append(f"pageerror: {exc}"))

    def _console(self, msg) -> None:
        if msg.type == "error":
            self.errors.append(f"console error: {msg.text}")

    def assert_clean(self) -> None:
        if self.errors:
            raise AssertionError(f"{self.label} console/page errors:\n" + "\n".join(self.errors))


def local_storage_script(session: dict[str, str]) -> str:
    return "\n".join(
        [
            f"localStorage.setItem('auth_token', {json.dumps(session['token'])});",
            f"localStorage.setItem('user_id', {json.dumps(session['user_id'])});",
            f"localStorage.setItem('pet_id', {json.dumps(session['pet_id'])});",
        ]
    )


async def launch_browser(pw):
    chrome = os.environ.get("CHROME", "/usr/bin/google-chrome")
    if Path(chrome).exists():
        return await pw.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox"])
    return await pw.chromium.launch(headless=True)


async def screenshot(page, name: str) -> None:
    await page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=True)


async def style_of(page, selector: str) -> dict[str, str]:
    return await page.locator(selector).evaluate(
        """el => {
          const s = getComputedStyle(el);
          return { opacity: s.opacity, transform: s.transform };
        }"""
    )


def assert_not_collapsed(style: dict[str, str], label: str) -> None:
    collapsed = {"matrix(0, 0, 0, 0, 0, 0)", "matrix3d(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)"}
    if style["transform"] in collapsed:
        raise AssertionError(f"{label} collapsed to zero transform: {style}")


async def run_normal(pw, data: dict[str, Any], lines: list[str]) -> None:
    browser = await launch_browser(pw)
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        geolocation={"latitude": 37.5665, "longitude": 126.9780},
        permissions=["geolocation"],
    )
    await context.add_init_script(local_storage_script(data["a"]))
    page = await context.new_page()
    watch = Watch("normal")
    watch.attach(page)

    await page.goto(f"{BASE}/#/home")
    await expect(page.locator("#start-walk")).to_be_visible()
    await screenshot(page, "01_normal_home")

    motion_import = await page.evaluate(
        """async () => {
          const m = await import('/static/js/motion.js');
          return Boolean(m.animate && m.springIn && m.staggerIn && m.sheetUp && m.SPRING && m.SOFT);
        }"""
    )
    assert motion_import is True
    lines.append("PASS normal: motion.js ESM import resolved with wrappers and spring tokens")

    await page.evaluate("window.blip.navigate('/rooms')")
    await page.wait_for_selector("#room-feed .tl-item")
    early = await style_of(page, ".screen")
    await page.wait_for_timeout(900)
    late = await style_of(page, ".screen")
    screen_motion = await page.locator(".screen").get_attribute("data-motion")
    assert screen_motion == "spring-in"
    assert late["opacity"] == "1"
    assert_not_collapsed(late, "screen transition")
    lines.append(f"PASS normal: screen transition springIn data-motion={screen_motion}, early={early}, late={late}")

    feed_motion = await page.locator("#room-feed .tl-item").first.get_attribute("data-motion")
    assert feed_motion == "stagger-in"
    await screenshot(page, "02_normal_rooms_feed_stagger")
    lines.append("PASS normal: room feed cards received staggerIn")

    await page.evaluate(
        """async () => {
          const ui = await import('/static/js/ui.js');
          ui.bottomSheet(() => ui.el('div.stack', { id: 'motion-test-sheet' }, [
            ui.el('div.h2', { text: 'Sheet motion' }),
            ui.el('button.cta', { text: 'Done' })
          ]));
        }"""
    )
    await page.wait_for_selector("#motion-test-sheet")
    sheet_start = await style_of(page, ".sheet")
    await page.wait_for_timeout(650)
    sheet_end = await style_of(page, ".sheet")
    sheet_motion = await page.locator(".sheet").get_attribute("data-motion")
    assert sheet_motion == "sheet-up"
    assert sheet_end["transform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)")
    assert_not_collapsed(sheet_end, "bottom sheet")
    await screenshot(page, "03_normal_bottom_sheet_up")
    lines.append(f"PASS normal: bottomSheet sheetUp start={sheet_start}, end={sheet_end}")

    await page.locator(".sheet-scrim").click(position={"x": 8, "y": 8})
    await page.wait_for_timeout(420)

    await page.evaluate("window.blip.navigate('/quest')")
    await page.wait_for_selector(".quest-card")
    await page.wait_for_timeout(900)
    quest_motion = await page.locator(".quest-card").first.get_attribute("data-motion")
    assert quest_motion == "stagger-in"
    await screenshot(page, "04_normal_quest_stagger")
    lines.append("PASS normal: quest candidate cards received staggerIn")

    await page.evaluate(f"window.blip.navigate('/session/{data['session']}')")
    await page.wait_for_selector(".celebrate-layer[data-motion='celebrate']")
    await screenshot(page, "05_normal_matching_celebrate")
    lines.append("PASS normal: matching session triggered mascot/confetti celebrate layer")

    await page.evaluate("window.blip.navigate('/record')")
    await page.wait_for_selector("#save-record")
    await page.locator("#save-record").scroll_into_view_if_needed()
    await page.wait_for_timeout(300)
    await page.locator("#save-record").evaluate(
        """el => el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))"""
    )
    try:
        await page.wait_for_function(
            """() => ['started', 'done'].includes(document.documentElement.dataset.recordSaveMotion)"""
        )
    except Exception as exc:
        detail = await page.evaluate(
            """() => ({
              hash: location.hash,
              recordSaveMotion: document.documentElement.dataset.recordSaveMotion || null,
              button: (() => {
                const b = document.querySelector('#save-record');
                return b ? { disabled: b.disabled, text: b.textContent, connected: b.isConnected } : null;
              })(),
              toasts: Array.from(document.querySelectorAll('.toast')).map(t => t.textContent)
            })"""
        )
        await screenshot(page, "06_normal_record_debug")
        raise AssertionError(f"record save motion did not start; state={detail}") from exc
    save_motion_state = await page.evaluate("document.documentElement.dataset.recordSaveMotion")
    assert save_motion_state in ("started", "done")
    await screenshot(page, "06_normal_record_fly_to_calendar")
    await page.wait_for_url("**/#/diary?saved=1", timeout=5000)
    await page.wait_for_selector(".cal[data-settle='calendar']")
    await screenshot(page, "07_normal_diary_calendar_settle")
    lines.append("PASS normal: record save flew toward diary and diary calendar settled")

    watch.assert_clean()
    lines.append("PASS normal: console/page errors = 0")
    await context.close()
    await browser.close()


async def run_reduced(pw, lines: list[str]) -> None:
    browser = await launch_browser(pw)
    context = await browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    page = await context.new_page()
    watch = Watch("reduced")
    watch.attach(page)

    await page.goto(f"{BASE}/")
    await page.wait_for_selector("#nickname")
    await page.fill("#nickname", f"reduced-{int(time.time())}")
    await page.click("#guest-cta")
    await page.wait_for_selector("#pet-name")
    await page.fill("#pet-name", "ReducedDog")
    await page.fill("#pet-breed", "Poodle")
    await page.click("#pet-size [data-val='small']")
    await page.click("#pet-tags .tag")
    await page.click("#pet-cta")
    await page.wait_for_selector("#start-walk")
    await screenshot(page, "08_reduced_signup_pet_home")

    home_style = await style_of(page, ".screen")
    assert home_style["opacity"] == "1"
    assert home_style["transform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)")
    lines.append(f"PASS reduced: signup -> pet -> home completed with reduced screen style={home_style}")

    token = await page.evaluate("localStorage.getItem('auth_token')")
    user_id = await page.evaluate("localStorage.getItem('user_id')")
    pet_id = await page.evaluate("localStorage.getItem('pet_id')")
    room = api("POST", "/api/rooms", token=token, body={"name": "Reduced Feed", "mode": "walk_friend"})
    api(
        "POST",
        "/api/records",
        token=token,
        body={
            "visibility": "room",
            "room_id": room["room_id"],
            "walked_at": TODAY,
            "text": f"Reduced feed for {user_id}/{pet_id}",
            "clip_ids": [],
        },
    )
    await page.evaluate("window.blip.navigate('/rooms')")
    await page.wait_for_selector("#room-feed .tl-item")
    await screenshot(page, "09_reduced_rooms_feed")
    reduced_feed_motion = await page.locator("#room-feed .tl-item").first.get_attribute("data-motion")
    assert reduced_feed_motion is None
    lines.append("PASS reduced: room feed loads and Motion One stagger is skipped")

    watch.assert_clean()
    lines.append("PASS reduced: console/page errors = 0")
    await context.close()
    await browser.close()


async def run_cdn_failure(pw, data: dict[str, Any], lines: list[str]) -> None:
    browser = await launch_browser(pw)
    context = await browser.new_context(viewport={"width": 390, "height": 844})
    await context.add_init_script(local_storage_script(data["a"]))
    await context.route("https://cdn.jsdelivr.net/npm/motion@11/**", lambda route: route.abort())
    page = await context.new_page()
    watch = Watch("cdn-failure")
    watch.attach(page)

    await page.goto(f"{BASE}/#/home")
    await page.wait_for_selector("#start-walk")
    await page.wait_for_timeout(1500)
    home_style = await style_of(page, ".screen")
    assert home_style["opacity"] == "1"
    await screenshot(page, "10_cdn_failure_home_fallback")

    await page.evaluate("window.blip.navigate('/rooms')")
    await page.wait_for_selector("#room-feed .tl-item")
    await page.wait_for_timeout(1500)
    room_style = await style_of(page, ".screen")
    assert room_style["opacity"] == "1"
    await screenshot(page, "11_cdn_failure_rooms_fallback")
    lines.append(f"PASS cdn-failure: screens stay visible when Motion CDN import is aborted, home={home_style}, rooms={room_style}")

    await context.close()
    await browser.close()


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"BASE={BASE}", f"OUT_DIR={OUT_DIR}"]
    data = prepare_normal_data()
    async with async_playwright() as pw:
        await run_normal(pw, data, lines)
        await run_reduced(pw, lines)
        await run_cdn_failure(pw, data, lines)
    log = "\n".join(lines) + "\n"
    (OUT_DIR / "motion_verify.log").write_text(log, encoding="utf-8")
    print(log)


if __name__ == "__main__":
    asyncio.run(main())
