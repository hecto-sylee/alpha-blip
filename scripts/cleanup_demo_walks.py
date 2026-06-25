"""One-time walk.db cleanup for the demo.

Keeps active walk sessions ONLY for the seeded demo dummies (초코·콩,
token `demo-dummy:*`) and per-tester mock 망고 (token `demo-mock:*`);
closes every other stale active walk session so `nearby` shows just the
three demo friends.

Run from the repo root:  python -m scripts.cleanup_demo_walks
"""
from __future__ import annotations

from server.database import SessionLocal, init_db
from server.models import Pet, User, WalkSession, utcnow
from server import seed

KEEP_PREFIXES = ("demo-dummy:", "demo-mock:")


def main() -> None:
    init_db()
    seed.run()  # ensure quests + 초코·콩 dummies exist before we prune

    db = SessionLocal()
    try:
        active = db.query(WalkSession).filter(WalkSession.status == "active").all()
        closed = 0
        for ws in active:
            owner = db.get(User, ws.user_id)
            token = owner.auth_token if owner else ""
            if token.startswith(KEEP_PREFIXES):
                continue
            ws.status = "closed"
            ws.ended_at = ws.ended_at or utcnow()
            closed += 1
        db.commit()

        print(f"closed {closed} stale active walk session(s)")
        remaining = db.query(WalkSession).filter(WalkSession.status == "active").all()
        print(f"remaining active sessions: {len(remaining)}")
        for ws in remaining:
            owner = db.get(User, ws.user_id)
            pet = db.get(Pet, ws.pet_id)
            print(
                f"  - pet={pet.name if pet else '?'!s:6} "
                f"owner={owner.nickname if owner else '?'!s:10} "
                f"token={owner.auth_token if owner else '?'} "
                f"@({ws.lat},{ws.lng}) visible={ws.is_location_visible}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
