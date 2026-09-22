from fastapi.testclient import TestClient

from app.core.rbac import Role
from app.core.security import create_access_token
from app.main import app


def test_validation_envelope_on_actual_endpoint() -> None:
    client = TestClient(app)
    token = create_access_token("test-farmer-id", role=Role.FARMER)

    response = client.post(
        "/api/v1/farmers/me/centre-selection",
        headers={"Authorization": f"Bearer {token}"},
        json={"preferred_centres": "invalid_not_a_list"},
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Enter a valid value."
    assert data["status_code"] == 422
    assert "errors" in data["details"]
    assert isinstance(data["details"]["errors"], list)
    assert len(data["details"]["errors"]) > 0
