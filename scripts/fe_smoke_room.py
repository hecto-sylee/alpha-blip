#!/usr/bin/env python3
"""Headless smoke for FE3 — 방 · 타임라인 · 이모지 반응 (SCR-23~26).

2개 컨텍스트(A·B):
  - A: UI에서 방 생성 → 참여코드 버튼 → 팝업의 6자리 join_code 단언.
  - B: 코드로 참여(UI) → 방 상세 진입 → 참여코드 팝업 확인 → '기록 올리기'(?room= 프리셋)
       → 가짜 카메라로 2초 클립 녹화 → visibility=room 기록 저장.
  - A: 방 상세 타임라인에 B의 기록(클립)이 보이는지 단언
       → 이모지 반응 토글 → 타임라인 반응 집계 갱신 단언.
콘솔 에러 0(외부/WebGL 잡음 제외), 각 단계 스크린샷 저장.
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
B_TEXT = "방에서 인사! 보리예요 🐶"


def apicall(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + "/api" + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def make_user(nick, petname, breed):
    u = apicall("POST", "/auth/guest", body={"nickname": nick})
    p = apicall("POST", "/pets", token=u["auth_token"],
                body={"name": petname, "breed": breed, "size": "small", "personality_tags": ["온순함"]})
    return u, p["pet_id"]


def inject(page, u, pet_id):
    page.goto(BASE, wait_until="domcontentloaded")
    page.evaluate(
        """([t,u,p]) => { localStorage.setItem('auth_token',t); localStorage.setItem('user_id',u); localStorage.setItem('pet_id',p); }""",
        [u["auth_token"], u["user_id"], pet_id],
    )


def guard(errors):
    def on_console(m):
        if m.type == "error" and not any(k in m.text.lower() for k in IGNORE):
            errors.append(f"{m.type}: {m.text}")
    return on_console


def open_code_popup(page):
    page.wait_for_selector("#room-code-open", timeout=8000)
    page.wait_for_selector(".toast", state="detached", timeout=3500)
    page.click("#room-code-open")
    page.wait_for_selector(".sheet-scrim.open #room-code", timeout=5000)
    page.wait_for_timeout(450)
    return page.inner_text("#room-code").strip()


def close_sheet(page):
    if not page.query_selector(".sheet-scrim"):
        return
    page.eval_on_selector(".sheet-scrim", "e => e.click()")
    page.wait_for_selector(".sheet-scrim", state="detached", timeout=1000)


def main():
    print(f"{DIM}BASE={BASE}{RESET}")
    errors = []

    def ok(page, msg, name):
        path = os.path.join(SHOTS, f"{name}.png")
        page.screenshot(path=path)
        print(f"  {GREEN}✅{RESET} {msg}  {DIM}{path}{RESET}")

    a, a_pet = make_user("방장A", "초코", "푸들")
    b, b_pet = make_user("멤버B", "보리", "비숑")
    print(f"{DIM}  fixture: A={a['user_id'][:8]} B={b['user_id'][:8]}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-fake-device-for-media-stream",
                  "--use-fake-ui-for-media-stream", "--use-gl=angle",
                  "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        ctxA = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        ctxB = browser.new_context(viewport={"width": 414, "height": 896}, locale="ko-KR")
        ctxB.grant_permissions(["camera", "microphone"])
        pageA = ctxA.new_page(); pageA.on("console", guard(errors))
        pageB = ctxB.new_page(); pageB.on("console", guard(errors))
        pageA.on("pageerror", lambda e: errors.append(f"A pageerror: {e}") if not any(k in str(e).lower() for k in IGNORE) else None)
        pageB.on("pageerror", lambda e: errors.append(f"B pageerror: {e}") if not any(k in str(e).lower() for k in IGNORE) else None)

        try:
            inject(pageA, a, a_pet)
            inject(pageB, b, b_pet)

            # --- A: 방 탭 진입 — 4탭 + data-tab="room" + 빈 상태 ---
            pageA.goto(BASE + "/#/rooms", wait_until="networkidle")
            pageA.wait_for_selector("#room-create-cta")
            tabs = pageA.eval_on_selector_all("#tabbar a", "els => els.map(e => e.dataset.tab)")
            assert tabs == ["walk", "room", "diary", "my"], f"탭바가 4탭(산책/방/기록/마이)이 아님: {tabs}"
            assert pageA.query_selector('#tabbar a[data-tab="room"].active'), "방 탭이 active가 아님"
            ok(pageA, f"방 탭 진입 → 4탭({'/'.join(tabs)}) + 방 탭 active + 빈 상태", "f3_00_roomtab")

            # --- A: 방 생성 (UI) ---
            pageA.click("#room-create-cta")
            pageA.wait_for_selector("#room-name")
            pageA.fill("#room-name", "동네 산책팟")
            pageA.click("#create-confirm")
            pageA.wait_for_function("location.hash.startsWith('#/room/')", timeout=8000)
            code = open_code_popup(pageA)
            room_id = pageA.evaluate("location.hash.split('/room/')[1]")
            assert len(code) == 6, f"join_code가 6자리가 아님: '{code}'"
            ok(pageA, f"A 방 생성 → 참여코드 팝업에서 6자리 join_code 노출 ({code})", "f3_01_create")
            close_sheet(pageA)

            # --- B: 코드로 참여 (UI) ---
            pageB.goto(BASE + f"/#/rooms/join?code={code}", wait_until="networkidle")
            pageB.wait_for_selector("#join-confirm")
            pageB.click("#join-confirm")
            pageB.wait_for_function("location.hash.startsWith('#/room/')", timeout=8000)
            b_code = open_code_popup(pageB)
            assert b_code == code, "B가 같은 방에 들어오지 않음"
            ok(pageB, "B 코드로 참여 → 같은 방 진입 + 참여코드 팝업 확인", "f3_02_join")
            close_sheet(pageB)

            # --- B: 방에 기록 공유 (기록 올리기 → ?room= 프리셋 → 2초 클립 → 저장) ---
            pageB.click("#post-record")
            pageB.wait_for_function("location.hash.startsWith('#/record')", timeout=8000)
            pageB.wait_for_selector("#cam-video", timeout=8000)
            # 공개범위가 '방 공유'로 프리셋됐는지 확인
            assert pageB.get_attribute("#vis-seg .opt[data-val='room']", "class").find("sel") >= 0, "방 공유 프리셋 아님"
            pageB.click("#rec-ring")
            pageB.wait_for_selector("[data-clip-id]", timeout=12000)
            pageB.fill("#record-text", B_TEXT)
            pageB.click("#save-record")
            pageB.wait_for_function("location.hash.startsWith('#/diary')", timeout=8000)
            ok(pageB, "B 방에 기록 공유(visibility=room, 클립 포함) 저장", "f3_03_share")

            # --- A: 방 탭 로그 피드에서 B의 기록 확인 ---
            pageA.goto(BASE + "/#/rooms", wait_until="networkidle")
            pageA.reload(wait_until="networkidle")
            pageA.wait_for_selector("#room-feed [data-rid]", timeout=8000)
            rid = pageA.get_attribute("#room-feed [data-rid]", "data-rid")
            assert B_TEXT[:6] in pageA.inner_text(f'#room-feed [data-rid="{rid}"]'), "로그 피드에 B 기록 본문이 없음"
            assert pageA.query_selector('#tabbar a[data-tab="room"].active'), "피드에서 방 탭 active 아님"
            ok(pageA, "A 방 탭 로그 피드에 B의 기록 노출", "f3_04_feed")

            # --- A: 피드 카드 탭 → 방 상세 진입, 타임라인 + 클립 확인 ---
            pageA.click(f'#room-feed [data-rid="{rid}"]')
            pageA.wait_for_function("location.hash.startsWith('#/room/')", timeout=8000)
            pageA.wait_for_selector("#room-timeline [data-rid]", timeout=8000)
            assert B_TEXT[:6] in pageA.inner_text(f'#room-timeline [data-rid="{rid}"]'), "방 상세 타임라인에 B 기록 본문이 없음"
            assert pageA.query_selector(f'#room-timeline [data-rid="{rid}"] .clip-chip'), "타임라인 기록에 클립이 없음"
            ok(pageA, "A 피드 카드 → 방 상세 타임라인(클립 포함) 진입", "f3_05_detail")

            # --- A: 이모지 반응 토글 → 집계 갱신 ---
            rx = f'.rx-bar[data-rid="{rid}"] .rx[data-emoji="🔥"]'
            pageA.click(rx)
            pageA.wait_for_function(
                """sel => { const e=document.querySelector(sel); return e && e.classList.contains('on') && e.querySelector('.n').textContent==='1'; }""",
                arg=rx, timeout=6000,
            )
            ok(pageA, "A 이모지 반응(🔥) 토글 → 타임라인 집계 1로 갱신", "f3_05_reaction")

        except Exception as e:
            pageA.screenshot(path=os.path.join(SHOTS, "f3_FAIL_A.png"))
            pageB.screenshot(path=os.path.join(SHOTS, "f3_FAIL_B.png"))
            print(f"  {RED}❌ 실패: {e}{RESET}")
            print(f"  {DIM}A.hash={pageA.evaluate('location.hash')} B.hash={pageB.evaluate('location.hash')}{RESET}")
            browser.close()
            return 1

        browser.close()

    if errors:
        print(f"\n{RED}❌ 콘솔 에러 {len(errors)}건:{RESET}")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"\n{GREEN}🎉 FE3 헤드리스 스모크 전부 통과 (콘솔 에러 0){RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
