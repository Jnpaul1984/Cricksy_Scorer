from __future__ import annotations

from pathlib import Path

import pytest


def test_model_cache_hit_does_not_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model_path = tmp_path / "pose_landmarker_full.task"
    model_path.write_bytes(b"x" * 10)

    monkeypatch.setenv("MODEL_LOCAL_PATH", str(model_path))

    def _boom(*args, **kwargs):
        raise AssertionError("boto3.client should not be called on cache hit")

    monkeypatch.setattr("backend.utils.model_cache.boto3.client", _boom)

    from backend.utils.model_cache import ensure_mediapipe_model_present

    resolved = ensure_mediapipe_model_present()
    assert resolved == str(model_path)


def test_model_cache_miss_downloads_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model_path = tmp_path / "pose_landmarker_full.task"
    monkeypatch.setenv("MODEL_LOCAL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_S3_BUCKET", "cricksy-coach-videos-prod")
    monkeypatch.setenv("MODEL_S3_KEY", "mediapipe/pose_landmarker_full.task")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    calls: list[tuple[str, str, str]] = []

    class _FakeS3:
        def download_file(self, bucket: str, key: str, filename: str) -> None:
            calls.append((bucket, key, filename))
            Path(filename).write_bytes(b"x" * 1_000_001)  # satisfy size check

    monkeypatch.setattr(
        "backend.utils.model_cache.boto3.client",
        lambda *args, **kwargs: _FakeS3(),
    )

    from backend.utils.model_cache import ensure_mediapipe_model_present

    resolved1 = ensure_mediapipe_model_present()
    assert resolved1 == str(model_path)
    assert model_path.exists()

    resolved2 = ensure_mediapipe_model_present()
    assert resolved2 == str(model_path)

    # Only one download for repeated calls
    assert len(calls) == 1
