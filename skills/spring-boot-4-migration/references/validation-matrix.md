# Evidence-based validation gates

| Gate | Minimal evidence | Fail state |
|---|---|---|
| Inventory | Git status; Maven/Java; modules; effective dependency tree | BLOCKED if unresolved |
| Baseline | Pre-change test log and exit code | BLOCKED unless waived |
| Rewrite | dry-run patch, dependency/recipe resolution, diff review | BLOCKED if no reproducible preview |
| Compilation | Clean compile exit code | FAIL |
| Unit | Test reports, count and failures | FAIL |
| Integration | Executed integration tests or NOT_RUN | PARTIAL when NOT_RUN |
| Runtime | Startup evidence, health/readiness, env/profile | PARTIAL when NOT_RUN |
| Contracts | API, JSON, authentication, persistence scenarios | PARTIAL when NOT_RUN |
| Delivery | CI/container compatibility verification | PARTIAL when NOT_RUN |

PASS requires all applicable mandatory gates evidenced as passed. Report test omissions explicitly and never infer operational correctness from a green unit suite.
