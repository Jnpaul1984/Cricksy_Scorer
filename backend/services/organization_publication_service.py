"""Default-private, reversible organization publication persistence."""

from __future__ import annotations

import ipaddress
import re
import uuid
from urllib.parse import unquote, urlsplit

import structlog
from backend.api.schemas.organization_publication import (
    OrganizationBrandingUpdate,
    OrganizationCommunitySettingsResponse,
    OrganizationCompetitionPublicationResponse,
    PublicCommunityCompetition,
    PublicCommunityFixture,
    PublicCommunityStanding,
    PublicOrganizationBranding,
    PublicOrganizationCommunityResponse,
)
from backend.services import school_competition_service
from backend.services.organization_service import (
    ACTIVE_MEMBERSHIP_STATUS,
    ACTIVE_ORGANIZATION_STATUS,
    OrganizationServiceError,
)
from backend.sql_app import models
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

PUBLIC_IDENTIFIER_PATTERN = re.compile(r"^org_[0-9a-f]{24}$")
PUBLICATION_MANAGERS = {"owner", "admin"}
_PUBLIC_IDENTIFIER_NAMESPACE = uuid.UUID("f095452d-9128-46ac-9a82-d504819bcb64")
_PUBLIC_IDENTIFIER_UNIQUE_CONSTRAINT = "uq_organization_public_settings_public_identifier"
_PUBLIC_SETTINGS_PRIMARY_KEY_CONSTRAINT = "organization_public_settings_pkey"
MAX_PUBLIC_COMPETITIONS = 8
MAX_PUBLIC_TEAMS_PER_COMPETITION = 16
MAX_PUBLIC_FIXTURES_PER_COMPETITION = 12
MAX_PUBLIC_STANDING_GAMES_PER_COMPETITION = 64
MAX_ADMIN_COMPETITIONS = 100
SAFE_LOGO_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"})


def _browser_ipv4_address(hostname: str) -> ipaddress.IPv4Address | None:
    """Parse the legacy numeric IPv4 forms normalized by browser URL parsers."""
    parts = hostname.split(".")
    if not parts or len(parts) > 4 or any(not part for part in parts):
        return None

    numbers: list[int] = []
    for part in parts:
        radix = 10
        digits = part
        if part.lower().startswith("0x"):
            radix = 16
            digits = part[2:]
        elif len(part) > 1 and part.startswith("0"):
            radix = 8
            digits = part[1:]

        if digits:
            allowed = {
                8: r"[0-7]+",
                10: r"[0-9]+",
                16: r"[0-9a-fA-F]+",
            }[radix]
            if re.fullmatch(allowed, digits) is None:
                return None
            number = int(digits, radix)
        else:
            number = 0
        numbers.append(number)

    if any(number > 255 for number in numbers[:-1]):
        return None
    if numbers[-1] >= 256 ** (5 - len(numbers)):
        return None

    value = numbers[-1]
    for index, number in enumerate(numbers[:-1]):
        value += number * 256 ** (3 - index)
    return ipaddress.IPv4Address(value)


def public_identifier_candidate(organization_id: str, collision_attempt: int = 0) -> str:
    """Derive an opaque stable candidate without exposing the tenant UUID."""
    seed = f"{organization_id}:{collision_attempt}"
    return f"org_{uuid.uuid5(_PUBLIC_IDENTIFIER_NAMESPACE, seed).hex[:24]}"


def _integrity_constraint_name(exc: IntegrityError) -> str | None:
    current: BaseException | None = exc.orig
    while current is not None:
        constraint_name = getattr(current, "constraint_name", None)
        if isinstance(constraint_name, str):
            return constraint_name
        current = current.__cause__ or current.__context__
    return None


async def create_default_settings(
    db: AsyncSession, *, organization_id: str
) -> models.OrganizationPublicSettings:
    """Insert one settings row, retrying identifier collisions under DB authority."""
    for collision_attempt in range(100):
        settings = models.OrganizationPublicSettings(
            organization_id=organization_id,
            public_identifier=public_identifier_candidate(organization_id, collision_attempt),
            publication_state="unpublished",
        )
        try:
            async with db.begin_nested():
                db.add(settings)
                await db.flush()
        except IntegrityError as exc:
            constraint_name = _integrity_constraint_name(exc)
            if constraint_name == _PUBLIC_SETTINGS_PRIMARY_KEY_CONSTRAINT:
                existing = await db.get(models.OrganizationPublicSettings, organization_id)
                if existing is not None:
                    return existing
            if constraint_name == _PUBLIC_IDENTIFIER_UNIQUE_CONSTRAINT:
                continue
            raise
        return settings
    raise RuntimeError("Unable to allocate organization public identifier")


async def _lock_active_organization(
    db: AsyncSession, *, organization_id: str
) -> models.Organization:
    organization = await db.scalar(
        select(models.Organization)
        .where(
            models.Organization.id == organization_id,
            models.Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
        .with_for_update()
    )
    if organization is None:
        raise OrganizationServiceError(404, "Organization not found")
    return organization


async def _current_membership(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, manage: bool
) -> models.OrganizationMembership:
    membership = await db.scalar(
        select(models.OrganizationMembership)
        .join(
            models.Organization,
            models.Organization.id == models.OrganizationMembership.organization_id,
        )
        .where(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.user_id == actor_user_id,
            models.OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
            models.Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
    )
    if membership is None:
        raise OrganizationServiceError(404, "Organization not found")
    if manage and membership.role not in PUBLICATION_MANAGERS:
        raise OrganizationServiceError(403, "Insufficient organization role")
    return membership


async def get_settings(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> models.OrganizationPublicSettings:
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=False
    )
    settings = await db.get(models.OrganizationPublicSettings, organization_id)
    if settings is None:
        raise OrganizationServiceError(404, "Organization not found")
    return settings


async def set_publication_state(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, publish: bool
) -> models.OrganizationPublicSettings:
    """Serialize with membership changes and make repeated transitions idempotent."""
    await _lock_active_organization(db, organization_id=organization_id)
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=True
    )
    settings = await db.scalar(
        select(models.OrganizationPublicSettings)
        .where(models.OrganizationPublicSettings.organization_id == organization_id)
        .with_for_update()
    )
    if settings is None:
        settings = await create_default_settings(db, organization_id=organization_id)
        await db.flush()

    requested_state = "published" if publish else "unpublished"
    if settings.publication_state != requested_state:
        now = await db.scalar(select(func.now()))
        settings.publication_state = requested_state
        settings.publication_version += 1
        settings.updated_by_user_id = actor_user_id
        if publish:
            settings.published_at = now
            settings.published_by_user_id = actor_user_id
        else:
            settings.unpublished_at = now
            settings.unpublished_by_user_id = actor_user_id
    await db.commit()
    await db.refresh(settings)
    logger.info(
        "organization.publication_changed",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        publication_state=settings.publication_state,
        publication_version=settings.publication_version,
    )
    return settings


async def get_public_organization(
    db: AsyncSession, *, public_identifier: str
) -> tuple[str, str, str] | None:
    if not PUBLIC_IDENTIFIER_PATTERN.fullmatch(public_identifier):
        return None
    row = (
        await db.execute(
            select(
                models.OrganizationPublicSettings.public_identifier,
                models.Organization.name,
                models.Organization.organization_type,
            )
            .join(
                models.Organization,
                models.Organization.id == models.OrganizationPublicSettings.organization_id,
            )
            .where(
                models.OrganizationPublicSettings.public_identifier == public_identifier,
                models.OrganizationPublicSettings.publication_state == "published",
                models.Organization.status == ACTIVE_ORGANIZATION_STATUS,
            )
            .limit(1)
        )
    ).one_or_none()
    return None if row is None else (row[0], row[1], row[2])


def validate_logo_url(value: str) -> str:
    """Validate a passive HTTPS raster-image URL without fetching it server-side."""
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        raise OrganizationServiceError(422, "Logo URL must be between 1 and 2048 characters")
    if any(ord(character) < 32 for character in candidate) or any(
        character in candidate for character in '<>"\\'
    ):
        raise OrganizationServiceError(422, "Logo URL contains unsafe characters")
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise OrganizationServiceError(422, "Logo URL is invalid") from exc
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise OrganizationServiceError(422, "Logo URL must use HTTPS")
    if "%" in parsed.netloc:
        raise OrganizationServiceError(422, "Logo URL host must not use percent encoding")
    if parsed.username or parsed.password or parsed.fragment:
        raise OrganizationServiceError(422, "Logo URL must not contain credentials or fragments")
    try:
        if parsed.port not in (None, 443):
            raise OrganizationServiceError(422, "Logo URL must use the standard HTTPS port")
    except ValueError as exc:
        raise OrganizationServiceError(422, "Logo URL has an invalid port") from exc

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").rstrip(".").lower()
    except UnicodeError as exc:
        raise OrganizationServiceError(422, "Logo URL host is invalid") from exc
    if not hostname:
        raise OrganizationServiceError(422, "Logo URL host is invalid")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise OrganizationServiceError(422, "Logo URL host is not public")
    address: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = _browser_ipv4_address(hostname)
    if address is not None and not address.is_global:
        raise OrganizationServiceError(422, "Logo URL host is not public")

    path = unquote(parsed.path).lower()
    extension = next((suffix for suffix in SAFE_LOGO_EXTENSIONS if path.endswith(suffix)), None)
    if extension is None:
        raise OrganizationServiceError(
            422, "Logo URL must reference a PNG, JPEG, WebP, GIF, or AVIF image"
        )
    return parsed._replace(scheme="https").geturl()


def _validated_alt_text(value: str | None, *, organization_name: str) -> str:
    candidate = (value or f"{organization_name} logo").strip()
    if not candidate or len(candidate) > 120:
        raise OrganizationServiceError(422, "Logo alt text must be between 1 and 120 characters")
    if any(ord(character) < 32 for character in candidate) or any(
        character in candidate for character in "<>"
    ):
        raise OrganizationServiceError(422, "Logo alt text contains unsafe characters")
    return candidate


def _fallback_text(organization_name: str) -> str:
    return next(
        (character.upper() for character in organization_name.strip() if character.isalnum()),
        "C",
    )


async def update_branding(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    payload: OrganizationBrandingUpdate,
) -> models.OrganizationPublicSettings:
    organization = await _lock_active_organization(db, organization_id=organization_id)
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=True
    )
    settings = await db.scalar(
        select(models.OrganizationPublicSettings)
        .where(models.OrganizationPublicSettings.organization_id == organization_id)
        .with_for_update()
    )
    if settings is None:
        settings = await create_default_settings(db, organization_id=organization_id)
        await db.flush()

    if payload.logo_url is None and payload.logo_alt_text is not None:
        raise OrganizationServiceError(422, "Logo alt text requires a logo URL")
    logo_url = validate_logo_url(payload.logo_url) if payload.logo_url is not None else None
    logo_alt_text = (
        _validated_alt_text(payload.logo_alt_text, organization_name=organization.name)
        if logo_url is not None
        else None
    )
    if settings.logo_url != logo_url or settings.logo_alt_text != logo_alt_text:
        settings.logo_url = logo_url
        settings.logo_alt_text = logo_alt_text
        settings.branding_version += 1
        settings.branding_updated_at = await db.scalar(select(func.now()))
        settings.branding_updated_by_user_id = actor_user_id
    await db.commit()
    await db.refresh(settings)
    return settings


async def get_community_settings(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> OrganizationCommunitySettingsResponse:
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=False
    )
    settings = await db.get(models.OrganizationPublicSettings, organization_id)
    if settings is None:
        raise OrganizationServiceError(404, "Organization not found")
    rows = (
        await db.execute(
            select(models.Tournament, models.OrganizationCompetitionPublication)
            .outerjoin(
                models.OrganizationCompetitionPublication,
                models.OrganizationCompetitionPublication.competition_id == models.Tournament.id,
            )
            .where(models.Tournament.organization_id == organization_id)
            .order_by(models.Tournament.name, models.Tournament.id)
            .limit(MAX_ADMIN_COMPETITIONS)
        )
    ).all()
    competitions = [
        OrganizationCompetitionPublicationResponse(
            competition_id=competition.id,
            competition_name=competition.name,
            publication_state=(publication.publication_state if publication else "unpublished"),
            publication_version=(publication.publication_version if publication else 1),
            published_at=(publication.published_at if publication else None),
            unpublished_at=(publication.unpublished_at if publication else None),
            updated_by_user_id=(publication.updated_by_user_id if publication else None),
        )
        for competition, publication in rows
    ]
    return OrganizationCommunitySettingsResponse(
        organization_id=organization_id,
        public_identifier=settings.public_identifier,
        publication_state=settings.publication_state,
        logo_url=settings.logo_url,
        logo_alt_text=settings.logo_alt_text,
        branding_version=settings.branding_version,
        branding_updated_at=settings.branding_updated_at,
        competitions=competitions,
    )


async def set_competition_publication_state(
    db: AsyncSession,
    *,
    organization_id: str,
    competition_id: str,
    actor_user_id: str,
    publish: bool,
) -> tuple[models.OrganizationCompetitionPublication, str]:
    await _lock_active_organization(db, organization_id=organization_id)
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=True
    )
    competition = await db.scalar(
        select(models.Tournament)
        .where(
            models.Tournament.id == competition_id,
            models.Tournament.organization_id == organization_id,
        )
        .with_for_update()
    )
    if competition is None:
        raise OrganizationServiceError(404, "Competition not found")
    publication = await db.scalar(
        select(models.OrganizationCompetitionPublication)
        .where(
            models.OrganizationCompetitionPublication.competition_id == competition_id,
            models.OrganizationCompetitionPublication.organization_id == organization_id,
        )
        .with_for_update()
    )
    if publication is None:
        publication = models.OrganizationCompetitionPublication(
            competition_id=competition_id,
            organization_id=organization_id,
            publication_state="unpublished",
        )
        db.add(publication)
        await db.flush()

    requested_state = "published" if publish else "unpublished"
    if publication.publication_state != requested_state:
        now = await db.scalar(select(func.now()))
        publication.publication_state = requested_state
        publication.publication_version += 1
        publication.updated_by_user_id = actor_user_id
        if publish:
            publication.published_at = now
            publication.published_by_user_id = actor_user_id
        else:
            publication.unpublished_at = now
            publication.unpublished_by_user_id = actor_user_id
    await db.commit()
    await db.refresh(publication)
    return publication, competition.name


async def get_public_community(
    db: AsyncSession, *, public_identifier: str
) -> PublicOrganizationCommunityResponse | None:
    if not PUBLIC_IDENTIFIER_PATTERN.fullmatch(public_identifier):
        return None
    identity = (
        await db.execute(
            select(models.OrganizationPublicSettings, models.Organization)
            .join(
                models.Organization,
                models.Organization.id == models.OrganizationPublicSettings.organization_id,
            )
            .where(
                models.OrganizationPublicSettings.public_identifier == public_identifier,
                models.OrganizationPublicSettings.publication_state == "published",
                models.Organization.status == ACTIVE_ORGANIZATION_STATUS,
            )
            .limit(1)
        )
    ).one_or_none()
    if identity is None:
        return None
    settings, organization = identity

    competitions = list(
        (
            await db.scalars(
                select(models.Tournament)
                .join(
                    models.OrganizationCompetitionPublication,
                    models.OrganizationCompetitionPublication.competition_id
                    == models.Tournament.id,
                )
                .where(
                    models.Tournament.organization_id == organization.id,
                    models.OrganizationCompetitionPublication.organization_id == organization.id,
                    models.OrganizationCompetitionPublication.publication_state == "published",
                )
                .order_by(
                    models.Tournament.start_date.is_(None),
                    models.Tournament.start_date,
                    models.Tournament.name,
                    models.Tournament.id,
                )
                .limit(MAX_PUBLIC_COMPETITIONS)
            )
        ).all()
    )
    competition_ids = [competition.id for competition in competitions]

    entrants_by_competition: dict[str, list[tuple[str, str]]] = {
        competition_id: [] for competition_id in competition_ids
    }
    entrant_totals: dict[str, int] = {}
    fixtures_by_competition: dict[str, list[PublicCommunityFixture]] = {
        competition_id: [] for competition_id in competition_ids
    }
    standings_by_competition: dict[str, list[PublicCommunityStanding]] = {
        competition_id: [] for competition_id in competition_ids
    }

    if competition_ids:
        entrant_rank = (
            func.row_number()
            .over(
                partition_by=models.TournamentTeam.tournament_id,
                order_by=(models.TournamentTeam.team_name, models.TournamentTeam.id),
            )
            .label("entrant_rank")
        )
        entrant_total = (
            func.count()
            .over(partition_by=models.TournamentTeam.tournament_id)
            .label("entrant_total")
        )
        ranked_entrants = (
            select(
                models.TournamentTeam.tournament_id.label("competition_id"),
                models.TournamentTeam.team_id,
                models.TournamentTeam.team_name,
                entrant_rank,
                entrant_total,
            )
            .where(
                models.TournamentTeam.tournament_id.in_(competition_ids),
                models.TournamentTeam.team_id.is_not(None),
            )
            .subquery()
        )
        entrant_rows = (
            await db.execute(
                select(ranked_entrants)
                .where(ranked_entrants.c.entrant_rank <= MAX_PUBLIC_TEAMS_PER_COMPETITION)
                .order_by(ranked_entrants.c.competition_id, ranked_entrants.c.entrant_rank)
            )
        ).all()
        for row in entrant_rows:
            competition_id = str(row.competition_id)
            entrants_by_competition[competition_id].append((str(row.team_id), row.team_name))
            entrant_totals[competition_id] = int(row.entrant_total)

        fixture_rank = (
            func.row_number()
            .over(
                partition_by=models.Fixture.tournament_id,
                order_by=(
                    models.Fixture.scheduled_date.is_(None),
                    models.Fixture.scheduled_date,
                    models.Fixture.match_number,
                    models.Fixture.id,
                ),
            )
            .label("fixture_rank")
        )
        ranked_fixtures = (
            select(
                models.Fixture.tournament_id.label("competition_id"),
                models.Fixture.team_a_name,
                models.Fixture.team_b_name,
                models.Fixture.match_number,
                models.Fixture.venue,
                models.Fixture.scheduled_date,
                models.Fixture.status.label("fixture_status"),
                models.Game.id.label("game_id"),
                models.Game.status.label("game_status"),
                models.Game.result.label("game_result"),
                models.Game.publication_state.label("game_publication_state"),
                fixture_rank,
            )
            .outerjoin(models.Game, models.Game.id == models.Fixture.game_id)
            .where(models.Fixture.tournament_id.in_(competition_ids))
            .subquery()
        )
        fixture_rows = (
            await db.execute(
                select(ranked_fixtures)
                .where(ranked_fixtures.c.fixture_rank <= MAX_PUBLIC_FIXTURES_PER_COMPETITION)
                .order_by(ranked_fixtures.c.competition_id, ranked_fixtures.c.fixture_rank)
            )
        ).all()
        for row in fixture_rows:
            game_status = getattr(row.game_status, "value", row.game_status)
            completed = game_status == models.GameStatus.completed.value
            scorecard_is_public = row.game_publication_state in {
                "published_live",
                "published_final",
            }
            fixtures_by_competition[str(row.competition_id)].append(
                PublicCommunityFixture(
                    team_a_name=row.team_a_name,
                    team_b_name=row.team_b_name,
                    match_number=row.match_number,
                    venue=row.venue,
                    scheduled_date=row.scheduled_date,
                    fixture_status=row.fixture_status,
                    game_status=game_status,
                    result=(
                        school_competition_service.authoritative_result_text(row.game_result)
                        if completed
                        else None
                    ),
                    public_scorecard_path=(
                        f"/school-scorecards/{row.game_id}" if scorecard_is_public else None
                    ),
                )
            )

        completed_counts = dict(
            (
                await db.execute(
                    select(models.Fixture.tournament_id, func.count(models.Fixture.id))
                    .join(models.Game, models.Game.id == models.Fixture.game_id)
                    .where(
                        models.Fixture.tournament_id.in_(competition_ids),
                        models.Game.status == models.GameStatus.completed,
                    )
                    .group_by(models.Fixture.tournament_id)
                )
            ).all()
        )
        standing_competition_ids = [
            competition_id
            for competition_id in competition_ids
            if entrant_totals.get(competition_id, 0) <= MAX_PUBLIC_TEAMS_PER_COMPETITION
            and completed_counts.get(competition_id, 0) <= MAX_PUBLIC_STANDING_GAMES_PER_COMPETITION
        ]
        if standing_competition_ids:
            standing_rows = list(
                (
                    await db.execute(
                        select(models.Fixture, models.Game)
                        .join(models.Game, models.Game.id == models.Fixture.game_id)
                        .where(
                            models.Fixture.tournament_id.in_(standing_competition_ids),
                            models.Game.status == models.GameStatus.completed,
                        )
                        .order_by(models.Fixture.tournament_id, models.Fixture.id)
                    )
                ).all()
            )
            standing_games: dict[str, list[tuple[models.Fixture, models.Game]]] = {
                competition_id: [] for competition_id in standing_competition_ids
            }
            for fixture, game in standing_rows:
                standing_games[fixture.tournament_id].append((fixture, game))
            for competition_id in standing_competition_ids:
                standings = school_competition_service.build_authoritative_standings(
                    competition_id=competition_id,
                    entrants=entrants_by_competition[competition_id],
                    fixture_games=standing_games[competition_id],
                )
                if standings.unresolved_completed_games == 0:
                    standings_by_competition[competition_id] = [
                        PublicCommunityStanding(
                            team_name=entry.team_name,
                            matches_played=entry.matches_played,
                            matches_won=entry.matches_won,
                            matches_lost=entry.matches_lost,
                            matches_drawn=entry.matches_drawn,
                            points=entry.points,
                        )
                        for entry in standings.entries
                    ]

    return PublicOrganizationCommunityResponse(
        public_identifier=settings.public_identifier,
        display_name=organization.name,
        organization_type=organization.organization_type,
        branding=PublicOrganizationBranding(
            logo_url=settings.logo_url,
            logo_alt_text=(settings.logo_alt_text or f"{organization.name} logo"),
            fallback_text=_fallback_text(organization.name),
        ),
        competitions=[
            PublicCommunityCompetition(
                name=competition.name,
                tournament_type=competition.tournament_type,
                start_date=competition.start_date,
                end_date=competition.end_date,
                status=competition.status,
                team_names=[team_name for _, team_name in entrants_by_competition[competition.id]],
                fixtures=fixtures_by_competition[competition.id],
                standings=standings_by_competition[competition.id],
            )
            for competition in competitions
        ],
    )
