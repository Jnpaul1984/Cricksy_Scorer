from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, model_validator

from backend.error_handlers import install_exception_handlers


class DeliveryLikePayload(BaseModel):
    runs_scored: int | None = None
    runs_off_bat: int | None = None

    @model_validator(mode="after")
    def reject_illegal_run_shape(self):
        if self.runs_off_bat not in (None, 0):
            raise ValueError("runs_off_bat must be 0/None on a legal ball")
        return self


class NumberPayload(BaseModel):
    value: int


def test_request_validation_error_with_valueerror_context_is_json_safe() -> None:
    app = FastAPI()
    install_exception_handlers(app)

    @app.post("/deliveries")
    async def deliveries(payload: DeliveryLikePayload) -> dict:
        return payload.model_dump()

    response = TestClient(app).post(
        "/deliveries", json={"runs_scored": 1, "runs_off_bat": 1}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["type"] == "validation_error"
    assert body["error"]["message"] == "Invalid request."
    assert body["error"]["details"][0]["ctx"]["error"] == (
        "runs_off_bat must be 0/None on a legal ball"
    )


def test_request_validation_error_without_exception_context_remains_structured() -> None:
    app = FastAPI()
    install_exception_handlers(app)

    @app.post("/number")
    async def number(payload: NumberPayload) -> dict:
        return payload.model_dump()

    response = TestClient(app).post("/number", json={"value": "not-a-number"})

    assert response.status_code == 422
    detail = response.json()["error"]["details"][0]
    assert detail["loc"] == ["body", "value"]
    assert detail["type"] == "int_parsing"
