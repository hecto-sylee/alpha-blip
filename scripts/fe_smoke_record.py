#!/usr/bin/env python3
"""Headless smoke for FE2 — 기록 에디터 · 2초 클립 · 다이어리 · 퀘스트 (SCR-27/20/21/22).

흐름:
  - 게스트+펫 API 셋업 후 브라우저 세션 주입.
  - 오늘의 퀘스트 후보 3개 노출 확인 → 1개 select(lock) → 미션 리스트 확인.
  - 기록 에디터: 가짜 카메라로 2초 클립 녹화가 실제 stop되고 /clips/upload 201인지 단언.
  - 텍스트 입력 후 저장 → 다이어리 캘린더/목록에 방금 기록(클립 연결) 노출 단언 → 상세 진입.
콘솔 에러 0(외부/WebGL 잡음 제외), 각 단계 스크린샷 저장.

카메라: --use-fake-device-for-media-stream --use-fake-ui-for-media-stream + camera/microphone 권한 grant.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8000")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fe_shots")
os.makedirs(SHOTS, exist_ok=True)

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
IGNORE = ("maplibre", "webgl", "tile.openstreetmap", "unpkg.com", "failed to load resource",
          "err_", "net::", "favicon")


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []
    uploads = []  # (status, url)

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    u = apicall("POST", "/auth/guest", body={"nickname": "기록이"})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": "콩", "breed": "말티즈", "size": "small", "personality_tags": ["온순함"]})
    print(f"{DIM}  fixture: user={u['user_id'][:8]} pet={p['pet_id'][:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-fake-device-for-media-stream",
                  "--use-fake-ui-for-media-stream", "--use-gl=angle",
                  "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctx = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        ctx.grant_permissions(["camera", "microphone"])
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                if m.type == "error" and not any(k in m.text.lower() for k in IGNORE) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}")
                if not any(k in str(e).lower() for k in IGNORE) else None)
        page.on("response", lambda r: uploads.append((r.status, r.url))
                if "/api/clips/upload" in r.url else None)

        try:
            page.goto(BASE, wait_until="domcontentloaded")
            page.evaluate(
                """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
                [u["auth_token"], u["user_id"], p["pet_id"]],
            )

            # --- SCR-27 퀘스트 후보 3개 ---
            page.goto(BASE + "/#/quest", wait_until="networkidle")
            page.wait_for_selector(".quest-card")
            n = len(page.query_selector_all(".quest-card"))
            assert n == 3, f"후보 퀘스트가 3개가 아님: {n}"
            ok(page, f"오늘의 퀘스트 후보 {n}개 노출", "f2_01_candidates")

            # --- select(lock) ---
            page.click(".quest-card >> nth=0")
            page.wait_for_function("!document.querySelector('#quest-confirm').disabled")
            page.click("#quest-confirm")
            page.wait_for_selector("#quest-locked", timeout=8000)
            assert page.query_selector(".mission-row"), "미션 리스트가 없음"
            ok(page, "퀘스트 select → lock + 미션 리스트('지금 찍어볼 순간')", "f2_02_locked")

            # --- SCR-20 기록 에디터 진입 ---
            page.click("#go-record")
            page.wait_for_function("location.hash.startsWith('#/record')", timeout=8000)
            page.wait_for_selector("#cam-video", timeout=8000)  # 카메라 스트림 활성
            ok(page, "기록 에디터 진입 + 카메라 프리뷰 활성", "f2_03_editor")

            # --- 2초 클립 녹화 (실제 stop + 업로드 201) ---
            page.click("#rec-ring")
            page.wait_for_selector("[data-clip-id]", timeout=12000)  # 업로드 성공해야 칩 생성
            assert uploads, "clips/upload 응답이 관측되지 않음"
            up_status = uploads[-1][0]
            assert up_status == 201, f"clip 업로드 상태가 201이 아님: {up_status}"
            clip_id = page.get_attribute("[data-clip-id]", "data-clip-id")
            ok(page, f"2초 클립 녹화 → stop → /clips/upload {up_status} (clip={clip_id[:8]})", "f2_04_recorded")

            # --- 텍스트 입력 후 저장 ---
            page.fill("#record-text", "콩이랑 동네 한 바퀴 돌았다 ☀️")
            page.click("#save-record")
            page.wait_for_function("location.hash.startsWith('#/diary')", timeout=8000)
            ok(page, "메모 입력 → 저장 → 다이어리 이동", "f2_05_saved")

            # --- 다이어리: 기록·클립·캘린더 노출 ---
            page.wait_for_selector("[data-rid]", timeout=8000)
            rid = page.get_attribute("[data-rid]", "data-rid")
            assert "클립 1개" in page.inner_text(f'[data-rid="{rid}"]'), "기록에 연결된 클립이 표시되지 않음"
            assert page.query_selector(".cal-cell.has"), "캘린더에 기록 표시(점)가 없음"
            assert page.query_selector(".stat"), "스탯 카드가 없음"
            ok(page, "다이어리: 캘린더 표시·스탯·기록(클립 1개) 노출", "f2_06_diary")

            # --- SCR-22 상세 ---
            page.click(f'[data-rid="{rid}"]')
            page.wait_for_function("location.hash.startsWith('#/record/')", timeout=8000)
            page.wait_for_selector("#record-view")
            assert page.query_selector("#record-view .clip-chip"), "상세에 클립이 없음"
            ok(page, "기록 상세 진입 + 클립 재생 요소 노출", "f2_07_detail")

        except Exception as e:
            page.screenshot(path=os.path.join(SHOTS, "f2_FAIL.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}hash={page.evaluate('location.hash')} uploads={uploads}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 FE2 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
