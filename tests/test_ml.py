from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from ml.features.build import TASK_FEATURES, shift_features, task_features
from ml.features.data import load_data, utc
from ml.inference import predict_energy_runout, rank_assignments
from ml.training.train import date_split, overlap_labels
from shared.constants import EV_CERTIFICATION, MachineClass, Powertrain, TaskStatus
from shared.schemas.prediction import AssignmentCandidate, EnergyInput


@pytest.fixture(scope="module")
def data():
    return load_data(Path(__file__).parents[1] / "data")


def test_normalization_and_label_exclusion(data):
    tel = data["telemetry_1min"]
    assert not {"anomaly_id", "anomaly_type", "energy_used", "timestamp"} & set(
        tel.columns
    )
    assert str(tel.recorded_at.dt.tz) == "UTC"
    diesel = tel.powertrain == Powertrain.DIESEL
    assert tel.loc[diesel, "energy_used_kwh"].isna().all()
    assert tel.loc[~diesel, "fuel_used_l"].isna().all()
    assert (
        str(utc(pd.Series(["2025-05-01 08:00:00"])).iloc[0])
        == "2025-05-01 02:30:00+00:00"
    )


def test_duration_has_no_outcome_features(data):
    rows = task_features(data["tasks"], data["operators"])
    assert (rows.task_status == TaskStatus.COMPLETED).all()
    assert not {
        "actual_duration_min",
        "productive_min",
        "completed_quantity",
        "avg_temp_c",
        "rain_during_task_mm",
    } & set(TASK_FEATURES)
    train, validation, test = date_split(rows.date)
    assert rows.date[train].max() < rows.date[validation].min()
    assert rows.date[validation].max() < rows.date[test].min()
    assert np.all(train.astype(int) + validation + test == 1)


def test_shift_features_do_not_change_with_labels(data):
    tel = data["telemetry_1min"].head(1500)
    original = shift_features(tel)
    changed = shift_features(tel.assign(anomaly_type="answer_key", anomaly_id="A9999"))
    pd.testing.assert_frame_equal(original, changed)


def test_overlap_excludes_different_machine_and_day():
    shifts = pd.DataFrame(
        [
            {
                "machine_id": "EXC001",
                "operator_id": "OP1001",
                "started_at": pd.Timestamp("2025-05-01T00:00:00Z"),
                "ended_at": pd.Timestamp("2025-05-01T08:00:00Z"),
            }
        ]
    )
    events = pd.DataFrame(
        [
            {
                "machine_id": "EXC002",
                "operator_id": "OP1001",
                "started_at": pd.Timestamp("2025-05-01T01:00:00Z"),
                "ended_at": pd.Timestamp("2025-05-01T02:00:00Z"),
            }
        ]
    )
    assert not overlap_labels(shifts, events)[0]


def test_energy_units_and_unknown_zero_rate():
    request = EnergyInput(
        powertrain=Powertrain.DIESEL,
        fuel_remaining_l=10,
        fuel_rate_lph=5,
        remaining_task_min=130,
    )
    result = predict_energy_runout(request)
    assert result.estimated_remaining_min == 120
    assert result.has_sufficient_energy is False
    request.fuel_rate_lph = 0
    assert predict_energy_runout(request).has_sufficient_energy is None
    with pytest.raises(ValidationError):
        EnergyInput(powertrain=Powertrain.ELECTRIC, power_kw=-5, remaining_task_min=1)
    with pytest.raises(ValueError):
        predict_energy_runout(
            EnergyInput(powertrain=Powertrain.ELECTRIC, remaining_task_min=10)
        )


def test_matcher_blocks_expired_missing_ev_and_insufficient_energy():
    cls = MachineClass.ELECTRIC_EXCAVATOR
    base = MachineClass.EXCAVATOR.value
    candidate = AssignmentCandidate(
        machine_id="EXC001",
        operator_id="OP1001",
        site_id="S01",
        machine_class=cls,
        certifications={base, EV_CERTIFICATION},
        certification_valid_until={
            base: date(2027, 1, 1),
            EV_CERTIFICATION: date(2027, 1, 1),
        },
        is_machine_available=True,
        is_operator_available=True,
        estimated_duration_min=60,
        estimated_remaining_min=120,
    )
    kwargs = {"site_id": "S01", "machine_class": cls, "on_date": date(2025, 5, 1)}
    assert rank_assignments([candidate], **kwargs) == [candidate]
    for update in [
        {"certifications": {base}},
        {"certification_valid_until": {}},
        {"is_machine_available": False},
        {"estimated_remaining_min": 30},
        {"site_id": "S02"},
    ]:
        assert rank_assignments([candidate.model_copy(update=update)], **kwargs) == []
