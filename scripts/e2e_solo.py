"""Solo flow: login -> onboard -> start walk -> quest page (NO map, NO other dogs)."""
import uuid
from playwright.sync_api import sync_playwright

LID = "solo_" + uuid.uuid4().hex[:8]
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader"])
    ctx = b.new_context(viewport={"width": 390, "height": 844},
                        geolocation={"latitude": 37.5009, "longitude": 127.0398},
                        permissions=["geolocation"], device_scale_factor=2)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append("PAGEERR " + str(e)))
    pg.on("console", lambda m: errors.append("CON " + m.text) if m.type == "error" else None)
    pg.goto("http://localhost:8000/", wait_until="networkidle")
    pg.fill("#login-id", LID); pg.click("#login-cta")
    pg.wait_for_selector(".cz-card", timeout=8000)
    pg.fill("#pet-breed", "시바"); pg.click("#pet-size .opt[data-val='medium']")
    pg.click("#pet-tags .tag >> nth=0"); pg.fill("#pet-name", "솔로"); pg.click("#pet-cta")
    pg.wait_for_timeout(1200)
    # 홈의 '산책하기'와 동일: walk 시작 + walkId 저장 후 퀘스트 페이지로
    pg.evaluate(
        """async () => {
            const tok = localStorage.getItem('auth_token');
            const petId = localStorage.getItem('pet_id');
            const r = await fetch('/api/walks/start', {method:'POST',
              headers:{'content-type':'application/json','authorization':'Bearer '+tok},
              body: JSON.stringify({pet_id: petId, latitude:37.5009, longitude:127.0398})});
            const j = await r.json();
            localStorage.setItem('active_walk_session_id', j.walk_session_id);
        }"""
    )
    pg.goto("http://localhost:8000/#/walk", wait_until="networkidle")
    pg.wait_for_selector(".quest-stack", timeout=8000)
    pg.wait_for_timeout(800)
    has_map = bool(pg.query_selector("#walk-map, .maplibregl-map"))
    has_other_dogs = bool(pg.query_selector(".dog-pin, #demo-peer-layer"))
    has_end = bool(pg.query_selector(".end-call"))
    quests = pg.eval_on_selector_all(".quest-card", "els => els.length")
    print("quest cards:", quests, "end button:", has_end, "map:", has_map, "other dogs:", has_other_dogs)
    pg.screenshot(path="/tmp/solo_quest.png", full_page=True)
    b.close()

print("errors:", errors)
assert has_end and not has_map and not has_other_dogs, "solo quest page must have end + no map + no other dogs"
assert not errors, errors
print("SOLO OK")
