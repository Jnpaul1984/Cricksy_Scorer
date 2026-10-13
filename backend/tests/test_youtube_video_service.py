import pytest

from backend.services.youtube_video_service import normalize_youtube_video_url

VIDEO_ID = "AbCdEf123_-"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?si=synthetic-share-token",
        f"https://youtube.com/live/{VIDEO_ID}?feature=share",
    ],
)
def test_normalizes_supported_youtube_url_forms(url: str) -> None:
    assert normalize_youtube_video_url(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        f"http://youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com.evil.invalid/watch?v={VIDEO_ID}",
        f"https://evil.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com:443/watch?v={VIDEO_ID}",
        f"https://youtube.com@evil.invalid/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}&v={VIDEO_ID}",
        "https://youtube.com/playlist?list=synthetic-list",
        "https://youtube.com/@synthetic-channel/live",
        "https://youtu.be/too-short",
        f"https://youtube.com/watch?v={VIDEO_ID}/",
        f"<iframe src='https://youtube.com/embed/{VIDEO_ID}'></iframe>",
        f"javascript:window.location='https://youtu.be/{VIDEO_ID}'",
        f" https://youtu.be/{VIDEO_ID}",
        "",
    ],
)
def test_rejects_unsupported_or_ambiguous_youtube_inputs(url: str) -> None:
    with pytest.raises(ValueError):
        normalize_youtube_video_url(url)
