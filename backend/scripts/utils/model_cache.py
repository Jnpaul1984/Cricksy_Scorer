"""Backward-compatible import path.

The canonical implementation lives at backend.utils.model_cache.
"""

from backend.utils.model_cache import ensure_mediapipe_model_present

__all__ = ["ensure_mediapipe_model_present"]
