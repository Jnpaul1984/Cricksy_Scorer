from backend.services.cpl_team_alias_registry import canonicalize_team_name


def test_barbados_royals_and_tridents_share_canonical_identity() -> None:
    royals = canonicalize_team_name("Barbados Royals")
    tridents = canonicalize_team_name("Barbados Tridents")
    assert royals[0] == "Barbados Royals"
    assert tridents[0] == "Barbados Royals"
    assert royals[1] == tridents[1] == "barbados_franchise"


def test_unknown_team_keeps_original_name() -> None:
    canonical, continuity = canonicalize_team_name("Trinbago Knight Riders")
    assert canonical == "Trinbago Knight Riders"
    assert continuity == "trinbago knight riders"
