# v0.12 engineering implementation and re-audit

## Scope and evidence

- Base: v0.11 scanner bundled in the previous adversarial lab. All 100 rules, 135 migration acceptance cases and original 38 oracle cases retained. No unverified MyBatis parameter-binding rule added.
- Reopened all three user-provided feedback ZIPs. Replayed only their allowlisted focused dependencies per module as **unattested imports**, not complete trees. Root version placeholder is irrelevant to component matching. No original classpaths available. No new real Maven capture or actual Spring Boot migration executed here.
- 44 original source/target-plan files byte-identical to v0.11. Added ten oracle expectations. Static run: 32 MET, 14 NOT_RUN_NO_GRAPH, 2 NOT_RUN_PROFILE. All original four missed anchors are now located. Each of three partial replay scenarios: 45 MET, zero GAP, three skipped (profile/capture attestation). No original four failed; negative decoy/compat checks met. These are fixture expectations, not accuracy or migration success.
- 175 scanner tests passed (165 prior including one intentionally updated expectation for a resolved fake Security method, plus ten new), six report tests passed. Policy verifier passes 100 rules/135 cases. Real JDK 21 used for AST and tiny compiled JAR fixtures. No Maven, Oracle, or live Boot container testing in this environment.

## Prior issues addressed

| Item | Implementation | Remaining boundary |
|---|---|---|
| G04 bytes serialization | AST invocation and same-line digest sink hint | No full dataflow/contract proof |
| G06 NullNode | One-argument old/new node accessor with owner/import hint | Actual nullable receiver and version behavior require test |
| G07 factory bean | Bean return type, one-hop unique same-package/import factory candidate, explicit enable/disable hints | No arbitrary multi-hop DI/proxy/Profile/config resolution |
| G09 Security DSL | Zero-argument AST invocation; actual owner or import/variable hint | Partial attribution / indirect chains remain candidates |
| Fake/compat modules | Filter resolved known-family call owners, targeted Java AST and version scope; keep Boot-specific relocation candidates | Generic text and unresolved lexical rules still admit false positives/negatives |
| Maven attestation | Local successful capture + module identities + fingerprint + merge + tree hash | Requested Maven profiles, not effective reactor or effective Spring profiles; no independent trusted execution environment |
| Parser warning | Per-family/module warning scope; multi-document YAML advisory | Unsafe skipped files still cause conservative uncertainty |
| jOOQ | Suppress declaration-only review when locally captured target scope shows no jOOQ; retain incompatible version blocker | Edition, active profile and full runtime graph verification remain open |
| Knowledge gap | Bounded family version coverage warnings, including Oracle 23.26 | Not an exhaustive knowledge coverage audit; Oracle new rules not added |
| Metadata/API/Graph diff | Executable bounded comparisons on paired local classpaths/graphs; connected to rule records | Real paired Maven JARs not tested here, direct APIs only, metadata not effective config |
| Runtime | Externally executed JSON observation comparison with build-file fingerprints | No automatic runtime execution/attestation; target-plan has no migrated code |
| Summary/Oracle | schema 2.0, ten additional checks, preserved source fixture | Still synthetic and author-designed; not an independent model or complete behavioral oracle |

## Residual audit priorities

1. Real user-environment rerun of all three scenarios, particularly `CAPTURED_SCOPED`, Hikari normal `NOT_APPLICABLE`, actual paired classpath comparison and report output. Imported replay cannot establish those results. Missing Maven means this is a blocker to declaring release fully verified.
2. Whole-program semantic analysis: method owner/signature beyond targeted detectors, actual call graph, dependency injection and effective Mapper settings; source tests, generated classes, reflection and overloaded methods remain incomplete. Never treat NOT_DETECTED as compatibility.
3. Effective Maven reactor/profile activation and full dependency resolution; capture scope deliberately limited to discovered POMs, requested flags and stable build fingerprints. No Gradle/Windows auto capture.
4. Configuration Metadata is not runtime configuration. Full Boot property precedence, environment, external files, profile, customizer and container defaults remain unresolved. API diff only checks direct members of referenced Spring Boot classes, not complete ABI, inheritance or multi-release JAR dispatch; no definitive attribution to specific intermediate version.
5. Runtime regression fixtures require actual migrated target implementation; existing target-plan is dependencies only. Runtime observation import remains unattested and never opens migration gate. No independent model review, no real Oracle/DB or full OpenRewrite execution.
6. Prior 13 source-review-pending rules and wider Oracle 23.26 / other component knowledge coverage not resolved by engineering changes. MyBatis implicit parameter-binding deferred until exact versions confirmed.

## Gate

`BLOCKED_PENDING_VERIFIED_EVIDENCE`, `automatic_patch=false`. No new version compatibility claim. Review source/target build and test evidence before patching. See re-audit-v0.12.json and test logs.
