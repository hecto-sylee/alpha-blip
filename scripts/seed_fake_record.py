"""특정 계정에 '가짜 산책 기록 + 영상'을 심거나(merge), 계정을 통째로 지우는(purge) 데모 도구.

서버 코드를 직접 import 해서 같은 DB(walk.db 또는 LETSPAW_DATABASE_URL)에 Record/Clip 을 만들고,
클립을 server/uploads/ 에 두고 merge 서비스로 합성 mp4까지 만든다. 서버 실행 여부와 무관.

[솔로] 가로 영상 여러 개를 순서대로 concat → 한 기록(특정 계정·일자)
  python3 scripts/seed_fake_record.py <login_id> --date 2026-06-20 \
      --videos a.mp4 b.mp4 c.mp4 --text "오늘 산책"

[합성] 영상 없이 테스트 클립 생성
  python3 scripts/seed_fake_record.py <login_id> --clips 3

[듀얼] 다른 유저 영상과 vstack(상=이 계정 / 하=상대)으로 합성 (앱의 매칭 합성 포맷)
  python3 scripts/seed_fake_record.py <login_id> --date 2026-06-20 \
      --videos me1.mp4 me2.mp4 \
      --partner-login friend01 --partner-videos fr1.mp4 fr2.mp4
  (장면 i = 위: 내 영상 i, 아래: 상대 영상 i. 한쪽이 없으면 그 칸은 검정.)

[삭제] 계정과 그 기록·클립·영상파일을 전부 제거
  python3 scripts/seed_fake_record.py <login_id> --delete
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from server.database import SessionLocal, init_db  # noqa: E402
from server import merge as merge_svc  # noqa: E402
from server.models import (  # noqa: E402
    Clip, MatchLog, MatchRequest, MatchSession, Pet, Reaction, Record,
    RoomMember, User, UserItem, WalkSession, utcnow,
)

try:
    from server.services import points as points_svc  # noqa: E402
except Exception:
    points_svc = None

UPLOADS_DIR = os.path.join(REPO, "server", "uploads")
MERGED_DIR = os.path.join(UPLOADS_DIR, "merged")
FFMPEG = merge_svc.FFMPEG

PALETTE = ["0x9ad0c2", "0xf6c177", "0xf2a6c2", "0x9bbcf0", "0xc7b3e6", "0xf3a26a"]


def _ff(args: list[str]) -> None:
    p = subprocess.run([FFMPEG, "-y", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-600:])


def make_synthetic_clip(out_path: str, idx: int) -> None:
    color = PALETTE[idx % len(PALETTE)]
    fc = (
        f"color=c={color}:s=640x360:d=2[bg];"
        f"testsrc2=s=640x360:r=30:d=2,format=yuva420p,colorchannelmixer=aa=0.18[ts];"
        f"[bg][ts]overlay[v]"
    )
    common = ["-c:v", "libvpx", "-b:v", "900k", "-deadline", "realtime", "-cpu-used", "5", "-an"]
    try:
        _ff(["-f", "lavfi", "-i", "anullsrc", "-filter_complex", fc, "-map", "[v]", "-t", "2", *common, out_path])
    except Exception:
        _ff(["-f", "lavfi", "-i", f"color=c={color}:s=640x360:d=2:r=30", *common, out_path])


def clip_from_video(src: str, out_path: str, dur: int | None) -> None:
    if not os.path.exists(src):
        raise SystemExit(f"영상 파일 없음: {src}")
    # 크롭 대신 패드(레터박스) — 가로 영상은 꽉 차고, 세로/회전 영상도 잘리지 않고 전체가 담김.
    # (mp4 회전 메타데이터는 ffmpeg가 디코드 시 자동 보정)
    vf = ("scale=640:360:force_original_aspect_ratio=decrease,"
          "pad=640:360:(ow-iw)/2:(oh-ih)/2:color=#1A1410,setsar=1,fps=30")
    args = ["-i", src, "-vf", vf, "-c:v", "libvpx", "-b:v", "1500k", "-deadline", "realtime", "-cpu-used", "5", "-an"]
    if dur:
        args += ["-t", str(dur)]
    args += [out_path]
    _ff(args)


def ensure_user(db, login_id: str, nickname: str | None) -> User:
    norm = login_id.strip().lower()
    if not norm:
        raise SystemExit("login_id 가 비어 있습니다")
    user = db.query(User).filter(User.login_id == norm).first()
    if user is None:
        user = User(nickname=(nickname or login_id.strip()), login_id=norm, auth_token=secrets.token_urlsafe(32))
        db.add(user)
        db.flush()
        print(f"  + 새 계정 생성: {norm}")
    else:
        print(f"  · 기존 계정 사용: {norm}")
    return user


def ensure_pet(db, user: User, breed: str) -> Pet:
    pet = db.query(Pet).filter(Pet.user_id == user.id).order_by(Pet.created_at.asc()).first()
    if pet is None:
        pet = Pet(user_id=user.id, name="데모", breed=breed, size="small",
                  personality_tags=json.dumps(["활발함", "사람 좋아함"], ensure_ascii=False))
        db.add(pet)
        db.flush()
        print(f"  + 펫 생성: {breed}")
    return pet


def make_clips(db, user: User, record_id: str, videos: list[str], n_synth: int, dur: int) -> list[str]:
    """클립 행 + 파일 생성. videos가 있으면 그걸로, 없으면 합성 n_synth개. 절대경로 리스트 반환."""
    srcs = videos if videos else [None] * max(1, n_synth)
    paths = []
    for i, src in enumerate(srcs):
        clip = Clip(record_id=record_id, user_id=user.id, mission_id=None,
                    file_path="", duration_ms=(dur * 1000 if src else 2000), order=i, status="active")
        db.add(clip)
        db.flush()
        abs_path = os.path.join(UPLOADS_DIR, f"{clip.id}.webm")
        if src:
            clip_from_video(src, abs_path, dur)
        else:
            make_synthetic_clip(abs_path, i)
        clip.file_path = f"uploads/{clip.id}.webm"
        paths.append(abs_path)
    return paths


# --------------------------- 삭제(purge) ---------------------------
def purge(db, login_id: str) -> None:
    norm = login_id.strip().lower()
    user = db.query(User).filter(User.login_id == norm).first()
    if user is None:
        print(f"  계정 없음: {norm} (할 일 없음)")
        return
    uid = user.id
    recs = db.query(Record).filter(Record.user_id == uid).all()
    nfiles = 0
    for rec in recs:
        if rec.merged_path:
            f = os.path.join(UPLOADS_DIR, rec.merged_path)
            if os.path.exists(f):
                os.remove(f); nfiles += 1
    clips = db.query(Clip).filter(Clip.user_id == uid).all()
    for c in clips:
        f = os.path.join(UPLOADS_DIR, f"{c.id}.webm")
        if os.path.exists(f):
            os.remove(f); nfiles += 1
    # DB 행 정리
    db.query(Clip).filter(Clip.user_id == uid).delete(synchronize_session=False)
    db.query(Reaction).filter(Reaction.user_id == uid).delete(synchronize_session=False)
    db.query(Record).filter(Record.user_id == uid).delete(synchronize_session=False)
    db.query(MatchLog).filter((MatchLog.user_a_id == uid) | (MatchLog.user_b_id == uid)).delete(synchronize_session=False)
    db.query(MatchSession).filter((MatchSession.user_a_id == uid) | (MatchSession.user_b_id == uid)).delete(synchronize_session=False)
    db.query(MatchRequest).filter((MatchRequest.requester_id == uid) | (MatchRequest.receiver_id == uid)).delete(synchronize_session=False)
    db.query(RoomMember).filter(RoomMember.user_id == uid).delete(synchronize_session=False)
    db.query(WalkSession).filter(WalkSession.user_id == uid).delete(synchronize_session=False)
    db.query(UserItem).filter(UserItem.user_id == uid).delete(synchronize_session=False)
    db.query(Pet).filter(Pet.user_id == uid).delete(synchronize_session=False)
    db.query(User).filter(User.id == uid).delete(synchronize_session=False)
    db.commit()
    print(f"  ✓ '{norm}' 삭제 완료 (기록 {len(recs)}건, 파일 {nfiles}개 제거)")


# --------------------------- 메인 ---------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("login_id")
    ap.add_argument("--delete", action="store_true", help="이 계정과 데이터/영상 전부 삭제")
    ap.add_argument("--videos", nargs="*", default=[], help="가로 영상들(순서=클립 순서)")
    ap.add_argument("--clips", type=int, default=3, help="합성 모드 클립 수(--videos 없을 때)")
    ap.add_argument("--date", default=None, help="기록 일자 YYYY-MM-DD (기본 오늘)")
    ap.add_argument("--text", default="데모 산책 기록")
    ap.add_argument("--seconds", type=int, default=10, help="영상→클립 최대 길이(초)")
    ap.add_argument("--breed", default="말티즈")
    ap.add_argument("--nickname", default=None)
    # 듀얼(상대 유저와 vstack)
    ap.add_argument("--partner-login", default=None, help="듀얼: 상대 계정 login_id")
    ap.add_argument("--partner-videos", nargs="*", default=[], help="듀얼: 상대 영상들(아래 칸)")
    ap.add_argument("--partner-breed", default="시바견")
    ap.add_argument("--partner-nickname", default=None)
    args = ap.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.delete:
            print(f"[purge] login_id='{args.login_id}'")
            purge(db, args.login_id)
            if args.partner_login:
                purge(db, args.partner_login)
            return

        walked = date.fromisoformat(args.date) if args.date else date.today()
        os.makedirs(MERGED_DIR, exist_ok=True)
        print(f"[seed] login_id='{args.login_id}'  date={walked}  "
              f"{'DUAL' if args.partner_login else 'SOLO'}")

        user = ensure_user(db, args.login_id, args.nickname)
        ensure_pet(db, user, args.breed)

        if args.partner_login:
            # ----- 듀얼: 매칭 세션 + 양쪽 기록 + vstack 합성 -----
            partner = ensure_user(db, args.partner_login, args.partner_nickname)
            ensure_pet(db, partner, args.partner_breed)
            mr = MatchRequest(requester_id=user.id, receiver_id=partner.id, status="matched")
            db.add(mr); db.flush()
            ms = MatchSession(match_request_id=mr.id, user_a_id=user.id, user_b_id=partner.id,
                              status="ended", a_met=True, b_met=True, ended_at=utcnow())
            db.add(ms); db.flush()

            rec_a = Record(user_id=user.id, match_session_id=ms.id, visibility="diary",
                           walked_at=walked, duration_minutes=20, distance_meters=1300, text=args.text)
            rec_b = Record(user_id=partner.id, match_session_id=ms.id, visibility="diary",
                           walked_at=walked, duration_minutes=20, distance_meters=1300, text=args.text)
            db.add(rec_a); db.add(rec_b); db.flush()

            tops = make_clips(db, user, rec_a.id, args.videos, args.clips, args.seconds)
            bots = make_clips(db, partner, rec_b.id, args.partner_videos, args.clips, args.seconds)
            n = max(len(tops), len(bots))
            scenes = [{"top": tops[i] if i < len(tops) else None,
                       "bottom": bots[i] if i < len(bots) else None} for i in range(n)]
            out_a = os.path.join(MERGED_DIR, f"{rec_a.id}.mp4")
            merge_svc.build_dual_video(scenes, out_a)
            rec_a.merged_path = os.path.relpath(out_a, UPLOADS_DIR)
            # 상대 계정도 '자기 소유' 합성본을 갖도록 복사(개별 삭제 시 서로 영향 없음)
            out_b = os.path.join(MERGED_DIR, f"{rec_b.id}.mp4")
            shutil.copy2(out_a, out_b)
            rec_b.merged_path = os.path.relpath(out_b, UPLOADS_DIR)
            if points_svc:
                try: points_svc.award_for_record(db, user, clip_count=len(tops), is_match=True)
                except Exception: pass
            db.commit()
            print(f"  ✓ 듀얼 기록 {rec_a.id}  scenes={n}  merged={rec_a.merged_path}")
            print(f"    (상대 '{partner.login_id}' 기록 {rec_b.id} 에도 동일 합성본 연결)")
        else:
            # ----- 솔로: concat -----
            rec = Record(user_id=user.id, visibility="diary", walked_at=walked,
                         duration_minutes=20, distance_meters=1200, text=args.text)
            db.add(rec); db.flush()
            paths = make_clips(db, user, rec.id, args.videos, args.clips, args.seconds)
            out = os.path.join(MERGED_DIR, f"{rec.id}.mp4")
            merge_svc.build_record_video(paths, out)
            rec.merged_path = os.path.relpath(out, UPLOADS_DIR)
            if points_svc:
                try: points_svc.award_for_record(db, user, clip_count=len(paths), is_match=False)
                except Exception: pass
            db.commit()
            print(f"  ✓ 솔로 기록 {rec.id}  clips={len(paths)}  merged={rec.merged_path}")

        total = db.query(Record).filter(Record.user_id == user.id).count()
        print(f"[done] '{user.login_id}' 총 기록 {total}건, 포인트 {user.points or 0}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
