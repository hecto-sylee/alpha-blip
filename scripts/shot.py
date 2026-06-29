"""Headless screenshot helper (preview_screenshot wedges in this env).

Usage: python3 scripts/shot.py <url> <out.png> [width] [full]
"""
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/shot.png"
width = int(sys.argv[3]) if len(sys.argv) > 3 else 900
full = (sys.argv[4] if len(sys.argv) > 4 else "full") != "viewport"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": 1200}, device_scale_factor=2)
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_timeout(600)
    pg.screenshot(path=out, full_page=full)
    b.close()
print("saved", out)
