#!/usr/bin/env python3
"""Capture the five UI groups used for final before/after review."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from html import escape

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
TAG = os.environ.get("TAG", "after")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "scripts", ".fe_shots_groups", TAG)
LAT, LNG = 37.5665, 126.9780
os.makedirs(SHOTS, exist_ok=True)
GROUPS = [
    ("01_onboarding", "온보딩"),
    ("02_walk", "산책"),
    ("03_room", "방"),
    ("04_record", "기록"),
    ("05_my", "마이"),
]
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon")


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode() or "{}")


def make_user(nick, petname):
    u = apicall("POST", "/auth/guest", body={"nickname": nick})
    p = apicall(
        "POST",
        "/pets",
        token=u["auth_token"],
        body={"name": petname, "breed": "푸들", "size": "small", "personality_tags": ["활발함"]},
    )
    return u, p["pet_id"]


def inject(page, user, pet_id):
    page.goto(BASE, wait_until="domcontentloaded")
    page.evaluate(
        """([t,u,p]) => {
          localStorage.setItem('auth_token', t);
          localStorage.setItem('user_id', u);
          localStorage.setItem('pet_id', p);
        }""",
        [user["auth_token"], user["user_id"], pet_id],
    )


def shot(page, name):
    path = os.path.join(SHOTS, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(path)


def build_gallery():
    root = os.path.join(ROOT, "scripts", ".fe_shots_groups")
    before = os.path.join(root, "before")
    after = os.path.join(root, "after")
    if not os.path.isdir(before) or not os.path.isdir(after):
        return
    rows = []
    for stem, title in GROUPS:
        b = os.path.join(before, f"{stem}.png")
        a = os.path.join(after, f"{stem}.png")
        if not os.path.exists(b) or not os.path.exists(a):
            continue
        b_rel = escape(os.path.relpath(b, root))
        a_rel = escape(os.path.relpath(a, root))
        rows.append(f"""
        <section>
          <h2>{escape(title)}</h2>
          <div class="pair">
            <figure><figcaption>Before</figcaption><img src="{b_rel}" alt="{escape(title)} before"></figure>
            <figure><figcaption>After</figcaption><img src="{a_rel}" alt="{escape(title)} after"></figure>
          </div>
        </section>""")
    if not rows:
        return
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>blip UI Before/After</title>
  <style>
    body {{ margin: 0; padding: 24px; font-family: system-ui, sans-serif; background: #f7f2ee; color: #2b2420; }}
    h1 {{ margin: 0 0 20px; font-size: 24px; }}
    section {{ margin: 0 0 28px; }}
    h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .pair {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: start; }}
    figure {{ margin: 0; padding: 10px; background: #fff; border-radius: 16px; box-shadow: 0 3px 0 #e2d8d0, 0 8px 18px rgba(43,36,32,.10); }}
    figcaption {{ margin: 0 0 8px; font-weight: 800; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 10px; }}
    @media (max-width: 760px) {{ .pair {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>blip UI Before/After</h1>
  {''.join(rows)}
</body>
</html>
"""
    out = os.path.join(root, "compare.html")
    with open(out, "w", encoding="utf-8") as f:
      f.write(html)
    print(out)


def main():
    errors = []
    user, pet_id = make_user(f"{TAG}-캡처", "초코")
    room = apicall("POST", "/rooms", token=user["auth_token"], body={"name": f"{TAG} 산책방", "mode": "walk_friend"})
    apicall(
        "POST",
        "/records",
        token=user["auth_token"],
        body={
            "visibility": "room",
            "room_id": room["room_id"],
            "walked_at": "2026-06-12",
            "text": f"{TAG} 방 로그",
            "clip_ids": [],
        },
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader"])
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896},
            locale="ko-KR",
            geolocation={"latitude": LAT, "longitude": LNG},
            permissions=["geolocation"],
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(str(e))
                if not any(k in str(e).lower() for k in IGNORE) else None)

        # onboarding
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_selector("#nickname")
        shot(page, "01_onboarding")

        inject(page, user, pet_id)

        # walk
        page.goto(BASE + "/#/walk", wait_until="networkidle")
        page.wait_for_selector(".map-screen, #walk-fallback", timeout=10000)
        shot(page, "02_walk")

        # room
        page.goto(BASE + f"/#/room/{room['room_id']}", wait_until="networkidle")
        page.wait_for_selector("#post-record", timeout=10000)
        shot(page, "03_room")

        # record
        page.goto(BASE + f"/#/record?room={room['room_id']}", wait_until="networkidle")
        page.wait_for_selector("#record-editor", timeout=10000)
        shot(page, "04_record")

        # my
        page.goto(BASE + "/#/my", wait_until="networkidle")
        page.wait_for_selector("#logout", timeout=10000)
        shot(page, "05_my")

        browser.close()

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    build_gallery()
    return 0


if __name__ == "__main__":
    sys.exit(main())
