"""E2E loop: login -> onboard -> walk -> camera(2s, fake) -> end -> record(diary). No console errors."""
import uuid
from playwright.sync_api import sync_playwright

LID = "loop_" + uuid.uuid4().hex[:8]
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=[
        "--use-gl=swiftshader",
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
    ])
    ctx = b.new_context(viewport={"width": 390, "height": 844},
                        geolocation={"latitude": 37.5009, "longitude": 127.0398},
                        permissions=["geolocation", "camera", "microphone"], device_scale_factor=2)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append("PAGEERR " + str(e)))
    pg.on("console", lambda m: errors.append("CON " + m.text) if m.type == "error" else None)
    pg.goto("http://localhost:8000/", wait_until="networkidle")
    pg.fill("#login-id", LID); pg.click("#login-cta")
    pg.wait_for_selector(".cz-card", timeout=8000)
    pg.fill("#pet-breed", "말티즈"); pg.click("#pet-size .opt[data-val='small']")
    pg.click("#pet-tags .tag >> nth=0"); pg.fill("#pet-name", "루프"); pg.click("#pet-cta")
    pg.wait_for_timeout(1200)

    # 데모 위치 고정(테스트에서 GPS 핸드셰이크 회피) 후 산책 화면으로
    pg.evaluate("() => localStorage.setItem('blip_demo_context', JSON.stringify({lat:37.5009,lng:127.0398}))")
    pg.goto("http://localhost:8000/#/walk", wait_until="networkidle")
    pg.wait_for_selector("#walk-shoot", timeout=10000); pg.wait_for_timeout(1500)
    pg.screenshot(path="/tmp/loop_walk.png")

    pg.click("#walk-shoot")
    pg.wait_for_selector("#cam-rec", timeout=8000); pg.wait_for_timeout(800)
    pg.click("#cam-rec")
    pg.wait_for_selector("#walk-shoot", timeout=12000); pg.wait_for_timeout(800)  # back after upload

    pg.click("#walk-end")
    pg.wait_for_timeout(2500)
    print("after end url:", pg.url)
    pg.wait_for_timeout(2000)  # let background merge run
    pg.reload(); pg.wait_for_timeout(1500)
    pg.screenshot(path="/tmp/loop_diary.png", full_page=True)
    b.close()

print("errors:", errors)
assert "diary" in pg.url, f"did not reach diary: {pg.url}"
assert not errors, errors
print("LOOP OK")
