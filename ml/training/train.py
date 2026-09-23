"""Run with python -m ml.training.train. Configuration comes from environment."""

import hashlib
import importlib.metadata
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from ml.features.build import (
    SHIFT_FEATURES,
    TASK_CATEGORICAL,
    TASK_FEATURES,
    operator_analytics,
    shift_features,
    task_features,
)
from ml.features.data import load_data
from shared.constants import SEED


def date_split(dates: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique = sorted(dates.unique())
    if len(unique) < 5:
        raise ValueError("At least five distinct dates are required")
    first, second = int(len(unique) * 0.6), int(len(unique) * 0.8)
    return tuple(
        dates.isin(part).to_numpy()
        for part in [unique[:first], unique[first:second], unique[second:]]
    )


def preprocessing(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        (
                            "impute",
                            SimpleImputer(strategy="median", keep_empty_features=True),
                        ),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical,
            ),
        ]
    )


def metrics(truth: np.ndarray, predicted: np.ndarray) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, predicted, average="binary", zero_division=0
    )
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "positive_count": int(truth.sum()),
        "predicted_count": int(predicted.sum()),
        "sample_count": len(truth),
    }


def overlap_labels(shifts: pd.DataFrame, events: pd.DataFrame) -> np.ndarray:
    """A positive means any event overlaps the machine/operator shift window."""
    return np.array(
        [
            bool(
                (
                    (events.machine_id == row.machine_id)
                    & (events.operator_id == row.operator_id)
                    & (events.started_at <= row.ended_at)
                    & (events.ended_at >= row.started_at)
                ).any()
            )
            for row in shifts.itertuples()
        ]
    )


def train_duration(tasks: pd.DataFrame, operators: pd.DataFrame) -> tuple[dict, dict]:
    frame = task_features(tasks, operators)
    train, validation, test = date_split(frame.date)
    numeric = [name for name in TASK_FEATURES if name not in TASK_CATEGORICAL]
    candidates = []
    # Select on validation days only; held-out test days are never used to tune.
    for depth in [2, 3, 4]:
        pipeline = Pipeline(
            [
                ("features", preprocessing(numeric, TASK_CATEGORICAL)),
                (
                    "model",
                    XGBRegressor(
                        n_estimators=250,
                        max_depth=depth,
                        learning_rate=0.04,
                        objective="reg:squarederror",
                        random_state=SEED,
                        n_jobs=1,
                    ),
                ),
            ]
        )
        pipeline.fit(
            frame.loc[train, TASK_FEATURES], frame.loc[train, "actual_duration_min"]
        )
        error = mean_absolute_error(
            frame.loc[validation, "actual_duration_min"],
            pipeline.predict(frame.loc[validation, TASK_FEATURES]),
        )
        candidates.append((error, pipeline))
    error, pipeline = min(candidates, key=lambda item: item[0])
    predicted = np.maximum(1, pipeline.predict(frame.loc[test, TASK_FEATURES]))
    result = {
        "model_mae_min": float(
            mean_absolute_error(frame.loc[test, "actual_duration_min"], predicted)
        ),
        "baseline_mae_min": float(
            mean_absolute_error(
                frame.loc[test, "actual_duration_min"],
                frame.loc[test, "planned_duration_min"],
            )
        ),
        "validation_mae_min": float(error),
        "split": split_description(frame.date, (train, validation, test)),
    }
    return {"pipeline": pipeline, "features": TASK_FEATURES}, result


def split_description(dates: pd.Series, masks: tuple) -> dict:
    return {
        name: {
            "from": str(dates[mask].min()),
            "through": str(dates[mask].max()),
            "rows": int(mask.sum()),
        }
        for name, mask in zip(["train", "validation", "test"], masks)
    }


def train_anomaly(
    shifts: pd.DataFrame, ground_truth: pd.DataFrame, alerts: pd.DataFrame
) -> tuple[dict, dict]:
    train, validation, test = date_split(shifts.date)
    columns = SHIFT_FEATURES + ["machine_class"]
    pipeline = Pipeline(
        [
            ("features", preprocessing(SHIFT_FEATURES, ["machine_class"])),
            ("model", IsolationForest(n_estimators=300, random_state=SEED, n_jobs=1)),
        ]
    )
    pipeline.fit(shifts.loc[train, columns])
    # Ground truth participates only in calibration/evaluation, never model inputs.
    scores = -pipeline.score_samples(shifts[columns])
    truth = overlap_labels(shifts, ground_truth)
    choices = np.unique(
        np.append(scores[validation], np.nextafter(scores[validation].max(), np.inf))
    )
    threshold = max(
        choices,
        key=lambda cut: (
            metrics(truth[validation], scores[validation] >= cut)["f1"],
            cut,
        ),
    )
    predicted = scores >= threshold
    baseline = overlap_labels(shifts, alerts)
    per_type = {}
    for kind, events in ground_truth.groupby("anomaly_type"):
        mask = overlap_labels(shifts, events) & test
        per_type[kind] = {
            "positive_shift_count": int(mask.sum()),
            "model_shift_recall": float(predicted[mask].mean()) if mask.any() else None,
            "baseline_shift_recall": (
                float(baseline[mask].mean()) if mask.any() else None
            ),
        }
    report = {
        "evaluation_grain": "machine_operator_day_any_event_overlap",
        "model": metrics(truth[test], predicted[test]),
        "baseline": metrics(truth[test], baseline[test]),
        "threshold": float(threshold),
        "per_type": per_type,
        "split": split_description(shifts.date, (train, validation, test)),
        "limitation": "Shift-level overlap does not establish event localization or anomaly-type classification. Baseline overlap may come from an unrelated alert in the same shift.",
    }
    return {
        "pipeline": pipeline,
        "threshold": float(threshold),
        "features": columns,
    }, report


def main() -> None:
    root = Path(os.getenv("CAT_DATA_DIR", "data"))
    output = Path(os.getenv("CAT_MODEL_DIR", "ml/models/v1"))
    # Fail before training rather than overwrite a previously evaluated version.
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(
            f"Choose a new CAT_MODEL_DIR; {output} already contains a model version"
        )
    data = load_data(root)
    shifts = shift_features(data["telemetry_1min"])
    duration, duration_report = train_duration(data["tasks"], data["operators"])
    anomaly, anomaly_report = train_anomaly(
        shifts, data["anomalies_ground_truth"], data["safety_alerts"]
    )
    version = output.name
    output.mkdir(parents=True, exist_ok=True)
    for name, bundle in [("duration", duration), ("anomaly", anomaly)]:
        bundle["model_version"] = version
        joblib.dump(bundle, output / f"{name}.joblib")
    report = {
        "model_version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "data_rows": {name: len(frame) for name, frame in data.items()},
        "duration": duration_report,
        "anomaly": anomaly_report,
        "energy": {
            "method": "linear_consumption_baseline",
            "time_until_empty_mae_min": None,
            "limitation": "No verified empty events supplied; runout accuracy is not established.",
        },
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.glob("*.csv"))
        },
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in [
                "pandas",
                "numpy",
                "scikit-learn",
                "xgboost",
                "joblib",
                "pydantic",
            ]
        },
    }
    (output / "evaluation.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    operator_analytics(data["telemetry_1min"]).to_json(
        output / "operator_analytics.json", orient="records", indent=2
    )
    print(
        json.dumps(
            {
                "model_dir": str(output),
                "duration": duration_report,
                "anomaly": anomaly_report["model"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
