from fastapi.testclient import TestClient

from app.main import app


def test_app_starts() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 404
