---
description: Migrate Spring Boot 4 migration with evidence and stage gates
argument-hint: "[target project or options]"
---

# Migrate

Do not proceed unless explicit user approval for plan AND source changes exists. Require clean git status and a dedicated branch/worktree. Run OpenRewrite `dryrun` with pinned plugin and recipe versions; inspect generated patch, artifact resolution errors and all changes. Explain and obtain explicit approval before invoking `apply`. Delegate residual compilation diagnostics to `code-migrator` after apply. Use Java LSP when configured, otherwise Maven errors and source inspection. Minimize diffs; no broad refactors or unchecked automatic loops. Persist each stage to `.migration` and stop on failure.

Instructions: The user's request arguments are `$ARGUMENTS`. Follow `skills/spring-boot-upgrade/SKILL.md`. Use `${CLAUDE_PLUGIN_ROOT}` paths to locate scripts; project path comes from the current working directory unless explicitly specified. Respect git and approval safety checks.
