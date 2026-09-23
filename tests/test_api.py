import os

os.environ["DATABASE_URL"] = "sqlite:///./test_backend.db"
os.environ["SECRET_KEY"] = "test-secret"

import pytest

# Phase 3 tests - skip if fastapi not available
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_admin_login(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "service": "api"}
    response = client.post(
        "/api/v1/auth/token", data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_admin_can_create_and_list_task(client: TestClient) -> None:
    token = client.post(
        "/api/v1/auth/token", data={"username": "admin", "password": "admin"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "task_type": "trenching",
            "site_id": "S01",
            "machine_id": "EXC001",
            "operator_id": "OP1001",
            "planned_duration_min": 45,
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "scheduled"
    listed = client.get("/api/v1/tasks", headers=headers)
    assert listed.status_code == 200
    assert any(task["id"] == created.json()["id"] for task in listed.json()["items"])


def test_model_contract_is_available_to_authenticated_clients(
    client: TestClient,
) -> None:
    token = client.post(
        "/api/v1/auth/token", data={"username": "admin", "password": "admin"}
    ).json()["access_token"]
    response = client.post(
        "/api/v1/predict/anomaly",
        headers={"Authorization": f"Bearer {token}"},
        json={"features": {"idle_ratio": 0.8, "harsh_events": 1}},
    )
    assert response.status_code == 200
    assert response.json()["is_anomaly"] is False
    assert response.json()["model_version"] == "baseline-v1"


def test_alert_websocket_accepts_connections(client: TestClient) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("subscribe")
