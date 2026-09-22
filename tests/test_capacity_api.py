from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.capacity import _get_capacity_service
from app.capacity.engine import CapacityStatus
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.rbac import Role
from app.core.security import create_access_token
from app.main import app
from app.schemas.capacity import CapacityRecordResponse
from app.services.capacity import CapacityService

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
    return AsyncMock(spec=CapacityService)


@pytest.fixture
def client(mock_service: AsyncMock) -> Iterator[TestClient]:
    app.dependency_overrides[_get_capacity_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15"
    )
    assert res.status_code == 401


def test_missing_query_parameters_returns_422(client: TestClient) -> None:
    centre_id = uuid4()
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)

    res1 = client.get(
        f"/api/v1/centres/{centre_id}/capacity",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 422

    res2 = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 422

    res3 = client.get(
        f"/api/v1/centres/{centre_id}/capacity?date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res3.status_code == 422


def test_farmer_read_active_centre_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    mock_response = CapacityRecordResponse(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1234.5678"),
        allocated_quantity_kg=Decimal("500.1000"),
        procured_quantity_kg=Decimal("200.0500"),
        available_capacity_kg=Decimal("734.4678"),
        utilisation=Decimal("0.4051"),
        capacity_status=CapacityStatus.PARTIAL,
        active=True,
    )
    mock_service.get_centre_capacity.return_value = mock_response

    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()

    assert body["centre_id"] == str(centre_id)
    assert body["crop_id"] == str(crop_id)
    assert body["date"] == "2026-11-15"
    assert body["total_capacity_kg"] == "1234.5678"
    assert body["allocated_quantity_kg"] == "500.1000"
    assert body["procured_quantity_kg"] == "200.0500"
    assert body["available_capacity_kg"] == "734.4678"
    assert body["utilisation"] == "0.4051"
    assert body["capacity_status"] == "PARTIAL"
    assert body["active"] is True

    assert isinstance(body["total_capacity_kg"], str)
    assert isinstance(body["allocated_quantity_kg"], str)
    assert isinstance(body["procured_quantity_kg"], str)
    assert isinstance(body["available_capacity_kg"], str)
    assert isinstance(body["utilisation"], str)
    assert "bottleneck" not in body


def test_officer_read_assigned_centre_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    mock_response = CapacityRecordResponse(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000.00"),
        allocated_quantity_kg=Decimal("0.00"),
        procured_quantity_kg=Decimal("0.00"),
        available_capacity_kg=Decimal("1000.00"),
        utilisation=Decimal("0.0000"),
        capacity_status=CapacityStatus.AVAILABLE,
        active=True,
    )
    mock_service.get_centre_capacity.return_value = mock_response

    token = create_access_token(subject=str(uuid4()), role=Role.OFFICER)
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["capacity_status"] == "AVAILABLE"
    assert body["utilisation"] == "0.0000"


def test_officer_read_unassigned_centre_returns_403(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    mock_service.get_centre_capacity.side_effect = PermissionDeniedError(
        message="Officers can only view capacity for their assigned centre."
    )

    token = create_access_token(subject=str(uuid4()), role=Role.OFFICER)
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_inactive_centre_returns_404(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    mock_service.get_centre_capacity.side_effect = NotFoundError(
        message="Procurement centre not found."
    )

    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_missing_capacity_record_returns_404(
    client: TestClient, mock_service: AsyncMock
) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    mock_service.get_centre_capacity.side_effect = NotFoundError(
        message="Capacity record not found for the specified centre, crop, and date."
    )

    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_user_without_role_returns_403(client: TestClient) -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    token = create_access_token(subject=str(uuid4()), role=None)

    res = client.get(
        f"/api/v1/centres/{centre_id}/capacity?crop_id={crop_id}&date=2026-11-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
