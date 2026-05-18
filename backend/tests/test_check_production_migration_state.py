from __future__ import annotations

from backend.scripts.check_production_migration_state import (
    build_connect_args,
    classify_migration_state,
    collect_lineage,
    load_script_directory,
)


def test_classify_migration_state_at_head() -> None:
    _, script = load_script_directory()
    repo_head = script.get_heads()[0]

    state = classify_migration_state((repo_head,), (repo_head,), script)

    assert state.status == "at_head"
    assert state.behind is False


def test_classify_migration_state_marks_ancestor_as_behind() -> None:
    _, script = load_script_directory()
    repo_head = script.get_heads()[0]
    lineage = sorted(collect_lineage(script, repo_head))
    ancestor = next(revision for revision in lineage if revision != repo_head)

    state = classify_migration_state((ancestor,), (repo_head,), script)

    assert state.status == "behind"
    assert state.behind is True
    assert "behind" in state.detail.lower()


def test_classify_migration_state_handles_uninitialized_database() -> None:
    _, script = load_script_directory()
    repo_head = script.get_heads()[0]

    state = classify_migration_state((), (repo_head,), script)

    assert state.status == "uninitialized"
    assert state.behind is True


def test_classify_migration_state_rejects_unknown_revision() -> None:
    _, script = load_script_directory()
    repo_head = script.get_heads()[0]

    state = classify_migration_state(("deadbeefdead",), (repo_head,), script)

    assert state.status == "unknown"
    assert state.behind is False


def test_build_connect_args_are_driver_aware() -> None:
    assert build_connect_args("postgresql+asyncpg://user:pass@localhost/db") == {
        "timeout": 60,
        "server_settings": {"application_name": "alembic-migration-state"},
    }
    assert build_connect_args("sqlite+aiosqlite:///tmp/test.db") == {"timeout": 60}
    assert build_connect_args("postgresql://user:pass@localhost/db") == {}
