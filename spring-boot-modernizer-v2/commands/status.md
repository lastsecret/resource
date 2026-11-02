---
description: Status Spring Boot 4 migration with evidence and stage gates
argument-hint: "[target project or options]"
---

# Status

Read `.migration/state.json`, latest run logs, plan and verification artifacts. Report completed/failed/not-yet-run stages, unresolved deltas, next safe action and approval gates. Never infer success from missing files; do not silently rerun or apply changes.

Instructions: The user's request arguments are `$ARGUMENTS`. Follow `skills/spring-boot-upgrade/SKILL.md`. Use `${CLAUDE_PLUGIN_ROOT}` paths to locate scripts; project path comes from the current working directory unless explicitly specified. Respect git and approval safety checks.
