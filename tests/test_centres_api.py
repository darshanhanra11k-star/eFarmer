from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rbac import Role
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import app
from app.models.centre import ProcurementCentre
from app.models.counter import Counter

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


class FakeCentreDbSession:
    def __init__(self) -> None:
        self.centres: dict[UUID, ProcurementCentre] = {}
        self.counters: dict[UUID, list[Counter]] = {}

    def add_centre(
        self,
        name: str,
        district: str,
        counter_names: list[str] | None = None,
    ) -> ProcurementCentre:
        cid = uuid4()
        now = datetime.now(UTC)
        c = ProcurementCentre(
            id=cid,
            name=name,
            district=district,
            active=True,
            created_at=now,
            updated_at=now,
        )
        c.counters = []
        if counter_names:
            for cname in counter_names:
                cnt = Counter(
                    id=uuid4(),
                    centre_id=cid,
                    name=cname,
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
                c.counters.append(cnt)
        self.centres[cid] = c
        return c

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        sql = str(stmt)
        if "count" in sql.lower():
            return _FakeScalarResult(len(self.centres))
        if "WHERE procurement_centres.id =" in sql or "procurement_centres.id =" in sql:
            for cid, centre in self.centres.items():
                for val in stmt.compile().params.values():
                    if val == cid or val == str(cid):
                        return _FakeScalarResult(centre)
            return _FakeScalarResult(None)

        sorted_centres = sorted(self.centres.values(), key=lambda x: x.name)
        offset = getattr(stmt, "_offset", 0) or 0
        limit = getattr(stmt, "_limit", 20) or 20
        items = sorted_centres[int(offset) : int(offset) + int(limit)]
        return _FakeScalarResult(items)


@pytest.fixture
def fake_centre_db() -> FakeCentreDbSession:
    return FakeCentreDbSession()


@pytest.fixture(autouse=True)
def _configure_jwt(
    monkeypatch: pytest.MonkeyPatch,
    fake_centre_db: FakeCentreDbSession,
) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_centre_db)

    app.dependency_overrides[get_db_session] = override_db
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_list_centres_success(fake_centre_db: FakeCentreDbSession) -> None:
    fake_centre_db.add_centre("Alpha Mandi", "District 1", ["Counter A", "Counter B"])
    fake_centre_db.add_centre("Beta Mandi", "District 2")

    client = TestClient(app)
    token = create_access_token(subject="user_1", role=Role.FARMER)

    res = client.get(
        "/api/v1/centres",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "Alpha Mandi"
    assert len(body["items"][0]["counters"]) == 2


def test_list_centres_pagination(fake_centre_db: FakeCentreDbSession) -> None:
    for i in range(5):
        fake_centre_db.add_centre(f"Centre {i:02d}", "District X")

    client = TestClient(app)
    token = create_access_token(subject="user_1", role=Role.OFFICER)

    res = client.get(
        "/api/v1/centres?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


def test_get_centre_success(fake_centre_db: FakeCentreDbSession) -> None:
    centre = fake_centre_db.add_centre("Kisan Kendra", "Ranchi", ["C1"])

    client = TestClient(app)
    token = create_access_token(subject="user_1", role=Role.FARMER)

    res = client.get(
        f"/api/v1/centres/{centre.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(centre.id)
    assert body["name"] == "Kisan Kendra"
    assert body["district"] == "Ranchi"
    assert len(body["counters"]) == 1
    assert body["counters"][0]["name"] == "C1"


def test_get_centre_missing_returns_404() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    token = create_access_token(subject="user_1", role=Role.OFFICER)
    random_id = uuid4()

    res = client.get(
        f"/api/v1/centres/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
