#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    head_revisions = script.get_heads()
    print("Discovered Alembic heads:")
    for revision in head_revisions:
        rev = script.get_revision(revision)
        message = rev.doc if rev and rev.doc else "(no message)"
        print(f"- {revision}: {message}")

    if len(head_revisions) != 1:
        print(f"ERROR: Expected exactly 1 Alembic head, found {len(head_revisions)}.")
        return 1

    print("OK: Exactly one Alembic head found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
