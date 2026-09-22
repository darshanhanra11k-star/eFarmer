from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rbac import Role
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import app
from app.models.farmer import Farmer
from app.models.user import User

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


class _FakeScalarResult:
    def __init__(self, item: Any) -> None:
        self._item = item

    def scalar_one_or_none(self) -> Any:
        return self._item

    def scalar_one(self) -> Any:
        return self._item

    def scalars(self) -> Any:
        return self

    def all(self) -> list[Any]:
        if self._item is None:
            return []
        if isinstance(self._item, list):
            return self._item
        return [self._item]


class FakeDbSession:
    def __init__(self) -> None:
        self.farmers: dict[UUID, Farmer] = {}
        self.farmers_by_farmer_id: dict[str, Farmer] = {}
        self.users: dict[UUID, User] = {}
        self._pending: list[Any] = []

    def add(self, obj: Any) -> None:
        self._pending.append(obj)

    async def flush(self) -> None:
        await self.commit()

    async def commit(self) -> None:
        for obj in self._pending:
            if isinstance(obj, Farmer):
                if obj.farmer_id in self.farmers_by_farmer_id:

                    class Orig(Exception):
                        sqlstate = "23505"

                    raise IntegrityError("duplicate key", params=None, orig=Orig())
                if obj.id is None:
                    obj.id = uuid4()
                if getattr(obj, "active", None) is None:
                    obj.active = True
                now = datetime.now(UTC)
                obj.created_at = now
                obj.updated_at = now
                self.farmers[obj.id] = obj
                self.farmers_by_farmer_id[obj.farmer_id] = obj
            elif isinstance(obj, User):
                if obj.id is None:
                    obj.id = uuid4()
                now = datetime.now(UTC)
                obj.created_at = now
                obj.updated_at = now
                self.users[obj.id] = obj
        self._pending.clear()

    async def refresh(self, obj: Any) -> None:
        pass

    async def rollback(self) -> None:
        self._pending.clear()

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        sql = str(stmt)
        if "FROM farmers" in sql:
            for farmer_id, farmer in self.farmers.items():
                cond1 = f"farmers.id = '{farmer_id}'" in sql
                cond2 = f"farmers.id = :{farmer_id}" in sql
                if cond1 or cond2:
                    return _FakeScalarResult(farmer)
                for val in stmt.compile().params.values():
                    if val == farmer_id or val == str(farmer_id):
                        return _FakeScalarResult(farmer)
            return _FakeScalarResult(None)
        if "FROM users" in sql:
            for user_id, user in self.users.items():
                if f"users.id = '{user_id}'" in sql:
                    return _FakeScalarResult(user)
                for val in stmt.compile().params.values():
                    if val == user_id or val == str(user_id):
                        return _FakeScalarResult(user)
            return _FakeScalarResult(None)
        return _FakeScalarResult(None)


@pytest.fixture
def fake_db() -> FakeDbSession:
    return FakeDbSession()


@pytest.fixture(autouse=True)
def _configure_jwt(
    monkeypatch: pytest.MonkeyPatch,
    fake_db: FakeDbSession,
) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_db)

    app.dependency_overrides[get_db_session] = override_db
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_create_farmer_success(fake_db: FakeDbSession) -> None:
    client = TestClient(app)
    token = create_access_token(subject="officer_1", role=Role.OFFICER)

    payload = {
        "farmer_id": "GOV-FARMER-101",
        "name": "Ravi Kumar",
        "phone": "9876543210",
        "village": "Rampur",
        "block": "Sadar",
        "district": "Bokaro",
        "state": "Jharkhand",
    }
    response = client.post(
        "/api/v1/farmers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["farmer_id"] == "GOV-FARMER-101"
    assert body["name"] == "Ravi Kumar"
    assert body["phone"] == "9876543210"
    assert body["village"] == "Rampur"
    assert body["state"] == "Jharkhand"
    assert body["active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert "password_hash" not in body


def test_create_farmer_duplicate_farmer_id_returns_409(
    fake_db: FakeDbSession,
) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    token = create_access_token(subject="officer_1", role=Role.OFFICER)

    payload = {
        "farmer_id": "GOV-FARMER-DUP",
        "name": "Ravi Kumar",
        "phone": "9876543210",
    }
    res1 = client.post(
        "/api/v1/farmers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/farmers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 409
    assert res2.json()["code"] == "conflict"


def test_create_farmer_invalid_input_returns_422() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    token = create_access_token(subject="officer_1", role=Role.OFFICER)

    res_missing_id = client.post(
        "/api/v1/farmers",
        json={"name": "Ravi Kumar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_missing_id.status_code == 422

    res_empty_name = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-123", "name": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_empty_name.status_code == 422

    res_bad_phone = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-123", "name": "Ravi", "phone": "123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_bad_phone.status_code == 422


def test_create_farmer_unauthenticated_returns_401() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-123", "name": "Ravi Kumar"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_create_farmer_forbidden_role_returns_403() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    farmer_token = create_access_token(subject="farmer_user", role=Role.FARMER)

    response = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-123", "name": "Ravi Kumar"},
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_get_farmer_success(fake_db: FakeDbSession) -> None:
    client = TestClient(app)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)

    create_res = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-GET-1", "name": "Suresh", "phone": "9998887776"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    farmer_uuid = create_res.json()["id"]

    get_res = client.get(
        f"/api/v1/farmers/{farmer_uuid}",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["id"] == farmer_uuid
    assert body["farmer_id"] == "GOV-GET-1"
    assert body["name"] == "Suresh"
    assert body["phone"] == "9998887776"


def test_get_farmer_missing_returns_404() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)
    random_id = uuid4()

    res = client.get(
        f"/api/v1/farmers/{random_id}",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


def test_farmer_cannot_read_another_farmer_returns_403(
    fake_db: FakeDbSession,
) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)

    res1 = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-F1", "name": "Farmer 1"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    f1_id = UUID(res1.json()["id"])

    res2 = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-F2", "name": "Farmer 2"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    f2_id = UUID(res2.json()["id"])

    farmer1_user_id = uuid4()
    farmer1_user = User(
        id=farmer1_user_id,
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=f1_id,
    )
    fake_db.users[farmer1_user_id] = farmer1_user

    farmer1_token = create_access_token(
        subject=str(farmer1_user_id),
        role=Role.FARMER,
    )

    res_own = client.get(
        f"/api/v1/farmers/{f1_id}",
        headers={"Authorization": f"Bearer {farmer1_token}"},
    )
    assert res_own.status_code == 200
    assert res_own.json()["id"] == str(f1_id)

    res_other = client.get(
        f"/api/v1/farmers/{f2_id}",
        headers={"Authorization": f"Bearer {farmer1_token}"},
    )
    assert res_other.status_code == 403
    assert res_other.json()["code"] == "permission_denied"


def test_officer_can_read_any_farmer(fake_db: FakeDbSession) -> None:
    client = TestClient(app)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)

    res = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-ANY-1", "name": "Any Farmer"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    farmer_id = res.json()["id"]

    res_read = client.get(
        f"/api/v1/farmers/{farmer_id}",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_read.status_code == 200
    assert res_read.json()["farmer_id"] == "GOV-ANY-1"


def test_farmer_contact_phone_is_persisted(fake_db: FakeDbSession) -> None:
    client = TestClient(app)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)

    contact_phone = "9876501234"
    res = client.post(
        "/api/v1/farmers",
        json={
            "farmer_id": "GOV-PHONE-1",
            "name": "Phone Test",
            "phone": contact_phone,
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 201
    farmer_id = res.json()["id"]

    get_res = client.get(
        f"/api/v1/farmers/{farmer_id}",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["phone"] == contact_phone


def test_response_does_not_leak_password_hash(fake_db: FakeDbSession) -> None:
    client = TestClient(app)
    officer_token = create_access_token(subject="officer_1", role=Role.OFFICER)

    res = client.post(
        "/api/v1/farmers",
        json={"farmer_id": "GOV-SEC-1", "name": "Security Test"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 201
    text = res.text
    assert "password" not in text.lower()
    assert "hash" not in text.lower()
