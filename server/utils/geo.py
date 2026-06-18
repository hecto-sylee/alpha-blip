"""Haversine distance + approximate-location offset (app-level, no PostGIS)."""
from __future__ import annotations

import hashlib
import math

EARTH_RADIUS_M = 6_371_000.0


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters between two lat/lng points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def approximate_location(lat: float, lng: float, seed: str, jitter_m: float = 120.0):
    """Return a deterministic-but-fuzzed coordinate near (lat, lng).

    The offset is derived from `seed` (e.g. walk_session_id) so the same
    session always reports the same approximate point — precise coords are
    never returned. Offset magnitude is ~jitter_m meters.
    """
    h = hashlib.sha256(seed.encode()).digest()
    # two values in [0, 1)
    angle = (h[0] / 256.0) * 2 * math.pi
    radius = (h[1] / 256.0) * jitter_m
    dlat = (radius * math.cos(angle)) / EARTH_RADIUS_M
    dlng = (radius * math.sin(angle)) / (
        EARTH_RADIUS_M * math.cos(math.radians(lat)) or 1e-9
    )
    return (
        lat + math.degrees(dlat),
        lng + math.degrees(dlng),
    )
