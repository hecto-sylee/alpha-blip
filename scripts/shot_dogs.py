import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dogs.png"
y = int(sys.argv[2]) if len(sys.argv) > 2 else 0
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 720, "height": 980}, device_scale_factor=1)
    pg.goto("http://localhost:8000/static/_dogtest.html", wait_until="networkidle")
    pg.wait_for_timeout(500)
    pg.evaluate(f"window.scrollTo(0,{y})")
    pg.wait_for_timeout(200)
    pg.screenshot(path=out, full_page=False)
    b.close()
print("saved", out)
