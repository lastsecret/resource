---
description: Verify Spring Boot 4 migration with evidence and stage gates
argument-hint: "[target project or options]"
---

# Verify

Delegate independently to `test-verifier`: review diff and delta catalog, run compile/test plus critical integration tests, and compare pre/post observable behavior of JSON, HTTP status, security rules, persistence/transactions and configuration where applicable. Use script `-Stage verify`; it only performs Maven checks, so write additional evidence for API/security/DB yourself. Classify PASS/FAIL/NOT_TESTED and never equate compilation success with migration success. Generate `.migration/VERIFICATION.md`.

Instructions: The user's request arguments are `$ARGUMENTS`. Follow `skills/spring-boot-upgrade/SKILL.md`. Use `${CLAUDE_PLUGIN_ROOT}` paths to locate scripts; project path comes from the current working directory unless explicitly specified. Respect git and approval safety checks.
