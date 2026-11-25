# v0.13 — Hybrid Migration Intelligence

The Scanner finds and scopes candidates. The Router directs work. Agents make evidence-based proposals. Runtime tests independently measure behavior. Human approval and Quality Gate remain separate. No full static DI/call graph is planned in this version.

## Routing contract

| Route | Decision | Meaning |
|---|---|---|
| DETERMINISTIC | NOT_APPLICABLE | Local paired graph establishes exclusion for the captured scope only. |
| DETERMINISTIC | BLOCK | Captured runtime/compile OSS jOOQ requires Java 21 but target is Java 17. |
| EVIDENCE | REVIEW_REQUIRED | Missing graph/scope/candidate evidence, or negative static search. |
| AGENT | AGENT_ANALYSIS_REQUIRED | Complex provenance, semantics, settings or remediation analysis. |
| RUNTIME | VALIDATION_REQUIRED | Validation-only risk; no patch proposed by this rule. |

No automatic CHANGE_NEEDED or NO_CHANGE conclusion from a static candidate. Exact direct API comparison still lacks complete ABI/signature/target compile proof. A no-hit result is not compatibility. For scope-level exclusions, effective reactor and profile activation remain unverified. Inactive jOOQ declarations are excluded only within local captured scope; this is not a claim about all possible profiles.

## Run

```sh
python3 tools/resolve_evidence.py --project /approved/source --target-project /approved/target --config examples/java17-to-boot413.json --output /approved/scan --execute-approved-build
python3 tools/agent_batch.py --queue /approved/scan/decision-routing.json --source /approved/source --target /approved/target --output /approved/batch --limit 8
```

`agent-batch.json` + `response-template.json` are local-only. In Claude Code load the standalone `agent-adapter/migration-analysis/SKILL.md` explicitly (install the skill before scanning, or copy it to an approved user-level skill location outside the project), point to the batch and ask for read-only analysis. This does not depend on an undocumented official plugin extension point. Do not assume the official Code Modernization plugin automatically invokes it. Then import a response:

```sh
python3 tools/evidence_store.py --queue /approved/scan/decision-routing.json --source /approved/source --target /approved/target --response /approved/response.json --output /approved/ledger-01
python3 tools/agent_batch.py --queue /approved/scan/decision-routing.json --source /approved/source --target /approved/target --ledger /approved/ledger-01/evidence-ledger.json --output /approved/batch-02
# For subsequent imports add --previous /approved/ledger-01/evidence-ledger.json and choose a new output.
```

A ledger is append-only by CLI convention (not a tamper-proof or authenticated audit service). The run ID binds discovered bounded file fingerprints, catalog hash, graph metadata and scan evaluations; task IDs bind rule/module/run. Queue/task checksums detect accidental changes; trusted local files and operator review are still required. References must exist in bounded discovered source/target files and have valid line numbers. Checksums do not establish correctness or provenance. `remaining_tasks` means *unanswered*, `pending_review_task_ids` means submitted but not independently verified; `unresolved_task_ids` retains all tasks. Agent assertions are never automatically approved. A new scan is needed after source/target changes. The target-plan lab contains POMs only; no target runtime claims are possible.

## Runtime

```sh
python3 tools/run_jackson_fixture.py --execute-approved-build --output /approved/jackson-probe
```

Runs bundled synthetic fixtures in a disposable copy, offline by default. `--online` requires approved repositories; Maven can execute build code and offline is not a sandbox. Report stores comparisons rather than raw probe values. JDK 17 recommended, check actual toolchain and Maven versions. Standalone fixture versions are fixed references, not actual application dependency versions. Existing loopback HTTP fixture in `verification-fixtures/web-container` remains available. Actual application runtime evidence can be imported via `--runtime-source` / `--runtime-target`; it is unattested and cannot pass release gate.

See `benchmarks/README.md` for A/B/C protocol. Keep MyBatis implicit binding change out until exact versions and reproducer are confirmed. Do not increase rule count to mask coverage gaps.
