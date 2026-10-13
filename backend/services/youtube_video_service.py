"""Validation for explicitly supported YouTube video URL forms."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_WATCH_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})


def normalize_youtube_video_url(value: str) -> str:
    """Return an 11-character video ID from a supported HTTPS watch/share/live URL."""
    if not value or len(value) > 2048 or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Enter a supported HTTPS YouTube video URL")

    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or ":" in parsed.netloc
            or parsed.port is not None
        ):
            raise ValueError
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("Enter a supported HTTPS YouTube video URL") from exc

    video_id: str | None = None
    if hostname == "youtu.be" and parsed.path.count("/") == 1:
        video_id = parsed.path[1:]
    elif hostname in _YOUTUBE_WATCH_HOSTS:
        if parsed.path == "/watch":
            values = [
                value
                for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                if key == "v"
            ]
            if len(values) == 1:
                video_id = values[0]
        elif parsed.path.startswith("/live/") and parsed.path.count("/") == 2:
            video_id = parsed.path.removeprefix("/live/")

    if video_id is None or not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("Enter a supported HTTPS YouTube video URL")
    return video_id
