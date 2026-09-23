# Caterpillar

Smart Operator Assistant for CAT Machinery.

The Member 3 implementation lives in `ml/`, with shared prediction contracts in
`shared/`. See [setup, training and backend handoff](docs/member3.md).

Anomaly and energy improvements are described in [Member 3 v2](docs/member3-v2.md).
Run the saved v2 models with `.venv/bin/python -m ml.demo_v2`.

For backend handoff, see the [Member 3 callable interface](docs/member3-integration.md).

Quick start after installing Python 3.11 dependencies:

```sh
.venv/bin/python -m ml.training.train
.venv/bin/pytest -q
```
