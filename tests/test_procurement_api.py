from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.procurement import _get_procurement_service
from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.rbac import Role
from app.core.security import create_access_token
from app.main import app
from app.models.procurement import IntentStatus, ProcurementIntent
from app.services.procurement import ProcurementService

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
    return AsyncMock(spec=ProcurementService)


@pytest.fixture
def client(mock_service: AsyncMock) -> Iterator[TestClient]:
    app.dependency_overrides[_get_procurement_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_unauthenticated_requests_return_401(client: TestClient) -> None:
    intent_id = uuid4()
    res_get = client.get(f"/api/v1/procurement/{intent_id}")
    assert res_get.status_code == 401

    payload = {
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": 1000.0,
        "ready_date": "2026-11-15",
    }
    res_post = client.post("/api/v1/procurement", json=payload)
    assert res_post.status_code == 401


def test_farmer_create_intent_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    farmer_user_id = uuid4()
    intent_id = uuid4()
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()

    mock_intent = ProcurementIntent(
        id=intent_id,
        farmer_id=farmer_id,
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1500.00"),
        ready_date=date(2026, 11, 15),
        status=IntentStatus.PENDING,
        created_by=farmer_user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_service.create_procurement_intent.return_value = mock_intent

    token = create_access_token(subject=str(farmer_user_id), role=Role.FARMER)
    payload = {
        "centre_id": str(centre_id),
        "crop_id": str(crop_id),
        "land_holding_id": str(holding_id),
        "expected_quantity_kg": 1500.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == str(intent_id)
    assert data["status"] == "PENDING"
    assert data["farmer_id"] == str(farmer_id)
    assert float(data["expected_quantity_kg"]) == 1500.0


def test_farmer_create_intent_cross_farmer_forbidden(
    client: TestClient, mock_service: AsyncMock
) -> None:
    farmer_user_id = uuid4()
    mock_service.create_procurement_intent.side_effect = PermissionDeniedError(
        message="Cannot create procurement intent for a different farmer."
    )

    token = create_access_token(subject=str(farmer_user_id), role=Role.FARMER)
    payload = {
        "farmer_id": str(uuid4()),
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": 1500.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 403


def test_officer_create_intent_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    officer_user_id = uuid4()
    intent_id = uuid4()
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()

    mock_intent = ProcurementIntent(
        id=intent_id,
        farmer_id=farmer_id,
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("2000.00"),
        ready_date=date(2026, 11, 20),
        status=IntentStatus.PENDING,
        created_by=officer_user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_service.create_procurement_intent.return_value = mock_intent

    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)
    payload = {
        "farmer_id": str(farmer_id),
        "centre_id": str(centre_id),
        "crop_id": str(crop_id),
        "land_holding_id": str(holding_id),
        "expected_quantity_kg": 2000.0,
        "ready_date": "2026-11-20",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == str(intent_id)
    assert data["status"] == "PENDING"
    assert data["farmer_id"] == str(farmer_id)
    assert float(data["expected_quantity_kg"]) == 2000.0


def test_officer_create_intent_cross_centre_forbidden(
    client: TestClient, mock_service: AsyncMock
) -> None:
    officer_user_id = uuid4()
    mock_service.create_procurement_intent.side_effect = PermissionDeniedError(
        message=(
            "Officers cannot create procurement intents for "
            "centres they are not assigned to."
        )
    )

    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)
    payload = {
        "farmer_id": str(uuid4()),
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": 1000.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 403


def test_user_without_role_create_intent_returns_403(client: TestClient) -> None:
    user_id = uuid4()
    token = create_access_token(subject=str(user_id), role=None)

    payload = {
        "farmer_id": str(uuid4()),
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": 1500.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 403


def test_create_intent_validation_error_returns_422(client: TestClient) -> None:
    officer_user_id = uuid4()
    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)

    # Invalid negative quantity
    payload = {
        "farmer_id": str(uuid4()),
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": -100.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 422


def test_create_intent_conflict_error_returns_409(
    client: TestClient, mock_service: AsyncMock
) -> None:
    officer_user_id = uuid4()
    mock_service.create_procurement_intent.side_effect = ConflictError(
        message="Farmer already has an active request for this crop at this centre."
    )

    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)
    payload = {
        "farmer_id": str(uuid4()),
        "centre_id": str(uuid4()),
        "crop_id": str(uuid4()),
        "land_holding_id": str(uuid4()),
        "expected_quantity_kg": 1000.0,
        "ready_date": "2026-11-15",
    }
    res = client.post(
        "/api/v1/procurement",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 409
    data = res.json()
    assert "Farmer already has an active request" in data["message"]


def test_get_procurement_by_id_success(
    client: TestClient, mock_service: AsyncMock
) -> None:
    farmer_user_id = uuid4()
    intent_id = uuid4()
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()

    mock_intent = ProcurementIntent(
        id=intent_id,
        farmer_id=farmer_id,
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1200.00"),
        ready_date=date(2026, 11, 15),
        status=IntentStatus.PENDING,
        created_by=farmer_user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_service.get_procurement_by_id.return_value = mock_intent

    token = create_access_token(subject=str(farmer_user_id), role=Role.FARMER)
    res = client.get(
        f"/api/v1/procurement/{intent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(intent_id)
    assert data["status"] == "PENDING"
    assert data["farmer_id"] == str(farmer_id)
    assert float(data["expected_quantity_kg"]) == 1200.0


def test_get_procurement_cross_centre_or_farmer_forbidden_returns_403(
    client: TestClient, mock_service: AsyncMock
) -> None:
    officer_user_id = uuid4()
    intent_id = uuid4()
    mock_service.get_procurement_by_id.side_effect = PermissionDeniedError(
        message=(
            "Officers cannot view procurement intents for "
            "centres they are not assigned to."
        )
    )

    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)
    res = client.get(
        f"/api/v1/procurement/{intent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_get_procurement_not_found_returns_404(
    client: TestClient, mock_service: AsyncMock
) -> None:
    officer_user_id = uuid4()
    intent_id = uuid4()
    mock_service.get_procurement_by_id.side_effect = NotFoundError(
        message="Procurement intent not found."
    )

    token = create_access_token(subject=str(officer_user_id), role=Role.OFFICER)
    res = client.get(
        f"/api/v1/procurement/{intent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
