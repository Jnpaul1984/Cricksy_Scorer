"""Phase 5C - Historical Import Batch Tracking Service.

Provides:
- ``create_import_batch`` - persist a dry-run preview batch record.
- ``find_duplicate_by_hash`` - detect exact duplicate by SHA-256.
- ``find_duplicate_by_semantic_key`` - detect semantic duplicate by match key.
- ``get_import_batch`` - retrieve a single batch by ID.
- ``list_import_batches`` - list batches scoped to a user/org.

No Game, Delivery, Player, or Team rows are created by any function here.
``is_finalized`` remains False for every batch in this phase.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.sql_app.models import HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def find_duplicate_by_hash(
    db: AsyncSession,
    source_hash: str,
    owner_user_id: str | None = None,
    owner_org_id: str | None = None,
) -> HistoricalImportBatch | None:
    """Return the most recent batch with the same source hash, scoped to user/org.

    Scoping priority:
    1. If *owner_user_id* is provided, check user-scoped records first.
    2. If *owner_org_id* is provided, also check org-scoped records.
    3. If neither is provided, check unscoped (anonymous) records only.
    """
    stmt = (
        select(HistoricalImportBatch)
        .where(HistoricalImportBatch.source_hash_sha256 == source_hash)
        .order_by(HistoricalImportBatch.created_at.desc())
        .limit(1)
    )

    if owner_user_id:
        stmt = stmt.where(HistoricalImportBatch.owner_user_id == owner_user_id)
    elif owner_org_id:
        stmt = stmt.where(HistoricalImportBatch.owner_org_id == owner_org_id)
    else:
        stmt = stmt.where(
            HistoricalImportBatch.owner_user_id.is_(None),
            HistoricalImportBatch.owner_org_id.is_(None),
        )

    result = await db.execute(stmt)
    return result.scalars().first()


async def find_duplicate_by_semantic_key(
    db: AsyncSession,
    semantic_key: str,
    owner_user_id: str | None = None,
    owner_org_id: str | None = None,
) -> HistoricalImportBatch | None:
    """Return the most recent batch with the same semantic key, scoped to user/org."""
    stmt = (
        select(HistoricalImportBatch)
        .where(HistoricalImportBatch.semantic_key == semantic_key)
        .order_by(HistoricalImportBatch.created_at.desc())
        .limit(1)
    )

    if owner_user_id:
        stmt = stmt.where(HistoricalImportBatch.owner_user_id == owner_user_id)
    elif owner_org_id:
        stmt = stmt.where(HistoricalImportBatch.owner_org_id == owner_org_id)
    else:
        stmt = stmt.where(
            HistoricalImportBatch.owner_user_id.is_(None),
            HistoricalImportBatch.owner_org_id.is_(None),
        )

    result = await db.execute(stmt)
    return result.scalars().first()


async def get_import_batch(
    db: AsyncSession,
    batch_id: str,
) -> HistoricalImportBatch | None:
    """Retrieve a single import batch by its ID."""
    result = await db.execute(
        select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
    )
    return result.scalars().first()


async def create_import_batch(
    db: AsyncSession,
    *,
    batch_id: str | None = None,
    source_hash_sha256: str,
    source_format: str,
    status: str,
    error_count: int,
    warning_count: int,
    innings_count: int,
    delivery_count: int,
    dry_run_summary: dict[str, Any] | None = None,
    owner_user_id: str | None = None,
    owner_org_id: str | None = None,
    source_filename: str | None = None,
    semantic_key: str | None = None,
) -> HistoricalImportBatch:
    """Create and persist a new historical import batch record.

    ``is_finalized`` is always False in Phase 5C.
    No Game/Delivery/Player/Team rows are created.
    """
    batch = HistoricalImportBatch(
        id=batch_id or str(uuid.uuid4()),
        owner_user_id=owner_user_id,
        owner_org_id=owner_org_id,
        source_filename=source_filename,
        source_format=source_format,
        source_hash_sha256=source_hash_sha256,
        semantic_key=semantic_key,
        status=status,
        error_count=error_count,
        warning_count=warning_count,
        innings_count=innings_count,
        delivery_count=delivery_count,
        dry_run_summary=dry_run_summary,
        is_finalized=False,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def list_import_batches(
    db: AsyncSession,
    owner_user_id: str | None = None,
    owner_org_id: str | None = None,
    limit: int = 50,
) -> list[HistoricalImportBatch]:
    """List historical import batch records for a given user or org.

    Results are ordered newest-first.  Limit is capped at 200.
    """
    effective_limit = min(limit, 200)

    stmt = (
        select(HistoricalImportBatch)
        .order_by(HistoricalImportBatch.created_at.desc())
        .limit(effective_limit)
    )

    if owner_user_id:
        stmt = stmt.where(HistoricalImportBatch.owner_user_id == owner_user_id)
    elif owner_org_id:
        stmt = stmt.where(HistoricalImportBatch.owner_org_id == owner_org_id)
    else:
        stmt = stmt.where(
            HistoricalImportBatch.owner_user_id.is_(None),
            HistoricalImportBatch.owner_org_id.is_(None),
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())
