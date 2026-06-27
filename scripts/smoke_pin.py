"""Onboard with geolocation, go to walk map, drop a pin, assert override set + screenshot."""
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader"])
    ctx = b.new_context(viewport={"width": 390, "height": 820},
                        geolocation={"latitude": 37.5006, "longitude": 127.0406},
                        permissions=["geolocation"])
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("dialog", lambda d: d.dismiss())
    pg.goto("http://localhost:8000/", wait_until="networkidle")
    pg.fill("#nickname", "핀테스트")
    pg.click("#guest-cta")
    pg.wait_for_selector(".cz-card")
    pg.fill("#pet-breed", "시바")
    pg.click("#pet-size .opt[data-val='small']")
    pg.click("#pet-tags .tag >> nth=0")
    pg.fill("#pet-name", "핀")
    pg.click("#pet-cta")
    pg.wait_for_timeout(1000)
    pg.goto("http://localhost:8000/#/walk", wait_until="networkidle")
    pg.wait_for_selector("#pin-btn", timeout=8000)
    pg.wait_for_timeout(1800)
    has_canvas = pg.eval_on_selector("#walk-map", "e => !!e.querySelector('canvas')") if pg.query_selector("#walk-map") else False
    print("map canvas present:", has_canvas)
    pg.screenshot(path="/tmp/walk_pin.png")
    ov0 = pg.evaluate("localStorage.getItem('override_location')")
    print("override before:", ov0)
    pg.click("#pin-btn")
    pg.wait_for_timeout(300)
    box = pg.query_selector("#walk-map").bounding_box()
    pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 - 40)
    pg.wait_for_timeout(900)
    ov1 = pg.evaluate("localStorage.getItem('override_location')")
    print("override after pin:", ov1)
    pg.screenshot(path="/tmp/walk_pin2.png")
    b.close()

print("console errors:", errors)
assert ov1, "override not set after pin drop"
print("PIN OK")
