# Member 3 callable interface for Member 2

Member 3 inference runs locally as Python functions. Member 2 owns HTTP routes, authentication, persistence, task creation, assignment transactions and WebSocket delivery. This file specifies the calls to connect; those backend components are not in this repository.

## Models and inputs

Load each version once when the backend starts. Artifacts are already trained and must come from a trusted local model directory.

```python
from pathlib import Path
from ml.inference import AdvancedModelService, ModelService

duration_and_general_anomaly = ModelService(Path("ml/models/v1"))
fuel_anomaly_and_energy = AdvancedModelService(Path("ml/models/v2"))
```

Call `ModelService.predict_task_duration(TaskDurationInput(...))` when an admin creates a supported task. The request fields are `machine_class`, `task_type`, `ground_condition`, `quantity`, `unit`, `planned_duration_min`, `rain_prev_24h_mm` and `experience_years`. The result has `estimated_duration_min` and `model_version`. Persist the result with the task and include it in the task response. The trained classes are those in `shared.constants.MachineClass`; dataset task types use `m2` or `m3`. The current dataset contains neither trucks nor `haul` tasks measured in tonnes. Reject that combination until the team supplies a valid schema, training examples and evaluation. `truck_loading` by a wheel loader is a different task and cannot stand in for hauling.

Call `AdvancedModelService.predict_energy_runout(EnergyForecastInput(...), normalized_history)` using the machine's most recent 60 consecutive one-minute telemetry rows. The request contains the machine ID, class, powertrain, positive tank/battery capacity, remaining litres/kWh and `remaining_task_min`. The forecast returns `estimated_remaining_min`, `has_sufficient_energy`, `recommended_action` (`none`, `refuel`, `recharge` or `unknown`), `forecast_used_pct`, `forecast_horizon_min`, `is_extrapolation` and `model_version`. Zero forecast consumption with remaining energy produces `unknown`; do not coerce that to sufficient. The simpler `predict_energy_runout(EnergyInput(...))` retains the transparent recent-rate baseline and now returns the same action field.

Call `rank_assignments(candidates, site_id=..., machine_class=..., on_date=...)` with actual `AssignmentCandidate` values. Backend code must supply current machine/operator availability, valid certification dates, the duration estimate and the energy estimate for each pair. Exclude unknown energy estimates before building candidates. The ranker filters invalid pairs and sorts eligible pairs by estimated duration, then IDs. Recheck availability and reserve the admin's final selection atomically. The ranker does not perform those backend operations.

Call `AdvancedModelService.detect_fuel_anomalies(normalized_telemetry)` after a completed shift or analysis window. It returns typed fuel anomaly scores, types and model version without allocating anomaly IDs. Call `ModelService.detect_anomalies(normalized_telemetry)` for the v1 general retrospective score. Required telemetry columns are validated and a physical or far-out-of-training-range value raises `ValueError`; expose that through the project's standard error envelope. These retrospective anomalies are distinct from real-time edge alerts. Member 2 must persist anomalies and publish the agreed WebSocket event before an admin dashboard can display them.

Call `summarize_operators(normalized_telemetry, tasks=normalized_tasks, operator_id=..., start_at=..., end_at=..., shift_date=...)` for analytics. It returns one record per operator and machine class. `start_at` and `end_at` form a half-open UTC interval; `shift_date` refers to the UTC date of normalized telemetry. Each record includes `completed_tasks`, `seatbelt_violations`, `harsh_events_count`, observed minutes, idle/seatbelt/unattended percentages, energy totals and load cycles. `seatbelt_violations` counts unfastened moving minutes, not distinct episodes. Supply normalized tasks with `task_id`, `task_status`, `machine_class`, `operator_id`, `actual_end_at` and `date` for completed-task counts; otherwise the count is `null`, not a fabricated zero. The API can choose one operator and period before returning results.

All timestamps in the ML interface are timezone-aware UTC. The frontend converts to IST for display. Model endpoints should follow the planned `/api/v1/predict/` routes; the backend creates IDs and uses the shared API error shape. The backend is still needed for acceptance cases `INT-01`, `INT-02` and `INT-04`. The requested truck-hauling end-to-end case also needs approved scope and representative data before a credible duration or energy model can be trained and evaluated.
