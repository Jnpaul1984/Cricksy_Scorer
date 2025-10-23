from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}