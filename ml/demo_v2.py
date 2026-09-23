"""Exercise the saved v2 anomaly and energy inference locally."""

import json
import os
from pathlib import Path

from ml.features.data import load_data
from ml.inference import AdvancedModelService
from shared.constants import Powertrain
from shared.schemas.prediction import EnergyForecastInput


def main() -> None:
    data = load_data(Path(os.getenv("CAT_DATA_DIR", "data")))
    models = AdvancedModelService()
    anomalies = models.detect_fuel_anomalies(data["telemetry_1min"])
    examples = []
    for powertrain in Powertrain:
        machine = (
            data["machines"].loc[data["machines"].powertrain == powertrain].iloc[0]
        )
        history = (
            data["telemetry_1min"]
            .loc[data["telemetry_1min"].machine_id == machine.machine_id]
            .head(60)
        )
        diesel = powertrain == Powertrain.DIESEL
        request = EnergyForecastInput(
            machine_id=machine.machine_id,
            machine_class=machine.machine_class,
            powertrain=powertrain,
            remaining_task_min=60,
            fuel_tank_l=float(machine.fuel_tank_l) if diesel else None,
            battery_kwh=float(machine.battery_kwh) if not diesel else None,
            fuel_remaining_l=float(machine.fuel_tank_l * 0.05) if diesel else None,
            energy_remaining_kwh=(
                float(machine.battery_kwh * 0.05) if not diesel else None
            ),
        )
        examples.append(
            {
                "powertrain": powertrain.value,
                "replay_budget_pct": 5,
                "prediction": models.predict_energy_runout(request, history).model_dump(
                    mode="json"
                ),
            }
        )
    print(
        json.dumps(
            {
                "model_version": models.energy["model_version"],
                "flagged_fuel_shift_count": sum(
                    bool(row.anomaly_types) for row in anomalies
                ),
                "first_fuel_anomalies": [
                    row.model_dump(mode="json")
                    for row in anomalies
                    if row.anomaly_types
                ][:3],
                "energy_examples": examples,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
