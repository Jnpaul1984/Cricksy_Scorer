from __future__ import annotations

from dataclasses import asdict, dataclass

ACTION_REGISTRY_VERSION = "cricket_coaching_actions.v1"


@dataclass(frozen=True)
class GovernedCoachingAction:
    action_id: str
    version: str
    discipline: str
    phases: tuple[str, ...]
    metric_terms: tuple[str, ...]
    technical_area: str
    why_it_matters: str
    coaching_objective: str
    coaching_cue: str
    drills: tuple[str, ...]
    coach_observation: str
    reassessment_criterion: str
    provenance: tuple[str, ...]
    review_status: str = "approved_for_coach_review"
    player_facing_eligible: bool = False
    requires_coach_approval: bool = True
    caution: str = "Coach review is required before this action is shared with a player."

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["phases"] = list(self.phases)
        payload["metric_terms"] = list(self.metric_terms)
        payload["drills"] = list(self.drills)
        payload["provenance"] = list(self.provenance)
        return payload


_PROVENANCE = (
    "Cricksy Player Development skill contract and coach-approval governance",
    "Cricksy Phase 10J V2 discipline/phase metric contracts",
    "ECB Core Coach: player-centred planning, practice design, and discipline-specific core principles "
    "(https://resources.ecb.co.uk/ecb/document/2021/11/09/"
    "abb54d97-4dc5-4f9c-aef1-e3642fd9dc0d/ECB_SUP_FND_I_Core_Coach_briefing.pdf)",
    "ICC Coaching Level 2: biomechanics, video analysis, skill acquisition, and specialist coaching "
    "(https://www.icc-cricket.com/media-releases/"
    "icc-strengthens-training-and-education-programme-with-launch-of-level-2-coaching-course)",
    "Phase 10J.14 repository-governed coaching review; action wording is an internal adaptation",
)


COACHING_ACTIONS: tuple[GovernedCoachingAction, ...] = (
    GovernedCoachingAction(
        "batting-base-alignment",
        ACTION_REGISTRY_VERSION,
        "batting",
        ("setup", "trigger", "backlift"),
        ("setup", "stance", "trigger", "backlift", "head"),
        "Base and early-movement alignment",
        "A repeatable base helps the batter organize movement into the scoring stroke.",
        "Repeat a balanced setup and controlled initial movement.",
        "Set the base, keep the eyes level, then move under control.",
        (
            "Static setup checkpoint with coach feedback",
            "Shadow batting through trigger and backlift",
        ),
        "Watch whether head and base remain organized into the downswing.",
        "Reassess the same V2 setup/trigger metric across at least three comparable repetitions.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "batting-swing-balance",
        ACTION_REGISTRY_VERSION,
        "batting",
        ("downswing", "contact_proxy_window", "follow_through"),
        ("downswing", "contact_proxy", "follow_through", "balance", "knee"),
        "Swing-phase balance",
        "Controlled body organization supports a repeatable path and balanced completion.",
        "Improve repeatable body organization through the scoring stroke.",
        "Stay balanced through the ball and finish under control.",
        ("Drop-feed balance drill", "Controlled throwdown with finish hold"),
        "Watch the head, front-side support, and balanced finish; contact remains a proxy without ball/bat evidence.",
        "Compare the linked phase metric and consistency classification on a comparable capture.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "pace-gather-delivery",
        ACTION_REGISTRY_VERSION,
        "pace_bowling",
        ("approach", "gather", "back_foot_contact", "delivery_stride"),
        ("approach", "gather", "back_foot", "delivery_stride", "alignment"),
        "Approach and delivery organization",
        "A repeatable gather connects approach momentum to an organized delivery stride.",
        "Build a repeatable approach, gather, and delivery-stride shape.",
        "Arrive balanced at the crease and carry momentum toward the target.",
        ("Walk-through gather drill", "Marked run-up and crease-alignment drill"),
        "Watch approach rhythm, gather balance, and alignment into the delivery stride.",
        "Reassess the linked approach/gather V2 metric over comparable deliveries.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "pace-release-follow-through",
        ACTION_REGISTRY_VERSION,
        "pace_bowling",
        ("front_foot_contact", "release", "follow_through"),
        ("front_foot", "release", "follow_through", "arm_angle", "trunk"),
        "Release and follow-through",
        "Release repeatability and directed follow-through support consistent execution.",
        "Improve release repeatability while maintaining direction through follow-through.",
        "Drive through the target and let the bowling action complete.",
        ("One-step release drill", "Target-bowling release corridor"),
        "Watch release-window consistency and continued movement toward the target.",
        "Compare the governed release metric and its valid-repetition spread.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "spin-gather-pivot",
        ACTION_REGISTRY_VERSION,
        "spin_bowling",
        ("approach", "gather", "pivot", "front_foot_contact"),
        ("approach", "gather", "pivot", "front_foot", "rotation"),
        "Gather and pivot",
        "A stable gather and pivot support repeatable rotation into the delivery.",
        "Coordinate a stable gather with a repeatable pivot into delivery.",
        "Stay tall through the gather and rotate around a stable front side.",
        ("Bound-and-pivot rehearsal", "Crease pivot alignment drill"),
        "Watch rhythm into the gather, pivot position, and front-foot stability.",
        "Reassess the linked pivot/rotation metric across comparable deliveries.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "spin-release-consistency",
        ACTION_REGISTRY_VERSION,
        "spin_bowling",
        ("release", "follow_through"),
        ("release", "arm_path", "alignment", "follow_through"),
        "Release consistency",
        "A repeatable arm path and release window support consistent delivery execution.",
        "Repeat the arm path and release window without forcing a prescribed outcome.",
        "Match the arm path to the target and complete the action.",
        ("Standing release-to-target drill", "Three-ball release-window check"),
        "Watch release-window repeatability and completion of the action.",
        "Compare the linked release metric and consistency evidence on the next session.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "keeping-ready-movement",
        ACTION_REGISTRY_VERSION,
        "wicketkeeping",
        ("setup", "ready", "lateral_movement", "movement"),
        ("ready", "base", "lateral", "movement", "head"),
        "Ready position and movement",
        "A balanced ready position supports efficient movement into a take.",
        "Create a balanced ready position that supports efficient lateral movement.",
        "Set early, stay balanced, and move the head with the line of the ball.",
        ("Ready-position freeze check", "Lateral take footwork drill"),
        "Watch base width, first movement, and head position into the take.",
        "Reassess the linked setup/movement metric over comparable takes.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "keeping-take-stumping",
        ACTION_REGISTRY_VERSION,
        "wicketkeeping",
        ("taking", "take", "standing_up", "standing_back", "leg_side", "stumping"),
        ("take", "collection", "glove", "stumping", "standing", "leg_side"),
        "Taking and stumping",
        "Stable collection supports an efficient transfer when ball and stump evidence is visible.",
        "Improve clean collection and efficient transfer where object evidence supports it.",
        "Receive the ball softly, then bring the hands to the target.",
        ("Coach-fed clean-take drill", "Take-to-stumps transfer drill"),
        "Watch glove presentation, collection stability, and transfer path.",
        "Reassess only with sufficient ball/stump evidence and comparable take type.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "fielding-collection",
        ACTION_REGISTRY_VERSION,
        "fielding",
        ("ground_fielding", "pickup", "collection", "catch", "boundary_movement"),
        ("ground", "pickup", "collection", "catch", "boundary", "head_base"),
        "Approach and collection",
        "Body organization behind the ball supports controlled collection and the next action.",
        "Organize the body behind the ball for a controlled collection.",
        "Get the head over the line and collect through the ball.",
        ("Rolling-ball approach and pickup drill", "Coach-fed catch-and-hold drill"),
        "Watch approach control, head position, and security of the collection.",
        "Reassess the linked collection metric with the same fielding action type.",
        _PROVENANCE,
    ),
    GovernedCoachingAction(
        "fielding-transfer-throw",
        ACTION_REGISTRY_VERSION,
        "fielding",
        ("transfer", "throw", "recovery", "follow_through"),
        ("transfer", "throw", "recovery", "shoulder_hip", "balance"),
        "Transfer and throw",
        "An organized transfer links collection to a balanced, directed throwing action.",
        "Connect a clean transfer to a balanced, directed throw.",
        "Transfer early, align to the target, and finish the throw.",
        ("Pickup-transfer-release drill", "Two-target throwing alignment drill"),
        "Watch transfer time, alignment, release direction, and recovery balance.",
        "Compare the linked transfer/throw metric on comparable attempts.",
        _PROVENANCE,
    ),
)


def discipline_from_metric(metric_id: str, fallback: str | None = None) -> str | None:
    for discipline in ("pace_bowling", "spin_bowling", "wicketkeeping", "fielding", "batting"):
        if metric_id.startswith(f"{discipline}_"):
            return discipline
    if fallback == "bowling":
        return None
    return fallback


def governed_actions_for(
    *, metric_id: str, discipline: str | None, phase: str | None
) -> list[dict[str, object]]:
    resolved_discipline = discipline_from_metric(metric_id, discipline)
    if resolved_discipline is None:
        return []
    normalized_phase = (phase or "").lower()
    normalized_metric = metric_id.lower()
    matches = [
        action
        for action in COACHING_ACTIONS
        if action.discipline == resolved_discipline
        and (
            normalized_phase in action.phases
            or any(term in normalized_metric for term in action.metric_terms)
        )
    ]
    return [action.as_payload() for action in matches[:3]]
