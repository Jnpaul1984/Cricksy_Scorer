from backend.services.cpl_team_alias_registry import canonicalize_team_name


def test_barbados_royals_and_tridents_share_canonical_identity() -> None:
    royals = canonicalize_team_name("Barbados Royals")
    tridents = canonicalize_team_name("Barbados Tridents")
    assert royals[0] == "Barbados Royals"
    assert tridents[0] == "Barbados Royals"
    assert royals[1] == tridents[1] == "barbados_franchise"


def test_unknown_team_keeps_original_name() -> None:
    canonical, continuity = canonicalize_team_name("Custom XI")
    assert canonical == "Custom XI"
    assert continuity == "custom xi"


def test_red_steel_and_knight_riders_share_canonical_identity() -> None:
    red_steel = canonicalize_team_name("Trinidad & Tobago Red Steel")
    knight_riders = canonicalize_team_name("Trinbago Knight Riders")
    assert red_steel[0] == knight_riders[0] == "Trinbago Knight Riders"
    assert red_steel[1] == knight_riders[1] == "trinbago_franchise"
