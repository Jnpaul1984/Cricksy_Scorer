"""
MediaPipe Tasks Vision Initialization

Handles loading and verification of MediaPipe Pose Landmarker model.
Fails fast if model is not available - no stubs, no fallbacks.

Environment:
  MEDIAPIPE_POSE_MODEL_PATH: Path to pose_landmarker_full.task file
    Default: /app/mediapipe_models/pose_landmarker_full.task (Docker mount)
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL_PATH = "/app/mediapipe_models/pose_landmarker_full.task"
DEFAULT_RUNNING_MODE = "VIDEO"
SUPPORTED_RUNNING_MODES = ("VIDEO", "IMAGE", "LIVE_STREAM")

# MediaPipe Pose keypoint names (33 landmarks)
KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "head",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_foot_index",
    "right_foot_index",
    "left_elbow_crease",
    "right_elbow_crease",
    "left_knee_crease",
    "right_knee_crease",
    "left_foot_external",
    "right_foot_external",
    "left_foot_internal",
    "right_foot_internal",
]

# Module-level state
# Note: _pose_landmarker removed - now using factory pattern to avoid timestamp monotonicity bugs
_model_path_verified = False


def get_model_path() -> str:
    """Get and validate MediaPipe pose model path.

    Reads MEDIAPIPE_POSE_MODEL_PATH environment variable on each call (not cached).

    Validates that:
    - File exists
    - File is readable
    - File is at least 1MB (practical minimum for model)

    Note: .task files are bundle packages (ZIP format internally) and may start
    with ZIP/PK bytes rather than TFL3 header, so we skip format validation here.
    Actual validation happens during PoseLandmarker.create_from_options().

    Raises:
        FileNotFoundError: If model file is not found
        RuntimeError: If path is misconfigured or file is invalid
    """
    # Read from environment on each call (not cached)
    model_path = os.getenv("MEDIAPIPE_POSE_MODEL_PATH", DEFAULT_MODEL_PATH)

    if not model_path:
        raise RuntimeError(
            f"MEDIAPIPE_POSE_MODEL_PATH is empty. Set it or mount model to {DEFAULT_MODEL_PATH}"
        )

    path_obj = Path(model_path)

    if not path_obj.exists():
        # Option B: allow runtime download + cache from S3 when the model is missing.
        # This is primarily used by the analysis worker container.
        try:
            from backend.utils.model_cache import ensure_mediapipe_model_present

            prev_local = os.environ.get("MODEL_LOCAL_PATH")
            os.environ["MODEL_LOCAL_PATH"] = model_path
            try:
                downloaded_path = ensure_mediapipe_model_present()
                logger.info(f"MediaPipe model fetched to: {downloaded_path}")
            finally:
                if prev_local is None:
                    os.environ.pop("MODEL_LOCAL_PATH", None)
                else:
                    os.environ["MODEL_LOCAL_PATH"] = prev_local

            path_obj = Path(model_path)
        except Exception as e:
            raise FileNotFoundError(
                f"MediaPipe pose model not found at: {model_path}\n"
                f"Attempted runtime download but failed: {e!s}\n"
                f"Expected path: {DEFAULT_MODEL_PATH}\n"
                f"Docker volume mount: -v /host/path/pose_landmarker_full.task:"
                f"/app/mediapipe_models/pose_landmarker_full.task"
            ) from e

    if not path_obj.exists():
        raise FileNotFoundError(
            f"MediaPipe pose model not found at: {model_path}\n"
            f"Expected path: {DEFAULT_MODEL_PATH}\n"
            f"Docker volume mount: -v /host/path/pose_landmarker_full.task:"
            f"/app/mediapipe_models/pose_landmarker_full.task"
        )

    if not path_obj.is_file():
        raise RuntimeError(f"MediaPipe pose model path is not a file: {model_path}")

    # Verify file is readable and has reasonable size
    try:
        file_size = path_obj.stat().st_size
        if file_size < 1_000_000:  # 1MB minimum
            raise RuntimeError(
                f"Model file is suspiciously small ({file_size} bytes). "
                f"Expected at least 1MB. File may be corrupted: {model_path}"
            )

        # Attempt to open and read first byte to verify readability
        with open(path_obj, "rb") as f:
            _ = f.read(1)
    except OSError as e:
        raise RuntimeError(f"Cannot read MediaPipe model file: {model_path}\n{e}") from e

    logger.info(f"[OK] MediaPipe pose model path validated: {model_path} ({file_size} bytes)")
    return str(model_path)


def get_running_mode() -> str:
    """Get and validate MediaPipe running mode.

    Reads MEDIAPIPE_RUNNING_MODE environment variable on each call.
    Supported modes: VIDEO, IMAGE, LIVE_STREAM (default: VIDEO)

    Returns:
        str: One of "VIDEO", "IMAGE", "LIVE_STREAM"

    Raises:
        ValueError: If running mode is not supported
    """
    running_mode = os.getenv("MEDIAPIPE_RUNNING_MODE", DEFAULT_RUNNING_MODE).upper()

    if running_mode not in SUPPORTED_RUNNING_MODES:
        raise ValueError(
            f"Unsupported MEDIAPIPE_RUNNING_MODE: {running_mode}. "
            f"Supported modes: {', '.join(SUPPORTED_RUNNING_MODES)}"
        )

    logger.info(f"[OK] MediaPipe running mode: {running_mode}")
    return running_mode


def build_pose_landmarker():
    """Build a new MediaPipe PoseLandmarker instance.

    Factory function that creates a fresh PoseLandmarker for each call.
    This is required because detect_for_video() is stateful and requires
    monotonically increasing timestamps per detector instance.

    Validates model file exists and attempts to create PoseLandmarker.
    Running mode is determined by MEDIAPIPE_RUNNING_MODE environment variable.
    This is where real format validation happens - if model is corrupted or
    incompatible, MediaPipe will raise an error here.

    Returns:
        mediapipe.tasks.python.vision.PoseLandmarker: New detector instance

    Raises:
        ImportError: If MediaPipe is not installed
        FileNotFoundError: If model file is missing
        ValueError: If running mode is invalid
        RuntimeError: If initialization fails

    Note:
        Caller MUST call detector.close() when done to release resources.
    """
    global _model_path_verified

    logger.info("Building new MediaPipe PoseLandmarker instance...")

    # Import and verify MediaPipe
    try:
        from mediapipe.tasks.python import vision
        import mediapipe as mp
    except ImportError as e:
        raise ImportError(
            f"MediaPipe is not installed. Install with: pip install mediapipe\n{e}"
        ) from e
    # Verify model path exists and is readable
    model_path = get_model_path()
    _model_path_verified = True

    # Get and validate running mode
    running_mode_str = get_running_mode()

    # Create detector options
    try:
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarkerOptions = vision.PoseLandmarkerOptions
        VisionRunningMode = vision.RunningMode

        # Map string to RunningMode enum
        running_mode_map = {
            "IMAGE": VisionRunningMode.IMAGE,
            "VIDEO": VisionRunningMode.VIDEO,
            "LIVE_STREAM": VisionRunningMode.LIVE_STREAM,
        }
        running_mode = running_mode_map[running_mode_str]

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=running_mode,
            num_poses=1,  # Single person detection
        )

        logger.info(f"Creating PoseLandmarker with running_mode={running_mode_str}...")
        landmarker = vision.PoseLandmarker.create_from_options(options)
        logger.info(f"[OK] MediaPipe PoseLandmarker created successfully (mode={running_mode_str})")

        return landmarker

    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Model file not found during initialization: {model_path}\n{e}"
        ) from e
    except ValueError as e:
        raise ValueError(f"Invalid running mode configuration: {e}") from e
    except Exception as e:
        # Clear error message for common failure cases
        error_msg = str(e)
        if "model_asset_path" in error_msg or "model asset" in error_msg.lower():
            raise RuntimeError(
                f"Failed to load model file: {model_path}\n"
                f"Model may be corrupted or in wrong format.\n"
                f"Error: {error_msg}"
            ) from e
        else:
            raise RuntimeError(
                f"Failed to initialize MediaPipe PoseLandmarker: {error_msg}\n"
                f"Model path: {model_path}\n"
                f"Running mode: {running_mode_str}"
            ) from e


def verify_mediapipe_setup() -> dict:
    """Verify MediaPipe setup and return status info.

    Returns:
        dict with keys:
            - mediapipe_available: bool
            - model_path: str
            - model_exists: bool
            - running_mode: str
            - landmarker_initialized: bool
            - error: Optional[str]

    Raises:
        Exception: If verification fails (intentional - no hiding errors)
    """
    status = {
        "mediapipe_available": False,
        "model_path": os.getenv("MEDIAPIPE_POSE_MODEL_PATH", DEFAULT_MODEL_PATH),
        "model_exists": False,
        "running_mode": DEFAULT_RUNNING_MODE,
        "landmarker_initialized": False,
        "error": None,
    }

    # Check MediaPipe import
    try:
        import mediapipe  # noqa: F401

        status["mediapipe_available"] = True
    except ImportError as e:
        status["error"] = f"MediaPipe not installed: {e}"
        raise RuntimeError(status["error"]) from e

    # Check model file
    try:
        model_path = get_model_path()
        status["model_path"] = model_path
        status["model_exists"] = Path(model_path).exists()
    except FileNotFoundError as e:
        status["error"] = str(e)
        raise
    except RuntimeError as e:
        status["error"] = str(e)
        raise

    # Check running mode
    try:
        running_mode = get_running_mode()
        status["running_mode"] = running_mode
    except ValueError as e:
        status["error"] = str(e)
        raise

    # Check landmarker
    try:
        landmarker = build_pose_landmarker()
        status["landmarker_initialized"] = landmarker is not None
    except Exception as e:
        status["error"] = f"Landmarker init failed: {e}"
        raise

    logger.info(f"MediaPipe verification passed: {status}")
    return status


def get_pose_landmarker():
    """Create a new PoseLandmarker instance (factory function).

    Returns a fresh detector instance for each call to avoid timestamp
    monotonicity conflicts when processing multiple videos concurrently.

    Returns:
        mediapipe.tasks.python.vision.PoseLandmarker: New detector instance

    Raises:
        RuntimeError: If initialization failed

    Note:
        Caller MUST call detector.close() when done to release resources.
        Do not cache the returned instance - get a new one per video analysis job.
    """
    return build_pose_landmarker()


def get_detection_method_name() -> str:
    """Get the appropriate detection method name based on running mode.

    Returns:
        str: "detect" for IMAGE mode, "detect_for_video" for VIDEO mode,
        "detect_async" for LIVE_STREAM

    Note:
        Use this to determine which detection method to call on the landmarker:
        - IMAGE mode: landmarker.detect(image)
        - VIDEO mode: landmarker.detect_for_video(image, timestamp_ms)
        - LIVE_STREAM: landmarker.detect_async(image, timestamp_ms)
    """
    try:
        running_mode = get_running_mode()
        mode_map = {
            "IMAGE": "detect",
            "VIDEO": "detect_for_video",
            "LIVE_STREAM": "detect_async",
        }
        return mode_map.get(running_mode, "detect_for_video")
    except Exception as e:
        logger.warning(f"Error getting detection method name, defaulting to detect_for_video: {e}")
        return "detect_for_video"


# shutdown_pose_landmarker() removed - no longer needed with factory pattern.
# Each caller must close their own detector instance in a finally block.
