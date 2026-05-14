"""CLI for Phase 5P deterministic training-dataset artifact builds (no model training)."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path

from sqlalchemy.exc import OperationalError

from backend.services.model_training_dataset_builder import (
    DatasetBuildFilters,
    DatasetBuildRequest,
    build_model_training_dataset,
)
from backend.sql_app.database import get_session_local


def _default_output_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "artifacts" / "model_training_datasets"


def _write_json(output_path: Path, artifact: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(output_path: Path, rows: list[dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({key for row in rows for key in row})
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def _run(args: argparse.Namespace) -> int:
    session_maker = get_session_local()

    request = DatasetBuildRequest(
        filters=DatasetBuildFilters(
            source_format=args.source_format,
            match_type=args.match_type,
            season=args.season,
            competition=args.competition,
        )
    )

    async with session_maker() as session:
        try:
            artifact = await build_model_training_dataset(session, request)
        except OperationalError as exc:
            raise RuntimeError(
                "Dataset build failed because required database tables are not ready. "
                "Run migrations (e.g., `alembic upgrade head`) before running this builder."
            ) from exc

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir()
    output_base = args.output_name or "training_dataset_v1"

    json_path = output_dir / f"{output_base}.json"
    _write_json(json_path, artifact)

    if args.format == "csv":
        csv_path = output_dir / f"{output_base}.csv"
        rows_obj = artifact.get("rows", [])
        rows = rows_obj if isinstance(rows_obj, list) else []
        _write_csv(csv_path, rows)

    print(f"Dataset schema: {artifact['dataset_schema_version']}")
    print(f"Included matches: {artifact['included_match_count']}")
    print(f"Excluded matches: {artifact['excluded_match_count']}")
    print(f"Rows: {artifact['row_count']}")
    print(f"JSON artifact: {json_path}")
    if args.format == "csv":
        print(f"CSV rows: {output_dir / f'{output_base}.csv'}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic model-training dataset artifacts from governed historical imports"
        )
    )
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--output-name", type=str, default=None)
    parser.add_argument("--source-format", type=str, default=None)
    parser.add_argument("--match-type", type=str, default=None)
    parser.add_argument("--season", type=str, default=None)
    parser.add_argument("--competition", type=str, default=None)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
