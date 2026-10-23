# P2: planner tracks more than the specified 25,000 states

Independent QA source/evidence review on candidate `v5.0-candidate-1faeb1daaf8b07e6` found an exact resource-bound mismatch. `docs/v5-build-plan.md` specifies a maximum 25,000 abstract states. The frozen `generated.py` checks `len(seen)>25000` only at the queue loop head (line 382), while line 411 inserts each unseen successor without checking capacity first. One expansion can therefore register more than 25,000 states before the next guard.

The existing actual Owner E1 `run1/e1.json` LIMIT-03 records 25,005 states and `PROOF_UNKNOWN`, with the deadline explicitly disabled. QA did not rerun this experiment while reviewing it. Its original 40-source before/after map is equal; current generated-domain bytes match that recorded hash. Four other current backend files differ from the historical experiment epoch, so the entire 40-source bundle is not represented as current.

The guard still rejects the level as unproved and unplayable. There is no observed admission bypass or unbounded search. This is a P2 precision defect in the configured resource maximum, requiring a capacity check immediately before registering a new unseen state.

Main authorized Backend's narrow fix. Independent follow-up will use the original frozen LIMIT-03 input, disable only the deadline, observe the actual `seen` count at `PROOF_UNKNOWN`, and require exactly 25,000. The changed solver also requires fresh nine domain witness replays and the twenty frozen bad admissions; the nine already completed HTTP routes and unrelated E1 limits are not repeated. Existing executions remain historical and unchanged.
