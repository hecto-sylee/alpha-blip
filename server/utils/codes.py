"""6-digit join code generation (room participation codes)."""
from __future__ import annotations

import secrets

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def gen_join_code(length: int = 6) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
