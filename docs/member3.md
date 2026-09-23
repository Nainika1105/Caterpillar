# Member 3 ML and analytics

This package implements a reproducible first version of the ML layer. The source synthetic CSVs are preserved. `ml/features/data.py` adapts legacy columns to the internal contract, converts the generator's IST timestamps to UTC, separates diesel litres from electric kWh, and removes telemetry answer-key columns before feature extraction.

This page describes v1. [Version 2](member3-v2.md) supersedes the anomaly/energy baseline with improved detectors and learned forecasts, evaluated on a fresh generated holdout. Duration, assignments and charger functions remain available as described here.

## Run locally

Use Python 3.11. On macOS, XGBoost also needs `brew install libomp`.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m ml.training.train
.venv/bin/python -m ml.demo
.venv/bin/pytest -q
.venv/bin/ruff check ml shared tests
.venv/bin/black --check ml shared tests
.venv/bin/mypy shared
```

Configuration is read from environment variables, with defaults in `.env.example`. The file is documentation and is not automatically loaded. Set `CAT_MODEL_DIR` to a new version directory for each run; training refuses to overwrite existing artifacts.

`requirements.lock` records the exact tested Python environment. To reproduce it, install with `.venv/bin/python -m pip install -r requirements.lock`. The demo loads saved models and prints example predictions; it does not retrain.

Training produces `duration.joblib`, `anomaly.joblib`, `evaluation.json`, and `operator_analytics.json`. Artifact files are ignored by Git and reproducible from the source and recorded dependency versions. Share the complete version directory with Member 2 through the team's artifact channel. Load only trusted joblib files.

## Model behavior

The duration estimator uses XGBoost and compares MAE in minutes against `planned_duration_min`. Only completed tasks with positive durations are included. The earliest 60% of distinct task dates are training, the next 20% validation, and the remaining dates test. Model depth is selected on validation days only; the selected model is not refit on test days. Inputs include task quantity and unit, machine class, ground condition, prior rain, operator experience and planned duration. Actual task weather, completed quantity, productive minutes and task telemetry are excluded because those are unavailable when estimating a new task. Current forecast inputs and historical operator aggregates can be added after a point-in-time contract is agreed.

Isolation Forest uses machine/operator/day summaries, with preprocessing fitted only on training days. Ground truth calibrates a threshold on validation days and measures held-out performance; it is not a feature or a filter on the training data. The output is a binary anomaly decision and score, not a diagnosis or anomaly type. Missing powertrain-specific measurements are imputed inside the saved pipeline.

Anomaly evaluation uses **any event overlapping a machine/operator/day window** for both the model and alert baseline. Its precision and recall are shift-level metrics. A baseline alert in a shift containing abnormal fuel burn does not establish detection of that fuel-burn event. Per-type shift recall is contextual, not event classification accuracy. More precise event localization and type-specific evaluation remain follow-up work. The supplied data have one daytime shift; overnight/multiple shifts require an explicit shift ID before using this aggregation in production.

Energy runout currently uses a transparent consumption-rate baseline, not a trained improvement over that baseline. The caller supplies the recent observed consumption rate (normally the last hour), remaining fuel/usable battery energy and remaining task time. A zero rate with positive remaining energy returns unknown instead of infinity. The dataset has no verified run-to-empty target, so the report does not claim a runout MAE. Charger suggestions filter by site, availability and compatibility, then minimize idealized charging time using the lower of charger and machine power. Charging taper, queue and travel time are not modeled.

Operator analytics group by operator and machine class. Percentages use observed minutes, not an assumed shift length. Aggregated litres and kWh are distinct; a zero total for a non-applicable powertrain is an aggregation result, not measured consumption.

## Member 2 handoff

Import only from `ml.inference` for ML implementation. Import request/response types from `shared.schemas.prediction`.

```python
from ml.inference import ModelService, predict_energy_runout, rank_assignments, suggest_charger
from shared.constants import MachineClass
from shared.schemas.prediction import TaskDurationInput

models = ModelService()  # Once at API startup, after artifacts are installed.
prediction = models.predict_task_duration(TaskDurationInput(
    machine_class=MachineClass.MINI_EXCAVATOR,
    task_type="trenching", ground_condition="dry", quantity=25,
    unit="m3", planned_duration_min=150, rain_prev_24h_mm=0,
    experience_years=6,
))
payload = prediction.model_dump(mode="json")
```

`ModelService.detect_anomalies` accepts normalized completed-shift telemetry and returns typed anomaly predictions without generating IDs. `summarize_operators` accepts the same normalized telemetry. Member 2 maps these results to persistence and API responses and implements authentication, error envelopes, IDs and WebSocket events.

`rank_assignments` ranks alternatives for one task, filtering exact machine class, site, current availability, required certifications, expiry and energy sufficiency. Electric classes additionally need `ev_high_voltage`. Certification expiry and current availability must come from the backend; the CSV's certification string alone does not establish validity. Missing expiry fails closed. The backend must recheck and reserve the selected pair atomically when an admin confirms. The matcher does not allocate multiple tasks or prevent races itself.

Suggested route mapping: `predict_task_duration` → `/api/v1/predict/task-duration`; `predict_energy_runout` → `/api/v1/predict/energy-runout`; `rank_assignments` → `/api/v1/predict/assignment`. HTTP routes are Member 2's work and are not created here.

## Validation and limits

Tests cover timestamp conversion, label exclusion, completed-task selection, chronological partitions, event overlap, energy-unit calculations, certificate/availability filtering, charger constraints, and a real train-save-load-predict cycle. The standalone dataset repository has no full-stack Docker Compose or API, so full-stack startup, OpenAPI and end-to-end application tests remain team integration checks.

Synthetic held-out performance is evidence about this generator only, not validation for operation of real machinery. Do not claim the anomaly model improves on rules unless the reported results support the comparison at the stated grain.

The initial `v1` duration evaluation used 125 held-out completed tasks: MAE was 35.08 minutes versus 57.94 for planned duration. Its anomaly F1 was 0.45 versus 0.882 for the rules baseline across 70 held-out machine/operator/day summaries; it missed both held-out abnormal-fuel-burn shifts. This version is a runnable baseline, and the anomaly model does not meet the project's improvement target. Future feature changes should be assessed on fresh generated dates or a new untouched holdout, because these test results have now been inspected.
