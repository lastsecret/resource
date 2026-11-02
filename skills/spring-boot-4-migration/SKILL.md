---
name: spring-boot-4-migration
description: Safely assess and migrate Maven-based Spring Boot 3.5.x projects to Spring Boot 4.x using OpenRewrite, optional Java LSP, and evidence-based verification. Use for impact assessment, dry runs, staged migration, troubleshooting, and migration reports.
argument-hint: "[analyze|baseline|dryrun|apply|verify|report] [project-path]"
disable-model-invocation: false
---

# Spring Boot 4 Migration Skill

## Scope and contract
- Default: Maven, Java 21 (keep unchanged), Spring Boot 3.5.x -> approved Spring Boot 4.x patch.
- Never assume Java 25 is mandatory. Never blanket-upgrade dependencies to latest.release.
- Gradle projects: assessment only in this edition; report `UNSUPPORTED` for automated execution.
- Works without Java LSP, but report semantic analysis as degraded.
- Do not edit source until baseline, dependency assessment, dry-run, and explicit user approval of the proposed diff.
- Never run `git reset --hard`, `git clean -fd`, automatic commit/push, deployment, or destructive operations.
- Never claim migration success solely from compile or unit tests.
- Do not expose Maven settings credentials, tokens, secrets, or full environment dumps in reports.
- Do not mutate application source or application POM to install OpenRewrite; run it using fully qualified Maven plugin command.
- Ask for target Boot patch if unspecified; if not provided, assess and report only. Select rewrite plugin/recipe versions from approved artifacts in private repository, not guesses.

## Stages and gates
0. **Discover**: inspect repo, module topology, Maven/Java versions, Boot baseline, BOMs, repositories, build plugins and private dependencies. Capture git state; require clean worktree before apply. Use `scripts/migrate.ps1 -Stage analyze -ProjectPath ...`.
1. **Baseline**: `mvn -B -ntp test`, dependency tree, test inventory, critical integration scenario inventory. Baseline failure is BLOCKED unless explicitly waived and documented. `-Stage baseline`.
2. **Impact analysis**: read `references/impact-checklist.md` and the official migration guide for the selected target release. Map EVERY issue to: dependency or source location, proof, migration action, test, owner. Categorize `AUTO_REWRITE`, `AI_ASSIST`, `MANUAL`, `UNKNOWN`. Check private BOMs, internal starters, Spring Cloud, Security 7, Jackson 3, persistence, MyBatis, Actuator, observability and runtime.
3. **OpenRewrite preview**: require pinned approved `RewritePluginVersion` and `RewriteSpringVersion`. Run `-Stage dryrun`. Inspect `target/rewrite/rewrite.patch`, logs, module coverage, and recipe discovery if recipe not resolved. Record expected changes and risks. Do not interpret empty patch as proof of compatibility.
4. **Approval gate**: obtain explicit approval before `apply`. Require clean repo and baseline evidence. For large changes, divide by module or type and take checkpoints.
5. **Apply**: `-Stage apply`. Review git diff, compare intended vs actual transformations and record unresolved items. Never override unknown uncommitted edits.
6. **Compile & diagnose**: `-Stage verify`, then identify FIRST root compilation error (not cascading errors). If Java LSP tools are available use workspace diagnostics, go-to-definition, references, symbol search and type inspection. Cross-check with compiler output. LSP is advisory and must not be claimed to be automatically integrated by the script. Use `references/lsp-protocol.md`.
7. **Fix in small batches**: investigate upstream docs + actual resolved dependency versions. Write minimal change, add or update test, run focused tests then full test. Limit autonomous retries to 3 per issue, stop on unknown behavior or security-sensitive changes. Do not silently weaken tests, suppress errors, or disable security controls.
8. **Verify runtime**: unit tests, integration tests, application startup with approved test profile, API contract, JSON shape, authn/authz, DB transaction/migration, actuator/health, container/CI verification. Only report tests genuinely executed. Use `references/validation-matrix.md`.
9. **Report**: `-Stage report`; include actual evidence, before/after dependency and version snapshots, commands, failures, remaining risks and decision `PASS | PARTIAL | BLOCKED`.

## Invocation
Run the included PowerShell script (PowerShell 7 recommended):
```powershell
$skill = '.claude/skills/spring-boot-4-migration'
& "$skill/scripts/migrate.ps1" -Stage analyze -ProjectPath .
& "$skill/scripts/migrate.ps1" -Stage baseline -ProjectPath .
& "$skill/scripts/migrate.ps1" -Stage dryrun -ProjectPath . -RewritePluginVersion 'APPROVED_VERSION' -RewriteSpringVersion 'APPROVED_VERSION'
# ONLY after review and explicit approval:
& "$skill/scripts/migrate.ps1" -Stage apply -ProjectPath . -RewritePluginVersion 'APPROVED_VERSION' -RewriteSpringVersion 'APPROVED_VERSION'
& "$skill/scripts/migrate.ps1" -Stage verify -ProjectPath .
& "$skill/scripts/migrate.ps1" -Stage report -ProjectPath .
```
The CLI performs technical stages, NOT full impact analysis or real runtime validation. The agent must add the human-readable impact matrix and verification evidence. Use `-SettingsPath` for a company Maven settings file; do not store secrets in artifacts. `-Offline` is only valid when all plugins and dependencies are cached.

## Failing and stopping
- If baseline fails, do not pretend post-upgrade failures are new.
- If OpenRewrite plugin/recipe cannot resolve, mark BLOCKED (private artifact mirror issue); do not modify application POM as a workaround without approval.
- A recipe may include 3.5 migration internally. Do not add unconditional intermediate upgrading if source is already 3.5.x.
- If a dependency is incompatible or unknown, do not invent an upgrade version.
- If tests fail, diagnose and preserve evidence. Do not fabricate result summaries.
- A missing runtime test means `NOT_RUN`, never `PASS`.

## Reference sources
- https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- https://docs.openrewrite.org/recipes/java/spring/boot4/upgradespringboot_4_0-community-edition/
- https://docs.openrewrite.org/reference/rewrite-maven-plugin
- Compare patterns (not blindly importing instructions): dingdaoyi/spring-boot4-upgrade-agent, tainn03/spring-boot-java-upgrade-openrewrite, addozhang/spring-boot-migrator-skill.
