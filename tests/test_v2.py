from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

# Phase 4 tests - skip if ML dependencies not available
pytest.importorskip("xgboost")

from ml.anomaly import fit_fuel_model, fuel_features, predict_fuel
from ml.energy import ENERGY_FEATURES, energy_examples, fit_energy, history_features
from ml.features.data import load_data
from ml.inference import AdvancedModelService
from shared.constants import MachineClass, MachineState, Powertrain
from shared.schemas.prediction import EnergyForecastInput


def energy_fixture():
    machine = pd.Series(
        {
            "machine_id": "EXC001",
            "machine_class": MachineClass.EXCAVATOR,
            "powertrain": Powertrain.DIESEL,
            "fuel_tank_l": 100.0,
            "battery_kwh": np.nan,
        }
    )
    telemetry = pd.DataFrame(
        {
            "machine_id": "EXC001",
            "recorded_at": pd.date_range(
                "2025-05-01T02:30:00Z", periods=180, freq="min"
            ),
            "state": MachineState.WORKING,
            "fuel_used_l": 0.1,
            "energy_used_kwh": np.nan,
        }
    )
    return telemetry, machine


def test_replay_target_and_past_only_features():
    telemetry, machine = energy_fixture()
    frame = energy_examples(telemetry, pd.DataFrame([machine]))
    assert frame.iloc[0].future_used_pct == pytest.approx(6)
    assert frame.iloc[0].drawdown_min == pytest.approx(50)
    changed = telemetry.copy()
    changed.loc[60:, "fuel_used_l"] *= 2
    after = energy_examples(changed, pd.DataFrame([machine]))
    pd.testing.assert_series_equal(
        frame.iloc[0][ENERGY_FEATURES], after.iloc[0][ENERGY_FEATURES]
    )
    assert after.iloc[0].future_used_pct == pytest.approx(12)
    assert after.iloc[0].drawdown_min == pytest.approx(25)


def test_replay_censors_without_inventing_empty_events():
    telemetry, machine = energy_fixture()
    telemetry["fuel_used_l"] = 0.001
    frame = energy_examples(telemetry, pd.DataFrame([machine]))
    assert frame.drawdown_min.isna().all()
    telemetry.loc[90, "state"] = MachineState.REFUELING
    stopped = energy_examples(telemetry, pd.DataFrame([machine]))
    assert len(stopped) == 1
    assert stopped.iloc[0].observed_at == telemetry.iloc[119].recorded_at


def test_history_rejects_gaps_short_windows_and_wrong_machine():
    telemetry, machine = energy_fixture()
    with pytest.raises(ValueError, match="60 consecutive"):
        history_features(telemetry.head(59), machine)
    with pytest.raises(ValueError, match="60 consecutive"):
        history_features(telemetry.iloc[:61].drop(index=20), machine)
    with pytest.raises(ValueError, match="requested machine"):
        history_features(telemetry.head(60).assign(machine_id="EXC002"), machine)


@pytest.fixture(scope="module")
def fuel_bundle_and_data():
    data = load_data(Path(__file__).parents[1] / "data")
    tel = data["telemetry_1min"]
    train = tel.loc[tel.recorded_at < pd.Timestamp("2025-05-19T00:00:00Z")]
    validation = tel.loc[tel.recorded_at >= pd.Timestamp("2025-05-19T00:00:00Z")]
    model = fit_fuel_model(train, validation, data["anomalies_ground_truth"])
    return model, data


def test_fuel_labels_never_affect_predictions(fuel_bundle_and_data):
    bundle, data = fuel_bundle_and_data
    tel = data["telemetry_1min"].head(4000)
    before = predict_fuel(bundle, tel)
    after = predict_fuel(
        bundle, tel.assign(anomaly_id="A9999", anomaly_type="answer_key")
    )
    pd.testing.assert_frame_equal(before, after)
    electric = predict_fuel(
        bundle,
        data["telemetry_1min"].loc[
            data["telemetry_1min"].powertrain == Powertrain.ELECTRIC
        ],
    )
    assert not electric.is_anomaly.any()


def test_parked_loss_ignores_overnight_level_changes(fuel_bundle_and_data):
    bundle, data = fuel_bundle_and_data
    tel = data["telemetry_1min"].head(2).copy()
    tel["state"] = MachineState.OFF
    tel["fuel_level_pct"] = [80.0, 60.0]
    tel.loc[tel.index[1], "recorded_at"] = tel.iloc[0].recorded_at + pd.Timedelta(
        days=1
    )
    result = fuel_features(tel, bundle["rates"])
    assert result.parked_fuel_drop_pct.max() == 0


def test_advanced_artifact_roundtrip_and_energy_bounds(tmp_path, fuel_bundle_and_data):
    anomaly, _ = fuel_bundle_and_data
    anomaly = dict(anomaly, model_version="test-v2")
    tel, machine = energy_fixture()
    rows = energy_examples(tel, pd.DataFrame([machine]))
    # Known constant-consumption fixture exercises fitting and serialization for
    # both separate powertrain estimators without depending on saved artifacts.
    train = pd.concat([rows] * 10, ignore_index=True)
    electric = train.assign(
        powertrain=Powertrain.ELECTRIC, machine_class=MachineClass.ELECTRIC_EXCAVATOR
    )
    both = pd.concat([train, electric], ignore_index=True)
    energy = fit_energy(both, both.copy())
    energy["model_version"] = "test-v2"
    joblib.dump(anomaly, tmp_path / "anomaly.joblib")
    joblib.dump(energy, tmp_path / "energy.joblib")
    service = AdvancedModelService(tmp_path)
    request = EnergyForecastInput(
        machine_id="EXC001",
        machine_class=MachineClass.EXCAVATOR,
        powertrain=Powertrain.DIESEL,
        fuel_tank_l=100,
        fuel_remaining_l=5,
        remaining_task_min=60,
    )
    result = service.predict_energy_runout(request, tel.head(60))
    assert result.estimated_remaining_min == pytest.approx(50, rel=0.01)
    assert result.has_sufficient_energy is False
    assert result.is_extrapolation is False
    assert (
        service.predict_energy_runout(
            request.model_copy(update={"fuel_remaining_l": 20}), tel.head(60)
        ).is_extrapolation
        is True
    )
    assert (
        service.predict_energy_runout(
            request.model_copy(update={"fuel_remaining_l": 0}), tel.head(60)
        ).estimated_remaining_min
        == 0
    )
    with pytest.raises(ValueError, match="capacity"):
        service.predict_energy_runout(
            request.model_copy(update={"fuel_remaining_l": 101}), tel.head(60)
        )
    assert service.detect_fuel_anomalies(pd.DataFrame()) == []
