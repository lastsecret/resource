---
description: Analyze Spring Boot 4 migration with evidence and stage gates
argument-hint: "[target project or options]"
---

# Analyze

Perform read-only project preflight and impact assessment. Use `${CLAUDE_PLUGIN_ROOT}/scripts/migrate.ps1` with `-Stage preflight`, `-Stage analyze`, and optionally `-Stage baseline` in target repo. Delegate project inventory to `dependency-analyst` and specific breaking changes to `version-delta-analyst`. Record exact dependency versions, affected source evidence, risk, and missing compatibility info. Do not modify source, upgrade POM, or invent LSP results. Output `.migration/DELTA_CATALOG.md` and `.migration/PROJECT_INVENTORY.md`.

Instructions: The user's request arguments are `$ARGUMENTS`. Follow `skills/spring-boot-upgrade/SKILL.md`. Use `${CLAUDE_PLUGIN_ROOT}` paths to locate scripts; project path comes from the current working directory unless explicitly specified. Respect git and approval safety checks.
