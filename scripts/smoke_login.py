"""Smoke: id-based login — same id => same user (+ data persists), case-insensitive."""
import json
import urllib.request as u

B = "http://localhost:8000"


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


# new id -> new user
r1 = req("POST", "/api/auth/login", {"login_id": "PocTest01", "nickname": "포코"})
print("new:", r1["is_new"], r1["nickname"])
assert r1["is_new"] is True
tok1 = r1["auth_token"]

# create a pet under this id
req("POST", "/api/pets", {"name": "포코강아지", "breed": "시바", "size": "medium",
                          "personality_tags": ["활발함"]}, tok=tok1)

# re-login with same id (different case) -> same user, sees the pet
r2 = req("POST", "/api/auth/login", {"login_id": "poctest01"})
print("relogin is_new:", r2["is_new"], "same user:", r2["user_id"] == r1["user_id"])
assert r2["is_new"] is False
assert r2["user_id"] == r1["user_id"], "same id must map to same user"
me = req("GET", "/api/auth/me", tok=r2["auth_token"])
assert len(me["pets"]) >= 1, "pet must persist for same id"
print("pets persisted:", len(me["pets"]))

# different id -> different user
r3 = req("POST", "/api/auth/login", {"login_id": "other99"})
assert r3["user_id"] != r1["user_id"]
print("LOGIN OK")
