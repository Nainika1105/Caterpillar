# Member 3 anomaly and energy improvements

Version 2 adds workload-adjusted fuel anomaly detection and learned energy consumption forecasting. Backend integration and the presentation remain outside this change. The duration estimator remains in v1.

## Run the saved models

From the repository root, run:

```sh
.venv/bin/python -m ml.demo_v2
.venv/bin/pytest -q
```

The v2 local artifacts are `ml/models/v2/anomaly.joblib` and `ml/models/v2/energy.joblib`. `validation.json` records development validation, and `evaluation.json` records the fresh holdout evaluation and model hashes. Model files and generated CSVs are ignored by Git. The source data and v1 artifacts were preserved.

## What changed in anomaly detection

The previous broad Isolation Forest mixed machine-class and workload differences with anomalies. V2 estimates each diesel machine class's typical fuel rate separately for each operating state, using medians learned only from training dates. It then computes a shift's median observed-to-expected fuel ratio and fits Isolation Forest to this normalized ratio. A high-consumption gate and at least 30 powered observations prevent low consumption or insufficient observations from being labeled abnormal fuel burn. Score thresholds are selected using development validation labels; no ground-truth fields enter the features or unsupervised fitting.

A separate calibrated parked-fuel-drop detector checks consecutive one-minute observations while a machine is off. This is a threshold detector, not Isolation Forest. Overnight gaps are excluded. The combined evaluation adds these fuel detections to the existing safety-rule review flags. It does not claim that the fuel model detects every safety anomaly, or rename safety alerts as ML anomalies.

Both model scores and type-specific decisions are available through `AdvancedModelService.detect_fuel_anomalies`. Unknown class/state baselines and electric machines do not produce abnormal diesel-fuel-burn detections. The model reports insufficient observations instead. This remains retrospective machine/operator/day detection, not precise event localization or an in-cab safety engine.

## What changed in energy estimation

Separate XGBoost models for diesel and electric powertrains forecast consumption over the next 60 minutes as a percentage of machine capacity. Features use the previous 60 minutes only: recent energy use, the last 15 minutes' use, working and idle percentages, current machine state, machine class and UTC time of day. Labels measure subsequent consumption, and all targets stay within a day. Targets crossing replenishment or a telemetry gap are excluded.

`AdvancedModelService.predict_energy_runout` accepts typed `EnergyForecastInput` plus normalized history for one machine. It requires 60 consecutive one-minute observations, positive capacity and valid remaining energy. It extrapolates the predicted hour's average consumption to the remaining budget. `is_extrapolation` explicitly identifies durations longer than the trained one-hour forecast horizon. Zero predicted consumption returns unknown remaining time for a non-empty machine, rather than infinity. Charger recommendations continue to use the existing function.

The original `predict_energy_runout` function is retained as the last-hour-rate baseline. Use the method on `AdvancedModelService` to call the learned model.

## Evaluation protocol

The existing May dataset was development data, because its original test results had already been inspected. Training used May 1–17 and calibration/model selection used May 19–30. After freezing the models, a fresh dataset was generated with seed 20260923, start June 1 and 60 calendar days. The generated holdout contains 324,540 telemetry records. It uses the same synthetic generator and machine fleet, so it measures temporal/random-seed generalization, not new-fleet or real-machine performance.

No threshold or model was adjusted after inspecting this holdout. The final evaluation contains 601 machine/operator/day summaries. Rules alone achieved precision 0.920, recall 0.898 and F1 0.909. Rules plus the fuel detectors achieved precision 0.922, recall 0.922 and F1 0.922.

For the specific `abnormal_fuel_burn` type, the model correctly detected 7 of 10 positive shifts, with no false-positive shifts of that type: precision 1.000 and recall 0.700. The parked-fuel-loss detector correctly detected 4 of 16 positive shifts: precision 1.000 and recall 0.250. These small denominators and remaining misses matter; this is an improvement, not perfect detection. Fuel-only outputs should complement, not replace, the safety rules.

Diesel one-hour consumption MAE was 0.511 percentage points of tank capacity, versus 1.207 for the last-hour baseline, across 7,500 examples. Electric MAE was 2.287 percentage points of battery capacity, versus 4.086, across 1,046 examples.

For timing evaluation, the replay asks how long it takes to consume a fixed 5% capacity budget. It integrates observed positive consumption until that budget is reached. Observation stops at refuel/recharge, a gap, shift end or 240 minutes. Reached cases with positive model and baseline rates are compared on identical samples. Diesel timing MAE was 23.74 minutes versus 42.01 across 6,706 comparable cases. Electric timing MAE was 4.48 minutes versus 14.06 across 1,012 comparable cases.

Of the forecast examples, 791 diesel and 33 electric replay cases were censored before budget consumption. An additional 3 reached diesel cases and 1 reached electric case lacked a positive prediction from one of the methods. The report includes these exclusions. Timing results apply to the reached subset and a 5% budget; they are not an unbiased estimate for all starting energy levels.

The dataset replenishes machines before empty, so no actual time-to-empty error can be established. Remaining-time predictions assume the next hour's average consumption continues, without refuelling or charging. Synthetic budget replay is the available validation proxy, not proof of real-world runout accuracy.

## Reproduce the experiment

Use the locked dependencies and the unchanged source dataset. Choose a fresh output directory:

```sh
CAT_MODEL_DIR=ml/models/v2-reproduction .venv/bin/python -m ml.training.improve fit
.venv/bin/python data/generate_dataset.py --seed 20260923 --start 2025-06-01 --days 60 --out data/generated/holdout_seed20260923
CAT_MODEL_DIR=ml/models/v2-reproduction CAT_DATA_DIR=data/generated/holdout_seed20260923 .venv/bin/python -m ml.training.improve evaluate
CAT_MODEL_DIR=ml/models/v2-reproduction .venv/bin/python -m ml.demo_v2
```

Model directories and final evaluation reports cannot be overwritten. Later model development must use validation data and a new untouched final holdout; re-running this seed can verify reproducibility but cannot provide a new independent test.

Tests cover past-only features, exact replay targets, replenishment censoring, missing-minute rejection, label exclusion, electric-machine behavior, overnight fuel-level changes, model serialization, capacity checks and forecast extrapolation. The full local suite also retains the v1 duration and assignment tests.
