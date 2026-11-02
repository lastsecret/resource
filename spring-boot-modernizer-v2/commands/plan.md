---
description: Plan Spring Boot 4 migration with evidence and stage gates
argument-hint: "[target project or options]"
---

# Plan

Read inventory, delta catalog and baseline test evidence. Delegate to `migration-planner`. Generate `.migration/MIGRATION_PLAN.md` containing pilot module, order, OpenRewrite recipe and pinned artifact coordinates, prereq approvals, expected test impact, rollback strategy, acceptance criteria and a phase-by-phase checklist. Stop before any write to source; ask user to approve plan. If no baseline, label risk and recommend obtaining one.

Instructions: The user's request arguments are `$ARGUMENTS`. Follow `skills/spring-boot-upgrade/SKILL.md`. Use `${CLAUDE_PLUGIN_ROOT}` paths to locate scripts; project path comes from the current working directory unless explicitly specified. Respect git and approval safety checks.
