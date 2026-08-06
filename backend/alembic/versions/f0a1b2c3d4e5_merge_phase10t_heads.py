"""Merge phase 10T heads (venue intelligence + podcast prep / CPL roster).

Revision ID: f0a1b2c3d4e5
Revises: 7a606e3d5b82, e7f8a9b0c1d2
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Union

from alembic import op  # noqa: F401

# Revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: Union[tuple[str, str], None] = ("7a606e3d5b82", "e7f8a9b0c1d2")
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
