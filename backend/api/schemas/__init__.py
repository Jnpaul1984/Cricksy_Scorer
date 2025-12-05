"""API schemas for the Cricksy Scorer backend."""

from .analyst_matches import (
    AnalystMatchListItem,
    AnalystMatchListResponse,
)
from .case_study import (
    CaseStudyAIBlock,
    CaseStudyDismissalByBowlerType,
    CaseStudyDismissalByShotType,
    CaseStudyDismissalByZone,
    CaseStudyDismissalPatterns,
    CaseStudyInningsSummary,
    CaseStudyKeyPhase,
    CaseStudyKeyPlayer,
    CaseStudyMatch,
    CaseStudyMomentumSummary,
    CaseStudyPhase,
    CaseStudyPlayerBatting,
    CaseStudyPlayerBowling,
    CaseStudyPlayerFielding,
    CaseStudySwingMetric,
    MatchCaseStudyResponse,
)

__all__ = [
    # Analyst Match List schemas
    "AnalystMatchListItem",
    "AnalystMatchListResponse",
    # Case Study schemas
    "CaseStudyAIBlock",
    "CaseStudyDismissalByBowlerType",
    "CaseStudyDismissalByShotType",
    "CaseStudyDismissalByZone",
    "CaseStudyDismissalPatterns",
    "CaseStudyInningsSummary",
    "CaseStudyKeyPhase",
    "CaseStudyKeyPlayer",
    "CaseStudyMatch",
    "CaseStudyMomentumSummary",
    "CaseStudyPhase",
    "CaseStudyPlayerBatting",
    "CaseStudyPlayerBowling",
    "CaseStudyPlayerFielding",
    "CaseStudySwingMetric",
    "MatchCaseStudyResponse",
]
