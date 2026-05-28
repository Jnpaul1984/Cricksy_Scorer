"""API schemas for the Cricksy Scorer backend."""

from .analyst_matches import (
    AnalystMatchListItem,
    AnalystMatchListResponse,
)
from .case_study import (
    CaseStudyAIBlock,
    CaseStudyAnalystCallout,
    CaseStudyDismissalByBowlerType,
    CaseStudyDismissalByShotType,
    CaseStudyDismissalByZone,
    CaseStudyDismissalPatterns,
    CaseStudyInningsAnalysis,
    CaseStudyInningsSummary,
    CaseStudyKeyPhase,
    CaseStudyKeyPlayer,
    CaseStudyMatch,
    CaseStudyMomentumSummary,
    CaseStudyPhase,
    CaseStudyPlayerBatting,
    CaseStudyPlayerBowling,
    CaseStudyPlayerFielding,
    CaseStudyStoryBlocks,
    CaseStudySwingMetric,
    MatchCaseStudyResponse,
)

__all__ = [
    # Analyst Match List schemas
    "AnalystMatchListItem",
    "AnalystMatchListResponse",
    # Case Study schemas
    "CaseStudyAIBlock",
    "CaseStudyAnalystCallout",
    "CaseStudyDismissalByBowlerType",
    "CaseStudyDismissalByShotType",
    "CaseStudyDismissalByZone",
    "CaseStudyDismissalPatterns",
    "CaseStudyInningsAnalysis",
    "CaseStudyInningsSummary",
    "CaseStudyKeyPhase",
    "CaseStudyKeyPlayer",
    "CaseStudyMatch",
    "CaseStudyMomentumSummary",
    "CaseStudyPhase",
    "CaseStudyPlayerBatting",
    "CaseStudyPlayerBowling",
    "CaseStudyPlayerFielding",
    "CaseStudyStoryBlocks",
    "CaseStudySwingMetric",
    "MatchCaseStudyResponse",
]
