# Engineering audit — v0.10

## Scope and evidence

Base: v0.9 hardening ZIP, all 100 rule IDs and 135 acceptance cases retained. Reviewed the actual detector code, declarative plans, import and module binding, javac tree helper, Agent queue, fixtures, and security boundary. No second model was independently invoked. Tests run using the available JDK 21 and Python; javac helper also compiled with `--release 17` (not a Java 17 runtime test). Maven, Gradle, Oracle DB and Java 17 runtime were not available. All actual Spring Boot migration cases remain NOT_RUN.

- Original 72 tests: passed in the final suite.
- New 85 tests: passed, including 62 one-anchor synthetic cases, actual javac parse/attribution/fallback, module pair isolation, XML/YAML and secret sentinel tests, inventory command/merge contracts, HTTP loopback mock verification.
- 157 total, no failures. See test-results-v0.10.txt and policy-results-v0.10.txt.
- Separate audit replays: 7 PASS, 4 RESIDUAL (re-audit-v0.10.json). The residuals are intentionally not transformed into passing tests.

## Coverage

35 existing candidate detectors + 62 new declarative detector plans = 97 candidate-enabled rules, 3 with only planned precise diff strategy. All 100 have execution strategy. This is configuration coverage, not detection recall, exact semantic coverage or confirmed migration applicability. One anchor test per newly configured rule does not test all alternatives, all negatives, or real library versions. Existing legacy detectors are not all moved to AST. Every selected rule yields an evaluation and Agent review task. The 3 unavailable diff implementations stay NOT_EVALUATED on the full route.

## Important improvements and evidence

1. Candidate logic is configured by YAML `match_any` clauses using reusable types. Registry remains backward compatible. Imported dependencies can also trigger artifact hints if bound to unique declared module.
2. Real javac compiler tree extraction masks comments and strings by tree structure for declarative Java matchers; optional attribution provides evidence of compiler resolution only, not identity of a matching framework API. Fallback on partial attribution. No annotation processing or generation. JDK 21 run verified; explicit --release 17 compile verified. No Java17 runtime proof.
3. Source paths bind to closest unambiguous POM coordinates. Known nonmatching modules filtered when a matching component pair exists; unbound locations remain candidates with NOT_VERIFIED association. No claim of effective Maven reactor/profile identity. Legacy report retains unbound diagnostic hints. Per-module Maven plan/merge/capture contracts tested with fake trees and mocked process, not real Maven. Offline flag is not a sandbox.
4. Added Agent queue; official plugin integration still untested. No automatic edits; all outcomes remain review-required.
5. Second pass found a transitive-dependency trigger gap and UTF-16 DTD inspection gap; repaired and regression-tested. Output values remain restricted, but file names/paths and approved scalar settings may themselves be sensitive. No adversarial concurrent filesystem guarantees.
6. Boot Undertow/Tomcat fixture includes URL decoding, required parameter and body/health probes. HTTP harness tested with real loopback Python mocks only. Neither Boot project has been compiled or started here.

## Residual risks / priority

| Priority | Gap | Required next action |
|---|---|---|
| P0 | No actual source/target Maven resolution or runtime migration evidence | Run on approved Java17/21, real dependencies and module profiles; compare test results. Keep gate blocked. |
| P1 | Simple-name matcher still finds unrelated local methods even when javac attributes them; 35 existing detectors not all AST-based | Introduce exact owner/method signature and callsite constraints, symbol-attribution evidence per detector, migrate legacy patterns. |
| P1 | Declared module binding is not full Maven reactor/profile resolution; source set and scopes not fully bound | Resolve effective POM, active profiles, module path/GA changes, reactor-generated sources and test vs compile classpaths. |
| P1 | Precise API removals, metadata property removal/rename, verified graph diff engines not implemented | Add versioned JAR API and metadata comparison, tie to references, verified graph evidence. |
| P1 | Effective Spring configuration, actual mapper provenance and cross-file call graph unknown | Add runtime snapshot and semantic tracking. Preserve UNKNOWN rather than inventing defaults. |
| P1 | 13 prior source claims not re-reviewed; Oracle JDBC 23.26.x, further version deltas not covered by all existing scopes | Perform claim-level review; no unconditional fixes. |
| P1 | Security/Oracle/Hibernate integration cases not executable here; full offline source mirror and official Agent hookup absent | Add approved DB and security fixtures, evidence collector, tested official integration. |

Release recommendation: read-only candidate discovery and controlled Agent evaluation are suitable for pilot use. No unattended patching or compatibility sign-off. The policy deliberately remains fail-closed. No production deployment approval.
