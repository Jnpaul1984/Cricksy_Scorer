from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

COACH_ANALYSIS_V2_SCHEMA_VERSION = "coach_analysis_v2.contract.v1"
COACH_ANALYSIS_CAPTURE_PROFILE_VERSION = "coach_analysis_capture_profile.v1"
DEFAULT_POSE_METRIC_VERSION = "pose_metrics.v1"
LOW_CONFIDENCE_THRESHOLD = 0.6


class CoachingDiscipline(StrEnum):
    batting = "batting"
    bowling = "bowling"
    wicketkeeping = "wicketkeeping"
    fielding = "fielding"
    mixed = "mixed"


class ValidityState(StrEnum):
    VALID = "VALID"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NOT_MEASURABLE = "NOT_MEASURABLE"
    INSUFFICIENT_VISIBILITY = "INSUFFICIENT_VISIBILITY"
    UNSUPPORTED_CAMERA_VIEW = "UNSUPPORTED_CAMERA_VIEW"
    INSUFFICIENT_FRAME_RATE = "INSUFFICIENT_FRAME_RATE"
    INVALID_RANGE = "INVALID_RANGE"
    INSUFFICIENT_REPETITIONS = "INSUFFICIENT_REPETITIONS"


class CompatibilityReasonCode(StrEnum):
    MISSING_PLAYER_ID = "MISSING_PLAYER_ID"
    PLAYER_ID_MISMATCH = "PLAYER_ID_MISMATCH"
    MISSING_CAPTURE_PROFILE = "MISSING_CAPTURE_PROFILE"
    MISSING_CAPTURE_METADATA = "MISSING_CAPTURE_METADATA"
    METRIC_ID_MISMATCH = "METRIC_ID_MISMATCH"
    METRIC_VERSION_MISMATCH = "METRIC_VERSION_MISMATCH"
    DISCIPLINE_MISMATCH = "DISCIPLINE_MISMATCH"
    CAMERA_VIEW_MISMATCH = "CAMERA_VIEW_MISMATCH"
    SAMPLE_FPS_MISMATCH = "SAMPLE_FPS_MISMATCH"
    EFFECTIVE_FPS_MISMATCH = "EFFECTIVE_FPS_MISMATCH"
    SOURCE_VIDEO_FPS_MISMATCH = "SOURCE_VIDEO_FPS_MISMATCH"
    RESOLUTION_CLASS_MISMATCH = "RESOLUTION_CLASS_MISMATCH"
    SOURCE_MODEL_MISMATCH = "SOURCE_MODEL_MISMATCH"
    CAPTURE_PROFILE_VERSION_MISMATCH = "CAPTURE_PROFILE_VERSION_MISMATCH"
    INCOMPATIBLE_VALIDITY_STATE = "INCOMPATIBLE_VALIDITY_STATE"


class CameraRequirements(BaseModel):
    supported_views: list[str] = Field(default_factory=list)
    minimum_sample_fps: float | None = None
    minimum_source_video_fps: float | None = None
    minimum_resolution_class: str | None = None

    model_config = ConfigDict(extra="forbid")


class EvidenceRef(BaseModel):
    ref_type: str
    ref_id: str | None = None
    label: str | None = None

    model_config = ConfigDict(extra="forbid")


class TimestampRef(BaseModel):
    start_ts: float | None = None
    end_ts: float | None = None

    model_config = ConfigDict(extra="forbid")


class FrameRef(BaseModel):
    frame_numbers: list[int] = Field(default_factory=list)
    start_frame: int | None = None
    end_frame: int | None = None

    model_config = ConfigDict(extra="forbid")


class CaptureProfile(BaseModel):
    schema_version: str = COACH_ANALYSIS_CAPTURE_PROFILE_VERSION
    capture_profile_version: str = "1.0.0"
    camera_view: str | None = None
    sample_fps: float | None = None
    effective_analysis_fps: float | None = None
    source_video_fps: float | None = None
    resolution_class: str | None = None
    analysis_mode: str | None = None
    discipline: str | None = None
    metric_version: str | None = None
    source_model: str | None = None
    compatibility_flags: list[str] = Field(default_factory=list)
    compatibility_notes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CoachingMetricResultV2(BaseModel):
    schema_version: str = COACH_ANALYSIS_V2_SCHEMA_VERSION
    metric_version: str
    metric_id: str
    discipline: CoachingDiscipline | str
    action_type: str | None = None
    repetition_id: str | None = None
    phase: str | None = None
    raw_value: Any | None = None
    unit: str | None = None
    normalized_score: float | None = Field(default=None, ge=0.0, le=1.0)
    classification_status: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    validity_state: ValidityState
    unavailable_reason: str | None = None
    limitations: list[str] = Field(default_factory=list)
    camera_requirements: CameraRequirements | None = None
    source_model: str | None = None
    capture_profile: CaptureProfile | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    timestamp_refs: list[TimestampRef] = Field(default_factory=list)
    frame_refs: list[FrameRef] = Field(default_factory=list)
    repetition_values: list[Any] = Field(default_factory=list)
    aggregate_stats: dict[str, Any] | None = None
    consistency: dict[str, Any] | None = None
    baseline: Any | None = None
    previous_value: Any | None = None
    personal_best: Any | None = None
    coach_target: Any | None = None
    trend: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_unavailable_reason(self) -> CoachingMetricResultV2:
        if (
            self.validity_state not in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}
            and not self.unavailable_reason
        ):
            raise ValueError("unavailable_reason is required for non-measurable metric states")
        return self


class RepetitionActionRecordV2(BaseModel):
    schema_version: str = COACH_ANALYSIS_V2_SCHEMA_VERSION
    repetition_id: str
    session_id: str | None = None
    job_id: str | None = None
    discipline: CoachingDiscipline | str
    action_type: str | None = None
    start_ts: float | None = None
    end_ts: float | None = None
    start_frame: int | None = None
    end_frame: int | None = None
    segmentation_method: str | None = None
    segmentation_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    manual_override: bool = False
    validity_state: ValidityState
    insufficient_reason: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PhaseRecordV2(BaseModel):
    schema_version: str = COACH_ANALYSIS_V2_SCHEMA_VERSION
    phase_id: str
    repetition_id: str
    phase_name: str
    start_ts: float | None = None
    end_ts: float | None = None
    start_frame: int | None = None
    end_frame: int | None = None
    detection_method: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    requires_object_evidence: bool = False
    camera_view_compatibility: list[str] = Field(default_factory=list)
    manual_correction_supported: bool = False
    validity_state: ValidityState
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class LongitudinalCompareMetadata(BaseModel):
    comparison_identity_fields: list[str] = Field(
        default_factory=lambda: [
            "player_id",
            "discipline",
            "metric_id",
            "metric_version",
            "capture_profile",
        ]
    )
    compatible_validity_states: list[ValidityState] = Field(
        default_factory=lambda: [ValidityState.VALID, ValidityState.LOW_CONFIDENCE]
    )

    model_config = ConfigDict(extra="forbid")


class CoachingAnalysisV2Contract(BaseModel):
    schema_version: str = COACH_ANALYSIS_V2_SCHEMA_VERSION
    capture_profile: CaptureProfile
    validity_state: ValidityState
    metric_results: list[CoachingMetricResultV2] = Field(default_factory=list)
    repetitions: list[RepetitionActionRecordV2] = Field(default_factory=list)
    phases: list[PhaseRecordV2] = Field(default_factory=list)
    longitudinal_compare: LongitudinalCompareMetadata = Field(
        default_factory=LongitudinalCompareMetadata
    )

    model_config = ConfigDict(extra="forbid")


class MetricCompareEligibilityResult(BaseModel):
    comparable: bool
    reason_codes: list[CompatibilityReasonCode] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    comparison_identity: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")
