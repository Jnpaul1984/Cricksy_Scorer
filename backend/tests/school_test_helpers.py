from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient


@dataclass(frozen=True)
class RegisteredUser:
    id: str
    email: str
    token: str
    role: str
    subscription: dict | None
    org_id: str | None

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def register_user(
    client: TestClient,
    email: str,
    password: str = "secret123",
) -> RegisteredUser:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    body = me.json()
    return RegisteredUser(
        id=body["id"],
        email=body["email"],
        token=token,
        role=body["role"],
        subscription=body.get("subscription"),
        org_id=body.get("org_id"),
    )


def create_school(client: TestClient, owner: RegisteredUser, name: str) -> dict:
    response = client.post(
        "/api/organizations",
        json={"name": name, "organization_type": "school"},
        headers=owner.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_membership(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    target_user_id: str,
    role: str,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/memberships",
        json={"user_id": target_user_id, "role": role},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
