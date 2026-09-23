from fastapi.testclient import TestClient

from backend.app.main import app


def auth_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/token", data={"username": "admin", "password": "admin"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_reference_data_and_prediction_contracts() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        sites = client.get("/api/v1/sites", headers=headers)
        machines = client.get("/api/v1/machines", headers=headers)
        operators = client.get("/api/v1/operators", headers=headers)
        assert sites.status_code == machines.status_code == operators.status_code == 200
        assert len(sites.json()["items"]) == 3
        assert len(machines.json()["items"]) == 12
        assert len(operators.json()["items"]) == 15

        energy = client.post(
            "/api/v1/predict/energy-runout",
            headers=headers,
            json={
                "machine_id": "EXC001",
                "energy_remaining_pct": 50,
                "burn_rate_per_hour": 10,
                "remaining_task_min": 30,
            },
        )
        assignment = client.post(
            "/api/v1/predict/assignment",
            headers=headers,
            json={
                "site_id": "S01",
                "machine_class": "excavator",
                "task_duration_min": 60,
            },
        )
        assert energy.status_code == assignment.status_code == 200
        assert energy.json()["will_complete_task"] is True
        assert assignment.json()["suggestions"]


def test_alert_and_weather_ingestion() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        alert = client.post(
            "/api/v1/alerts/ingest",
            headers=headers,
            json={
                "alert_code": "overspeed",
                "severity": "medium",
                "site_id": "S01",
                "machine_id": "EXC001",
                "started_at": "2026-09-23T08:00:00Z",
                "duration_min": 2,
            },
        )
        weather = client.post(
            "/api/v1/weather",
            headers=headers,
            json={
                "site_id": "S01",
                "observed_at": "2026-09-23T08:00:00Z",
                "temperature_c": 34,
                "rain_mm": 0,
            },
        )
        assert alert.status_code == 201
        assert weather.status_code == 201
        assert client.get("/api/v1/alerts", headers=headers).json()["items"]
        assert (
            client.get("/api/v1/weather/S01", headers=headers).json()["site_id"]
            == "S01"
        )


def test_task_incident_and_training_resource_operations() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        task = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "task_type": "excavation",
                "site_id": "S01",
                "planned_duration_min": 60,
            },
        )
        task_id = task.json()["id"]
        updated = client.patch(
            f"/api/v1/tasks/{task_id}", headers=headers, json={"notes": "priority"}
        )
        incident = client.post(
            "/api/v1/incidents",
            headers=headers,
            json={
                "site_id": "S01",
                "category": "site_hazard",
                "description": "Loose rock",
                "severity": "medium",
            },
        )
        training = client.post(
            "/api/v1/training",
            headers=headers,
            json={"operator_id": "OP1001", "course_name": "Pre-shift inspection"},
        )
        assert task.status_code == 201
        assert updated.status_code == 200 and updated.json()["notes"] == "priority"
        assert incident.status_code == 201
        assert client.get("/api/v1/incidents", headers=headers).json()["items"]
        assert training.status_code == 201
