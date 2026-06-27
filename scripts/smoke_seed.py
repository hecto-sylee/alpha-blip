"""Reseed demo dummies -> verify breed-diverse nearby dogs (with appearance)."""
import json
import urllib.request as u

B = "http://localhost:8000"


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


tok = req("POST", "/api/auth/guest", {"nickname": "시드확인"})["auth_token"]
req("POST", "/api/demo/reset", {}, tok=tok)  # 새 더미 목록으로 재시드

pid = req("POST", "/api/pets", {"name": "관찰자", "breed": "믹스", "size": "medium",
                                "personality_tags": ["활발함"]}, tok=tok)["pet_id"]
req("POST", "/api/walks/start", {"pet_id": pid, "latitude": 37.5009, "longitude": 127.0398}, tok=tok)

res = req("GET", "/api/nearby/dogs?latitude=37.5009&longitude=127.0398&radius_meters=1500", tok=tok)
dogs = res["dogs"]
breeds = sorted({d["pet"]["breed"] for d in dogs})
equipped = [d["pet"]["name"] for d in dogs if (d["pet"].get("appearance") or {}).get("equipped")]
print("nearby dogs:", len(dogs))
print("breeds:", breeds)
print("with equipped items:", equipped)
assert len(dogs) >= 5, f"expected >=5 demo dogs, got {len(dogs)}"
assert len(breeds) >= 5, f"expected >=5 distinct breeds, got {breeds}"
assert equipped, "expected some dummies to have equipped accessories"
print("SEED OK")
