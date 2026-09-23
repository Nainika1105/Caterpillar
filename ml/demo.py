"""Local inference smoke demo using the installed version's saved models."""

import json
import os
from pathlib import Path

from ml.features.build import TASK_FEATURES, task_features
from ml.features.data import load_data
from ml.inference import ModelService, predict_energy_runout
from shared.constants import Powertrain
from shared.schemas.prediction import EnergyInput, TaskDurationInput


def main() -> None:
    data = load_data(Path(os.getenv("CAT_DATA_DIR", "data")))
    models = ModelService()
    tasks = task_features(data["tasks"], data["operators"])
    request = TaskDurationInput.model_validate(tasks[TASK_FEATURES].iloc[-1].to_dict())
    predictions = models.detect_anomalies(data["telemetry_1min"])
    print(
        json.dumps(
            {
                "duration": models.predict_task_duration(request).model_dump(
                    mode="json"
                ),
                "energy_example": predict_energy_runout(
                    EnergyInput(
                        powertrain=Powertrain.DIESEL,
                        fuel_remaining_l=20,
                        fuel_rate_lph=5,
                        remaining_task_min=180,
                    )
                ).model_dump(mode="json"),
                "scored_shift_count": len(predictions),
                "last_shift": predictions[-1].model_dump(mode="json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
