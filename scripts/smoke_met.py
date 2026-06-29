"""Smoke: match-request to mock -> auto-accept -> session -> POST met -> both_met (mock auto-met)."""
import json
import time
import urllib.request as u

B = "http://localhost:8000"


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


tok = req("POST", "/api/auth/login", {"login_id": "met_" + time.strftime("%H%M%S")})["auth_token"]
req("POST", "/api/pets", {"name": "만남이", "breed": "믹스", "size": "medium", "personality_tags": ["활발함"]}, tok=tok)
demo = req("POST", "/api/demo/setup", {}, tok=tok)
mock_ws = demo["mock_walk_session_id"]

rid = req("POST", "/api/match-requests", {"receiver_walk_session_id": mock_ws}, tok=tok)["match_request_id"]
sid = None
for _ in range(10):
    r = req("GET", "/api/match-requests/" + rid, tok=tok)
    if r.get("status") == "accepted" and r.get("match_session_id"):
        sid = r["match_session_id"]
        break
    time.sleep(0.4)
assert sid, "mock auto-accept failed (no session)"

s = req("GET", "/api/match-sessions/" + sid, tok=tok)
print("before met:", "both_met=", s["both_met"])
m = req("POST", f"/api/match-sessions/{sid}/met", {}, tok=tok)
print("after met:", "i_met=", m["i_met"], "both_met=", m["both_met"], "status=", m["status"])
assert m["i_met"] is True and m["both_met"] is True, "mock partner should auto-met -> both_met"
assert m["status"] == "walking", "both met -> status walking"
print("MET OK")
