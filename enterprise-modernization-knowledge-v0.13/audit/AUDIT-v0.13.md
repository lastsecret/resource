# v0.13 engineering re-audit

Scope: v0.12 source archives + actual user v0.12 feedback(3–5).zip (default/jOOQ/Hikari). Implemented a conservative hybrid router, structured agent batches, local evidence proposal ledger, safe report adapter, synthetic fixture execution and manual A/B/C scoring. The same author performed the re-audit; no independent model or real agent execution.

## Evidence and results

- 193 Scanner/Router tests passed (175 prior tests + 18 additions); one pre-existing Undertow default test updated from REVIEW_REQUIRED to VALIDATION_REQUIRED to check the new contract, with the original detection/location assertions retained. 7 report tests passed (6 prior + 1 ledger privacy). Total 200. `verify_policy.py` passes: 100 rules, 135 unexecuted migration acceptance cases, 100 execution plans. All 9 YAML rule files and all 44 source/target lab files are byte-identical to v0.12.
- Read actual three v0.12 feedback summaries, reconstructed partial focused dependency trees; unknown classifiers were left absent, root project versions are replay placeholders. These are flat imported replay data, NOT original full graphs, real classpaths or attestations. Real Maven unavailable; Java 21 available. No classpath artifact comparisons or Spring Boot runtime verified in this replay. The 54-case Oracle preserves all 48 v0.12 cases and adds 6 routing checks. Per replay: 47 MET, 0 GAP, 7 NOT_RUN. See re-audit-v0.13.json. The three captures' actual previous v0.12 Oracle results were 46/46/45 MET; cannot directly compare rates across different scope and oracle. Unknown counts in partial replay are not comparable to actual v0.12 Maven.
- CLI dry handoff using actual replay queue and untouched default response template: 2 proposals submitted for review, 2 different tasks in next batch, 107 unanswered tasks; no actual agent or evidence closure. Report exported counts only. No fixture source modifications or synthetic canary detected in checked reports.

## Re-audit checklist

| Check | Outcome | Evidence |
|---|---|---|
| Retire stale graph warnings only for paired captured scope, preserve blockers | PASS (synthetic local capture contract) | test_sync_keeps_blockers_and_scope, test_imported_no_exclusion |
| Hikari 7.0.2 scoped exclusion; no imported exclusion | PASS (contract) | test_attested_exclusion, original exact-version tests |
| No jOOQ in captured scope, no unnecessary candidate; transitive jOOQ can still block | PASS (contract) | test_inactive_jooq, test_jooq_active, test_transitive_jooq_no_declaration_still_blocks |
| Candidate lacking component version routes to evidence; no negative scan means NO_CHANGE | PASS | test_candidate_with_unknown_version_routes_to_evidence, test_negative_search_not_no_change |
| Agent / runtime routing; validation-only cannot produce patch | PASS | test_provenance_agent, test_runtime_validation_only, test_validation_only_reject_patch |
| Source mutation, path escape, unsupported result, duplicate submission, accidental task mutation | PASS for tested cases | test_stale_source, test_fake_result_and_escape, test_ledger_append_and_no_approval, test_queue_accidental_tamper |
| Batch/ledger response loop without automatic approval or repeated answered task | PASS (template-only) | CLI handoff + test_batch_excludes_already_submitted_but_not_resolved |
| No private note exported in feedback | PASS for tested case | test_ledger_counts_no_notes |
| A/B/C missing metrics and mixed model rejection | PASS for tested cases | test_benchmark_missing_metrics_and_unadjudicated |
| Maven unavailable prevents fixture runtime claims | PASS | test_no_maven_runtime_explicit_block |
| Actual v0.13 Maven capture and classpath diff | NOT_RUN | needs operator rerun |
| Official plugin hook, actual agents, real behavior and A/B/C comparison | NOT_RUN | standalone manual integration only |

## Residual issues / deliberate boundaries

1. Deterministic decisions restricted to scope exclusion and observed jOOQ JDK blocker. Exact positive CHANGE_NEEDED/NO_CHANGE needs stronger evidence than current API diff/mapper hints. No claim of automatic final modification decisions; agent proposals always remain pending review. No general DI, effective config or call graph engine. Negative static search still requires coverage review.
2. Requested Maven flags and discovered POM capture are not effective reactor/profile completeness. Absence applies only to captured scope; no global profile exclusion. Imported data cannot close graph warnings. The local capture conditions are not a security attestation against a malicious operator.
3. Metadata missing is explicitly METADATA_UNAVAILABLE_IN_TARGET_CLASSPATH, not removal. Changed defaults/replacement are hints, not proven effective values; source owner module and actual replacement require investigation. API diff compares total jump (not isolated 4.0→4.1), not full ABI.
4. Legacy mapper hints excluded from exported summary; raw legacy diagnostics remain local. No complete security certification. File paths and component coordinates remain visible and require review before sharing.
5. Ledger is local, append-only by convention; checksums prevent accidental mismatch, not forgery. Source fingerprint covers discoverable bounded files, not excluded files, environment, external configuration or runtime. Local analysis notes may contain sensitive information. No cryptographic authorization, no automatic patch, no actual evidence approval. The ledger tracks answered tasks separately from unresolved tasks.
6. Runtime runner exercises fixed synthetic Jackson fixtures only, not the actual application; Maven and JDK17 runtime unavailable here. Existing runtime observation comparator is unattested. No actual runtime collection for all rules. Benchmark requires real operator-run agent experiments and independent decision oracle; no claimed speed/token/precision improvement. Oracle v3 tests routing rather than actual business edit correctness.
7. The user-requested MyBatis implicit-parameter issue is held pending exact versions, no rule added. All previous knowledge coverage gaps, including Oracle JDBC 23.26, remain visible. No claim-level source review expansion in this release.
