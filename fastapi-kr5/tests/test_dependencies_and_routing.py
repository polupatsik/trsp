from fastapi.testclient import TestClient
from app.main import app
from app.storage import tasks

client = TestClient(app)


def setup_function():
    tasks.clear()


def test_users_me():
    response = client.get(
        "/users/me",
        headers={"X-User-Id": "10"}
    )

    assert response.status_code == 200


def test_admin_forbidden():
    response = client.get(
        "/admin/stats",
        headers={
            "X-User-Id": "10",
            "X-User-Role": "user"
        }
    )

    assert response.status_code == 403
