"""Seed a record (clips+merge) via API for a login_id, then verify W5 기록탭 UI + download button."""
import json
import os
import subprocess
import time
import urllib.request as u
import uuid

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
FF = imageio_ffmpeg.get_ffmpeg_exe()
LID = "diary_" + uuid.uuid4().hex[:6]


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


def upload(fpath, tok, order):
    bd = "----lp" + uuid.uuid4().hex
    with open(fpath, "rb") as f:
        content = f.read()
    body = ("--" + bd + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"c.webm\"\r\nContent-Type: video/webm\r\n\r\n").encode() + content + b"\r\n"
    body += ("--" + bd + f"\r\nContent-Disposition: form-data; name=\"order\"\r\n\r\n{order}\r\n").encode()
    body += ("--" + bd + "--\r\n").encode()
    r = u.Request(B + "/api/clips/upload", data=body, headers={"content-type": "multipart/form-data; boundary=" + bd, "authorization": "Bearer " + tok}, method="POST")
    return json.load(u.urlopen(r))["clip_id"]


# --- API: login_id 유저 + 펫 + 클립 2개 + 기록(합성) ---
tok = req("POST", "/api/auth/login", {"login_id": LID, "nickname": "기록확인"})["auth_token"]
req("POST", "/api/pets", {"name": "기록이", "breed": "비숑", "size": "small", "personality_tags": ["활발함"]}, tok=tok)
clip_ids = []
for i in range(2):
    cp = f"/tmp/dc_{i}.webm"
    subprocess.run([FF, "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30", "-c:v", "libvpx", "-an", cp], capture_output=True)
    clip_ids.append(upload(cp, tok, i))
import datetime
rec = req("POST", "/api/records", {"visibility": "diary", "walked_at": datetime.date.today().isoformat(), "clip_ids": clip_ids}, tok=tok)
print("record:", rec["record_id"], "points:", rec.get("points_awarded"))
for _ in range(30):
    if req("GET", "/api/records/" + rec["record_id"], tok=tok).get("merged_ready"):
        break
    time.sleep(1)
print("merged ready")

# --- UI: 같은 login_id로 로그인 → /diary 확인 ---
errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto("http://localhost:8000/", wait_until="networkidle")
    pg.fill("#login-id", LID); pg.click("#login-cta")
    pg.wait_for_timeout(1500)
    pg.goto("http://localhost:8000/#/diary", wait_until="networkidle")
    pg.wait_for_selector(".card", timeout=8000)
    pg.wait_for_timeout(1500)
    cards = pg.eval_on_selector_all(".card", "els => els.length")
    has_dl = pg.eval_on_selector_all("button", "els => els.some(b => b.textContent.includes('다운로드'))")
    has_video = bool(pg.query_selector(".rec-media video"))
    print("diary cards:", cards, "download btn:", has_dl, "inline video:", has_video)
    pg.screenshot(path="/tmp/diary_check.png", full_page=True)
    b.close()
print("errors:", errors)
assert cards >= 1 and has_dl, "diary did not render record + download"
assert not errors, errors
print("DIARY OK")
