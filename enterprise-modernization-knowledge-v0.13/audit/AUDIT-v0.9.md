# Enterprise Modernization v0.9 — Second Engineering Audit

Date: 2026-11-25. This is an independent second pass within the same assistant session, not a different model or external certification. Original v0.8 preserved.

## Release decision

- **GO**: local read-only candidate research and Agent-assisted review on a trusted copy, subject to output review.
- **NO-GO**: autonomous production migration, complete dependency/semantic analysis, or runtime compatibility sign-off.
- 72/72 Python unit tests; optimized-mode policy verification (`python -O`); 100 rule IDs, 135 migration acceptance scenarios (NOT_RUN). Original 46 tests retained, with expectations deliberately tightened for Java policy: config-only PASS is now REVIEW_REQUIRED. 26 additional tests.
- Re-executed original v0.8 reproduction script verbatim; 9 of its 10 checks no longer reproduce the old issue. A09 still reports true because it checks only `legacy.findings`; the new registry emits SB4-PACKAGE-002 in unified `findings`/`evaluations`, which is verified by the replacement A09 acceptance test. Do not report the original script as 10/10 passed.
- 12 additional independent probes: 9 PASS, 3 RESIDUAL. R09 initially exposed a Java-comment lexical false positive; corrected and re-tested. Final output is in `re-audit-results.json`.
- No actual Maven/Gradle resolution, OpenRewrite, Spring Boot app compile/start, JDK17 runtime, Oracle or full regression test performed. Environment has JDK21 but no Maven, Gradle or JDK17. Jackson fixture is supplied but NOT_RUN.

## Previous audit findings

| ID | Status | Evidence and remaining scope |
|---|---|---|
| A01 | corrected in tested cases | complete numeric Boot release versions; patch downgrade BLOCK |
| A02 | corrected in tested cases | SNAPSHOT/RC/incomplete version REVIEW; no prerelease opt-in implemented |
| A03 | corrected in published findings | unified scope-filtered results; legacy scan still collects hints internally before filtering; imported component transitions can legitimately select earlier rule families |
| A04 | corrected in tested cases | separate ObjectMapper/JsonMapper builder patterns, FQCN and multiline support; not type resolution |
| A05 | corrected in tested cases | bounded scalar allowlist, omit raw excerpts, redact arbitrary values; not universal secret prevention |
| A06 | improved | cross-file/profile Tomcat conflict candidates; not effective configuration resolver |
| A07 | fail-closed | ignores user boolean, graph file hashes/fingerprints only; no origin attestation and no PASS |
| A08 | corrected in tested cases | Dockerfile variants and several CI types; configurable CI/GitOps scanning remains incomplete |
| A09 | improved, new contract | registry emits per-rule status; 65 of 100 lack detectors, 35 are hints only |
| A10 | corrected in tested cases | links skipped, output path bounded, existing output blocked; no TOCTOU/hardlink race security guarantee; Windows junction handling not tested on Windows |

## Second audit residuals

| ID | Priority | Finding | Required next step |
|---|---|---|---|
| R10 | P1 | Module-aware graph matching is not module-to-file binding. A source file can receive a candidate because a dependency changes in a different module. Reproduced. | Actual module source roots, module-specific classpath and profile identity, bind each candidate location to the module and dependency path. Until then `location_module_binding=NOT_VERIFIED`. |
| R11 | P1 | 65/100 rules have no detector; 35 have lexical/declaration detection only. Reproduced. | Implement rule-specific semantic analyzers, typed configuration resolution and runtime adapters. Never interpret NOT_EVALUATED or NOT_DETECTED as compatible. |
| R12 | P0 production gate | Runtime proof absent: no actual Java17 build, Maven resolved tree, Oracle or OpenRewrite run. Reproduced as NOT_RUN. | Capture dependency provenance and exact BOM; run actual source/target application fixtures, JDK/bytecode checks, baseline/regression and approved patch gate. |

## Additional review caveats

- Snapshot hashes bind imported bytes and currently observed build files, not original Maven invocation or immutable source revision. Imported graph may be stale, incomplete, or manually crafted. Does not capture all settings, profiles, plugin dependencies, buildSrc or Git dirty-state. No trusted attestation mechanism implemented.
- Version engine supports numeric component boundaries with `.Final` suffix, not arbitrary Maven qualifiers/version ordering, classifiers/edition transformations or complete patch-specific behavior. Both Jackson generations can coexist; pairs are hints, not proof a mapper actually migrated. Existing Hikari exact 7.0.0 regression excluded when imported target is 7.0.2. Oracle 23.7→23.9 knowledge must not be extrapolated to 23.26; Boot 4.1.3 documentation reference indicates 23.26.4.0.0. Additional driver changes require targeted evidence; no generic breaking changes invented.
- Existing legacy YAML, Boot4.1 JSON and new component delta JSON remain separate source schemas; registry and catalog consistency checks added, but single canonical generator not complete. 13 legacy claims still require source review. New offline summaries cover only 7 new claims, not full source repository.
- Generic regex may match strings or similar identifiers, or miss factories/dynamic properties/overloads; Java comments now masked for generic detectors, not full lexical/AST parser. No Effective Configuration resolution, Spring runtime inspection, or semantic call graph. Old Boot4.0 Undertow→Tomcat defaults marked unknown for exact Boot4.1 target; no numeric worker/timeout conversion. Target properties need final container version and effective runtime verification.
- Output policy prevents tested common leaks and paths, not arbitrary secret encodings, metadata, malicious concurrent changes, archive attacks, or OS-level containment. Use stable trusted worktree, least privileges and output review. Recipe guard only annotates textual diff risks; always blocks automatic sign-off, cannot replace git review, recipe artifact/authorization validation or real tests.
- Actual Claude Code Modernization integration remains a documented adapter contract, not a verified official plugin execution path. No UI change.

## Added official-source-reviewed component deltas

Hibernate 7.1 LockOptions removals, 7.2 registry generic signatures, 7.3 @Columns removal / single result deduplication / schema actions without entities, 7.4 Oracle HQL current/local date, Jackson 3.1 NullNode fallback and Optional coercion. These are conditional candidates, not automatic fixes; see `deltas/component-deltas-v09.json` and `sources/` (locators and SHA-256 of original summaries). Review sources are version-line documentation, not frozen patch-specific copies. Test actual source/target versions.

## Recommended next release gates

1. Capture and verify source/target graphs per module/profile with exact BOM artifacts and tool invocation evidence; bind code locations. Real compile/Java17 runtime and bytecode verification.
2. Implement real executable fixtures: Spring-managed/manual Jackson, Undertow/Tomcat runtime/load, Hibernate + Oracle date/native query, security authorization matrix. Supplied standalone Jackson fixture requires actual build and testing.
3. Claim-level re-review the 13 remaining items, plus actual 4.1 target dependencies (Oracle JDBC 23.26, Security 7.1, MyBatis 4.1 and other components as applicable). No claimed change without source evidence; verification-only if no exact delta established.
4. Expand semantic detectors as measured by fixture results, then integrate Agent approval and verification with official Modernization. Only then consider automatic change approval.
