# A/B/C controlled experiment (NOT_RUN)

Purpose: measure marginal benefit of the pack and router relative to the official Claude Code Modernization workflow. This is a manual agent-execution protocol plus machine-readable scoring; it does not launch Claude or pretend to capture telemetry automatically.

- Use identical clean disposable snapshots (fresh worktree per run), same model/version, plugin version, target Boot/Java, repository access, prompt revision, token/time budget, test suite, and operator approval rules. Do not expose the oracle to any agent. Randomize arm order; use at least 3 runs per arm (more for useful variance). No shared agent sessions or previous outputs; retain isolated logs locally.
- A: native official Modernization plugin only. B: same plugin + Knowledge Pack, no scanner output or router. C: same plugin + Knowledge Pack + resolver + Decision Router + local batches/ledger. Record scanner preparation time/tokens separately and include in total cost. In each arm ask for preservation of source behavior and Java target, candidate plan, then approved fixes and regression. Do not permit test expectation changes just to pass.
- After execution, independent reviewer assigns stable change IDs (required or not required) using actual version evidence and behavior tests. Do not use the lab's candidate-location oracle as a ground truth for required edits. Amendments to the oracle must be adjudicated consistently across arms before scoring; mark unadjudicated proposals rather than counting them false or true. A target plan is not a migrated application; use a real source baseline and runnable target for regression.
- Record input/output tokens from actual tool logs if available, wall time including preparation, human interventions, applied/proposed change IDs (use same definition across arms), regression passed/total and evidence complete/total. Missing data is null, not zero. The score tool reports medians and sample sizes; it does not perform significance testing, authenticate logs, or prove a causal improvement.

```sh
python3 tools/benchmark.py --oracle benchmarks/reviewed-oracle.json --observations benchmarks/observations.json --output /approved/benchmark-results.json
```

Copy templates and replace example placeholders with independently reviewed real data. `oracle-template.json` and `observations-template.json` are intentionally incomplete and must not be used as benchmark results. No agent experiment has been executed in the authoring environment.
