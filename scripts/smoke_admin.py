"""Smoke: kakao url (disabled w/o creds), demo setup -> reset purges demo data."""
import json
import urllib.request as u

B = "http://localhost:8000"


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


# kakao url disabled without creds
k = req("GET", "/api/auth/kakao/url")
print("kakao url:", k)
assert k["enabled"] is False, "kakao should be disabled without env creds"

# create a real user + demo mock, then reset
tok = req("POST", "/api/auth/guest", {"nickname": "관리자"})["auth_token"]
req("POST", "/api/pets", {"name": "관리펫", "breed": "믹스", "size": "medium",
                          "personality_tags": ["활발함"]}, tok=tok)
req("POST", "/api/demo/setup", {}, tok=tok)  # creates demo-mock:{uid}
r = req("POST", "/api/demo/reset", {}, tok=tok)
print("reset:", r)
assert r["reseeded"] is True
assert r["removed_demo_users"] >= 1, "expected to remove demo/mock users"

# my own pet still there (real user untouched)
me = req("GET", "/api/auth/me", tok=tok)
assert len(me["pets"]) == 1, "real user's pet must survive reset"
print("real user pets preserved:", len(me["pets"]))
print("ADMIN OK")
