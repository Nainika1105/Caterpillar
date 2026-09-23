"""Fit v2 on development dates, or evaluate frozen artifacts on a fresh dataset."""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import joblib

from ml.anomaly import evaluate_fuel, fit_fuel_model
from ml.energy import energy_examples, evaluate_energy, fit_energy
from ml.features.data import load_data


def fingerprint(root: Path) -> dict:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.glob("*.csv"))
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fit", "evaluate"])
    args = parser.parse_args()
    root = Path(os.getenv("CAT_DATA_DIR", "data"))
    output = Path(os.getenv("CAT_MODEL_DIR", "ml/models/v2"))
    data = load_data(root)
    tel = data["telemetry_1min"]
    days = tel.recorded_at.dt.strftime("%Y-%m-%d")
    examples = energy_examples(tel, data["machines"])
    if args.mode == "fit":
        if output.exists() and any(output.iterdir()):
            raise FileExistsError(
                "Set CAT_MODEL_DIR to a new version; existing artifacts are immutable"
            )
        unique = sorted(days.unique())
        if len(unique) < 10:
            raise ValueError("At least ten development dates required")
        cutoff = unique[int(len(unique) * 0.6)]
        train, validation = tel.loc[days < cutoff], tel.loc[days >= cutoff]
        anomaly = fit_fuel_model(train, validation, data["anomalies_ground_truth"])
        energy = fit_energy(
            examples.loc[examples.date < cutoff], examples.loc[examples.date >= cutoff]
        )
        report = {
            "purpose": "development_validation_not_final_test",
            "train_through": unique[int(len(unique) * 0.6) - 1],
            "validation_from": cutoff,
            "anomaly": evaluate_fuel(
                anomaly,
                validation,
                data["anomalies_ground_truth"],
                data["safety_alerts"],
            ),
            "energy": evaluate_energy(energy, examples.loc[examples.date >= cutoff]),
            "source_sha256": fingerprint(root),
            "development_through": max(unique),
        }
        output.mkdir(parents=True)
        for name, bundle in [("anomaly", anomaly), ("energy", energy)]:
            bundle["model_version"] = output.name
            joblib.dump(bundle, output / f"{name}.joblib")
        # Duration v1 is unchanged; v2 is explicitly an anomaly/energy bundle.
        filename = "validation.json"
    else:
        training = json.loads((output / "validation.json").read_text())
        if min(days) <= training["development_through"]:
            raise ValueError(
                "Final evaluation must use dates strictly after development"
            )
        if (output / "evaluation.json").exists():
            raise FileExistsError(
                "Final evaluation already exists; do not overwrite test results"
            )
        anomaly = joblib.load(output / "anomaly.joblib")
        energy = joblib.load(output / "energy.joblib")
        report = {
            "purpose": "fresh_generated_holdout",
            "from": min(days),
            "through": max(days),
            "anomaly": evaluate_fuel(
                anomaly, tel, data["anomalies_ground_truth"], data["safety_alerts"]
            ),
            "energy": evaluate_energy(energy, examples),
            "source_sha256": fingerprint(root),
            "artifact_sha256": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in ["anomaly.joblib", "energy.joblib"]
            },
        }
        filename = "evaluation.json"
    report["created_at"] = datetime.now(UTC).isoformat()
    (output / filename).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "anomaly": report["anomaly"],
                "energy": report["energy"],
                "report": str(output / filename),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
