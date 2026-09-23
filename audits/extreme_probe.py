"""Exercise the same extreme fuel/cycle value across supported diesel classes."""

import pandas as pd

from ml.features.build import SHIFT_FEATURES, shift_features
from ml.features.data import load_data
from shared.constants import MachineClass


def probe(shifts, service):
    results = []
    for cls in [MachineClass.EXCAVATOR, MachineClass.MINI_EXCAVATOR, MachineClass.DOZER, MachineClass.WHEEL_LOADER, MachineClass.BACKHOE_LOADER]:
        values = shifts.loc[shifts.machine_class == cls, SHIFT_FEATURES].median().to_dict()
        values.update(machine_class=cls.value, idle_pct=12.0, harsh_events_count=1, fuel_per_load_cycle_l=99999)
        try:
            score = float(service.score_shift_features(pd.DataFrame([values]))[0])
            results.append({"machine_class": cls.value, "fuel_per_load_cycle_l": 99999, "score": score, "threshold": service.anomaly["threshold"], "anomaly": score >= service.anomaly["threshold"]})
        except ValueError as exc:
            results.append({"machine_class": cls.value, "fuel_per_load_cycle_l": 99999, "rejected": str(exc)})
    passed = all(row.get("anomaly") or row.get("rejected") for row in results)
    return passed, results, "None" if passed else "Extreme 99999 L/cycle is accepted as normal for some supported machine classes. Isolation Forest score saturation plus a global threshold is not input validation."


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = load_data(root / "data")
    from ml.inference import ModelService
    passed, actual, issue = probe(shift_features(data["telemetry_1min"]), ModelService(root / "ml/models/v1"))
    path = root / "audits/results/member3-acceptance.json"
    report = json.loads(path.read_text())
    row = next(row for row in report["tests"] if row["test_id"] == "AD-07")
    row.update(input="fuel_per_load_cycle_l=99999 across all five supported diesel machine classes; other fields are class medians, idle_pct=12 and harsh_events_count=1", actual=actual, status="PASS" if passed else "FAIL", issue=issue)
    if not passed:
        row["smallest_fix"] = "Validate physically impossible engineered fuel/cycle values or flag out-of-domain inputs before Isolation Forest scoring; add this cross-class regression test."
    for summary in report["summary"]:
        rows = [r for r in report["tests"] if r["module"] == summary["module"]]
        summary["passed"] = sum(r["status"] == "PASS" for r in rows)
        summary["failed"] = len(rows) - summary["passed"]
        summary["status"] = "PASS" if summary["failed"] == 0 else "FAIL"
    report["passed"] = sum(r["status"] == "PASS" for r in report["tests"])
    report["failed"] = report["total"] - report["passed"]
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"test_id": "AD-07", "passed": passed, "actual": actual, "issue": issue}, indent=2))
