from __future__ import annotations

from dataclasses import asdict, dataclass

ACTION_REGISTRY_VERSION = "cricket_coaching_actions.v1"


@dataclass(frozen=True)
class GovernedCoachingAction:
    action_id: str
    version: str
    discipline: str
    phases: tuple[str, ...]
    metric_ids: tuple[str, ...]
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
        payload["metric_ids"] = list(self.metric_ids)
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


# Production V2 metric-pack contracts are the authority for governed action
# selection. Each entry is (discipline, phase, action_id).
PRODUCTION_METRIC_ACTION_CONTRACTS: dict[str, tuple[str, str, str]] = {
    "batting_setup_stance_width_ratio": ("batting", "setup", "batting-base-alignment"),
    "batting_setup_head_base_offset_ratio": (
        "batting",
        "setup",
        "batting-base-alignment",
    ),
    "batting_trigger_head_displacement_ratio": (
        "batting",
        "trigger",
        "batting-base-alignment",
    ),
    "batting_downswing_head_stability_score": (
        "batting",
        "downswing",
        "batting-swing-balance",
    ),
    "batting_contact_proxy_front_knee_angle_deg": (
        "batting",
        "contact_proxy_window",
        "batting-swing-balance",
    ),
    "batting_follow_through_balance_drift_ratio": (
        "batting",
        "follow_through",
        "batting-swing-balance",
    ),
    "pace_bowling_approach_head_stability_score": (
        "pace_bowling",
        "approach",
        "pace-gather-delivery",
    ),
    "pace_bowling_gather_balance_drift_ratio": (
        "pace_bowling",
        "gather",
        "pace-gather-delivery",
    ),
    "pace_bowling_front_foot_contact_front_knee_angle_deg": (
        "pace_bowling",
        "front_foot_contact",
        "pace-release-follow-through",
    ),
    "pace_bowling_release_proxy_bowling_arm_angle_deg": (
        "pace_bowling",
        "release_proxy_window",
        "pace-release-follow-through",
    ),
    "pace_bowling_release_proxy_trunk_lean_deg": (
        "pace_bowling",
        "release_proxy_window",
        "pace-release-follow-through",
    ),
    "pace_bowling_follow_through_balance_drift_ratio": (
        "pace_bowling",
        "follow_through",
        "pace-release-follow-through",
    ),
    "spin_bowling_approach_head_stability_score": (
        "spin_bowling",
        "approach",
        "spin-gather-pivot",
    ),
    "spin_bowling_coil_balance_drift_ratio": (
        "spin_bowling",
        "coil",
        "spin-gather-pivot",
    ),
    "spin_bowling_pivot_shoulder_hip_separation_deg": (
        "spin_bowling",
        "pivot",
        "spin-gather-pivot",
    ),
    "spin_bowling_delivery_stride_head_base_offset_ratio": (
        "spin_bowling",
        "delivery_stride",
        "spin-gather-pivot",
    ),
    "spin_bowling_release_proxy_bowling_arm_angle_deg": (
        "spin_bowling",
        "release_proxy_window",
        "spin-release-consistency",
    ),
    "spin_bowling_follow_through_balance_drift_ratio": (
        "spin_bowling",
        "follow_through",
        "spin-release-consistency",
    ),
    "wicketkeeping_set_stance_width_ratio": (
        "wicketkeeping",
        "set",
        "keeping-ready-movement",
    ),
    "wicketkeeping_set_knee_flexion_angle_deg": (
        "wicketkeeping",
        "set",
        "keeping-ready-movement",
    ),
    "wicketkeeping_reaction_head_stability_score": (
        "wicketkeeping",
        "reaction_read",
        "keeping-ready-movement",
    ),
    "wicketkeeping_movement_lateral_displacement_ratio": (
        "wicketkeeping",
        "movement",
        "keeping-ready-movement",
    ),
    "wicketkeeping_collection_balance_drift_ratio": (
        "wicketkeeping",
        "collection",
        "keeping-take-stumping",
    ),
    "wicketkeeping_recovery_head_base_offset_ratio": (
        "wicketkeeping",
        "recovery",
        "keeping-ready-movement",
    ),
    "wicketkeeping_context_standing_set_depth_delta_ratio": (
        "wicketkeeping",
        "set",
        "keeping-ready-movement",
    ),
    "wicketkeeping_leg_side_movement_lateral_displacement_ratio": (
        "wicketkeeping",
        "movement",
        "keeping-ready-movement",
    ),
    "wicketkeeping_stumping_action_wrist_compactness_ratio": (
        "wicketkeeping",
        "action",
        "keeping-take-stumping",
    ),
    "fielding_ready_stance_width_ratio": (
        "fielding",
        "ready",
        "fielding-collection",
    ),
    "fielding_reaction_head_stability_score": (
        "fielding",
        "reaction",
        "fielding-collection",
    ),
    "fielding_approach_balance_drift_ratio": (
        "fielding",
        "approach",
        "fielding-collection",
    ),
    "fielding_ground_collection_body_drop_ratio": (
        "fielding",
        "collection",
        "fielding-collection",
    ),
    "fielding_ground_collection_knee_flexion_angle_deg": (
        "fielding",
        "collection",
        "fielding-collection",
    ),
    "fielding_ground_collection_head_base_offset_ratio": (
        "fielding",
        "collection",
        "fielding-collection",
    ),
    "fielding_catch_collection_wrist_compactness_ratio": (
        "fielding",
        "collection",
        "fielding-collection",
    ),
    "fielding_transfer_balance_drift_ratio": (
        "fielding",
        "transfer",
        "fielding-transfer-throw",
    ),
    "fielding_throw_action_shoulder_hip_separation_deg": (
        "fielding",
        "throw_action",
        "fielding-transfer-throw",
    ),
    "fielding_recovery_balance_drift_ratio": (
        "fielding",
        "recovery",
        "fielding-transfer-throw",
    ),
}

# Narrow exact aliases retained for existing persisted fixtures and historical
# V2 payloads. They are compatibility-only and never production authority.
_COMPATIBILITY_METRIC_ACTION_CONTRACTS: dict[str, tuple[str, str, str]] = {
    "batting_setup_head_alignment_ratio": ("batting", "setup", "batting-base-alignment"),
    "batting_contact_proxy_alignment_ratio": (
        "batting",
        "contact_proxy_window",
        "batting-swing-balance",
    ),
    "pace_bowling_release_arm_angle_degrees": (
        "pace_bowling",
        "release",
        "pace-release-follow-through",
    ),
    "spin_bowling_pivot_alignment_ratio": (
        "spin_bowling",
        "pivot",
        "spin-gather-pivot",
    ),
    "wicketkeeping_ready_base_width_ratio": (
        "wicketkeeping",
        "ready",
        "keeping-ready-movement",
    ),
    "fielding_collection_head_base_ratio": (
        "fielding",
        "collection",
        "fielding-collection",
    ),
    "fielding_transfer_balance_ratio": (
        "fielding",
        "transfer",
        "fielding-transfer-throw",
    ),
}
_METRIC_ACTION_CONTRACTS = {
    **PRODUCTION_METRIC_ACTION_CONTRACTS,
    **_COMPATIBILITY_METRIC_ACTION_CONTRACTS,
}


def _metric_ids_for(action_id: str) -> tuple[str, ...]:
    return tuple(
        metric_id
        for metric_id, (_, _, mapped_action_id) in _METRIC_ACTION_CONTRACTS.items()
        if mapped_action_id == action_id
    )


COACHING_ACTIONS: tuple[GovernedCoachingAction, ...] = (
    GovernedCoachingAction(
        "batting-base-alignment",
        ACTION_REGISTRY_VERSION,
        "batting",
        ("setup", "trigger", "backlift"),
        _metric_ids_for("batting-base-alignment"),
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
        _metric_ids_for("batting-swing-balance"),
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
        _metric_ids_for("pace-gather-delivery"),
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
        ("front_foot_contact", "release_proxy_window", "follow_through", "release"),
        _metric_ids_for("pace-release-follow-through"),
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
        ("approach", "coil", "pivot", "delivery_stride"),
        _metric_ids_for("spin-gather-pivot"),
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
        ("release_proxy_window", "follow_through", "release"),
        _metric_ids_for("spin-release-consistency"),
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
        ("set", "reaction_read", "movement", "recovery", "ready"),
        _metric_ids_for("keeping-ready-movement"),
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
        ("collection", "action", "taking", "take", "standing_up", "standing_back"),
        _metric_ids_for("keeping-take-stumping"),
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
        ("ready", "reaction", "approach", "collection"),
        _metric_ids_for("fielding-collection"),
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
        ("transfer", "throw_action", "recovery"),
        _metric_ids_for("fielding-transfer-throw"),
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
    contract = _METRIC_ACTION_CONTRACTS.get(metric_id)
    if contract is None:
        return []
    expected_discipline, expected_phase, action_id = contract
    supplied_discipline = (discipline or "").strip().lower()
    supplied_phase = (phase or "").strip().lower()
    metric_discipline = discipline_from_metric(metric_id)
    if (
        metric_discipline != expected_discipline
        or supplied_discipline != expected_discipline
        or supplied_phase != expected_phase
    ):
        return []
    action = next(
        (
            candidate
            for candidate in COACHING_ACTIONS
            if candidate.action_id == action_id
            and candidate.discipline == expected_discipline
            and metric_id in candidate.metric_ids
        ),
        None,
    )
    return [action.as_payload()] if action is not None else []
