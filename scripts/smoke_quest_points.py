"""Verify: solo vs match quests differ (mode), and points rule (walk10 + clip5*n + match20)."""
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


tok = req("POST", "/api/auth/login", {"login_id": "qp_" + time.strftime("%H%M%S")})["auth_token"]
uid = req("GET", "/api/auth/me", tok=tok)["id"]
req("POST", "/api/pets", {"name": "퀘포", "breed": "믹스", "size": "medium", "personality_tags": ["활발함"]}, tok=tok)

# 1) 솔로 vs 매칭 퀘스트 모드 분리
solo = req("GET", f"/api/quests/candidates?scope=user&scope_id={uid}&mode=solo", tok=tok)
match = req("GET", f"/api/quests/candidates?scope=user&scope_id={uid}&mode=match", tok=tok)
solo_titles = {c["title"] for c in solo["candidates"]}
match_titles = {c["title"] for c in match["candidates"]}
print("solo quests:", solo_titles)
print("match quests:", match_titles)
assert solo_titles and match_titles, "both modes must have quests"
assert solo_titles.isdisjoint(match_titles), "solo and match quests must differ"

# 2) 포인트: 솔로 기록 0컷 = 10
p0 = req("POST", "/api/records", {"visibility": "diary", "walked_at": time.strftime("%Y-%m-%d"), "clip_ids": []}, tok=tok)
print("solo 0-clip points:", p0["points_awarded"])
assert p0["points_awarded"] == 10, f"solo 0clip should be 10, got {p0['points_awarded']}"

# 3) 매칭 보너스: 세션 만들고 매칭 기록 0컷 = 10 + 20 = 30
demo = req("POST", "/api/demo/setup", {}, tok=tok)
rid = req("POST", "/api/match-requests", {"receiver_walk_session_id": demo["mock_walk_session_id"]}, tok=tok)["match_request_id"]
sid = None
for _ in range(10):
    r = req("GET", "/api/match-requests/" + rid, tok=tok)
    if r.get("match_session_id"):
        sid = r["match_session_id"]; break
    time.sleep(0.4)
assert sid
pm = req("POST", "/api/records", {"visibility": "diary", "walked_at": time.strftime("%Y-%m-%d"),
                                  "clip_ids": [], "match_session_id": sid}, tok=tok)
print("match 0-clip points:", pm["points_awarded"])
assert pm["points_awarded"] == 30, f"match 0clip should be 30 (10+20), got {pm['points_awarded']}"
print("QUEST+POINTS OK")
