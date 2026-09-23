"""Execute the user's 60 acceptance cases without changing production code/models.

Run from repository root: .venv/bin/python -m audits.member3_audit
"""

import ast
import hashlib
import inspect
import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pydantic import ValidationError
from sklearn.metrics import confusion_matrix, mean_absolute_error, mean_squared_error

from audits.extreme_probe import probe as extreme_probe

from ml.anomaly import evaluate_fuel, predict_fuel
from ml.energy import ENERGY_FEATURES, energy_examples, evaluate_energy, history_features
from ml.features.build import SHIFT_FEATURES, TASK_FEATURES, operator_analytics, shift_features, task_features
from ml.features.data import load_data
from ml.inference import AdvancedModelService, ModelService, predict_energy_runout, rank_assignments, suggest_charger, summarize_operators
from ml.training.train import date_split, metrics, overlap_labels, train_duration
from shared.constants import AnomalyType, MachineClass, MachineState, Powertrain, SeatbeltStatus, TaskStatus
from shared.schemas.prediction import AssignmentCandidate, ChargeInput, ChargePoint, EnergyForecastInput, EnergyInput, TaskDurationInput

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audits" / "results"
OUT.mkdir(exist_ok=True)
ROWS = []
DETAIL = {}


def serial(value):
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, (datetime, date, pd.Timestamp, Path)):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def location(file, function):
    path = ROOT / file
    if not path.exists():
        return {"file": file, "function": function, "line": None}
    tree = ast.parse(path.read_text())
    target = function.split(".")[-1]
    matches = [n.lineno for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == target]
    if "." in function:
        cls = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == function.split(".")[0]), None)
        if cls:
            matches = [n.lineno for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == target] or [cls.lineno]
    return {"file": file, "function": function, "line": min(matches) if matches else 1}


def case(test_id, module, inputs, expected, fn, file, function, fix):
    try:
        passed, actual, issue = fn()
    except Exception as exc:
        passed, actual, issue = False, {"exception": type(exc).__name__, "message": str(exc)}, "Unhandled exception during the requested case"
    row = {"test_id": test_id, "module": module, "input": inputs, "expected": expected,
           "actual": actual, "status": "PASS" if passed else "FAIL", "issue": issue or "None",
           "responsible": location(file, function), "smallest_fix": fix if not passed else "Not required for this case"}
    ROWS.append(row)
    print(f"{test_id}: {row['status']} — {str(issue)[:140]}", flush=True)


def caught(fn):
    try:
        return {"value": fn(), "exception": None}
    except Exception as exc:
        return {"exception": type(exc).__name__, "message": str(exc)}


def main():
    data = load_data(ROOT / "data")
    holdout = load_data(ROOT / "data/generated/holdout_seed20260923")
    tel = data["telemetry_1min"]
    basic = ModelService(ROOT / "ml/models/v1")
    advanced = AdvancedModelService(ROOT / "ml/models/v2")
    artifact_paths = list((ROOT / "ml/models/v1").glob("*.joblib")) + list((ROOT / "ml/models/v2").glob("*.joblib"))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifact_paths}
    shifts = shift_features(tel)
    # Complete operational baseline for unspecified 'normal' fields. Explicit
    # user values override these class medians; labels are not selected as inputs.
    frame = shifts.loc[shifts.machine_class == MachineClass.DOZER, SHIFT_FEATURES].median().to_dict()
    frame.update(machine_class=MachineClass.DOZER.value, idle_pct=12.0, fuel_per_load_cycle_l=7.8, harsh_events_count=1)

    def broad(**changes):
        row = dict(frame, **changes)
        score = float(-basic.anomaly["pipeline"].score_samples(pd.DataFrame([row])[basic.anomaly["features"]])[0])
        return {"anomaly": score >= basic.anomaly["threshold"], "score": score, "threshold": basic.anomaly["threshold"], "features": row}

    def synthetic(n=480, idle=0.12, harsh=1, multiplier=1.0, operator="OP1002"):
        row = tel.loc[tel.machine_id == "EXC002"].iloc[0]
        out = pd.DataFrame([row.to_dict()] * n)
        out["recorded_at"] = pd.date_range("2025-08-01T02:30:00Z", periods=n, freq="min")
        out["operator_id"] = operator
        out["state"] = MachineState.WORKING
        out.loc[: int(n * idle) - 1, "state"] = MachineState.IDLE
        out["is_power_on"] = True
        out["is_operator_present"] = True
        out["seatbelt_status"] = SeatbeltStatus.FASTENED
        out["ground_speed_kmh"] = 0.3
        out["fuel_rate_lph"] = [advanced.anomaly["rates"].loc[(MachineClass.EXCAVATOR.value, s)] * multiplier for s in out.state]
        out["fuel_used_l"] = out.fuel_rate_lph / 60
        out["energy_used_kwh"] = np.nan
        out["fuel_level_pct"] = 80 - out.fuel_used_l.cumsum() / 345 * 100
        out["harsh_events"] = 0
        out.loc[0, "harsh_events"] = harsh
        out["load_cycles"] = 0
        cycles = max(1, round(out.fuel_used_l.sum() / 7.8))
        out.loc[0, "load_cycles"] = cycles
        out["proximity_min_m"] = 20
        out["coolant_temp_c"] = 88
        return out

    def fuel(multiplier):
        return advanced.detect_fuel_anomalies(synthetic(multiplier=multiplier))[0].model_dump(mode="json")

    normal = broad()
    case("AD-01", "Anomaly Detection", "v1 dozer: idle_pct=12, fuel_per_load_cycle_l=7.8, harsh_events_count=1; other inputs=class medians (dozer baseline 7.67 L/cycle)", "anomaly=false", lambda: (not normal["anomaly"], {"v1": normal, "v2_fuel_control": fuel(1.0)}, "The supplied 7.8 L/cycle normal assumption is class-dependent; dozer is the closest baseline in this dataset." if normal["anomaly"] else "None"), "ml/training/train.py", "train_anomaly", "Calibrate normal-operation validation fixtures per machine class and tune the v1 threshold on validation data; add a regression test. Do not declare 7.8 L/cycle universally normal.")
    def idle_test():
        value = broad(idle_pct=70)
        return value["anomaly"] or value["score"] >= normal["score"] + 0.02, value, "v1 general detector tested; v2 is fuel-specific and does not detect idling."
    case("AD-02", "Anomaly Detection", "v1 idle_pct=70; other fields fixed to AD-01", "Anomaly or score rises by at least 0.02 (audit operationalization of clearly elevated)", idle_test, "ml/training/train.py", "train_anomaly", "Add a calibrated idle-duration feature/detector to the general anomaly path; retain safety rules and evaluate validation-only threshold changes.")
    case("AD-03", "Anomaly Detection", "v2 normalized telemetry: fuel_rate_lph and fuel_used_l=2.5× learned class/state baseline; same work and cycles", "abnormal_fuel_burn detected", lambda: (AnomalyType.ABNORMAL_FUEL_BURN in fuel(2.5)["anomaly_types"], fuel(2.5), "None"), "ml/anomaly.py", "predict_fuel", "Calibrate the workload-normalized fuel residual on validation data and expose that detector in inference.")
    case("AD-04", "Anomaly Detection", "v1 harsh_events_count=200; idle_pct=12; fuel_per_load_cycle_l=8.58", "anomaly=true", lambda: ((r := broad(harsh_events_count=200, fuel_per_load_cycle_l=8.58))["anomaly"], r, "None"), "ml/training/train.py", "train_anomaly", "Add harsh-event-rate calibration to the general model and re-evaluate on an untouched holdout.")
    def borderline():
        controls = [broad(idle_pct=i, fuel_per_load_cycle_l=f) for i, f in [(12, 7.8), (14, 8.0), (16, 8.2)]]
        return not all(r["anomaly"] for r in controls), controls, "None" if not all(r["anomaly"] for r in controls) else "All normal/borderline fixtures flagged by the general v1 model; v2 fuel controls remain separate."
    case("AD-05", "Anomaly Detection", "v1 idle_pct 12/14/16; fuel_per_load_cycle_l 7.8/8.0/8.2; harsh count 1", "Not every small deviation is flagged", borderline, "ml/training/train.py", "train_anomaly", "Build per-class normal/borderline validation fixtures and select a threshold with a false-positive-rate constraint.")
    def missing_anomaly():
        omitted = caught(lambda: basic.detect_anomalies(synthetic().drop(columns="fuel_used_l")))
        nan = broad(fuel_per_load_cycle_l=np.nan)
        passed = omitted["exception"] in {"ValidationError", "ValueError"}
        return passed, {"omitted_raw_input": omitted, "NaN_engineered_feature": nan}, "None" if passed else "NaN engineered values are imputed, but an omitted raw column causes an unwrapped exception."
    case("AD-06", "Anomaly Detection", "Remove raw fuel_used_l; additionally set engineered fuel_per_load_cycle_l=NaN", "Imputation or a clear ValueError/ValidationError at inference boundary", missing_anomaly, "ml/inference.py", "ModelService.detect_anomalies", "Check required telemetry columns before shift_features and raise ValueError listing missing columns; preserve existing NaN imputation.")
    case("AD-07", "Anomaly Detection", "fuel_per_load_cycle_l=99999 across all five supported diesel machine classes; other fields are class medians, idle_pct=12 and harsh_events_count=1", "Reject or flag extreme input for every class", lambda: extreme_probe(shifts, basic), "ml/inference.py", "ModelService.score_shift_features", "Validate physically impossible engineered fuel/cycle values or flag out-of-domain inputs before Isolation Forest scoring; add this cross-class regression test.")
    def leakage():
        forbidden = {"anomaly_id", "anomaly_type", "anomaly_ground_truth"}
        used = set(basic.anomaly["features"]) | set(advanced.anomaly["forest"].feature_names_in_) | set(TASK_FEATURES) | set(ENERGY_FEATURES)
        a = advanced.detect_fuel_anomalies(synthetic())
        b = advanced.detect_fuel_anomalies(synthetic().assign(anomaly_id="A9999", anomaly_type="answer", anomaly_ground_truth=1))
        return not (forbidden & used) and a == b, {"feature_names": sorted(used), "forbidden_intersection": sorted(forbidden & used), "perturbation_unchanged": a == b}, "Labels are used for validation calibration/evaluation only, not feature inputs."
    case("AD-08", "Anomaly Detection", "Inspect persisted feature_names; inject all three forbidden label columns", "No label features and unchanged predictions", leakage, "ml/anomaly.py", "fit_fuel_model", "Remove label columns from every estimator input whitelist and rebuild affected artifacts.")
    def anomaly_metrics():
        test = shifts.loc[shifts.date >= "2025-05-24"]
        actual = overlap_labels(test, data["anomalies_ground_truth"])
        pred = -basic.anomaly["pipeline"].score_samples(test[basic.anomaly["features"]]) >= basic.anomaly["threshold"]
        report = {"v1_may_test": {**metrics(actual, pred), "confusion_matrix": confusion_matrix(actual, pred, labels=[False, True]).tolist()}}
        hs = predict_fuel(advanced.anomaly, holdout["telemetry_1min"])
        truth = overlap_labels(hs, holdout["anomalies_ground_truth"])
        rules = overlap_labels(hs, holdout["safety_alerts"])
        for name, p in [("v2_fuel_only", hs.is_anomaly.to_numpy()), ("holdout_rules", rules), ("holdout_rules_plus_v2", rules | hs.is_anomaly.to_numpy())]:
            report[name] = {**metrics(truth, p), "confusion_matrix": confusion_matrix(truth, p, labels=[False, True]).tolist()}
        report["typed_v2"] = evaluate_fuel(advanced.anomaly, holdout["telemetry_1min"], holdout["anomalies_ground_truth"], holdout["safety_alerts"])["typed_fuel_model"]
        report["matrix_order"] = "Rows actual [normal, anomaly]; columns predicted [normal, anomaly]: [[TN, FP], [FN, TP]]"
        DETAIL["anomaly_metrics"] = report
        return True, report, "Metrics are shift-level, not event-level. Combined safety+fuel results are not fuel-only ML performance."
    case("AD-09", "Anomaly Detection", "Recompute v1 May24–30 and v2 June1–July30 predictions vs ground-truth CSVs", "Return precision, recall, F1 and confusion matrices", anomaly_metrics, "ml/anomaly.py", "evaluate_fuel", "Add confusion_matrix to the saved evaluation output; use matching evaluation grain.")

    base = dict(machine_class=MachineClass.EXCAVATOR, task_type="excavation", ground_condition="dry", quantity=100, unit="m3", planned_duration_min=120, rain_prev_24h_mm=0, experience_years=5)
    def duration(**changes):
        return basic.predict_task_duration(TaskDurationInput(**dict(base, **changes))).estimated_duration_min
    case("TT-01", "Task Time Estimator", "Supported equivalent: excavator excavation, 100 m3, dry, prior rain 0 mm, experience 5 years, planned 120 min; haul/truck_01 is unsupported", "Finite positive duration in minutes for a supported task", lambda: (0 < (v := duration()) < 24 * 60, {"duration_min": v, "scope": "Supported-machine control; literal hauling scenario tested in E2E-01"}, "The truck/haul example has no machine class in this project's schema."), "ml/inference.py", "ModelService.predict_task_duration", "Add hauling/truck data and supported machine classes before promising that literal use case; retain a positive-duration guard.")
    def quantity():
        pairs = [{"task_type": t, "quantity_100_min": duration(task_type=t, quantity=100), "quantity_500_min": duration(task_type=t, quantity=500)} for t in ["excavation", "trenching", "truck_loading"]]
        return all(p["quantity_500_min"] > p["quantity_100_min"] for p in pairs), pairs, "planned_duration_min held at 120 as requested; this may conflict with quantity-derived planning."
    case("TT-02", "Task Time Estimator", "100 vs 500 quantity across excavation/trenching/truck_loading; every other field fixed", "Larger quantity predicts longer duration", quantity, "ml/training/train.py", "train_duration", "Add a monotonic quantity constraint or model duration per unit with consistent units; validate across task types rather than relying only on planned duration.")
    def rain():
        clear, wet = duration(), duration(ground_condition="wet", rain_prev_24h_mm=30)
        return wet > clear, {"clear_dry_min": clear, "wet_prior_30mm_min": wet, "current_heavy_rain_feature": "absent"}, "Only prior rain and ground are supported; current/forecast heavy-rain intensity is not an input."
    case("TT-03", "Task Time Estimator", "Dry/0 prior rain vs wet/30 mm prior rain; same task. Current-rain input unavailable", "Supported wet/prior-rain scenario takes longer", rain, "ml/features/build.py", "task_features", "Add point-in-time forecast rain/temperature to TASK_FEATURES and TaskDurationInput, train using forecasts available at task creation, and validate directional impact.")
    case("TT-04", "Task Time Estimator", "Same task: experience_years 1 vs 15", "Experienced operator predicts no longer duration and feature affects result", lambda: ((new := duration(experience_years=1)) > (old := duration(experience_years=15)), {"one_year_min": new, "fifteen_years_min": old}, "Uses experience_years, not learned operator-history aggregates."), "ml/training/train.py", "train_duration", "Add past-only operator performance aggregates or constrain experience direction where justified; validate with matched tasks.")
    def missing_weather():
        payload = dict(base)
        del payload["rain_prev_24h_mm"]
        result = caught(lambda: TaskDurationInput(**payload))
        return result["exception"] == "ValidationError", result, "Missing prior rain is rejected explicitly; there is no weather fallback."
    case("TT-05", "Task Time Estimator", "Omit rain_prev_24h_mm", "Fallback or validation error", missing_weather, "shared/schemas/prediction.py", "TaskDurationInput", "Make the field optional with a documented trained imputation policy, or preserve explicit required-field validation.")
    def negative_quantity():
        result = caught(lambda: duration(quantity=-50))
        return result["exception"] == "ValidationError", result, "None"
    case("TT-06", "Task Time Estimator", "quantity=-50", "Reject negative quantity", negative_quantity, "shared/schemas/prediction.py", "TaskDurationInput", "Enforce Field(gt=0) before model inference.")
    case("TT-07", "Task Time Estimator", "task_type=unseen_task_type", "Graceful handling", lambda: (math.isfinite(v := duration(task_type="unseen_task_type")) and v > 0, {"duration_min": v, "encoder": "handle_unknown=ignore"}, "Graceful numerical prediction does not establish accuracy for unseen tasks."), "ml/training/train.py", "preprocessing", "Use handle_unknown=ignore or reject unsupported task types explicitly.")
    tasks = task_features(data["tasks"], data["operators"])
    masks = date_split(tasks.date)
    def split():
        ranges = [{"from": tasks.date[m].min(), "through": tasks.date[m].max(), "rows": int(m.sum())} for m in masks]
        return ranges[0]["through"] < ranges[1]["from"] and ranges[1]["through"] < ranges[2]["from"], ranges, "v2 holdout dates also follow development; previously viewed data are not claimed as a new holdout."
    case("TT-08", "Task Time Estimator", "Execute date_split on completed tasks", "Training dates precede validation and test dates", split, "ml/training/train.py", "date_split", "Split distinct dates before fitting preprocessing and estimators.")
    case("TT-09", "Task Time Estimator", "Run task_features on all 766 tasks, including partial and missing durations", "Only completed positive-duration tasks train the estimator", lambda: (bool((tasks.task_status == TaskStatus.COMPLETED).all() and tasks.actual_duration_min.gt(0).all()), {"retained": len(tasks), "excluded": len(data["tasks"]) - len(tasks), "statuses": tasks.task_status.value_counts().to_dict()}, "None"), "ml/features/build.py", "task_features", "Filter incomplete and invalid-duration tasks before training, or implement a separate censored-duration model.")
    def duration_metrics():
        test = tasks.loc[masks[2]]
        p = np.maximum(1, basic.duration["pipeline"].predict(test[TASK_FEATURES]))
        report = {"test_count": len(test), "mae_min": float(mean_absolute_error(test.actual_duration_min, p)), "rmse_min": float(np.sqrt(mean_squared_error(test.actual_duration_min, p))), "baseline_mae_min": float(mean_absolute_error(test.actual_duration_min, test.planned_duration_min))}
        DETAIL["duration_metrics"] = report
        return report["mae_min"] < report["baseline_mae_min"], report, "Re-evaluation of existing held-out split, not a newly unseen test."
    case("TT-10", "Task Time Estimator", "Saved XGBoost on 125 completed May24–30 tasks", "Report MAE/RMSE; beat planned-duration baseline", duration_metrics, "ml/training/train.py", "train_duration", "Select model/features on validation dates; add RMSE reporting and retain a separate untouched final test.")

    def energy_case(remaining, rate, electric=False):
        kwargs = dict(powertrain=Powertrain.ELECTRIC if electric else Powertrain.DIESEL, remaining_task_min=240)
        kwargs.update(dict(energy_remaining_kwh=remaining, power_kw=rate) if electric else dict(fuel_remaining_l=remaining, fuel_rate_lph=rate))
        return predict_energy_runout(EnergyInput(**kwargs)).model_dump(mode="json")
    case("EN-01", "Energy Model", "80 L; 10 L/hour; remaining task 240 min", "40 L required; enough=true; remaining=480 min", lambda: ((r := energy_case(80, 10))["has_sufficient_energy"] is True and r["estimated_remaining_min"] == 480, {"prediction": r, "independent_required_l": 40}, "The function returns sufficiency and remaining minutes, not an explicit required-energy field."), "ml/inference.py", "predict_energy_runout", "Expose required_fuel_l if the caller needs it; calculate rate * remaining_task_min / 60.")
    case("EN-02", "Energy Model", "20 L; 10 L/hour; task 240 min", "enough=false AND explicit REFUEL recommendation", lambda: ((r := energy_case(20, 10)).get("has_sufficient_energy") is False and r.get("recommended_action") == "refuel", {"prediction": r, "independent_required_l": 40}, "None"), "shared/schemas/prediction.py", "EnergyPrediction", "Add a typed recommended_action field and set it to refuel for insufficient diesel energy.")
    case("EN-03", "Energy Model", "70% battery, 8%/hour, 4 hours; normalized explicitly to a 100 kWh battery: 70 kWh, 8 kW", "Enough battery; remaining=525 min", lambda: ((r := energy_case(70, 8, True))["has_sufficient_energy"] is True and r["estimated_remaining_min"] == 525, r, "The public function accepts kWh/kW, not raw battery percentages."), "ml/inference.py", "predict_energy_runout", "Convert percentages through validated battery capacity before energy inference.")
    def low_ev():
        check = energy_case(20, 8, True)
        advice = suggest_charger(ChargeInput(site_id="S01", battery_capacity_kwh=100, energy_remaining_kwh=20, target_soc_pct=80, max_charge_kw=50), [ChargePoint(energy_point_id="S01-DC1", site_id="S01", power_kw=100, is_available=True, is_compatible=True)])
        passed = check["has_sufficient_energy"] is False and check["recommended_action"] == "recharge" and advice is not None
        return passed, {"energy": check, "separately_called_charge_advisory": advice.model_dump(mode="json")}, "Local composition passes; automatic charger-choice orchestration is absent."
    case("EN-04", "Energy Model", "20% on 100 kWh battery; consumption 8 kW; 240-min task; compatible available 50-kW-limited charger", "Insufficiency plus a real charge recommendation", low_ev, "ml/inference.py", "suggest_charger", "Call suggest_charger from an energy advisory coordinator after insufficiency is detected.")
    case("EN-05", "Energy Model", "Positive fuel, zero burn", "No divide-by-zero; unknown time is acceptable", lambda: ((r := energy_case(20, 0))["estimated_remaining_min"] is None, r, "Returns unknown sufficiency instead of infinity."), "ml/inference.py", "predict_energy_runout", "Handle zero rate explicitly before division.")
    def negative_energy():
        r = caught(lambda: energy_case(-10, 10))
        return r["exception"] == "ValidationError", r, "None"
    case("EN-06", "Energy Model", "fuel_remaining_l=-10", "Validation error", negative_energy, "shared/schemas/prediction.py", "EnergyInput", "Validate remaining energy as nonnegative.")
    case("EN-07", "Energy Model", "60 L; 12 L/hour", "300 min (5 hours)", lambda: ((r := energy_case(60, 12))["estimated_remaining_min"] == 300, r, "This exact-case check tests the transparent baseline, not the learned forecast."), "ml/inference.py", "predict_energy_runout", "Convert hours to minutes exactly once when dividing remaining fuel by litres/hour.")
    def energy_metrics():
        examples = energy_examples(holdout["telemetry_1min"], holdout["machines"])
        report = evaluate_energy(advanced.energy, examples)
        DETAIL["energy_metrics"] = report
        ok = all(r["model_consumption_mae_pct"] < r["baseline_consumption_mae_pct"] and r["model_drawdown_mae_min"] < r["baseline_drawdown_mae_min"] for r in report["by_powertrain"].values())
        return ok, report, "Pass is for forecast and fixed-5%-budget replay comparison; actual empty-machine timing remains unverified."
    case("EN-08", "Energy Model", "Recompute v2 on June–July dataset, both powertrains", "Learned forecast/replay error lower than recent-hour extrapolation; disclose censoring", energy_metrics, "ml/energy.py", "evaluate_energy", "Add actual depletion observations or a separately justified simulation before claiming real time-to-empty MAE.")

    def candidate(**updates):
        values = dict(machine_id="EXC002", operator_id="OP1002", site_id="S01", machine_class=MachineClass.EXCAVATOR, certifications={MachineClass.EXCAVATOR.value}, certification_valid_until={MachineClass.EXCAVATOR.value: date(2027, 1, 1)}, is_machine_available=True, is_operator_available=True, estimated_duration_min=140, estimated_remaining_min=500)
        values.update(updates)
        return AssignmentCandidate(**values)
    def rank(candidates):
        return rank_assignments(candidates, site_id="S01", machine_class=MachineClass.EXCAVATOR, on_date=date(2026, 9, 23))
    def rank_result(candidates, expected_count):
        r = rank(candidates)
        return len(r) == expected_count, [x.model_dump(mode="json") for x in r], "None"
    matcher_cases = [
        ("TM-01", "Available, valid excavator certificate", [candidate()], 1, "Include eligible operator"),
        ("TM-02", "Missing certification", [candidate(certifications=set())], 0, "Exclude, not merely penalize"),
        ("TM-03", "Certificate expired 2025-01-01; assignment 2026-09-23", [candidate(certification_valid_until={MachineClass.EXCAVATOR.value: date(2025, 1, 1)})], 0, "Exclude expired certificate"),
        ("TM-04", "is_operator_available=false", [candidate(is_operator_available=False)], 0, "Exclude unavailable operator"),
        ("TM-05", "Energy estimate 100 min; task estimate 140 min", [candidate(estimated_remaining_min=100)], 0, "Reject insufficient-energy machine"),
        ("TM-07", "One uncertified pair and one unavailable machine", [candidate(certifications=set()), candidate(machine_id="EXC003", is_machine_available=False)], 0, "Return empty recommendations"),
    ]
    for tid, inp, candidates, count, expect in matcher_cases:
        case(tid, "Task Matcher", inp, expect, lambda cs=candidates, n=count: rank_result(cs, n), "ml/inference.py", "rank_assignments", "Apply certification expiry, availability and energy eligibility filters before ranking; never use an invalid fallback.")
    case("TM-06", "Task Matcher", "A ETA140, B ETA180; all other eligibility equal", "A ranks first", lambda: ((r := rank([candidate(machine_id="EXC003", estimated_duration_min=180), candidate()]))[0].machine_id == "EXC002", [x.model_dump(mode="json") for x in r], "Machine health is not modeled; both fixtures assumed healthy."), "ml/inference.py", "rank_assignments", "Sort eligible candidates by estimated_duration_min with deterministic ID tie-breaks.")
    def determinism():
        runs = [[x.machine_id for x in rank([candidate(machine_id="EXC003"), candidate()])] for _ in range(10)]
        return all(r == runs[0] for r in runs), runs, "None"
    case("TM-08", "Task Matcher", "Identical tied eligible pairs, 10 calls", "Same ordering each call", determinism, "ml/inference.py", "rank_assignments", "Keep stable machine_id/operator_id tie-breaks after predicted duration.")
    def duration_consumed():
        a, b = duration(quantity=100, planned_duration_min=120), duration(quantity=500, planned_duration_min=600)
        r = rank([candidate(estimated_duration_min=a, estimated_remaining_min=1000), candidate(machine_id="EXC003", estimated_duration_min=b, estimated_remaining_min=1000)])
        return len(r) == 2 and r[0].estimated_duration_min == min(a, b), {"actual_model_durations_min": [a, b], "ranking": [x.machine_id for x in r]}, "Consumes actual model estimates supplied by this test; matcher itself does not invoke duration inference."
    case("TM-09", "Task Matcher", "Feed two actual XGBoost predictions into candidates", "Matcher consumes estimates in ranking", duration_consumed, "ml/inference.py", "rank_assignments", "Add an orchestration function to compute estimates before constructing candidates; current ranking already consumes supplied estimates.")
    def energy_consumed():
        low, high = energy_case(20, 10), energy_case(80, 10)
        r = rank([candidate(estimated_duration_min=240, estimated_remaining_min=low["estimated_remaining_min"]), candidate(machine_id="EXC003", estimated_duration_min=240, estimated_remaining_min=high["estimated_remaining_min"])])
        return [c.machine_id for c in r] == ["EXC003"], {"energy_outputs": [low, high], "ranking": [x.machine_id for x in r]}, "Consumes calculated remaining time, not the boolean field; unknown (None) energy must be excluded by the caller."
    case("TM-10", "Task Matcher", "Feed actual 120-min and 480-min energy estimates for a 240-min task", "Exclude low-energy pair; choose high-energy pair", energy_consumed, "ml/inference.py", "rank_assignments", "Map calculated energy time into candidates and explicitly exclude unknown sufficiency before ranking.")

    clean = synthetic(n=480, idle=0.25, harsh=7)
    def task_count():
        ten = data["tasks"].loc[data["tasks"].task_status == TaskStatus.COMPLETED].head(10).copy()
        ten["operator_id"] = "OP1002"
        ten["machine_class"] = MachineClass.EXCAVATOR
        r = summarize_operators(clean)
        attempt = caught(lambda: summarize_operators(clean, tasks=ten))
        passed = attempt["exception"] is None and attempt["value"][0].get("completed_tasks") == 10
        return passed, {"completed_task_fixture_count": len(ten), "analytics_without_tasks": r, "pass_tasks_attempt": attempt}, "None" if passed else "Analytics accepts no tasks input or returns an incorrect completed-task count."
    case("OA-01", "Operator Analytics", "10 completed tasks for OP1002 plus one shift's telemetry", "completed_tasks=10", task_count, "ml/features/build.py", "operator_analytics", "Accept tasks plus a period, count distinct completed task_id by operator, and merge counts into the response.")
    case("OA-02", "Operator Analytics", "480 observed minutes; 120 idle minutes", "idle_pct=25 (canonical equivalent of idle_ratio=0.25)", lambda: ((r := summarize_operators(clean))[0]["idle_pct"] == 25, r, "Conventions require percentages 0–100, so 25% is the correct representation."), "ml/features/build.py", "operator_analytics", "Compute idle minutes / observed minutes * 100 and preserve the percentage suffix.")
    def belt():
        t = synthetic(n=60, idle=0)
        t.loc[:3, "seatbelt_status"] = SeatbeltStatus.UNFASTENED
        r = summarize_operators(t)
        passed = r[0].get("seatbelt_violations") == 4
        return passed, {"analytics": r, "derived_violating_minutes": r[0]["unbelted_moving_pct"] * 60 / 100}, "None" if passed else "Only a percentage is returned, not the requested count; event count vs violating-minute count is also undefined."
    case("OA-03", "Operator Analytics", "60 moving minutes with exactly 4 unfastened samples", "Explicit seatbelt violation count=4", belt, "ml/features/build.py", "operator_analytics", "Expose unbelted_moving_min or a defined seatbelt_violations_count; distinguish contiguous events from violating samples.")
    case("OA-04", "Operator Analytics", "7 harsh events in the synthetic shift", "Explicit harsh event total=7", lambda: ((r := summarize_operators(clean))[0].get("harsh_events_count") == 7, {"analytics": r, "shift_feature_harsh_count": int(shift_features(clean).iloc[0].harsh_events_count)}, "None"), "ml/features/build.py", "operator_analytics", "Include harsh_events_count in the grouped sum column list.")
    def isolated():
        a, b = synthetic(n=60, idle=0.25), synthetic(n=60, idle=0.5, operator="OP1003")
        b.recorded_at += pd.Timedelta(minutes=60)
        r = summarize_operators(pd.concat([a, b], ignore_index=True))
        by = {x["operator_id"]: x for x in r}
        return by["OP1002"]["idle_pct"] == 25 and by["OP1003"]["idle_pct"] == 50, r, "None"
    case("OA-05", "Operator Analytics", "OP1002 idle25%; OP1003 idle50%; combined input", "Separate operator metrics", isolated, "ml/features/build.py", "operator_analytics", "Group on operator_id and machine_class before aggregation.")
    def filtering():
        a = synthetic(n=60, idle=0.25)
        b = synthetic(n=60, idle=0.75)
        b.recorded_at += pd.Timedelta(days=1)
        t = pd.concat([a, b], ignore_index=True)
        query = caught(lambda: summarize_operators(t, start_at=pd.Timestamp("2025-08-01T00:00:00Z"), end_at=pd.Timestamp("2025-08-02T00:00:00Z")))
        passed = query["exception"] is None and query["value"][0]["idle_pct"] == 25
        return passed, {"query": query, "unfiltered": summarize_operators(t), "caller_prefiltered": summarize_operators(a)}, "None" if passed else "Date filtering is unavailable or returns the wrong period."
    case("OA-06", "Operator Analytics", "Two days with 25%/75% idle; query only day 1", "Only requested date appears in analytics", filtering, "ml/inference.py", "summarize_operators", "Add start_at/end_at and optional operator_id filters before aggregation, using a half-open UTC interval.")
    case("OA-07", "Operator Analytics", "Typed empty telemetry frame for nonexistent operator", "Clean empty list", lambda: ((r := summarize_operators(tel.iloc[:0])) == [], r, "Input keeps the required schema; a completely columnless DataFrame is not a valid telemetry frame."), "ml/inference.py", "summarize_operators", "Return [] for an empty schema-valid frame before aggregation.")

    def linkage():
        joined = tel.dropna(subset=["task_id"]).merge(data["tasks"][["task_id", "machine_id", "operator_id", "site_id"]], on="task_id", suffixes=("", "_task"), validate="many_to_one")
        mismatch = ((joined.machine_id != joined.machine_id_task) | (joined.operator_id != joined.operator_id_task) | (joined.site_id != joined.site_id_task)).sum()
        # Independently exercise the loader with an existing task ID belonging
        # to another machine; ID membership alone must not establish linkage.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["tasks", "machines", "operators", "safety_alerts", "anomalies_ground_truth"]:
                shutil.copyfile(ROOT / "data" / f"{name}.csv", root / f"{name}.csv")
            raw = pd.read_csv(ROOT / "data/telemetry_1min.csv", nrows=3)
            other = data["tasks"].loc[data["tasks"].machine_id != raw.iloc[0].machine_id].iloc[0].task_id
            raw.loc[0, "task_id"] = other
            raw.to_csv(root / "telemetry_1min.csv", index=False)
            response = caught(lambda: len(load_data(root)["telemetry_1min"]))
        return int(mismatch) == 0 and response["exception"] is not None, {"source_mismatch_count": int(mismatch), "foreign_machine_task_injection": response}, "Loader checks task ID existence but not task-to-machine/operator/site consistency."
    case("FP-01", "Feature Pipeline", "Validate actual task linkage; inject existing task_id from another machine", "Correct source links and reject contradictory links", linkage, "ml/features/data.py", "load_data", "Join task metadata and reject non-null task_id rows whose machine_id/operator_id/site_id disagree; validate active task timing if required.")
    case("FP-02", "Feature Pipeline", "480 minutes, 120 idle, 7 harsh events; known summed energy and cycles", "Correct minute counts, percentage and sums", lambda: (bool((r := shift_features(clean).iloc[0]).observed_min == 480 and r.idle_pct == 25 and r.harsh_events_count == 7 and np.isclose(r.fuel_used_l, clean.fuel_used_l.sum())), r.to_dict(), "None"), "ml/features/build.py", "shift_features", "Compute aggregation from validated unique minute records with explicit units.")
    def duplicates():
        original = synthetic(n=60, idle=0.25)
        duplicated = pd.concat([original, original.iloc[[0]]], ignore_index=True)
        a = summarize_operators(original)[0]
        public = caught(lambda: summarize_operators(duplicated))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["tasks", "machines", "operators", "safety_alerts", "anomalies_ground_truth"]:
                shutil.copyfile(ROOT / "data" / f"{name}.csv", root / f"{name}.csv")
            raw = pd.read_csv(ROOT / "data/telemetry_1min.csv", nrows=2)
            pd.concat([raw, raw.iloc[[0]]]).to_csv(root / "telemetry_1min.csv", index=False)
            loader = caught(lambda: len(load_data(root)["telemetry_1min"]))
        passed = public["exception"] == "ValueError" or public.get("value") == [a]
        return passed, {"unique": a, "duplicated_public_analytics": public, "loader_duplicate_check": loader}, "None" if passed else "CSV loader rejects duplicates, but public telemetry analytics silently double-counts them."
    case("FP-03", "Feature Pipeline", "Append a duplicate machine/timestamp row; test CSV loader and public analytics", "Reject or deduplicate before aggregation", duplicates, "ml/features/build.py", "shift_features", "Reject duplicate (machine_id, recorded_at) keys inside the shared telemetry validation path used by public inference too.")
    def gaps():
        t = synthetic(n=60, idle=0.25).drop(index=list(range(5, 10)))
        r = summarize_operators(t)[0]
        machine = data["machines"].loc[data["machines"].machine_id == "EXC002"].iloc[0]
        energy = caught(lambda: history_features(t, machine))
        return r["observed_min"] == 55 and np.isclose(r["idle_pct"], 10 / 55 * 100) and energy["exception"] == "ValueError", {"analytics": r, "energy": energy}, "Analytics uses observed minutes; it does not report a coverage percentage for the missing window."
    case("FP-04", "Feature Pipeline", "Remove five idle minutes from a 60-minute history", "Observed-window aggregation or explicit rejection", gaps, "ml/features/build.py", "shift_features", "Expose coverage if full-shift estimates are needed; reject irregular windows for fixed-cadence forecasts.")
    def units():
        d = tel.loc[tel.powertrain == Powertrain.DIESEL]
        e = tel.loc[tel.powertrain == Powertrain.ELECTRIC]
        rate_error = float((d.fuel_used_l - d.fuel_rate_lph / 60).abs().max())
        good = d.energy_used_kwh.isna().all() and e.fuel_used_l.isna().all() and rate_error < 0.001
        return bool(good and energy_case(60, 12)["estimated_remaining_min"] == 300), {"diesel_kwh_null": bool(d.energy_used_kwh.isna().all()), "electric_litres_null": bool(e.fuel_used_l.isna().all()), "fuel_rate_to_minute_max_rounding_error_l": rate_error, "speed_field": "ground_speed_kmh", "idle_output": "0–100 pct", "time_case_min": 300}, "No speed conversion is performed; source and features both use km/h."
    case("FP-05", "Feature Pipeline", "Actual normalized diesel/electric telemetry plus known hourly-to-minute case", "Consistent litres/kWh, percentages, km/h and minutes", units, "ml/features/data.py", "load_data", "Keep explicit powertrain-aware units and validate conversions at ingestion.")
    def availability():
        raw = synthetic(n=180, idle=0.2)
        machine = data["machines"].loc[data["machines"].machine_id == "EXC002"].iloc[0]
        before = energy_examples(raw, pd.DataFrame([machine]))
        changed = raw.copy()
        changed.loc[60:, "fuel_used_l"] *= 3
        after = energy_examples(changed, pd.DataFrame([machine]))
        causal = before.iloc[0][ENERGY_FEATURES].equals(after.iloc[0][ENERGY_FEATURES])
        bad = {"actual_duration_min", "productive_min", "completed_quantity", "avg_temp_c", "rain_during_task_mm"} & set(TASK_FEATURES)
        return causal and not bad, {"energy_future_mutation_preserves_first_input": causal, "duration_outcome_features": sorted(bad), "duration_inputs": TASK_FEATURES}, "Anomaly scoring is retrospective after a shift; ground condition/prior rainfall must be measured before task prediction."
    case("FP-06", "Feature Pipeline", "Perturb future energy consumption; inspect duration input whitelist", "No future-derived inference inputs", availability, "ml/energy.py", "history_features", "Build every historical feature as of prediction time; exclude task outcomes and realized future weather.")

    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        trained, _ = train_duration(data["tasks"], data["operators"])
        trained["model_version"] = "acceptance-audit"
        request_frame = pd.DataFrame([TaskDurationInput(**base).model_dump(mode="json")])[TASK_FEATURES]
        prediction_before = float(trained["pipeline"].predict(request_frame)[0])
        target = temp / "duration.joblib"
        joblib.dump(trained, target)
        case("MP-01", "Model Persistence", "Actually train duration model, then joblib.dump to a temporary directory", "Nonempty model file generated", lambda: (target.exists() and target.stat().st_size > 0, {"bytes": target.stat().st_size, "model_version": trained["model_version"]}, "Original saved models were not overwritten."), "ml/training/train.py", "train_duration", "Persist the complete trained pipeline and version metadata with joblib.")
        input_file = temp / "input.json"
        input_file.write_text(json.dumps(TaskDurationInput(**base).model_dump(mode="json")))
        child_code = "import joblib,json,pandas as pd,sys; b=joblib.load(sys.argv[1]); x=pd.DataFrame([json.load(open(sys.argv[2]))]); print(json.dumps({'prediction':float(b['pipeline'].predict(x[b['features']])[0]),'steps':list(b['pipeline'].named_steps)}))"
        child = subprocess.run([sys.executable, "-c", child_code, str(target), str(input_file)], capture_output=True, text=True, check=False)
        child_output = json.loads(child.stdout) if child.returncode == 0 else {"stderr": child.stderr}
        case("MP-02", "Model Persistence", "Fresh Python subprocess loads saved model and predicts", "Prediction succeeds without retraining", lambda: (child.returncode == 0 and math.isfinite(child_output["prediction"]), {"exit_code": child.returncode, **child_output}, "Child process only called joblib.load and predict."), "ml/inference.py", "ModelService.__init__", "Package model artifacts and dependencies together; load the serialized pipeline on startup.")
        case("MP-03", "Model Persistence", "Compare newly fitted model output before save vs new-process reload", "Numerically equal predictions", lambda: (child.returncode == 0 and np.isclose(prediction_before, child_output["prediction"], atol=1e-9), {"before": prediction_before, "after": child_output.get("prediction")}, "None"), "ml/training/train.py", "train_duration", "Save preprocessing and estimator together and preserve exact feature order.")
        case("MP-04", "Model Persistence", "Inspect and use reloaded duration pipeline; inspect v1/v2 preprocessors", "Encoders/imputers/scalers and mappings persist", lambda: ("features" in joblib.load(target)["pipeline"].named_steps, {"duration_steps": list(joblib.load(target)["pipeline"].named_steps), "v1_anomaly_steps": list(basic.anomaly["pipeline"].named_steps), "v2_energy_steps": {k: list(v["pipeline"].named_steps) for k, v in advanced.energy["models"].items()}, "v2_fuel_rates_persisted": len(advanced.anomaly["rates"])}, "v2 fuel detector stores its learned class/state rate mapping alongside its forest."), "ml/training/train.py", "preprocessing", "Serialize learned transforms with the estimator instead of refitting them at inference.")

    # These tests intentionally distinguish actual local compositions from API
    # and dashboard integrations. A temporary dict is not a persisted task.
    api_exists = (ROOT / "api/main.py").exists()
    case("INT-01", "Integration", "Attempt to locate task-create service; exercise duration function directly", "Created task response includes estimated duration", lambda: (False, {"api_main_present": api_exists, "local_estimate_min": duration(), "create_task_callable": False}, "Task creation/persistence/API is absent; a local prediction is not a task response."), "api/services/tasks.py", "create_task (not implemented)", "Implement task creation orchestration that invokes ModelService.predict_task_duration and persists/returns the estimate; add an endpoint integration test.")
    case("INT-02", "Integration", "Request create-task→candidate evaluation; run local ranker as control", "Created task triggers ranked recommendation", lambda: (False, {"task_create_service_present": api_exists, "local_rank": [c.machine_id for c in rank([candidate()])]}, "No task service connects creation, model calls and candidate construction."), "api/services/tasks.py", "recommend_assignments (not implemented)", "Add a service that reads eligible operators/machines, computes duration/energy estimates, constructs candidates and calls rank_assignments.")
    case("INT-03", "Integration", "Local model calculation→matcher with 20 L vs 80 L for 240-min task", "Choose high-energy machine or return no eligible option", energy_consumed, "ml/inference.py", "rank_assignments", "Wire the already working local energy→matcher composition into task assignment; no API validation is claimed here.")
    def dashboard():
        r = advanced.detect_fuel_anomalies(synthetic(multiplier=2.5))
        return False, {"local_model_output": [x.model_dump(mode="json") for x in r], "api_present": api_exists, "web_present": (ROOT / "web").exists()}, "Serializable anomaly results exist, but no backend persistence/event route or admin dashboard consumes them."
    case("INT-04", "Integration", "Generate 2.5× fuel telemetry; call actual model; check backend/admin delivery", "Anomaly reaches backend/admin analytics", dashboard, "api/services/anomalies.py", "publish_anomaly (not implemented)", "Persist typed anomaly outputs, publish the agreed event and consume it in the admin UI; keep edge alerts separate.")
    def analytics_update():
        a = synthetic(n=60, idle=0)
        b = synthetic(n=60, idle=1)
        b.recorded_at += pd.Timedelta(minutes=60)
        before, after = summarize_operators(a), summarize_operators(pd.concat([a, b], ignore_index=True))
        return before[0]["idle_pct"] == 0 and after[0]["idle_pct"] == 50 and after[0]["observed_min"] == 120, {"before": before, "after": after}, "Local recalculation passes; no persistent/live backend analytics service is claimed."
    case("INT-05", "Integration", "Simulated working hour followed by idle hour for same operator", "New telemetry updates that operator's analytics", analytics_update, "ml/inference.py", "summarize_operators", "Invoke analytics from the backend on new data and persist/query the required period.")

    def end_to_end():
        literal = caught(lambda: TaskDurationInput(machine_class="truck", task_type="haul", quantity=400, unit="tonnes", ground_condition="wet", rain_prev_24h_mm=30, planned_duration_min=300, experience_years=10))
        # Supported-machine control exercises real predictions/calculations, but
        # is not silently substituted for the user's hauling requirement.
        eta = duration(quantity=400, planned_duration_min=300, ground_condition="wet", rain_prev_24h_mm=30, experience_years=10)
        h = synthetic(n=60, idle=0.12)
        context = dict(machine_id="EXC002", machine_class=MachineClass.EXCAVATOR, powertrain=Powertrain.DIESEL, remaining_task_min=eta, fuel_tank_l=345)
        low = advanced.predict_energy_runout(EnergyForecastInput(**context, fuel_remaining_l=345 * 0.15), h)
        h_b = tel.loc[tel.machine_id == "EXC003"].head(60)
        context_b = dict(context, machine_id="EXC003")
        high = advanced.predict_energy_runout(EnergyForecastInput(**context_b, fuel_remaining_l=345 * 0.80), h_b)
        candidates = [candidate(machine_id=mid, site_id=site, operator_id=oid, certifications={MachineClass.EXCAVATOR.value} if oid == "OP1002" else set(), estimated_duration_min=eta, estimated_remaining_min=energy.estimated_remaining_min) for mid, site, energy in [("EXC002", "S01", low), ("EXC003", "S02", high)] for oid in ["OP1002", "OP1003"]]
        ranking = rank(candidates)
        anomaly = fuel(2.5)
        analytics = summarize_operators(synthetic(multiplier=2.5))
        trace = {"literal_haul_truck_request": literal, "supported_excavator_control": {"eta_min": eta, "clear_eta_min": duration(quantity=400, planned_duration_min=300, experience_years=10), "low_energy": low.model_dump(mode="json"), "high_energy": high.model_dump(mode="json"), "candidate_sites": {"EXC002": "S01", "EXC003": "S02"}, "ranking_for_S01": [c.model_dump(mode="json") for c in ranking], "fuel_anomaly": anomaly, "analytics": analytics}, "hardcoded_predictions_used": False, "api_or_dashboard_exercised": False}
        DETAIL["end_to_end_trace"] = trace
        return False, trace, "Literal hauling/truck task unsupported; current-heavy-rain feature and task/API/dashboard orchestration absent. Real-fleet control has no eligible same-site replacement excavator, so the ranker correctly returns none."
    case("E2E-01", "End-to-End", "Haul 400 tonnes; heavy rain/wet; A certified/B uncertified; machine fuel15%/80%; abnormal fuel during shift", "Full requested workflow executes with real model/calculation outputs and recommends A+machine B", end_to_end, "shared/constants.py", "MachineClass", "First decide whether hauling/trucks are in scope; if so add class/task/unit support with training data. Then add a task orchestration service with point-in-time weather, inference, energy filtering, anomaly delivery and period-aware analytics. This needs several components, not a one-line fix.")

    order = {name: i for i, name in enumerate(["Anomaly Detection", "Task Time Estimator", "Energy Model", "Task Matcher", "Operator Analytics", "Feature Pipeline", "Model Persistence", "Integration", "End-to-End"])}
    ROWS.sort(key=lambda row: (order[row["module"]], row["test_id"]))
    summary = []
    for module in order:
        selected = [r for r in ROWS if r["module"] == module]
        counts = Counter(r["status"] for r in selected)
        summary.append({"module": module, "passed": counts["PASS"], "failed": counts["FAIL"], "status": "PASS" if not counts["FAIL"] else "FAIL"})
    assert len(ROWS) == 60, len(ROWS)
    assert len({r["test_id"] for r in ROWS}) == 60
    after_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifact_paths}
    report = {"created_at": datetime.now(UTC).isoformat(), "total": len(ROWS), "passed": sum(r["status"] == "PASS" for r in ROWS), "failed": sum(r["status"] == "FAIL" for r in ROWS), "readiness": "PARTIALLY READY", "summary": summary, "tests": ROWS, "details": DETAIL, "original_model_hashes": hashes, "original_models_unchanged": hashes == after_hashes,
              "methodology": ["60 requested acceptance cases, separate from the repository's regression suite.", "Omitted backend components are FAIL (not implemented), not silently skipped; local composition is labeled explicitly.", "General-anomaly fixtures use dozer class medians plus stated user values: dozer median fuel/cycle is 7.67 L, closest to the supplied normal 7.8 L. V2 fuel controls use an excavator normalized to its own class/state baseline.", "TT-01 uses a supported-machine control; the literal unsupported hauling scenario is failed in E2E-01.", "Anomaly ratios map to canonical percentages; EV percentages are normalized using an explicit 100-kWh capacity.", "Saved predictions and metrics are recomputed; original model artifacts are hashed before and after.", "Reused holdouts provide regression evidence, not a new independent validation sample."]}
    # Normalize NaN feature fixture values to JSON null for portable report UIs.
    raw = json.dumps(report, default=serial)
    normalized = json.loads(raw, parse_constant=lambda _: None)
    (OUT / "member3-acceptance.json").write_text(json.dumps(normalized, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"total": report["total"], "passed": report["passed"], "failed": report["failed"], "summary": summary, "original_models_unchanged": report["original_models_unchanged"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
