"""Matched flow: request->accept(mock)->matching met-gate ([만났습니다]/[산책종료], 2 dogs only)->quest page."""
import json
import urllib.request as u
import uuid
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
LID = "match_" + uuid.uuid4().hex[:8]


def api(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


# --- API 셋업: 유저+펫+데모(목업)+요청(자동수락) ---
login = api("POST", "/api/auth/login", {"login_id": LID})
tok, uid = login["auth_token"], login["user_id"]
api("POST", "/api/pets", {"name": "매치", "breed": "푸들", "size": "small", "personality_tags": ["활발함"]}, tok=tok)
demo = api("POST", "/api/demo/setup", {}, tok=tok)
rid = api("POST", "/api/match-requests", {"receiver_walk_session_id": demo["mock_walk_session_id"]}, tok=tok)["match_request_id"]

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
    pg.evaluate("([t,u]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); }", [tok, uid])
    pg.goto(f"http://localhost:8000/#/matching/{rid}", wait_until="networkidle")
    pg.wait_for_function("() => { const b=document.getElementById('w3-cta'); return b && !b.disabled && b.textContent.includes('만났'); }", timeout=10000)
    met_text = pg.eval_on_selector("#w3-cta", "e => e.textContent")
    has_end = bool(pg.query_selector("#w3-end"))
    other_pins = pg.eval_on_selector_all(".dog-pin", "els => els.length")  # nearby markers must NOT appear
    print("met btn:", met_text, "end btn:", has_end, "nearby pins:", other_pins)
    pg.screenshot(path="/tmp/match_gate.png")
    # 만났습니다 → mock 자동 met → 퀘스트 페이지
    pg.click("#w3-cta")
    pg.wait_for_selector(".quest-stack", timeout=10000)
    print("after met url:", pg.url)
    b.close()

print("errors:", errors)
assert "만났" in met_text and has_end and other_pins == 0, "met-gate: 만났습니다+산책종료, no nearby dogs"
assert "walk" in pg.url, "after both met -> quest page (/walk)"
assert not errors, errors
print("MATCH OK")
