from __future__ import annotations

import datetime as dt
import os
from typing import Any

UTC = getattr(dt, "UTC", dt.UTC)

# Limit for sponsor file uploads (5MB)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB


def detect_image_ext(data: bytes, content_type: str | None, filename: str | None) -> str | None:
    """
    Return 'svg' | 'png' | 'webp' if valid, else None.
    Uses content-type, extension, and simple signature checks.
    """
    ct = (content_type or "").lower()
    ext = os.path.splitext(filename or "")[1].lower()
    head = data[:256]

    # SVG
    if ct == "image/svg+xml" or ext == ".svg" or b"<svg" in head.lower():
        return "svg"
    # PNG
    if ct == "image/png" or ext == ".png" or data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # WEBP
    if ct == "image/webp" or ext == ".webp" or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "webp"
    return None


def parse_iso_dt(s: str | None) -> dt.datetime | None:
    """
    Parse ISO-8601 strings (including trailing Z) into a timezone-aware datetime in UTC.
    Returns None on failure or when s is falsy.
    """
    if not s:
        return None
    s = s.strip()
    try:
        if s.endswith("Z"):
            return dt.datetime.fromisoformat(s[:-1]).replace(tzinfo=UTC)
        dt_obj = dt.datetime.fromisoformat(s)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=UTC)
        return dt_obj
    except Exception:
        return None


def iso_or_none(x: Any) -> str | None:
    """
    Return isoformat string if x is a datetime, else None.
    """
    return x.isoformat() if isinstance(x, dt.datetime) else None


__all__ = [
    "MAX_UPLOAD_BYTES",
    "UTC",
    "detect_image_ext",
    "iso_or_none",
    "parse_iso_dt",
]
