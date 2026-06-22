"""Small JSON helpers shared across API modules."""
from __future__ import annotations

import json


def loads_list(value: str | None) -> list:
    """Parse a JSON-string column into a list; [] on null/garbage."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []
