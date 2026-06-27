"""Smoke: guest signup -> create pet with appearance -> read back (round-trip)."""
import json
import urllib.request as u

B = "http://localhost:8000"


def post(path, data, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    req = u.Request(B + path, data=json.dumps(data).encode(), headers=h, method="POST")
    return json.load(u.urlopen(req))


def get(path, tok):
    req = u.Request(B + path, headers={"authorization": "Bearer " + tok})
    return json.load(u.urlopen(req))


tok = post("/api/auth/guest", {"nickname": "테스트"})["auth_token"]
appearance = {"breed": "corgi", "coat": "#F0A24E", "ears": "perkyBig",
              "tail": "short", "legs": "tiny", "pattern": "saddle"}
pid = post("/api/pets", {
    "name": "콩이", "breed": "웰시코기", "size": "small",
    "personality_tags": ["활발함"], "appearance": appearance,
}, tok)["pet_id"]
pet = get("/api/pets/" + pid, tok)
print("appearance:", json.dumps(pet.get("appearance"), ensure_ascii=False))
assert pet.get("appearance", {}).get("breed") == "corgi", "appearance not persisted!"

# PATCH update appearance
pet2 = json.load(u.urlopen(u.Request(
    B + "/api/pets/" + pid,
    data=json.dumps({"appearance": {**appearance, "coat": "#FFFFFF", "pattern": "spots"}}).encode(),
    headers={"content-type": "application/json", "authorization": "Bearer " + tok},
    method="PATCH",
)))
assert pet2["appearance"]["coat"] == "#FFFFFF", "patch not persisted!"
print("OK round-trip + patch")
