"""Retrospective fuel anomaly models; safety alerts remain separate evidence."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.features.build import shift_features
from ml.training.train import metrics, overlap_labels
from shared.constants import (
    FUEL_BURN_MIN_RATIO,
    FUEL_FOREST_MIN_SCORE,
    FUEL_LOSS_MIN_DROP_PCT,
    FUEL_MIN_POWERED_SAMPLE_COUNT,
    SEED,
    AnomalyType,
    MachineState,
    Powertrain,
)


def fuel_features(telemetry: pd.DataFrame, rates: pd.Series) -> pd.DataFrame:
    rows = shift_features(telemetry)
    t = telemetry.sort_values(["machine_id", "recorded_at"]).copy()
    t["date"] = t.recorded_at.dt.strftime("%Y-%m-%d")
    expected = pd.MultiIndex.from_frame(t[["machine_class", "state"]]).map(rates)
    t["fuel_burn_ratio"] = t.fuel_rate_lph.to_numpy() / np.asarray(
        expected, dtype=float
    )
    eligible = (
        (t.powertrain == Powertrain.DIESEL)
        & t.is_power_on
        & (np.asarray(expected, dtype=float) > 0)
    )
    t.loc[~eligible, "fuel_burn_ratio"] = np.nan
    grouped = t.groupby(["machine_id", "operator_id", "date"], sort=False)
    ratios = grouped.fuel_burn_ratio.median().rename("fuel_burn_ratio")
    counts = grouped.fuel_burn_ratio.count().rename("powered_sample_count")
    # Compare only consecutive parked samples. Quantized level readings are 0.1%.
    previous = t.groupby("machine_id").shift(1)
    consecutive = (t.recorded_at - previous.recorded_at).dt.total_seconds().eq(60)
    parked = (t.state == MachineState.OFF) & (previous.state == MachineState.OFF)
    t["parked_fuel_drop_pct"] = (
        (previous.fuel_level_pct - t.fuel_level_pct)
        .clip(lower=0)
        .where(consecutive & parked, 0)
    )
    losses = t.groupby(["machine_id", "operator_id", "date"]).parked_fuel_drop_pct.max()
    return rows.merge(
        pd.concat([ratios, counts, losses], axis=1).reset_index(),
        on=["machine_id", "operator_id", "date"],
        validate="one_to_one",
    )


def best_cut(values: np.ndarray, truth: np.ndarray, floor: float) -> float:
    candidates = np.unique(
        np.r_[
            floor,
            values[values >= floor],
            np.nextafter(max(float(values.max()), floor), np.inf),
        ]
    )
    # Prefer the stricter threshold in a tie. No positives => conservative no-call.
    return float(
        max(candidates, key=lambda cut: (metrics(truth, values >= cut)["f1"], cut))
    )


def fit_fuel_model(
    train: pd.DataFrame, validation: pd.DataFrame, truth: pd.DataFrame
) -> dict:
    rates = (
        train.loc[(train.powertrain == Powertrain.DIESEL) & train.is_power_on]
        .groupby(["machine_class", "state"])
        .fuel_rate_lph.median()
    )
    features = fuel_features(train, rates)
    valid = features.fuel_burn_ratio.notna() & features.powered_sample_count.ge(
        FUEL_MIN_POWERED_SAMPLE_COUNT
    )
    model = IsolationForest(n_estimators=200, random_state=SEED, n_jobs=1)
    model.fit(features.loc[valid, ["fuel_burn_ratio"]])
    val = fuel_features(validation, rates)
    burn_truth = overlap_labels(
        val, truth.loc[truth.anomaly_type == AnomalyType.ABNORMAL_FUEL_BURN]
    )
    loss_truth = overlap_labels(
        val, truth.loc[truth.anomaly_type == AnomalyType.FUEL_LOSS]
    )
    # Model score gates are selected on validation only. High-rate direction avoids
    # treating unusually LOW consumption as abnormal fuel burn.
    burn_score = -model.score_samples(val[["fuel_burn_ratio"]].fillna(1))
    burn_score = np.where(
        val.fuel_burn_ratio.gt(FUEL_BURN_MIN_RATIO)
        & val.powered_sample_count.ge(FUEL_MIN_POWERED_SAMPLE_COUNT),
        burn_score,
        0,
    )
    return {
        "kind": "fuel_residual_v2",
        "rates": rates,
        "forest": model,
        "burn_threshold": best_cut(burn_score, burn_truth, FUEL_FOREST_MIN_SCORE),
        "loss_threshold_pct": best_cut(
            val.parked_fuel_drop_pct.to_numpy(), loss_truth, FUEL_LOSS_MIN_DROP_PCT
        ),
        "min_powered_sample_count": FUEL_MIN_POWERED_SAMPLE_COUNT,
        "min_burn_ratio": FUEL_BURN_MIN_RATIO,
    }


def predict_fuel(bundle: dict, telemetry: pd.DataFrame) -> pd.DataFrame:
    frame = fuel_features(telemetry, bundle["rates"])
    score = -bundle["forest"].score_samples(frame[["fuel_burn_ratio"]].fillna(1))
    frame["burn_score"] = np.where(
        frame.fuel_burn_ratio.gt(bundle["min_burn_ratio"])
        & frame.powered_sample_count.ge(bundle["min_powered_sample_count"]),
        score,
        0,
    )
    frame["is_abnormal_fuel_burn"] = frame.burn_score >= bundle["burn_threshold"]
    frame["is_fuel_loss"] = frame.parked_fuel_drop_pct >= bundle["loss_threshold_pct"]
    frame["is_anomaly"] = frame.is_abnormal_fuel_burn | frame.is_fuel_loss
    return frame


def evaluate_fuel(
    bundle: dict, telemetry: pd.DataFrame, truth: pd.DataFrame, alerts: pd.DataFrame
) -> dict:
    frame = predict_fuel(bundle, telemetry)
    actual = overlap_labels(frame, truth)
    baseline = overlap_labels(frame, alerts)
    predicted = frame.is_anomaly.to_numpy()
    typed = {}
    for kind, column in [
        (AnomalyType.ABNORMAL_FUEL_BURN, "is_abnormal_fuel_burn"),
        (AnomalyType.FUEL_LOSS, "is_fuel_loss"),
    ]:
        typed[kind.value] = metrics(
            overlap_labels(frame, truth.loc[truth.anomaly_type == kind]),
            frame[column].to_numpy(),
        )
    return {
        "grain": "machine_operator_day",
        "rules": metrics(actual, baseline),
        "fuel_model_only": metrics(actual, predicted),
        "rules_plus_fuel_model": metrics(actual, baseline | predicted),
        "typed_fuel_model": typed,
        "limitation": "Combined review flags are the union of rule alerts and ML fuel anomalies. Safety alerts are not relabeled as ML detections. Type metrics require the matching fuel type; no credit from unrelated safety alerts.",
    }
