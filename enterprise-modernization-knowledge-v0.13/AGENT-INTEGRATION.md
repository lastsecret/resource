# Agent hand-off contract (v0.9)

This is a local tool adapter contract, not a modification to the Claude Code official plugin. Verify the installed plugin's version and artifact locations before integration.

## Assessment
1. Collect exact source/target versions; obtain user approval for target Java changes. Keep source worktree read-only. Do not run Maven on untrusted code automatically.
2. Export dependency trees from approved disposable source/target worktrees and active profile sets. Use dependency-plugin JSON support (3.7.0+); verify installed artifact in private repository. For multi-module projects export each module separately and supply a JSON list of root objects (avoid overwriting reactor output). Record Maven/JDK versions, exit codes, profiles, commit/dirty state, repository policy and hashes separately. The importer does not attest this provenance.
3. Call `tools/migration_scan.py` (see README). Exit 2 means REVIEW_REQUIRED and reports can be consumed. Exit 3 means BLOCK or scan/input error; never interpret as success. There is no runtime compatibility PASS in v0.9.
4. Read `scan-summary.json`, `evaluations`, `findings`, `coverage`, `unrouted_component_rules_pending_inventory`, `preflight.issues`, and source rule content by ID. Findings are text hints. Do not treat them as confirmed breakage. Unimplemented detectors and unknown inventory remain unresolved. The tool's evidence gate is fail-closed, not an implementation of runtime sign-off.

## Uplift / pilot
Investigate only exact affected symbols, effective configuration (per module, profile, mapper, callsite), source and target behavior, official source evidence. Use local reviewed summaries and approved offline documents. Do not assume `application.properties` affects manually instantiated mappers. Do not assume Undertow thread counts map to Tomcat. Never patch merely because a package is present. `VALIDATION_ONLY` rules request tests, not edits. Unreviewed claim-level rules must stay in review. Reconcile candidate findings with actual final resolved classpath; verify Jackson 2/3 coexistence. Preserve user-selected Java and security policy.

Run only approved, available recipe artifacts in an isolated working tree; inspect transitive recipe list (including JDK upgrades), dry run, then run `python3 tools/recipe_guard.py path/to/git.diff`. This command never approves or applies any diff; the user must inspect full patch. Do not modify old baseline tests to force success. Retain before/after git hashes, dependency reports, test output and approvals outside the source tree. Do not send secrets, internal source or full unredacted artifacts to non-approved services.

## Verify
Compile and run on the actual target JDK; check runtime classpath and bytecode, verify baseline and target with the same cases, require authorized review of intentional deviations. A separate external approval/verification process is still required; this package cannot assert migration success. Attach evidence to official Modernization verification artifacts according to the installed plugin's contract, never overwrite them or mark them passed from static scan. CLI/UI can display evaluation status and link to local files. A production integration and session approval bridge are not implemented or tested.
