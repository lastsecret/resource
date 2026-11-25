# Enterprise Modernization v0.13 — Hybrid Decision Routing

100 knowledge rules and 135 unexecuted migration acceptance cases preserved. Read [HYBRID-WORKFLOW.md](HYBRID-WORKFLOW.md) first. The recommended entry point remains `tools/resolve_evidence.py`. New `decision-routing.json` / `agent-queue.json` route rule/module tasks; `tools/agent_batch.py` prepares bounded local batches; `tools/evidence_store.py` validates and stores proposals pending independent review. No automatic edit, no release approval. `tools/run_jackson_fixture.py` provides approved synthetic fixture execution; `tools/benchmark.py` scores manually executed A/B/C comparisons. Actual official plugin and runtime tests remain NOT_RUN. Historical notes below are retained for reference; this version takes precedence.

---

# Enterprise Modernization v0.12 — Feedback-driven semantic and evidence improvements

Recommended entrypoint: `tools/resolve_evidence.py`. Preserves all 100 knowledge rules and 135 NOT_RUN migration acceptance cases. This release adds bounded scoped Maven capture attestation, per-detector warning coverage, high-priority semantic matching and one-hop Mapper factory hints, graph diff and local classpath metadata/direct API comparison, coverage-gap reporting, and a runtime observation import comparator. No automatic patch or migration approval.

```sh
python3 -m pip install -r requirements.txt
python3 tools/resolve_evidence.py --project /path/to/source --target-project /path/to/target --config examples/java17-to-boot413.json --output /path/to/new-report --execute-approved-build
python3 tools/summary_report.py --raw /path/to/new-report --output /path/to/new-feedback
```

`--execute-approved-build` executes trusted Maven builds offline per discovered POM. Only use disposable, reviewed workspaces: Maven can run extensions and code; offline is not a sandbox. Without the flag, scan read-only. `--source-profiles` and `--target-profiles` specify Maven profile flags (not Spring profiles). Capture attestation records successful local tree commands, module identities, unchanged build fingerprint, merge and matching tree hash. It is **not** full effective reactor/profile completeness. Imported dependency graphs remain unattested. `NOT_APPLICABLE` is a scoped applicability outcome only; no approval. `NOT_DETECTED` is absence of a candidate within the analyzed scope. Summary Report 2.0 exports allowlisted fields; review relative file paths and component coordinates before sharing.

Use `--source-tree` and `--target-tree` to import paired external graphs; for artifact comparisons, supply **both** `--classpath-manifest` and `--target-classpath-manifest` (trusted JSON map `module_dir -> platform pathsep-separated local jars`). With approved successful local capture, paired classpaths are read automatically. Metadata diff compares entries by key and reports locations of source-configured keys whose metadata changes; reports aggregate differences for metadata keys even if unset; does not infer runtime defaults or property removals solely from metadata. API diff compares direct public/protected classfile descriptors for referenced Spring Boot classes, not inherited APIs, reflection, multi-release dispatch, or complete JVM ABI. It compares the entire source/target jump, not exclusively the 4.1 boundary. Missing artifacts / ambiguity / absent runtime evidence remain unresolved. Use `--runtime-source` and `--runtime-target` to optionally import externally executed observations; see `tools/runtime_evidence.py` for schema. It compares JSON observations and build fingerprints, does not attest test execution or approve migration.

See `audit/AUDIT-v0.12.md` for test counts, replay methodology and residual risks. The rest of this README is historical v0.11/v0.10 documentation; the above takes precedence where contradictory.

---

# Enterprise Modernization v0.11 — Evidence Resolution

Recommended entrypoint: `tools/resolve_evidence.py`. Preserves 100 rules and 135 NOT_RUN acceptance cases. v0.10 information below is historical; 165 tests passed in v0.11.

```sh
python3 tools/resolve_evidence.py --project /path/to/source --target-project /path/to/target --config examples/java17-to-boot413.json --output /path/to/new-report --execute-approved-build
```

The target must be a separately prepared worktree, not a guessed BOM. The explicit flag authorizes offline Maven execution in both trusted disposable worktrees. Maven may execute arbitrary build extensions; offline is not a sandbox. Omit the flag to perform read-only AST scanning and emit plans. `--source-profiles` and `--target-profiles` specify approved profile lists. On Windows, use reviewed export/merge plans and supply `--source-tree` and `--target-tree` instead. A supplied `--classpath-manifest` must be trusted. If both captures succeed, import paired graphs, attempt type attribution with source classpath and reevaluate once. Partial capture, missing Maven, missing target or approval prevent graph acquisition. No inference of absence, no auto patch, no compatibility approval. Exit 2 review, 3 block/error. Evidence report groups unresolved rule IDs by shared missing evidence; not all groups have automatic collectors. Effective configuration, exact API/metadata diff, runtime probes and official plugin integration remain unfinished. See `audit/AUDIT-v0.11.md`.

---

# Enterprise Modernization Knowledge Pack v0.10 — Deterministic First

Candidate-only migration analysis. Preserves all 100 v0.9 rules and 135 NOT_RUN migration acceptance cases. Adds execution strategies for all rules, 62 declaration-based candidate detectors (97/100 configured including 35 existing detectors), optional javac AST/attribution, Maven module-aware inventory capture/merge, and an Agent queue. **157 automated tests passed in the authoring environment; none proves a real Spring Boot migration succeeded.** See audit/AUDIT-v0.10.md.

## Quick start

Python 3.10+, approved PyYAML and jsonschema packages, optionally a trusted JDK 17+ (JDK 21 tested). No network required for default scanning.

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 -O tools/verify_policy.py
python3 tools/migration_scan.py --project examples/springboot3-undertow-demo --config examples/java17-to-boot413.json --output "$HOME/migration-report-v10" --java-ast
```

Choose a NEW external output directory. Exit 2 = REVIEW_REQUIRED; 3 = BLOCK or error. No auto patch. Without `--java-ast`, lexical detection is used. With `--attribute`, javac attempts attribution (implies AST); optionally use `--classpath-manifest` with the source module's trusted exported classpath. Incomplete attribution falls back to lexical candidates. JDK compiler front end does not generate application classes or run annotation processors. It does not implement complete call graph, mapper provenance, or exact receiver matching. 35 existing detectors retain their old lexical/legacy behavior. The source tree is not executed by the scanner.

## Module-aware Maven inventory

Run only in a trusted disposable worktree with approved Maven repositories, settings, plugins, extensions and profiles. **Maven can execute code; `-o` is not a security sandbox.** Default plan/merge do not execute Maven. Use one separate new export directory per source/target/profile. Maven plugin 3.8.1 is pinned (JSON support since 3.7.0). Official reference: https://maven.apache.org/plugins/maven-dependency-plugin/examples/tree-mojo.html and https://maven.apache.org/plugins/maven-dependency-plugin/build-classpath-mojo.html.

```sh
python3 tools/maven_inventory.py plan --project /approved/source --output /approved/source-exports --profiles prod
# Inspect plan.json; execute each reviewed tree_command and classpath_command in the worktree.
python3 tools/maven_inventory.py merge --project /approved/source --exports /approved/source-exports --output /approved/source-inventory
# Repeat for target.
python3 tools/migration_scan.py --project /approved/source --target-project /approved/target --source-tree /approved/source-inventory/tree.json --target-tree /approved/target-inventory/tree.json --config examples/java17-to-boot413.json --output /approved/report --attribute --classpath-manifest /approved/source-inventory/classpath.json
```

Optional explicitly approved POSIX execution (not real-Maven tested here; Windows use plan/manual/merge):

```sh
python3 tools/maven_inventory.py capture --project /approved/source --output /approved/source-exports --profiles prod --execute-approved-build
```

`-N` per module may require local reactor dependencies already installed. Missing artifacts, profile-specific modules, duplicate coordinates, changed GA, generated sources and unresolved parent properties remain review items. Declared POM module binding is not the effective Maven reactor. Imported graph and hashes are not execution attestation, even when actual Maven exited zero. No complete profile resolution, Gradle resolver or automatic runtime compatibility sign-off. Graph pair is matched by coordinates/module/scope/classifier; source locations bind to closest unambiguous declared POM. Unknown bindings are explicitly unverified. `legacy` is diagnostic-only; authoritative candidate locations are `evaluations` and `findings`.

## Outputs / extension points

- `detectors/execution-plans.yaml`: all 100 strategies; `match_any` OR semantics, not full rule applicability. Supported types: Java symbol, call, annotation, import, constructor; dependency artifact (declaration/import); config key; MyBatis XML element; file name. Add a plan without editing the scanner. The legacy registry supplies component version windows and previous detection modes. Exact symbols/values/usage must be confirmed separately. 3 rules remain NOT_EVALUATED: property metadata diff, removed Boot API diff and verified BOM graph diff.
- `scan-summary.json` and `summary.md`: selected rule evaluations, candidate locations, module binding, evidence mode, coverage, AST scan status. `NOT_DETECTED` does not imply absence of impact; `UNKNOWN`/`NOT_EVALUATED` remain unresolved. Component coverage outside selected route is pending inventory. No finding is CONFIRMED solely by this tool.
- `agent-queue.json`: review task per selected rule, knowledge file, evidence requirement, candidate locations, priority and explicit no-patch policy. `agent-adapter/migration-analysis/SKILL.md` is an optional standalone skill specification; no automatic installation/official plugin hook or actual Agent invocation has been tested. Read only relevant rules.
- `tools/recipe_guard.py`: pre-existing candidate patch review, not automatic authorization.
- `verification-fixtures/jackson/`: Jackson 2/3 standalone probe retained; `verification-fixtures/web-container/`: Boot 3.5.7 Undertow and Boot 4.1.3 Tomcat projects and loopback HTTP comparator. Actual Java dependencies/runtime tests NOT_RUN. HTTP harness tested against Python mocks, not Spring containers.
- `audit/AUDIT-v0.10.md`, `audit/re_audit_v10.py`, `audit/re-audit-v0.10.json`, `audit/test-results-v0.10.txt`: latest evidence and residuals. Older audits remain historical.

## Security and evidence boundary

No source edits, no automatic approval, Java target preservation policy unchanged. Run on a stable trusted isolated workspace. No sandbox, no concurrency/race guarantees. Raw file names, coordinates, logs and approved scalar settings can still be sensitive. Review before sharing. Source claims, 13 historical review-pending items, version-specific Oracle JDBC 23.26.x knowledge and actual runtime behavior are not made more complete by adding a detector. The 135 acceptance cases remain NOT_RUN. See EVIDENCE-POLICY.md and the latest audit. This README supersedes older descriptions of detector counts, module bindings and integration capabilities.
