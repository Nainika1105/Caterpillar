from pathlib import Path

import joblib
import pytest

# Phase 4 tests - skip if ML dependencies not available
pytest.importorskip("xgboost")

from ml.features.build import TASK_FEATURES, task_features
from ml.features.data import load_data
from ml.inference import ModelService, suggest_charger
from ml.training.train import train_duration
from shared.schemas.prediction import ChargeInput, ChargePoint, TaskDurationInput


def test_duration_training_serialization_and_prediction(tmp_path):
    data = load_data(Path(__file__).parents[1] / "data")
    bundle, report = train_duration(data["tasks"], data["operators"])
    bundle["model_version"] = "test"
    joblib.dump(bundle, tmp_path / "duration.joblib")
    joblib.dump({}, tmp_path / "anomaly.joblib")
    request = TaskDurationInput.model_validate(
        task_features(data["tasks"], data["operators"])[TASK_FEATURES].iloc[0].to_dict()
    )
    result = ModelService(tmp_path).predict_task_duration(request)
    assert result.estimated_duration_min > 0
    assert result.model_version == "test"
    assert report["model_mae_min"] >= 0


def test_charger_respects_machine_limit_and_compatibility():
    request = ChargeInput(
        site_id="S01",
        battery_capacity_kwh=100,
        energy_remaining_kwh=20,
        target_soc_pct=80,
        max_charge_kw=50,
        charging_efficiency_pct=100,
    )
    point = ChargePoint(
        energy_point_id="S01-DC1",
        site_id="S01",
        power_kw=100,
        is_available=True,
        is_compatible=True,
    )
    result = suggest_charger(request, [point])
    assert result.estimated_charge_min == pytest.approx(72)
    assert result.energy_required_kwh == 60
    assert (
        suggest_charger(request, [point.model_copy(update={"is_compatible": False})])
        is None
    )
    assert (
        suggest_charger(request, [point.model_copy(update={"is_available": False})])
        is None
    )
