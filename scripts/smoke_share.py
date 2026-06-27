"""Verify dog SVG -> canvas -> PNG share path (canvas must not be tainted)."""
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto("http://localhost:8000/", wait_until="networkidle")
    size = pg.evaluate(
        """async () => {
            const { makeDogPng } = await import('/static/js/dog/share.js');
            const { appearanceForBreed } = await import('/static/js/dog/params.js');
            const blob = await makeDogPng(
              { ...appearanceForBreed('corgi'), equipped: ['party_hat'] },
              { name: '테스트', size: 384 });
            return blob ? blob.size : 0;
        }"""
    )
    print("png blob size:", size)
    data_url = pg.evaluate(
        """async () => {
            const { makeDogPng } = await import('/static/js/dog/share.js');
            const { appearanceForBreed } = await import('/static/js/dog/params.js');
            const blob = await makeDogPng(
              { ...appearanceForBreed('shiba'), equipped: ['crown'] },
              { name: '두부', size: 384 });
            return await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(blob); });
        }"""
    )
    import base64
    with open("/tmp/share_dog.png", "wb") as f:
        f.write(base64.b64decode(data_url.split(",", 1)[1]))
    b.close()

print("errors:", errors)
assert size > 2000, f"png generation failed (size={size})"
print("SHARE OK")
