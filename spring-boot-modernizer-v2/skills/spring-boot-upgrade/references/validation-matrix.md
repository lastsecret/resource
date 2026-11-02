# Verification matrix

| Domain | Baseline evidence | Post-migration evidence | Result PASS/FAIL/NOT_TESTED |
|---|---|---|---|
| Compile/package | Maven log | Maven log | NOT_TESTED |
| Unit/integration tests | Surefire/Failsafe summary | Same tests/inputs | NOT_TESTED |
| HTTP API status and schema | Sample requests/responses | Structural diff | NOT_TESTED |
| Jackson date/time/null/enum | Golden test fixtures | Exact or approved delta | NOT_TESTED |
| Security endpoints/roles | allow/deny matrix | Same requests | NOT_TESTED |
| JPA/MyBatis data and transactions | Deterministic fixtures | Same queries/rollbacks | NOT_TESTED |
| Config/profiles/startup | config snapshot/startup trace | startup and smoke check | NOT_TESTED |
| Operational behavior | metrics/health/traces | same observability checks | NOT_TESTED |

Mark `PASS` only when evidence file paths and command/fixture are present. Verify expected version has actually changed. Different behavior requires explicit approval, never silent acceptance.
