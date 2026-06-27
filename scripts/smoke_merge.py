"""Smoke: upload clip(s) -> create record -> background ffmpeg merge -> download mp4."""
import json
import os
import subprocess
import time
import urllib.request as u
import uuid

import imageio_ffmpeg

B = "http://localhost:8000"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def req(method, path, data=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data is not None else None
    return json.load(u.urlopen(u.Request(B + path, data=body, headers=h, method=method)))


def upload(fpath, tok):
    boundary = "----lp" + uuid.uuid4().hex
    with open(fpath, "rb") as f:
        content = f.read()
    b = b""
    b += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"clip.webm\"\r\nContent-Type: video/webm\r\n\r\n").encode() + content + b"\r\n"
    b += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"duration_ms\"\r\n\r\n2000\r\n").encode()
    b += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"order\"\r\n\r\n0\r\n").encode()
    b += ("--" + boundary + "--\r\n").encode()
    r = u.Request(B + "/api/clips/upload", data=b,
                  headers={"content-type": "multipart/form-data; boundary=" + boundary,
                           "authorization": "Bearer " + tok}, method="POST")
    return json.load(u.urlopen(r))


# 1) 테스트 webm 2개 생성
clips = []
for i in range(2):
    cp = f"/tmp/test_clip_{i}.webm"
    subprocess.run([FF, "-y", "-f", "lavfi", "-i",
                    f"testsrc=duration=2:size=320x240:rate=30",
                    "-c:v", "libvpx", "-an", cp], capture_output=True)
    assert os.path.exists(cp) and os.path.getsize(cp) > 0, f"webm gen failed: {cp}"
    clips.append(cp)

tok = req("POST", "/api/auth/guest", {"nickname": "합성테스트"})["auth_token"]
pid = req("POST", "/api/pets", {"name": "합성", "breed": "믹스", "size": "medium",
                                "personality_tags": ["활발함"]}, tok=tok)["pet_id"]
clip_ids = [upload(c, tok)["clip_id"] for c in clips]
print("uploaded clips:", clip_ids)

import datetime
rec = req("POST", "/api/records", {"visibility": "diary",
                                   "walked_at": datetime.date.today().isoformat(),
                                   "clip_ids": clip_ids}, tok=tok)["record_id"]
print("record:", rec)

# 2) 합성 완료까지 폴링
ready = False
for _ in range(30):
    r = req("GET", "/api/records/" + rec, tok=tok)
    if r.get("merged_ready"):
        ready = True
        break
    time.sleep(1)
print("merged_ready:", ready)
assert ready, "merge did not complete in time"

# 3) 다운로드
data = u.urlopen(u.Request(B + f"/api/records/{rec}/video/download",
                           headers={"authorization": "Bearer " + tok})).read()
open("/tmp/merged_out.mp4", "wb").write(data)
print("downloaded bytes:", len(data))
assert len(data) > 1000, "merged mp4 too small"
assert b"ftyp" in data[:64], "not a valid mp4 (no ftyp box)"
print("MERGE+DOWNLOAD OK")
