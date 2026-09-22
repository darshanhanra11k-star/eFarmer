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
    centre = ProcurementCentre(id=uuid4(), name="Centre T", district="District T")
    farmer = Farmer(
        id=uuid4(), farmer_id="F-201", name="Farmer Token", phone="9988776611"
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
        username="officer_t",
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


def test_get_token_as_farmer_owner(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    farmer_token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    join_res = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={},
    )
    assert join_res.status_code == 201
    token_id = join_res.json()["id"]

    get_res = client.get(
        f"/api/v1/tokens/{token_id}",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == token_id


def test_get_token_as_other_farmer_returns_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    other_farmer = Farmer(id=uuid4(), farmer_id="F-OTHER-2", name="Other")
    other_user = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.FARMER,
        farmer_id=other_farmer.id,
    )
    fake_db.add_all([other_farmer, other_user])
    fake_db.sync_flush()

    farmer_token = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    join_res = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={},
    )
    assert join_res.status_code == 201
    token_id = join_res.json()["id"]

    other_token = create_access_token(
        subject=str(other_user.id),
        role=Role.FARMER,
    )
    get_res = client.get(
        f"/api/v1/tokens/{token_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert get_res.status_code == 403


def test_token_full_lifecycle_api(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, officer, queue = _seed_test_env(fake_db)

    farmer_jwt = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    officer_jwt = create_access_token(
        subject=str(officer.id),
        role=Role.OFFICER,
    )

    # 1. Join queue (WAITING)
    join_res = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_jwt}"},
        json={},
    )
    assert join_res.status_code == 201
    token_id = join_res.json()["id"]

    # 2. Cannot process while WAITING
    bad_proc = client.post(
        f"/api/v1/tokens/{token_id}/process",
        headers={"Authorization": f"Bearer {officer_jwt}"},
    )
    assert bad_proc.status_code == 409

    # 3. Call next (CALLED)
    call_res = client.post(
        f"/api/v1/queues/{queue.id}/call-next",
        headers={"Authorization": f"Bearer {officer_jwt}"},
        json={},
    )
    assert call_res.status_code == 200
    assert call_res.json()["status"] == "CALLED"

    # 4. Process (PROCESSING)
    proc_res = client.post(
        f"/api/v1/tokens/{token_id}/process",
        headers={"Authorization": f"Bearer {officer_jwt}"},
    )
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "PROCESSING"

    # 5. Complete (COMPLETED)
    comp_res = client.post(
        f"/api/v1/tokens/{token_id}/complete",
        headers={"Authorization": f"Bearer {officer_jwt}"},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

    # 6. Cannot process once completed
    bad_again = client.post(
        f"/api/v1/tokens/{token_id}/process",
        headers={"Authorization": f"Bearer {officer_jwt}"},
    )
    assert bad_again.status_code == 409


def test_cancel_token_api(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    farmer_jwt = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )

    join_res = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_jwt}"},
        json={},
    )
    assert join_res.status_code == 201
    token_id = join_res.json()["id"]

    cancel_res = client.post(
        f"/api/v1/tokens/{token_id}/cancel",
        headers={"Authorization": f"Bearer {farmer_jwt}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Cannot cancel again
    cancel_res2 = client.post(
        f"/api/v1/tokens/{token_id}/cancel",
        headers={"Authorization": f"Bearer {farmer_jwt}"},
    )
    assert cancel_res2.status_code == 409


def test_get_token_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.get(f"/api/v1/tokens/{uuid4()}")
    assert response.status_code == 401


def test_get_token_nonexistent_returns_404(client: TestClient) -> None:
    token = create_access_token(
        subject=str(uuid4()),
        role=Role.OFFICER,
    )
    response = client.get(
        f"/api/v1/tokens/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_officer_cross_centre_token_actions_return_403(
    client: TestClient,
    fake_db: FakeQueueDbSession,
) -> None:
    _, _, user, _, queue = _seed_test_env(fake_db)

    # Farmer creates token
    farmer_jwt = create_access_token(
        subject=str(user.id),
        role=Role.FARMER,
    )
    join_res = client.post(
        f"/api/v1/queues/{queue.id}/join",
        headers={"Authorization": f"Bearer {farmer_jwt}"},
        json={},
    )
    assert join_res.status_code == 201
    token_id = join_res.json()["id"]

    # Foreign officer from different centre
    foreign_centre = ProcurementCentre(
        id=uuid4(), name="Foreign Centre T", district="Foreign"
    )
    foreign_officer = User(
        id=uuid4(),
        password_hash="pw_hash",
        role=Role.OFFICER,
        centre_id=foreign_centre.id,
        username="foreign_officer_t",
    )
    fake_db.add_all([foreign_centre, foreign_officer])
    fake_db.sync_flush()

    foreign_jwt = create_access_token(
        subject=str(foreign_officer.id),
        role=Role.OFFICER,
    )

    # Process attempt -> 403
    p_res = client.post(
        f"/api/v1/tokens/{token_id}/process",
        headers={"Authorization": f"Bearer {foreign_jwt}"},
    )
    assert p_res.status_code == 403

    # Complete attempt -> 403
    c_res = client.post(
        f"/api/v1/tokens/{token_id}/complete",
        headers={"Authorization": f"Bearer {foreign_jwt}"},
    )
    assert c_res.status_code == 403

    # Cancel attempt -> 403
    cn_res = client.post(
        f"/api/v1/tokens/{token_id}/cancel",
        headers={"Authorization": f"Bearer {foreign_jwt}"},
    )
    assert cn_res.status_code == 403
