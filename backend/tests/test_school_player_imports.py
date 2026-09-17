from __future__ import annotations

import asyncio
import datetime as dt
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select, text

from backend.api.schemas.player_imports import PlayerImportApplyRequest
from backend.services import organization_entitlement_service, school_player_import_service
from backend.sql_app.models import (
    PlayerProfile,
    RoleEnum,
    SchoolPlayerImport,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_school,
    register_user,
)


def _preview_url(organization_id: str) -> str:
    return f"/api/organizations/{organization_id}/player-imports/preview"


def _apply_url(organization_id: str, import_id: str) -> str:
    return f"/api/organizations/{organization_id}/player-imports/{import_id}/apply"


def _preview(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    content: bytes,
    filename: str = "players.csv",
    mapping: dict[str, str] | None = None,
):
    data = {} if mapping is None else {"column_mapping": json.dumps(mapping)}
    return client.post(
        _preview_url(organization_id),
        files={"file": (filename, content, "application/octet-stream")},
        data=data,
        headers=actor.headers,
    )


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _create_team(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/teams",
        json={"name": name},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_roster_player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    *,
    name: str,
    student_identifier: str | None = None,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/players",
        json={"player_name": name, "student_identifier": student_identifier},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_csv_preview_is_roster_immutable_and_apply_creates_canonical_players(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-csv-owner@example.com")
    organization = create_school(school_client, owner, "CSV Import School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    response = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,student_identifier,year_group,Ignored\nAsha Khan,S-1,Year 8,private\n",
    )
    assert response.status_code == 201, response.text
    preview = response.json()
    assert preview["file_type"] == "csv"
    assert preview["row_count"] == 1
    assert preview["rows"][0]["classification"] == "create_new"
    assert "Ignored" not in preview["column_mapping"]
    assert "private" not in response.text

    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 0
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 0
        assert await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) == 0
        assert await session.scalar(select(func.count(User.id))) == 1
        stored = await session.get(SchoolPlayerImport, preview["import_id"])
        assert stored is not None
        assert stored.preview_rows[0]["values"] == {
            "player_name": "Asha Khan",
            "student_identifier": "S-1",
            "year_group": "Year 8",
            "team_name": None,
        }

    applied = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["summary"]["created_players"] == 1
    async with session_maker() as session:
        profile = (await session.execute(select(PlayerProfile))).scalar_one()
        membership = (await session.execute(select(SchoolPlayerMembership))).scalar_one()
        assert profile.player_name == "Asha Khan"
        assert membership.player_profile_id == profile.player_id
        assert membership.student_identifier == "S-1"
        assert await session.scalar(select(func.count(User.id))) == 1


async def test_xlsx_preview_zero_mutations_and_happy_path_team_apply(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-xlsx-owner@example.com")
    organization = create_school(school_client, owner, "XLSX Import School")
    team = _create_team(school_client, owner, organization["id"], "Under 15")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    before_team = None
    async with session_maker() as session:
        stored_team = await session.get(Team, team["id"])
        assert stored_team is not None
        before_team = list(stored_team.players)

    response = _preview(
        school_client,
        owner,
        organization["id"],
        _xlsx(
            [
                ["Student Name", "ID Number", "Form", "Cricket Team"],
                ["Miguel Thomas", "M-7", "Form 3", "Under 15"],
            ]
        ),
        filename="ordinary-roster.xlsx",
        mapping={
            "Student Name": "player_name",
            "ID Number": "student_identifier",
            "Form": "year_group",
            "Cricket Team": "team_name",
        },
    )
    assert response.status_code == 201, response.text
    preview = response.json()
    assert preview["file_type"] == "xlsx"
    assert preview["rows"][0]["resolved_team_id"] == team["id"]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 0
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 0
        assert await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) == 0

    applied = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["summary"] == {
        "created_players": 1,
        "linked_existing_players": 0,
        "reactivated_memberships": 0,
        "team_assignments_created": 1,
        "team_assignments_reactivated": 0,
        "no_op_rows": 0,
        "skipped_rows": 0,
        "failed_rows": 0,
    }
    async with session_maker() as session:
        assignment = (await session.execute(select(SchoolTeamPlayerMembership))).scalar_one()
        membership = await session.get(
            SchoolPlayerMembership, assignment.school_player_membership_id
        )
        stored_team = await session.get(Team, team["id"])
        assert membership is not None and membership.organization_id == organization["id"]
        assert stored_team is not None and stored_team.players == before_team == []


def test_same_name_rows_are_not_auto_merged_and_can_create_distinct_players(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-same-name@example.com")
    organization = create_school(school_client, owner, "Same Name Import School")
    preview_response = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nJohn Smith\nJohn Smith\n",
    )
    assert preview_response.status_code == 201
    preview = preview_response.json()
    assert [row["classification"] for row in preview["rows"]] == [
        "ambiguous_needs_review",
        "ambiguous_needs_review",
    ]
    unresolved = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert unresolved.status_code == 200
    assert unresolved.json()["summary"]["failed_rows"] == 2

    second = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nJohn Smith\nJohn Smith\n",
    ).json()
    applied = school_client.post(
        _apply_url(organization["id"], second["import_id"]),
        json={
            "resolutions": [
                {"source_row_number": 2, "action": "create_new"},
                {"source_row_number": 3, "action": "create_new"},
            ]
        },
        headers=owner.headers,
    )
    assert applied.status_code == 200
    ids = [row["player_profile_id"] for row in applied.json()["rows"]]
    assert len(set(ids)) == 2


async def test_existing_and_inactive_memberships_require_bound_explicit_resolution(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-existing-owner@example.com")
    coach = register_user(school_client, "import-existing-coach@example.com")
    organization = create_school(school_client, owner, "Existing Import School")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")
    existing = _create_roster_player(
        school_client,
        owner,
        organization["id"],
        name="Retained Student",
        student_identifier="RET-1",
    )
    school_client.patch(
        f"/api/organizations/{organization['id']}/players/{existing['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,student_identifier\nRetained Student,RET-1\n",
    ).json()
    row = preview["rows"][0]
    assert row["classification"] == "ambiguous_needs_review"
    assert row["resolved_school_player_membership_id"] == existing["id"]

    tampered = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "reactivate_existing",
                    "school_player_membership_id": "foreign-id",
                }
            ]
        },
        headers=owner.headers,
    )
    assert tampered.status_code == 200
    assert tampered.json()["rows"][0]["outcome"] == "failed"

    coach_preview = _preview(
        school_client,
        coach,
        organization["id"],
        b"player_name,student_identifier\nRetained Student,RET-1\n",
    ).json()
    coach_apply = school_client.post(
        _apply_url(organization["id"], coach_preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "reactivate_existing",
                    "school_player_membership_id": existing["id"],
                }
            ]
        },
        headers=coach.headers,
    )
    assert coach_apply.status_code == 200
    assert coach_apply.json()["rows"][0]["detail"] == (
        "Only owner/admin may reactivate roster membership"
    )

    owner_preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,student_identifier\nRetained Student,RET-1\n",
    ).json()
    reactivated = school_client.post(
        _apply_url(organization["id"], owner_preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "reactivate_existing",
                    "school_player_membership_id": existing["id"],
                }
            ]
        },
        headers=owner.headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["summary"]["reactivated_memberships"] == 1
    assert reactivated.json()["rows"][0]["school_player_membership_id"] == existing["id"]
    assert reactivated.json()["rows"][0]["player_profile_id"] == existing["player_profile_id"]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 1
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1


async def test_team_resolution_duplicate_archived_and_existing_assignment(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-team-resolution@example.com")
    organization = create_school(school_client, owner, "Team Resolution School")
    team_a = _create_team(school_client, owner, organization["id"], "First XI")
    team_b = _create_team(school_client, owner, organization["id"], "First XI")
    archived = _create_team(school_client, owner, organization["id"], "Archived XI")
    school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{archived['id']}",
        headers=owner.headers,
    )
    existing = _create_roster_player(
        school_client,
        owner,
        organization["id"],
        name="Existing Team Player",
        student_identifier="TEAM-1",
    )

    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,student_identifier,team_name\nExisting Team Player,TEAM-1,First XI\n",
    ).json()
    assert preview["rows"][0]["classification"] == "ambiguous_needs_review"
    assert {item["team_id"] for item in preview["rows"][0]["team_candidates"]} == {
        team_a["id"],
        team_b["id"],
    }
    applied = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "use_existing",
                    "school_player_membership_id": existing["id"],
                    "team_id": team_a["id"],
                }
            ]
        },
        headers=owner.headers,
    )
    assert applied.status_code == 200
    assert applied.json()["summary"]["created_players"] == 0
    assert applied.json()["summary"]["team_assignments_created"] == 1

    archived_preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,team_name\nNew Player,Archived XI\n",
    )
    assert archived_preview.status_code == 201
    assert archived_preview.json()["rows"][0]["classification"] == "invalid"
    assert "Archived Team" in archived_preview.text


@pytest.mark.parametrize("role", ["scorer", "viewer"])
def test_read_only_roles_cannot_preview_or_apply(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"import-{role}-owner@example.com")
    reader = register_user(school_client, f"import-{role}@example.com")
    organization = create_school(school_client, owner, f"{role} Import School")
    add_membership(school_client, owner, organization["id"], reader.id, role)
    denied = _preview(
        school_client,
        reader,
        organization["id"],
        b"player_name\nDenied\n",
    )
    assert denied.status_code == 403


async def test_nonmember_global_authority_and_missing_capability_do_not_bypass(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "import-gates-owner@example.com")
    outsider = register_user(school_client, "import-gates-outsider@example.com")
    organization = create_school(school_client, owner, "Import Gates School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        stored.role = RoleEnum.org_pro
        stored.is_superuser = True
        stored.org_id = organization["id"]
        await session.commit()
    denied = _preview(
        school_client,
        outsider,
        organization["id"],
        b"player_name\nDenied\n",
    )
    assert denied.status_code == 404

    approved = organization_entitlement_service.SCHOOL_FREE_CAPABILITIES - {"school_master_roster"}
    monkeypatch.setitem(
        organization_entitlement_service.PLAN_CAPABILITIES,
        organization_entitlement_service.SCHOOL_FREE_PLAN_KEY,
        frozenset(approved),
    )
    capability_denied = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nDenied\n",
    )
    assert capability_denied.status_code == 403


@pytest.mark.parametrize("missing_capability", ["school_persistent_teams", "school_team_rosters"])
def test_team_import_requires_both_team_capabilities(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    missing_capability: str,
) -> None:
    owner = register_user(school_client, f"import-{missing_capability}@example.com")
    organization = create_school(school_client, owner, f"Missing {missing_capability} Import")
    _create_team(school_client, owner, organization["id"], "Capability XI")
    approved = organization_entitlement_service.SCHOOL_FREE_CAPABILITIES - {missing_capability}
    monkeypatch.setitem(
        organization_entitlement_service.PLAN_CAPABILITIES,
        organization_entitlement_service.SCHOOL_FREE_PLAN_KEY,
        frozenset(approved),
    )
    denied = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,team_name\nDenied Player,Capability XI\n",
    )
    assert denied.status_code == 403
    assert denied.json() == {"detail": f"Organization capability not enabled: {missing_capability}"}


def test_cross_tenant_resolution_ids_are_rejected_without_metadata_leakage(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "import-cross-a@example.com")
    owner_b = register_user(school_client, "import-cross-b@example.com")
    school_a = create_school(school_client, owner_a, "Import Cross A")
    school_b = create_school(school_client, owner_b, "Import Cross B")
    team_a = _create_team(school_client, owner_a, school_a["id"], "Shared Team Name")
    team_b = _create_team(school_client, owner_b, school_b["id"], "Secret Foreign Team")
    foreign_player = _create_roster_player(
        school_client,
        owner_b,
        school_b["id"],
        name="Secret Foreign Player",
        student_identifier="FOREIGN-1",
    )
    preview = _preview(
        school_client,
        owner_a,
        school_a["id"],
        b"player_name,team_name\nLocal Reviewed Player,Shared Team Name\n",
    ).json()
    assert preview["rows"][0]["resolved_team_id"] == team_a["id"]
    tampered = school_client.post(
        _apply_url(school_a["id"], preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "use_existing",
                    "school_player_membership_id": foreign_player["id"],
                    "team_id": team_b["id"],
                }
            ]
        },
        headers=owner_a.headers,
    )
    assert tampered.status_code == 200
    assert tampered.json()["rows"][0]["outcome"] == "failed"
    assert "Secret Foreign" not in tampered.text

    team_preview = _preview(
        school_client,
        owner_a,
        school_a["id"],
        b"player_name,team_name\nAnother Local Player,Shared Team Name\n",
    ).json()
    tampered_team = school_client.post(
        _apply_url(school_a["id"], team_preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "create_new",
                    "team_id": team_b["id"],
                }
            ]
        },
        headers=owner_a.headers,
    )
    assert tampered_team.status_code == 200
    assert tampered_team.json()["rows"][0]["outcome"] == "failed"
    assert "Secret Foreign" not in tampered_team.text
    roster = school_client.get(
        f"/api/organizations/{school_a['id']}/players", headers=owner_a.headers
    )
    assert roster.status_code == 200
    assert roster.json() == []


def test_non_unique_school_student_identifier_is_ambiguous_candidate_signal(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-nonunique-id@example.com")
    organization = create_school(school_client, owner, "Nonunique Identifier School")
    first = _create_roster_player(
        school_client,
        owner,
        organization["id"],
        name="First Candidate",
        student_identifier="SHARED-ID",
    )
    second = _create_roster_player(
        school_client,
        owner,
        organization["id"],
        name="Second Candidate",
        student_identifier="SHARED-ID",
    )
    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name,student_identifier\nFirst Candidate,SHARED-ID\n",
    ).json()
    row = preview["rows"][0]
    assert row["classification"] == "ambiguous_needs_review"
    assert row["resolution_required"] is True
    assert {item["school_player_membership_id"] for item in row["candidate_memberships"]} == {
        first["id"],
        second["id"],
    }
    assert "not unique" in " ".join(row["warnings"])


async def test_preview_is_actor_and_organization_bound_and_replay_is_controlled(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "import-binding-owner@example.com")
    other = register_user(school_client, "import-binding-other@example.com")
    school_a = create_school(school_client, owner, "Import Binding A")
    school_b = create_school(school_client, owner, "Import Binding B")
    add_membership(school_client, owner, school_a["id"], other.id, "admin")
    preview = _preview(
        school_client,
        owner,
        school_a["id"],
        b"player_name\nBound Player\n",
    ).json()

    wrong_actor = school_client.post(
        _apply_url(school_a["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=other.headers,
    )
    wrong_org = school_client.post(
        _apply_url(school_b["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert wrong_actor.status_code == wrong_org.status_code == 404
    assert "Bound Player" not in wrong_actor.text + wrong_org.text

    tampered_values = school_client.post(
        _apply_url(school_a["id"], preview["import_id"]),
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "create_new",
                    "player_name": "Substituted Player",
                }
            ]
        },
        headers=owner.headers,
    )
    assert tampered_values.status_code == 422

    applied = school_client.post(
        _apply_url(school_a["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    replay = school_client.post(
        _apply_url(school_a["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert applied.status_code == 200
    assert replay.status_code == 409
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1


async def test_expired_preview_cannot_apply(school_client: TestClient) -> None:
    owner = register_user(school_client, "import-expired@example.com")
    organization = create_school(school_client, owner, "Expired Import School")
    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nExpired Player\n",
    ).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(SchoolPlayerImport, preview["import_id"])
        assert stored is not None
        stored.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1)
        await session.commit()
    expired = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert expired.status_code == 410


@pytest.mark.parametrize(
    ("content", "filename", "expected_status"),
    [
        (b"", "empty.csv", 422),
        (b"player_name\n\xff\n", "invalid.csv", 422),
        (b"player_name,player_name\nA,B\n", "duplicate.csv", 422),
        (b"player_name\n=2+2\n", "formula.csv", 422),
        (b"not a workbook", "malformed.xlsx", 422),
        (b"player_name\nA\n", "legacy.xls", 415),
    ],
)
def test_malformed_unsupported_and_formula_inputs_are_rejected(
    school_client: TestClient,
    content: bytes,
    filename: str,
    expected_status: int,
) -> None:
    owner = register_user(school_client, f"import-invalid-{filename}@example.com")
    organization = create_school(school_client, owner, f"Invalid {filename} School")
    response = _preview(school_client, owner, organization["id"], content, filename)
    assert response.status_code == expected_status


def test_xlsx_formula_macro_and_archive_safety(school_client: TestClient) -> None:
    owner = register_user(school_client, "import-xlsx-safety@example.com")
    organization = create_school(school_client, owner, "XLSX Safety School")
    formula = _preview(
        school_client,
        owner,
        organization["id"],
        _xlsx([["player_name"], ["=1+1"]]),
        "formula.xlsx",
    )
    assert formula.status_code == 422
    assert formula.json()["detail"] == "XLSX formulas are not supported"

    macro_payload = io.BytesIO()
    with zipfile.ZipFile(macro_payload, "w") as archive:
        archive.writestr("xl/vbaProject.bin", b"not executable")
    macro = _preview(
        school_client,
        owner,
        organization["id"],
        macro_payload.getvalue(),
        "renamed-macro.xlsx",
    )
    assert macro.status_code == 422
    assert macro.json()["detail"] == "Macro-enabled workbooks are not supported"

    encrypted_payload = io.BytesIO()
    with zipfile.ZipFile(encrypted_payload, "w") as archive:
        archive.writestr("xl/workbook.xml", b"encrypted content")
    encrypted_bytes = bytearray(encrypted_payload.getvalue())
    local_header = encrypted_bytes.find(b"PK\x03\x04")
    central_header = encrypted_bytes.find(b"PK\x01\x02")
    assert local_header >= 0 and central_header >= 0
    encrypted_bytes[local_header + 6] |= 0x01
    encrypted_bytes[central_header + 8] |= 0x01
    encrypted = _preview(
        school_client,
        owner,
        organization["id"],
        bytes(encrypted_bytes),
        "encrypted.xlsx",
    )
    assert encrypted.status_code == 422
    assert encrypted.json()["detail"] == "Encrypted XLSX files are not supported"

    expanded_payload = io.BytesIO()
    with zipfile.ZipFile(expanded_payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/oversized.xml",
            b"A" * (school_player_import_service.MAX_XLSX_UNCOMPRESSED_BYTES + 1),
        )
    expanded = _preview(
        school_client,
        owner,
        organization["id"],
        expanded_payload.getvalue(),
        "expanded.xlsx",
    )
    assert expanded.status_code == 422
    assert "expanded size" in expanded.text


def test_file_row_column_and_cell_limits(school_client: TestClient) -> None:
    owner = register_user(school_client, "import-limits@example.com")
    organization = create_school(school_client, owner, "Import Limits School")
    oversized = _preview(
        school_client,
        owner,
        organization["id"],
        b"x" * (school_player_import_service.MAX_FILE_BYTES + 1),
        "oversized.csv",
    )
    assert oversized.status_code == 413

    too_many_rows = b"player_name\n" + b"A\n" * (school_player_import_service.MAX_ROWS + 1)
    assert _preview(school_client, owner, organization["id"], too_many_rows).status_code == 422
    headers = ",".join(f"h{i}" for i in range(school_player_import_service.MAX_COLUMNS + 1))
    too_many_columns = f"{headers}\n".encode()
    assert _preview(school_client, owner, organization["id"], too_many_columns).status_code == 422
    long_cell = ("player_name\n" + "A" * 256 + "\n").encode()
    assert _preview(school_client, owner, organization["id"], long_cell).status_code == 422

    xlsx_rows = [
        ["player_name"],
        *[["A"] for _ in range(school_player_import_service.MAX_ROWS + 1)],
    ]
    assert (
        _preview(
            school_client,
            owner,
            organization["id"],
            _xlsx(xlsx_rows),
            "too-many-rows.xlsx",
        ).status_code
        == 422
    )
    xlsx_columns = [[f"h{index}" for index in range(school_player_import_service.MAX_COLUMNS + 1)]]
    assert (
        _preview(
            school_client,
            owner,
            organization["id"],
            _xlsx(xlsx_columns),
            "too-many-columns.xlsx",
        ).status_code
        == 422
    )


async def test_row_failure_rolls_back_orphan_but_preserves_independent_success(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "import-row-atomic@example.com")
    organization = create_school(school_client, owner, "Row Atomic Import School")
    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nSuccess Player\nRolled Back Player\n",
    ).json()
    ids = iter(
        ["profile-success", "membership-conflict", "profile-rollback", "membership-conflict"]
    )
    monkeypatch.setattr(school_player_import_service, "_new_id", lambda: next(ids))
    applied = school_client.post(
        _apply_url(organization["id"], preview["import_id"]),
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["summary"]["created_players"] == 1
    assert applied.json()["summary"]["failed_rows"] == 1
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.get(PlayerProfile, "profile-success") is not None
        assert await session.get(PlayerProfile, "profile-rollback") is None
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 1


async def test_postgres_concurrent_same_import_apply_executes_once(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Import concurrency contract requires real PostgreSQL")

    owner = register_user(school_client, "import-concurrent@example.com")
    organization = create_school(school_client, owner, "Concurrent Import School")
    preview = _preview(
        school_client,
        owner,
        organization["id"],
        b"player_name\nConcurrent Player\n",
    ).json()
    ready = 0
    ready_lock = asyncio.Lock()
    start = asyncio.Event()

    async def apply_once() -> tuple[str, int | None]:
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            try:
                await school_player_import_service.apply_import(
                    session,
                    organization_id=organization["id"],
                    import_id=preview["import_id"],
                    actor_user_id=owner.id,
                    payload=PlayerImportApplyRequest(),
                )
            except school_player_import_service.SchoolPlayerImportServiceError as exc:
                return "error", exc.status_code
            return "success", None

    results = await asyncio.gather(apply_once(), apply_once())
    assert sorted(results) == [("error", 409), ("success", None)]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 1


async def test_postgres_import_schema_contract(school_client: TestClient) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Import persistence contract requires real PostgreSQL")
        rows = (
            await session.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) AS definition "
                    "FROM pg_constraint WHERE conrelid = 'school_player_imports'::regclass"
                )
            )
        ).all()
        definitions = {row.conname: row.definition for row in rows}
        assert "ON DELETE CASCADE" in definitions["fk_school_player_imports_organization"]
        assert "ON DELETE SET NULL" in definitions["fk_school_player_imports_actor"]
        assert "previewed" in definitions["ck_school_player_imports_status"]
        assert "applied" in definitions["ck_school_player_imports_status"]
