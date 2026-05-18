#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.script.revision import Revision

MigrationStatus = Literal["at_head", "behind", "uninitialized", "multiple_heads", "unknown"]


@dataclass(frozen=True)
class MigrationState:
    current_revisions: tuple[str, ...]
    repo_heads: tuple[str, ...]
    status: MigrationStatus
    behind: bool
    detail: str


def load_script_directory() -> tuple[Path, ScriptDirectory]:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    return backend_dir, ScriptDirectory.from_config(config)


def build_connect_args(database_url: str) -> dict[str, object]:
    driver_name = make_url(database_url).drivername
    if driver_name.endswith("+asyncpg"):
        return {
            "timeout": 60,
            "server_settings": {"application_name": "alembic-migration-state"},
        }
    if driver_name.endswith("+aiosqlite"):
        return {"timeout": 60}
    return {}


async def fetch_current_revisions(database_url: str) -> tuple[str, ...]:
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
        connect_args=build_connect_args(database_url),
    )
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            return tuple(str(row[0]) for row in result.fetchall())
    except ProgrammingError as exc:
        message = str(exc).lower()
        if "alembic_version" in message and (
            "does not exist" in message
            or "undefinedtable" in message
            or "undefined table" in message
            or "no such table" in message
        ):
            return ()
        raise
    finally:
        await engine.dispose()


def _iter_down_revisions(revision: Revision) -> tuple[str, ...]:
    down_revision = revision.down_revision
    if down_revision is None:
        return ()
    if isinstance(down_revision, str):
        return (down_revision,)
    return tuple(str(value) for value in down_revision)


def collect_lineage(script: ScriptDirectory, head_revision: str) -> set[str]:
    lineage: set[str] = set()
    stack: list[Revision] = []

    head = script.get_revision(head_revision)
    if head is None:
        return lineage
    stack.append(head)

    while stack:
        revision = stack.pop()
        revision_id = str(revision.revision)
        if revision_id in lineage:
            continue
        lineage.add(revision_id)
        for down_revision in _iter_down_revisions(revision):
            down = script.get_revision(down_revision)
            if down is not None:
                stack.append(down)

    return lineage


def classify_migration_state(
    current_revisions: tuple[str, ...],
    repo_heads: tuple[str, ...],
    script: ScriptDirectory,
) -> MigrationState:
    if len(repo_heads) != 1:
        return MigrationState(
            current_revisions=current_revisions,
            repo_heads=repo_heads,
            status="multiple_heads",
            behind=False,
            detail="Repository Alembic graph must have exactly one head before deployment.",
        )

    repo_head = repo_heads[0]
    if current_revisions == (repo_head,):
        return MigrationState(
            current_revisions=current_revisions,
            repo_heads=repo_heads,
            status="at_head",
            behind=False,
            detail="Production database is already at the repository Alembic head.",
        )

    lineage = collect_lineage(script, repo_head)
    if not current_revisions:
        return MigrationState(
            current_revisions=current_revisions,
            repo_heads=repo_heads,
            status="uninitialized",
            behind=True,
            detail=(
                "Production database has no alembic_version row and is behind the "
                "repository head."
            ),
        )

    if all(revision in lineage for revision in current_revisions):
        return MigrationState(
            current_revisions=current_revisions,
            repo_heads=repo_heads,
            status="behind",
            behind=True,
            detail="Production database revision is behind the repository Alembic head.",
        )

    return MigrationState(
        current_revisions=current_revisions,
        repo_heads=repo_heads,
        status="unknown",
        behind=False,
        detail=(
            "Production database revision is not an ancestor of the repository head. "
            "Manual investigation is required before deployment."
        ),
    )


def _annotation(level: Literal["warning", "error"], message: str) -> None:
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")


def _write_summary(label: str, state: MigrationState) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    current_display = ", ".join(state.current_revisions) if state.current_revisions else "(none)"
    head_display = ", ".join(state.repo_heads) if state.repo_heads else "(none)"
    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write(f"### Alembic migration gate ({label})\n")
        summary.write(f"- Current DB revision(s): `{current_display}`\n")
        summary.write(f"- Repo head revision(s): `{head_display}`\n")
        summary.write(f"- Status: `{state.status}`\n")
        summary.write(f"- Behind repo head: `{'yes' if state.behind else 'no'}`\n")
        summary.write(f"- Detail: {state.detail}\n\n")


async def async_main() -> int:
    parser = argparse.ArgumentParser(
        description="Report production database Alembic state and optionally require head parity."
    )
    parser.add_argument(
        "--label",
        default="production",
        help="Label used in human-readable output (for example pre-upgrade or post-upgrade).",
    )
    parser.add_argument(
        "--require-at-head",
        action="store_true",
        help="Exit non-zero unless the database is exactly at the repository Alembic head.",
    )
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is required.")
        return 1

    _, script = load_script_directory()
    repo_heads = tuple(script.get_heads())
    current_revisions = await fetch_current_revisions(database_url)
    state = classify_migration_state(current_revisions, repo_heads, script)

    current_display = ", ".join(current_revisions) if current_revisions else "(none)"
    head_display = ", ".join(repo_heads) if repo_heads else "(none)"
    print(f"[{args.label}] Current production DB revision(s): {current_display}")
    print(f"[{args.label}] Repo Alembic head revision(s): {head_display}")
    print(f"[{args.label}] Behind repo head: {'yes' if state.behind else 'no'}")
    print(f"[{args.label}] Detail: {state.detail}")
    if state.behind:
        print(
            f"[{args.label}] Action: run `python -m alembic -c backend/alembic.ini upgrade head` "
            "before deploying backend code."
        )

    _write_summary(args.label, state)

    if state.status in {"multiple_heads", "unknown"}:
        _annotation("error", state.detail)
        return 1

    if args.require_at_head and state.status != "at_head":
        _annotation(
            "error",
            (
                f"{args.label}: production database is not at repo head "
                f"({current_display} vs {head_display})."
            ),
        )
        return 1

    if state.behind:
        _annotation(
            "warning",
            (
                f"{args.label}: production database is behind repo head "
                f"({current_display} vs {head_display})."
            ),
        )

    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
