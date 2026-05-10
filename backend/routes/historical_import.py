from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from backend.api.schemas.historical_import import HistoricalImportDryRunResponse
from backend.services.historical_import_preview import build_dry_run_response

router = APIRouter(prefix="/api/historical-import/json", tags=["historical-import"])


@router.post("/dry-run", response_model=HistoricalImportDryRunResponse)
async def historical_json_dry_run(
    request: Request,
    file: UploadFile | None = File(default=None),
) -> HistoricalImportDryRunResponse | JSONResponse:
    payload_bytes: bytes

    if file is not None:
        payload_bytes = await file.read()
    else:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            raise HTTPException(
                status_code=415,
                detail="Provide application/json payload or multipart file upload.",
            )
        payload_bytes = await request.body()

    status_code, response = build_dry_run_response(payload_bytes)
    if status_code >= 400:
        return JSONResponse(status_code=status_code, content=response.model_dump())
    return response
