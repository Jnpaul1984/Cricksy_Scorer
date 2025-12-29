"""
S3-Backed Model Manager for Production ML Model Management
===========================================================

Responsibilities:
1. Download models from S3 on startup
2. Cache models in /tmp/cricksy_models/
3. Poll S3 for updates every 120s
4. Atomically reload models when new versions detected
5. Provide thread-safe access to models

Environment Variables:
- S3_MODEL_BUCKET: S3 bucket name (required in production)
- S3_MODEL_PREFIX: S3 key prefix (default: "models")
- MODEL_CACHE_DIR: Local cache directory (default: "/tmp/cricksy_models")
- MODEL_RELOAD_INTERVAL_SECONDS: Polling interval (default: 120)
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Literal

import joblib

logger = logging.getLogger(__name__)

# Type aliases
ModelType = Literal["win_probability", "score_predictor"]
MatchFormat = Literal["t20", "odi"]


class ModelManager:
    """
    Thread-safe manager for ML models with S3 backend and automatic reloading.
    
    Implements lazy loading pattern:
    - Models downloaded from S3 on first access
    - Cached in local filesystem for fast subsequent access
    - Background polling checks for updates every 120s
    - Atomic swaps when new versions detected
    """

    def __init__(self):
        """Initialize model manager with S3 and local cache configuration."""
        # S3 configuration
        self.s3_bucket = os.getenv("S3_MODEL_BUCKET", "")
        self.s3_prefix = os.getenv("S3_MODEL_PREFIX", "models")
        self.use_s3 = bool(self.s3_bucket)

        # Local cache configuration
        self.cache_dir = Path(os.getenv("MODEL_CACHE_DIR", "/tmp/cricksy_models"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Model storage (thread-safe access via lock)
        self._models: dict[str, Any] = {}  # {cache_key: loaded_model}
        self._model_versions: dict[str, str] = {}  # {cache_key: version}
        self._model_lock = threading.RLock()

        # S3 client (lazy init)
        self._s3_client = None

        # Background polling state
        self._reload_interval = int(os.getenv("MODEL_RELOAD_INTERVAL_SECONDS", "120"))
        self._poll_task = None
        self._shutdown_event = threading.Event()

        logger.info(
            "ModelManager initialized: s3_bucket=%s, cache_dir=%s, use_s3=%s",
            self.s3_bucket or "(local only)",
            self.cache_dir,
            self.use_s3,
        )

    def _get_s3_client(self):
        """Lazy initialize boto3 S3 client (assumes IAM role permissions)."""
        if self._s3_client is None and self.use_s3:
            try:
                import boto3

                self._s3_client = boto3.client("s3")
                logger.info("S3 client initialized for bucket: %s", self.s3_bucket)
            except Exception as e:
                logger.error("Failed to initialize S3 client: %s", e)
                self.use_s3 = False
        return self._s3_client

    def _get_cache_key(self, model_type: ModelType, match_format: MatchFormat) -> str:
        """Generate cache key for model lookup."""
        return f"{model_type}_{match_format}"

    def _get_s3_latest_key(self, model_type: ModelType, match_format: MatchFormat) -> str:
        """Get S3 key for latest.json pointer file."""
        model_name = self._get_model_name(model_type, match_format)
        return f"{self.s3_prefix}/{model_name}/latest.json"

    def _get_model_name(self, model_type: ModelType, match_format: MatchFormat) -> str:
        """Generate model name for S3 paths."""
        if model_type == "win_probability":
            return f"{match_format}_win_predictor"
        return f"{match_format}_score_predictor"

    def _download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """
        Download file from S3 to local path.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.use_s3:
            return False

        try:
            s3 = self._get_s3_client()
            if s3 is None:
                return False

            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(self.s3_bucket, s3_key, str(local_path))
            logger.info("Downloaded s3://%s/%s to %s", self.s3_bucket, s3_key, local_path)
            return True
        except Exception as e:
            logger.error("Failed to download s3://%s/%s: %s", self.s3_bucket, s3_key, e)
            return False

    def _get_latest_metadata(
        self, model_type: ModelType, match_format: MatchFormat
    ) -> dict[str, Any] | None:
        """
        Fetch latest.json from S3 to get current model version.
        
        Returns:
            Dict with {version, updated_at, s3_prefix} or None if not found
        """
        if not self.use_s3:
            return None

        latest_key = self._get_s3_latest_key(model_type, match_format)
        latest_path = self.cache_dir / "latest_metadata" / latest_key.replace("/", "_")

        # Download latest.json
        if not self._download_from_s3(latest_key, latest_path):
            return None

        # Parse JSON
        try:
            with open(latest_path, "r") as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            logger.error("Failed to parse latest.json from %s: %s", latest_path, e)
            return None

    def _get_local_fallback_path(
        self, model_type: ModelType, match_format: MatchFormat
    ) -> Path | None:
        """
        Get path to bundled model in Docker image (fallback when S3 unavailable).
        
        Returns:
            Path to .pkl file or None if not found
        """
        base_path = Path(__file__).parent.parent / "ml_models"

        if model_type == "win_probability":
            path = base_path / "win_probability" / f"{match_format}_win_predictor_v3.pkl"
        elif match_format == "t20":
            path = base_path / "score_predictor" / "t20_score_predictor.pkl"
        else:
            path = base_path / "score_predictor" / "odi_score_predictor_v3.pkl"

        return path if path.exists() else None

    def load_model(
        self, model_type: ModelType, match_format: MatchFormat
    ) -> Any:
        """
        Load model (from S3 or local cache).
        
        Strategy:
        1. Check in-memory cache first
        2. Try S3 download if configured
        3. Fall back to bundled models
        4. Return None if all fail
        
        Args:
            model_type: "win_probability" or "score_predictor"
            match_format: "t20" or "odi"
            
        Returns:
            Loaded model object or None
        """
        cache_key = self._get_cache_key(model_type, match_format)

        # Fast path: return cached model
        with self._model_lock:
            if cache_key in self._models:
                return self._models[cache_key]

        # Slow path: download and load
        model = self._load_model_from_storage(model_type, match_format)

        # Cache result
        with self._model_lock:
            self._models[cache_key] = model

        return model

    def _load_model_from_storage(
        self, model_type: ModelType, match_format: MatchFormat
    ) -> Any:
        """
        Load model from S3 or local fallback.
        
        Returns:
            Loaded model or None
        """
        cache_key = self._get_cache_key(model_type, match_format)

        # Try S3 first
        if self.use_s3:
            metadata = self._get_latest_metadata(model_type, match_format)
            if metadata:
                version = metadata.get("version", "unknown")
                s3_model_key = metadata.get("s3_prefix", "") + "/model.pkl"
                local_model_path = self.cache_dir / cache_key / version / "model.pkl"

                # Download if not cached
                if not local_model_path.exists():
                    if self._download_from_s3(s3_model_key, local_model_path):
                        logger.info(
                            "Downloaded model %s version %s from S3", cache_key, version
                        )

                # Try loading from cache
                if local_model_path.exists():
                    try:
                        model = joblib.load(local_model_path)
                        with self._model_lock:
                            self._model_versions[cache_key] = version
                        logger.info("Loaded model %s version %s", cache_key, version)
                        return model
                    except Exception as e:
                        logger.error("Failed to load model from %s: %s", local_model_path, e)

        # Fall back to bundled models
        fallback_path = self._get_local_fallback_path(model_type, match_format)
        if fallback_path:
            try:
                model = joblib.load(fallback_path)
                logger.info("Loaded bundled fallback model: %s", fallback_path.name)
                with self._model_lock:
                    self._model_versions[cache_key] = "bundled"
                return model
            except Exception as e:
                logger.error("Failed to load fallback model %s: %s", fallback_path, e)

        logger.warning("No model found for %s", cache_key)
        return None

    async def _check_for_updates_async(self):
        """
        Background task to poll S3 for model updates.
        
        Runs every 120s (configurable) and reloads models if new versions detected.
        """
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._reload_interval)

                if not self.use_s3:
                    continue

                # Check each loaded model for updates
                with self._model_lock:
                    model_keys = list(self._models.keys())

                for cache_key in model_keys:
                    # Parse cache key back to type/format
                    parts = cache_key.split("_", 2)
                    if len(parts) < 3:
                        continue

                    if parts[0] == "win":
                        model_type = "win_probability"
                        match_format = parts[2]
                    else:
                        model_type = "score_predictor"
                        match_format = parts[1]

                    # Check S3 for new version
                    metadata = self._get_latest_metadata(model_type, match_format)
                    if metadata:
                        new_version = metadata.get("version", "unknown")

                        with self._model_lock:
                            current_version = self._model_versions.get(cache_key)

                        if current_version != new_version:
                            logger.info(
                                "New model version detected for %s: %s -> %s",
                                cache_key,
                                current_version,
                                new_version,
                            )
                            # Reload model
                            new_model = self._load_model_from_storage(model_type, match_format)
                            if new_model:
                                with self._model_lock:
                                    self._models[cache_key] = new_model
                                logger.info("Successfully reloaded model %s", cache_key)

            except Exception as e:
                logger.error("Error in model update check: %s", e)

    def start_background_polling(self):
        """Start background task to poll for model updates."""
        if not self.use_s3 or self._poll_task is not None:
            return

        def run_async_loop():
            """Run async event loop in background thread."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._check_for_updates_async())

        self._poll_task = threading.Thread(target=run_async_loop, daemon=True)
        self._poll_task.start()
        logger.info("Started background model polling (interval=%ds)", self._reload_interval)

    def shutdown(self):
        """Gracefully shutdown background polling."""
        self._shutdown_event.set()
        if self._poll_task:
            self._poll_task.join(timeout=5)
        logger.info("ModelManager shutdown complete")


# Global singleton instance
_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Get global ModelManager singleton."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
