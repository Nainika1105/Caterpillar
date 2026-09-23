# Shared terminology

Use **machine**, **machine_class**, **powertrain**, **operator**, **site**, **task**, and **load_cycle** as defined in the team conventions.

An **alert** is a real-time rule violation. An **anomaly** is a retrospectively flagged ML pattern. An **incident** is reported by a person. Energy means fuel or battery energy as appropriate to the powertrain.

Python enum values live in `shared/constants.py`. API fields use snake_case. Percentages use 0–100. Timestamps are UTC; conversion to IST belongs to display. IDs belong to the backend; inference never allocates them.

The prediction schemas are a proposed Member 3 contract for Member 2. Changes under `shared/` require the team's two-reviewer process before merging.
