"""Smoke: points award (record) -> shop list -> buy -> equip (pet appearance)."""
import datetime
import json
import urllib.error
import urllib.request as u

B = "http://localhost:8000"


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    r = u.Request(B + path, data=body, headers=h, method=method)
    return json.load(u.urlopen(r))


tok = req("POST", "/api/auth/guest", {"nickname": "상점테스트"})["auth_token"]
pid = req("POST", "/api/pets", {"name": "별이", "breed": "포메", "size": "small",
                                "personality_tags": ["활발함"]}, tok=tok)["pet_id"]

today = datetime.date.today().isoformat()
pts = 0
for _ in range(3):  # 3 records -> 30 points (>= bandana 25)
    res = req("POST", "/api/records", {"visibility": "diary", "walked_at": today, "clip_ids": []}, tok=tok)
    pts = res["points"]
print("points after 3 records:", pts)
assert pts >= 25, f"expected >=25 points, got {pts}"

shop = req("GET", "/api/shop", tok=tok)
print("shop points:", shop["points"], "items:", len(shop["items"]))

# buy too-expensive -> 400
try:
    req("POST", "/api/shop/buy", {"item_key": "crown"}, tok=tok)  # cost 120
    raise SystemExit("FAIL: crown buy should have failed")
except urllib.error.HTTPError as e:
    assert e.code == 400, e.code
    print("crown buy correctly rejected (400)")

# buy bandana (25)
after = req("POST", "/api/shop/buy", {"item_key": "bandana"}, tok=tok)
print("points after buy:", after["points"])
assert after["points"] == pts - 25
assert any(i["key"] == "bandana" and i["owned"] for i in after["items"])

# equip via pet appearance
pet = req("GET", "/api/pets/" + pid, tok=tok)
app = pet.get("appearance") or {}
app["equipped"] = ["bandana"]
pet2 = req("PATCH", "/api/pets/" + pid, {"appearance": app}, tok=tok)
assert pet2["appearance"]["equipped"] == ["bandana"], pet2["appearance"]
print("equip persisted:", pet2["appearance"]["equipped"])
print("SHOP OK")
