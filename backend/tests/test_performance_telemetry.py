from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from backend.services import performance_telemetry
from backend.services.performance_telemetry import instrument_coach_operation


@dataclass
class _PdfResult:
    pdf_size_bytes: int
    private_report: str


@pytest.mark.asyncio
async def test_instrumentation_records_safe_metadata_without_response_content(monkeypatch) -> None:
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        performance_telemetry.logger,
        "info",
        lambda event, **fields: events.append((event, fields)),
    )

    @instrument_coach_operation("coach_plus.pdf_export")
    async def operation() -> _PdfResult:
        return _PdfResult(pdf_size_bytes=2048, private_report="not-for-telemetry")

    result = await operation()

    assert result.private_report == "not-for-telemetry"
    assert events[0][0] == "coach_performance"
    assert events[0][1] == {
        "operation": "coach_plus.pdf_export",
        "layer": "backend",
        "duration_ms": events[0][1]["duration_ms"],
        "outcome": "success",
        "status": 200,
        "payload_size_bytes": 2048,
    }
    assert "private_report" not in repr(events)
    assert "not-for-telemetry" not in repr(events)


@pytest.mark.asyncio
async def test_instrumentation_records_status_and_preserves_handler_failure(monkeypatch) -> None:
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        performance_telemetry.logger,
        "info",
        lambda event, **fields: events.append((event, fields)),
    )

    @instrument_coach_operation("coach_plus.completed_session")
    async def operation() -> None:
        raise HTTPException(status_code=404, detail="not found")

    with pytest.raises(HTTPException, match="not found"):
        await operation()

    assert events[0][1]["outcome"] == "failure"
    assert events[0][1]["status"] == 404


@pytest.mark.asyncio
async def test_instrumentation_failure_does_not_break_handler_result(monkeypatch) -> None:
    def fail_to_log(*args, **kwargs) -> None:
        raise RuntimeError("logging unavailable")

    monkeypatch.setattr(performance_telemetry.logger, "info", fail_to_log)

    @instrument_coach_operation("coach_plus.session_list")
    async def operation() -> list[str]:
        return ["unchanged"]

    assert await operation() == ["unchanged"]
