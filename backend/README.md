# Backend API

The backend owns authentication, task and incident services, weather and training reads, WebSocket events, and the model-serving boundary.

The application is modularized under `backend/app`: `db.py` owns SQLAlchemy configuration and models, `schemas.py` owns API contracts, `auth.py` owns JWT and role dependencies, `events.py` owns WebSocket/Redis events, `weather.py` owns provider integration, and `routers/` owns auth, tasks, resources, and prediction endpoints.

## Run locally

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "."
uvicorn api.main:app --reload
```

The local SQLite database is `backend.db`. The service creates the schema on startup and seeds an `admin` user with password `admin` for the demo only.

## Run with PostgreSQL

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation is at `/docs`.

## Integration contracts

- REST resources are under `/api/v1/tasks`, `/api/v1/incidents`, `/api/v1/weather/{site_id}`, and `/api/v1/operators/{operator_id}/training`.
- Authenticate with `POST /api/v1/auth/token` using OAuth2 form fields `username` and `password`.
- Subscribe to alert and task events at `/ws`; events use `{ "type": "task.updated", "data": {...} }`.
- Events are also published to Redis channel `operator-assistant.events` when `REDIS_URL` is configured.
- Refresh cached provider weather with `POST /api/v1/weather/{site_id}/refresh`; it requires `WEATHER_API_KEY`.
- Member 3 can replace the fallback implementations behind `POST /api/v1/predict/task-duration` and `POST /api/v1/predict/anomaly` while preserving the request and response schemas.
- Set `DATABASE_URL` to a SQLAlchemy URL and `SECRET_KEY` outside local development.
