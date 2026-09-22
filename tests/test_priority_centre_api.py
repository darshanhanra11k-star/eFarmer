from collections.abc import Iterator
from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.farmers import (
    _get_priority_centre_service as _get_farmer_priority_service,
)
from app.core.config import get_settings
from app.core.rbac import Role
from app.core.security import create_access_token
from app.main import app
from app.schemas.priority_centre import (
    CentreEvaluationDetail,
    PriorityCentreSelectionResponse,
)
from app.services.priority_centre import PriorityCentreService

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
    return AsyncMock(spec=PriorityCentreService)


@pytest.fixture
def client(mock_service: AsyncMock) -> Iterator[TestClient]:
    app.dependency_overrides[_get_farmer_priority_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "500.00",
            "preferred_centres": [
                {"centre_id": str(uuid4()), "priority": 1},
            ],
        },
    )
    assert response.status_code == 401


def test_officer_role_forbidden_returns_403(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.OFFICER)
    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "500.00",
            "preferred_centres": [
                {"centre_id": str(uuid4()), "priority": 1},
            ],
        },
    )
    assert response.status_code == 403


def test_empty_preferred_centres_returns_422(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "500.00",
            "preferred_centres": [],
        },
    )
    assert response.status_code == 422


def test_zero_or_negative_quantity_returns_422(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    c_id = str(uuid4())

    response_zero = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "0.00",
            "preferred_centres": [{"centre_id": c_id, "priority": 1}],
        },
    )
    assert response_zero.status_code == 422

    response_neg = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "-10.00",
            "preferred_centres": [{"centre_id": c_id, "priority": 1}],
        },
    )
    assert response_neg.status_code == 422


def test_duplicate_centre_id_returns_422(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    same_id = str(uuid4())

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "100.00",
            "preferred_centres": [
                {"centre_id": same_id, "priority": 1},
                {"centre_id": same_id, "priority": 2},
            ],
        },
    )
    assert response.status_code == 422
    assert "duplicate centre" in response.text.lower()


def test_duplicate_priority_returns_422(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "100.00",
            "preferred_centres": [
                {"centre_id": str(uuid4()), "priority": 1},
                {"centre_id": str(uuid4()), "priority": 1},
            ],
        },
    )
    assert response.status_code == 422
    assert "duplicate priorities" in response.text.lower()


def test_priorities_not_starting_at_1_returns_422(client: TestClient) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(uuid4()),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "100.00",
            "preferred_centres": [
                {"centre_id": str(uuid4()), "priority": 2},
                {"centre_id": str(uuid4()), "priority": 3},
            ],
        },
    )
    assert response.status_code == 422
    assert "must start at 1" in response.text.lower()


def test_successful_selection_returns_200(
    client: TestClient, mock_service: AsyncMock
) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    c1 = uuid4()
    crop_id = uuid4()

    mock_service.select_priority_centre.return_value = PriorityCentreSelectionResponse(
        success=True,
        selected_centre_id=c1,
        selected_priority=1,
        crop_id=crop_id,
        ready_date=date(2026, 11, 15),
        requested_quantity_kg="500.00",
        available_capacity_kg="1000.00",
        evaluated_centres=[
            CentreEvaluationDetail(
                centre_id=c1,
                priority=1,
                status="AVAILABLE",
                reason="Sufficient capacity available.",
            )
        ],
        message=f"Centre {c1} selected with priority 1.",
    )

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(crop_id),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "500.00",
            "preferred_centres": [{"centre_id": str(c1), "priority": 1}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["selected_centre_id"] == str(c1)
    assert data["selected_priority"] == 1
    assert data["available_capacity_kg"] == "1000.00"
    assert len(data["evaluated_centres"]) == 1


def test_all_unavailable_returns_200_domain_failure(
    client: TestClient, mock_service: AsyncMock
) -> None:
    token = create_access_token(subject=str(uuid4()), role=Role.FARMER)
    c1 = uuid4()
    crop_id = uuid4()

    mock_service.select_priority_centre.return_value = PriorityCentreSelectionResponse(
        success=False,
        selected_centre_id=None,
        selected_priority=None,
        crop_id=crop_id,
        ready_date=date(2026, 11, 15),
        requested_quantity_kg="500.00",
        available_capacity_kg=None,
        evaluated_centres=[
            CentreEvaluationDetail(
                centre_id=c1,
                priority=1,
                status="UNAVAILABLE",
                reason="Procurement centre is inactive.",
            )
        ],
        message="No preferred centre available satisfying the requested quantity.",
    )

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop_id": str(crop_id),
            "ready_date": "2026-11-15",
            "requested_quantity_kg": "500.00",
            "preferred_centres": [{"centre_id": str(c1), "priority": 1}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["selected_centre_id"] is None
    assert data["selected_priority"] is None
    assert "no preferred centre available" in data["message"].lower()
