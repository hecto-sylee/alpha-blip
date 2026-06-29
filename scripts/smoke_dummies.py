"""Verify only the curated demo dummies (1~2) are active/visible on the map."""
import sys
sys.path.insert(0, "/data/workspace/02_AlphaTeam/alpha-blip")
from server.database import SessionLocal
from server.models import User, WalkSession

db = SessionLocal()
dummies = db.query(User).filter(User.auth_token.like("demo-dummy:%")).all()
active = 0
for u in dummies:
    n = (
        db.query(WalkSession)
        .filter(
            WalkSession.user_id == u.id,
            WalkSession.status == "active",
            WalkSession.is_location_visible.is_(True),
        )
        .count()
    )
    flag = "VISIBLE" if n else "hidden"
    print(f"  {u.nickname:12} active/visible sessions={n}  [{flag}]")
    active += n
print(f"dummy users total={len(dummies)}  active+visible={active}")
assert active <= 2, f"map should show 1~2 dummies, got {active}"
print("DUMMY COUNT OK")
db.close()
