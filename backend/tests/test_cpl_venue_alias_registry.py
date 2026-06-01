from backend.services.cpl_venue_alias_registry import resolve_venue_identity


def test_merges_daren_sammy_missing_country_suffix() -> None:
    resolved = resolve_venue_identity("Daren Sammy National Cricket Stadium, Gros Islet")

    assert resolved is not None
    assert (
        resolved.canonical_display_name
        == "Daren Sammy National Cricket Stadium, Gros Islet, St Lucia"
    )
    assert (
        resolved.canonical_venue_key == "daren_sammy_national_cricket_stadium_gros_islet_st_lucia"
    )
    assert resolved.source_method == "explicit_alias"
    assert resolved.confidence == "high"


def test_handles_punctuation_case_and_spacing_normalization() -> None:
    resolved = resolve_venue_identity("  QUEEN'S   PARK OVAL ,   PORT OF SPAIN ")

    assert resolved is not None
    assert resolved.canonical_display_name == "Queen's Park Oval, Port of Spain, Trinidad"
    assert resolved.canonical_venue_key == "queens_park_oval_port_of_spain_trinidad"
    assert resolved.country == "Trinidad"


def test_uses_cpl_context_for_city_only_alias() -> None:
    resolved = resolve_venue_identity(
        "North Sound",
        competition_name="Caribbean Premier League",
        competition_code="CPL_MEN",
    )

    assert resolved is not None
    assert resolved.canonical_display_name == "Sir Vivian Richards Stadium, North Sound, Antigua"
    assert resolved.source_method == "competition_context_alias"
    assert resolved.confidence == "medium"


def test_does_not_over_resolve_ambiguous_without_context() -> None:
    resolved = resolve_venue_identity("North Sound")

    assert resolved is not None
    assert resolved.canonical_display_name == "North Sound"
    assert resolved.canonical_venue_key == "north sound"
    assert resolved.source_method == "raw_fallback"
    assert resolved.confidence == "low"


def test_merges_warner_park_missing_country_suffix() -> None:
    resolved_short = resolve_venue_identity("Warner Park, Basseterre")
    resolved_full = resolve_venue_identity("Warner Park, Basseterre, St Kitts")

    assert resolved_short is not None
    assert resolved_full is not None
    assert resolved_short.canonical_display_name == "Warner Park, Basseterre, St Kitts"
    assert resolved_full.canonical_display_name == "Warner Park, Basseterre, St Kitts"
    assert resolved_short.canonical_venue_key == "warner_park_basseterre_st_kitts"
    assert resolved_full.canonical_venue_key == "warner_park_basseterre_st_kitts"
