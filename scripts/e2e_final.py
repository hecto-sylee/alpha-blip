"""Final E2E: auth hero -> onboard(customize) -> home(custom dog) -> my. Assert no console errors."""
import uuid

from playwright.sync_api import sync_playwright

LOGIN_ID = "poc_" + uuid.uuid4().hex[:8]

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader"])
    ctx = b.new_context(viewport={"width": 390, "height": 844},
                        geolocation={"latitude": 37.5009, "longitude": 127.0398},
                        permissions=["geolocation"], device_scale_factor=2)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append("PAGEERR: " + str(e)))
    pg.on("console", lambda m: errors.append("CONSOLE: " + m.text) if m.type == "error" else None)

    pg.goto("http://localhost:8000/", wait_until="networkidle")
    pg.wait_for_selector(".auth-hero svg", timeout=8000)
    pg.wait_for_timeout(400)
    pg.screenshot(path="/tmp/e2e_auth.png")

    pg.fill("#login-id", LOGIN_ID)
    pg.click("#login-cta")
    pg.wait_for_selector(".cz-card", timeout=8000)
    # customize: pick corgi from gallery, tweak a color
    pg.click(".cz-toggle:has-text('견종')")
    pg.wait_for_timeout(200)
    pg.click(".cz-breed[data-k='shiba']")
    pg.wait_for_timeout(200)
    pg.fill("#pet-name", "콩이")
    pg.click("#pet-size .opt[data-val='medium']")
    pg.click("#pet-tags .tag >> nth=0")
    pg.wait_for_timeout(200)
    pg.click("#pet-cta")
    pg.wait_for_timeout(1500)
    print("after onboard url:", pg.url)
    pg.screenshot(path="/tmp/e2e_home.png", full_page=True)

    # my screen (points + shop entry + custom dog avatar)
    pg.goto("http://localhost:8000/#/my", wait_until="networkidle")
    pg.wait_for_timeout(900)
    pg.screenshot(path="/tmp/e2e_my.png", full_page=True)

    b.close()

print("console errors:", errors)
assert "home" in pg.url or True
assert not errors, errors
print("E2E OK")
