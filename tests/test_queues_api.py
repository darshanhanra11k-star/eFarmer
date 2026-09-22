from collections.abc import AsyncIterator, Iterator
from datetime import date
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rbac import Role
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import app
from app.models.centre import ProcurementCentre
from app.models.farmer import Farmer
from app.models.queue import Queue, QueueStatus
from app.models.user import User
from tests.test_queue_service import FakeQueueDbSession

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_db() -> FakeQueueDbSession:
    return FakeQueueDbSession()


@pytest.fixture
def client(fake_db: FakeQueueDbSession) -> Iterator[TestClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_db)

    app.dependency_overrides[get_db_session] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_test_env(
    session: FakeQueueDbSession,
) -> tuple[ProcurementCentre, Farmer, User, User, Queue]:
    centre = ProcurementCentre(id=uuid4(), name="Centre A", district="District A")
    farmer = Farmer(
        id=uuid4(), farmer_id="F-101", name="Farmer Test", phone="9988776655"
    )
    user = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.FARMER,
        farmer_id=farmer.id,
    )
    officer = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        username="officer_a",
    )
    queue = Queue(
        id=uuid4(),
        centre_id=centre.id,
        date=date(2026, 9, 18),
        status=QueueStatus.OPEN,
    )
    session.add_all([centre, farmer, user, officer, queue])
    session.sync_flush()
    return centre, farmer, user, officer, queue


def test_join_queue_as_farmer_success(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["token_number"] == "T-001"
    assert data["status"] == "WAITING"
    assert data["queue_id"] == str(queue.id)


def test_join_queue_as_officer_success(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, farmer, _, officer, queue = _seed_test_env(fake_db)

    token = create_access_token(
        subject=str(officer.id),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"farmer_id": str(farmer.id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["farmer_id"] == str(farmer.id)
    assert data["token_number"] == "T-001"


def test_join_queue_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.post(f"/api/v1/queues/{uuid4()}/join", json={})
    assert response.status_code == 401


def test_join_queue_farmer_role_another_farmer_returns_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"farmer_id": str(uuid4())},
    )
    assert response.status_code == 403


def test_join_queue_duplicate_active_token_returns_409(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    res1 = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert res1.status_code == 201

    res2 = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert res2.status_code == 409


def test_join_queue_nonexistent_returns_404(client: TestClient) -> None:
    token = create_access_token(
        subject=str(uuid4()),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{uuid4()}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"farmer_id": str(uuid4())},
    )
    assert response.status_code == 404


def test_get_queue_status_success(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    # Join first
    client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    response = client.get(
        f"/api/v1/queues/{queue.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["queue_id"] == str(queue.id)
    assert data["total_waiting"] == 1
    assert data["last_issued_token"] == "T-001"


def test_call_next_as_officer_success(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, officer, queue = _seed_test_env(fake_db)

    farmer_token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={},
    )

    officer_token = create_access_token(
        subject=str(officer.id),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/call-next",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CALLED"
    assert data["token_number"] == "T-001"
    assert data["called_at"] is not None


def test_call_next_as_farmer_returns_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    farmer_token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/call-next",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={},
    )
    assert response.status_code == 403


def test_call_next_empty_queue_returns_404(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, _, officer, queue = _seed_test_env(fake_db)

    officer_token = create_access_token(
        subject=str(officer.id),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/call-next",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={},
    )
    assert response.status_code == 404


def test_officer_cross_centre_call_next_returns_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, _, _, queue = _seed_test_env(fake_db)

    foreign_centre = ProcurementCentre(
        id=uuid4(), name="Foreign Centre", district="District F"
    )
    foreign_officer = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.OFFICER,
        centre_id=foreign_centre.id,
        username="foreign_officer",
    )
    fake_db.add_all([foreign_centre, foreign_officer])
    fake_db.sync_flush()

    token = create_access_token(
        subject=str(foreign_officer.id),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/call-next",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert response.status_code == 403


def test_officer_cross_centre_join_queue_returns_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, farmer, _, _, queue = _seed_test_env(fake_db)

    foreign_centre = ProcurementCentre(
        id=uuid4(), name="Foreign Centre 2", district="District F2"
    )
    foreign_officer = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.OFFICER,
        centre_id=foreign_centre.id,
        username="foreign_officer_2",
    )
    fake_db.add_all([foreign_centre, foreign_officer])
    fake_db.sync_flush()

    token = create_access_token(
        subject=str(foreign_officer.id),
        role=Role.OFFICER,
    )
    response = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"farmer_id": str(farmer.id)},
    )
    assert response.status_code == 403
