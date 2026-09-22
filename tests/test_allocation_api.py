from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.centres import _get_allocation_service as _get_centre_allocation_service
from app.api.v1.farmers import _get_allocation_service as _get_farmer_allocation_service
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.rbac import Role
from app.core.security import create_access_token
from app.main import app
from app.models.allocation import AllocationDecision
from app.services.allocation import AllocationService

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
def mock_service() -> AsyncMock:
    return AsyncMock(spec=AllocationService)


@pytest.fixture
def client(mock_service: AsyncMock) -> Iterator[TestClient]:
    app.dependency_overrides[_get_farmer_allocation_service] = lambda: mock_service
    app.dependency_overrides[_get_centre_allocation_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# Farmer Endpoint: GET /api/v1/farmers/me/intents/{intent_id}/allocation
# =========================================================================


def test_farmer_intent_allocation_unauthenticated(client: TestClient) -> None:
    intent_id = uuid4()
    response = client.get(f"/api/v1/farmers/me/intents/{intent_id}/allocation")
    assert response.status_code == 401


def test_farmer_intent_allocation_not_found(
    client: TestClient, mock_service: AsyncMock
) -> None:
    intent_id = uuid4()
    user_id = uuid4()
    mock_service.get_intent_allocation.side_effect = NotFoundError(
        message="Allocation decision not found for the specified intent."
    )

    token = create_access_token(subject=str(user_id), role=Role.FARMER)
    response = client.get(
        f"/api/v1/farmers/me/intents/{intent_id}/allocation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


def test_farmer_intent_allocation_forbidden_for_wrong_farmer(
    client: TestClient, mock_service: AsyncMock
) -> None:
    intent_id = uuid4()
    user_id = uuid4()
    mock_service.get_intent_allocation.side_effect = PermissionDeniedError(
        message="You are not authorized to view this allocation decision."
    )

    token = create_access_token(subject=str(user_id), role=Role.FARMER)
    response = client.get(
        f"/api/v1/farmers/me/intents/{intent_id}/allocation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["message"].lower()


def test_farmer_intent_allocation_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    intent_id = uuid4()
    user_id = uuid4()
    farmer_id = uuid4()
    decision_id = uuid4()
    run_id = uuid4()

    mock_decision = AllocationDecision(
        id=decision_id,
        allocation_run_id=run_id,
        intent_id=intent_id,
        farmer_id=farmer_id,
        requested_quantity_kg=Decimal("500.00"),
        allocated_quantity_kg=Decimal("500.00"),
        remaining_capacity_kg=Decimal("1500.00"),
        selected=True,
        rank=1,
        ordering_reason="WAITING_AGE",
        tie_break_digest=None,
        created_at=datetime.now(UTC),
    )
    mock_service.get_intent_allocation.return_value = mock_decision

    token = create_access_token(subject=str(user_id), role=Role.FARMER)
    response = client.get(
        f"/api/v1/farmers/me/intents/{intent_id}/allocation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(decision_id)
    assert data["intent_id"] == str(intent_id)
    assert data["farmer_id"] == str(farmer_id)
    assert data["selected"] is True
    assert data["requested_quantity_kg"] == "500.00"
    assert data["allocated_quantity_kg"] == "500.00"


# =========================================================================
# Officer Endpoint: GET /api/v1/centres/{centre_id}/allocation
# =========================================================================


def test_centre_allocation_unauthenticated(client: TestClient) -> None:
    centre_id = uuid4()
    response = client.get(f"/api/v1/centres/{centre_id}/allocation")
    assert response.status_code == 401


def test_centre_allocation_forbidden_for_farmer_role(client: TestClient) -> None:
    centre_id = uuid4()
    user_id = uuid4()
    token = create_access_token(subject=str(user_id), role=Role.FARMER)

    response = client.get(
        f"/api/v1/centres/{centre_id}/allocation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_centre_allocation_forbidden_for_wrong_centre(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    user_id = uuid4()
    mock_service.get_centre_allocations.side_effect = PermissionDeniedError(
        message="Officers may only access allocations for their assigned centre."
    )

    token = create_access_token(subject=str(user_id), role=Role.OFFICER)
    response = client.get(
        f"/api/v1/centres/{centre_id}/allocation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_centre_allocation_success(client: TestClient, mock_service: AsyncMock) -> None:
    centre_id = uuid4()
    user_id = uuid4()
    crop_id = uuid4()

    mock_decision = AllocationDecision(
        id=uuid4(),
        allocation_run_id=uuid4(),
        intent_id=uuid4(),
        farmer_id=uuid4(),
        requested_quantity_kg=Decimal("100.00"),
        allocated_quantity_kg=Decimal("100.00"),
        remaining_capacity_kg=Decimal("900.00"),
        selected=True,
        rank=1,
        ordering_reason="WAITING_AGE",
        tie_break_digest=None,
        created_at=datetime.now(UTC),
    )
    mock_service.get_centre_allocations.return_value = [mock_decision]

    token = create_access_token(subject=str(user_id), role=Role.OFFICER)
    response = client.get(
        f"/api/v1/centres/{centre_id}/allocation?crop_id={crop_id}&allocation_date=2026-10-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["selected"] is True
    assert data[0]["requested_quantity_kg"] == "100.00"
