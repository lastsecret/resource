# v0.11 — Evidence acquisition audit

## Scope and results
- Original v0.10 ZIP extracted without editing original. 100 knowledge rules unchanged; 135 migration cases remain NOT_RUN.
- Old same-project demo: 9 detected, 31 not detected, 57 unknown, 3 not evaluated. 56 unknown had UNKNOWN_COMPONENT_PAIR; one WEB-UNDERTOW-006 lost its location anchor despite Undertow hints.
- New same-project demo: 10 detected, 31 not detected, 56 unknown, 3 not evaluated. The one corrected candidate is not a confirmed behavior change.
- 165/165 tests passed (157 existing + 8 new). JDK AST actually ran. Paired-tree import and reevaluation were exercised using synthetic Hibernate dependency tree fixtures; mocked Maven acquisition is not actual Maven execution.
- Regressions checked: shared grouping, no capture without approval, missing Maven, partial capture, success-path reevaluation, output outside target, distinct worktrees, Undertow location anchor. Existing v0.10 safety and policy tests still pass.

## Residual limitations
- No Maven installed, no target worktree for original incomplete demonstration POM, no verified dependency graph. Thus the 56 actual unknowns cannot honestly be resolved in this environment. All share one missing graph acquisition group.
- Maven capture is only POSIX, offline, per module (-N), not full effective reactor resolution. Captured and imported graphs remain unattested and cannot prove absence or completeness. Maven can execute arbitrary build extensions; explicit approval and isolated trusted worktrees required. No sandbox supplied.
- Evidence acquisition is bounded to one pass and reevaluation, not a general autonomous loop for config, runtime or API evidence. Exact config metadata, API diff and graph diff rules remain NOT_EVALUATED. Spring effective profile/config, mapper provenance, behavioral evidence and Agent integration remain pending. No actual Spring Boot or Oracle integration run.
- Legacy scan-summary schema stays 0.10 for compatibility; resolver evidence report schema is 0.11.
