"""
Sponsor Rotation Engine - Automatic sponsor rotation scheduling and tracking

Features:
- Sponsor rotation schedule builder based on game phases
- Exposure tracking (impressions/displays per sponsor)
- Dynamic rotation based on high-engagement moments (wickets, boundaries)
- Priority weighting for sponsors
- Analytics: sponsor exposure metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EngagementEvent(str, Enum):
    """High-engagement moments in cricket match"""

    WICKET = "wicket"
    BOUNDARY = "boundary"
    SIX = "six"
    FIFTY = "fifty"
    MILESTONE = "milestone"
    TIMEOUT = "timeout"


class RotationStrategy(str, Enum):
    """Sponsor rotation strategies"""

    EQUAL_TIME = "equal_time"  # Each sponsor gets equal overs
    PRIORITY_WEIGHTED = "priority_weighted"  # High-priority sponsors get more overs
    DYNAMIC = "dynamic"  # Adjust based on engagement


@dataclass
class Sponsor:
    """Sponsor configuration"""

    sponsor_id: str
    name: str
    logo_url: str
    priority: int  # 1-10, higher = more exposure
    target_exposures: int  # Target number of displays per match
    max_consecutive_overs: int = 2  # Max overs sponsor can display consecutively


@dataclass
class SponsorSlot:
    """Individual sponsor slot in rotation"""

    slot_id: str
    over_num: int  # 1-indexed
    ball_num: int  # 1-6 per over
    sponsor_id: str
    sponsor_name: str
    priority: int
    event_type: str | None = None  # Type of engagement triggering this slot
    exposure_value: float = 1.0  # 1.0 = standard, 1.5 = premium (wicket/boundary)


@dataclass
class SponsorExposureMetrics:
    """Metrics for sponsor exposure during match"""

    sponsor_id: str
    sponsor_name: str
    total_exposures: int
    premium_exposures: int  # During high-engagement moments
    exposure_rate: float  # % of total slots
    first_exposure_over: int
    last_exposure_over: int
    peak_engagement_over: int | None  # Over with most events


@dataclass
class RotationSchedule:
    """Complete sponsor rotation schedule for a match"""

    schedule_id: str
    game_id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    strategy: RotationStrategy
    sponsors: list[Sponsor]
    slots: list[SponsorSlot] = field(default_factory=list)
    max_overs: int = 20  # T20 = 20, ODI = 50
    exposures_per_sponsor: dict[str, int] = field(default_factory=dict)
    engagement_events: list[tuple[int, EngagementEvent]] = field(
        default_factory=list
    )  # (over, event)


class SponsorRotationEngine:
    """Engine for managing sponsor rotation scheduling and tracking"""

    @staticmethod
    def build_rotation_schedule(
        game_id: str,
        organization_id: str,
        sponsors: list[Sponsor],
        max_overs: int = 20,
        strategy: RotationStrategy = RotationStrategy.EQUAL_TIME,
    ) -> RotationSchedule:
        """
        Build initial sponsor rotation schedule for a match

        Args:
            game_id: ID of the game
            organization_id: ID of the organization
            sponsors: List of Sponsor configurations
            max_overs: Total overs in match (20 for T20, 50 for ODI)
            strategy: Rotation strategy to use

        Returns:
            RotationSchedule with slots populated
        """
        if not sponsors:
            return RotationSchedule(
                schedule_id=f"schedule_{game_id}_{organization_id}",
                game_id=game_id,
                organization_id=organization_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                strategy=strategy,
                sponsors=sponsors,
                max_overs=max_overs,
            )

        schedule = RotationSchedule(
            schedule_id=f"schedule_{game_id}_{organization_id}",
            game_id=game_id,
            organization_id=organization_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            strategy=strategy,
            sponsors=sponsors,
            max_overs=max_overs,
        )

        # Calculate slots based on strategy
        if strategy == RotationStrategy.EQUAL_TIME:
            slots = SponsorRotationEngine._build_equal_time_slots(sponsors, max_overs, game_id)
        elif strategy == RotationStrategy.PRIORITY_WEIGHTED:
            slots = SponsorRotationEngine._build_priority_weighted_slots(
                sponsors, max_overs, game_id
            )
        else:  # DYNAMIC
            slots = SponsorRotationEngine._build_dynamic_slots(sponsors, max_overs, game_id)

        schedule.slots = slots

        # Initialize exposure tracking
        for sponsor in sponsors:
            schedule.exposures_per_sponsor[sponsor.sponsor_id] = 0

        return schedule

    @staticmethod
    def _build_equal_time_slots(
        sponsors: list[Sponsor], max_overs: int, game_id: str
    ) -> list[SponsorSlot]:
        """
        Build rotation slots with equal time distribution

        Each sponsor gets roughly equal overs throughout match
        """
        slots = []
        total_overs = max_overs
        total_sponsors = len(sponsors)
        overs_per_sponsor = total_overs // total_sponsors
        remainder = total_overs % total_sponsors

        current_sponsor_idx = 0
        overs_for_current = overs_per_sponsor + (1 if current_sponsor_idx < remainder else 0)

        for over_num in range(1, total_overs + 1):
            # Create one slot per over (could expand to multiple per over if needed)
            sponsor = sponsors[current_sponsor_idx]
            slot = SponsorSlot(
                slot_id=f"slot_{game_id}_{over_num}_1",
                over_num=over_num,
                ball_num=1,
                sponsor_id=sponsor.sponsor_id,
                sponsor_name=sponsor.name,
                priority=sponsor.priority,
                exposure_value=1.0,
            )
            slots.append(slot)

            overs_for_current -= 1
            if overs_for_current == 0:
                current_sponsor_idx = (current_sponsor_idx + 1) % total_sponsors
                overs_for_current = overs_per_sponsor + (
                    1 if current_sponsor_idx < remainder else 0
                )

        return slots

    @staticmethod
    def _build_priority_weighted_slots(
        sponsors: list[Sponsor], max_overs: int, game_id: str
    ) -> list[SponsorSlot]:
        """
        Build rotation slots with priority weighting

        Sponsors with higher priority (1-10) get more slots
        """
        slots = []
        total_priority = sum(s.priority for s in sponsors)
        total_overs = max_overs

        # Calculate overs per sponsor based on priority weight
        sponsor_overs: dict[str, int] = {}
        overs_assigned = 0

        for i, sponsor in enumerate(sponsors):
            is_last = i == len(sponsors) - 1
            if is_last:
                # Give last sponsor remaining overs
                overs_for_sponsor = total_overs - overs_assigned
            else:
                # Calculate based on priority weight
                weight = sponsor.priority / total_priority
                overs_for_sponsor = int(total_overs * weight)

            sponsor_overs[sponsor.sponsor_id] = overs_for_sponsor
            overs_assigned += overs_for_sponsor

        # Distribute slots
        over_assignments = []
        for sponsor in sponsors:
            overs = sponsor_overs[sponsor.sponsor_id]
            for _ in range(overs):
                over_assignments.append(sponsor)

        for over_num, sponsor in enumerate(over_assignments, start=1):
            slot = SponsorSlot(
                slot_id=f"slot_{game_id}_{over_num}_1",
                over_num=over_num,
                ball_num=1,
                sponsor_id=sponsor.sponsor_id,
                sponsor_name=sponsor.name,
                priority=sponsor.priority,
                exposure_value=1.0,
            )
            slots.append(slot)

        return slots

    @staticmethod
    def _build_dynamic_slots(
        sponsors: list[Sponsor], max_overs: int, game_id: str
    ) -> list[SponsorSlot]:
        """
        Build rotation slots with dynamic adjustment

        Starts with equal distribution, ready for dynamic updates based on engagement
        """
        # Start with equal time, can be modified dynamically during match
        return SponsorRotationEngine._build_equal_time_slots(sponsors, max_overs, game_id)

    @staticmethod
    def get_sponsor_for_over(
        schedule: RotationSchedule, over_num: int, ball_num: int = 1
    ) -> SponsorSlot | None:
        """
        Get sponsor display for specific over and ball

        Args:
            schedule: Current rotation schedule
            over_num: Over number (1-indexed)
            ball_num: Ball number in over (1-6)

        Returns:
            SponsorSlot if found, else None
        """
        for slot in schedule.slots:
            if slot.over_num == over_num and slot.ball_num == ball_num:
                return slot
        return None

    @staticmethod
    def record_engagement(
        schedule: RotationSchedule,
        over_num: int,
        event_type: EngagementEvent,
    ) -> None:
        """
        Record engagement event and adjust rotation if using DYNAMIC strategy

        Args:
            schedule: Current rotation schedule
            over_num: Over when event occurred
            event_type: Type of engagement event
        """
        schedule.engagement_events.append((over_num, event_type))

        # For DYNAMIC strategy, could increase exposure of current sponsor
        if schedule.strategy == RotationStrategy.DYNAMIC:
            current_slot = SponsorRotationEngine.get_sponsor_for_over(schedule, over_num)
            if current_slot:
                # Increase exposure value during high-engagement moments
                if event_type in [
                    EngagementEvent.WICKET,
                    EngagementEvent.SIX,
                    EngagementEvent.BOUNDARY,
                ]:
                    current_slot.event_type = event_type.value
                    current_slot.exposure_value = 1.5  # Premium exposure

    @staticmethod
    def record_exposure(schedule: RotationSchedule, sponsor_id: str, premium: bool = False) -> None:
        """
        Record that a sponsor was displayed

        Args:
            schedule: Current rotation schedule
            sponsor_id: ID of sponsor that was displayed
            premium: Whether this was a premium exposure (high-engagement moment)
        """
        if sponsor_id not in schedule.exposures_per_sponsor:
            schedule.exposures_per_sponsor[sponsor_id] = 0

        # Count premium exposures differently if tracking separately
        schedule.exposures_per_sponsor[sponsor_id] += 1
        schedule.updated_at = datetime.utcnow()

    @staticmethod
    def get_exposure_metrics(schedule: RotationSchedule) -> dict[str, SponsorExposureMetrics]:
        """
        Calculate exposure metrics for all sponsors

        Args:
            schedule: Current rotation schedule

        Returns:
            Dict mapping sponsor_id to SponsorExposureMetrics
        """
        metrics: dict[str, SponsorExposureMetrics] = {}
        total_slots = len(schedule.slots)

        # Find first and last exposure for each sponsor
        sponsor_over_ranges: dict[str, tuple[int, int]] = {}

        for slot in schedule.slots:
            sponsor_id = slot.sponsor_id
            if sponsor_id not in sponsor_over_ranges:
                sponsor_over_ranges[sponsor_id] = (slot.over_num, slot.over_num)
            else:
                first, last = sponsor_over_ranges[sponsor_id]
                sponsor_over_ranges[sponsor_id] = (
                    min(first, slot.over_num),
                    max(last, slot.over_num),
                )

        # Find peak engagement overs
        engagement_by_over: dict[int, int] = {}
        for over_num, _event in schedule.engagement_events:
            if over_num not in engagement_by_over:
                engagement_by_over[over_num] = 0
            engagement_by_over[over_num] += 1

        # Build metrics for each sponsor
        for sponsor in schedule.sponsors:
            sponsor_id = sponsor.sponsor_id
            exposure_count = schedule.exposures_per_sponsor.get(sponsor_id, 0)

            first_over, last_over = sponsor_over_ranges.get(sponsor_id, (0, 0))
            peak_over = None

            if first_over > 0:
                # Find peak engagement over for this sponsor
                peak_engagement_count = 0
                for slot in schedule.slots:
                    if slot.sponsor_id == sponsor_id and slot.over_num in engagement_by_over:
                        if engagement_by_over[slot.over_num] > peak_engagement_count:
                            peak_engagement_count = engagement_by_over[slot.over_num]
                            peak_over = slot.over_num

            metrics[sponsor_id] = SponsorExposureMetrics(
                sponsor_id=sponsor_id,
                sponsor_name=sponsor.name,
                total_exposures=exposure_count,
                premium_exposures=sum(
                    1
                    for slot in schedule.slots
                    if slot.sponsor_id == sponsor_id and slot.exposure_value > 1.0
                ),
                exposure_rate=exposure_count / max(total_slots, 1) * 100,
                first_exposure_over=first_over if first_over > 0 else 0,
                last_exposure_over=last_over if last_over > 0 else 0,
                peak_engagement_over=peak_over,
            )

        return metrics

    @staticmethod
    def adjust_rotation_for_phase(
        schedule: RotationSchedule,
        phase: str,  # "powerplay", "middle", "death"
        boost_priority_sponsor_id: str | None = None,
    ) -> None:
        """
        Adjust rotation based on match phase

        Args:
            schedule: Current rotation schedule
            phase: Match phase (powerplay/middle/death)
            boost_priority_sponsor_id: Optional sponsor to boost in this phase
        """
        if phase == "powerplay":
            # Powerplay: overs 1-6
            phase_overs = range(1, 7)
        elif phase == "death":
            # Death: last 3 overs
            phase_overs = range(max(1, schedule.max_overs - 2), schedule.max_overs + 1)
        else:  # middle
            # Middle overs
            phase_overs = range(7, schedule.max_overs - 2)

        if boost_priority_sponsor_id:
            # Increase exposure value for priority sponsor in this phase
            for slot in schedule.slots:
                if slot.over_num in phase_overs and slot.sponsor_id == boost_priority_sponsor_id:
                    slot.exposure_value = 1.3

        schedule.updated_at = datetime.utcnow()
