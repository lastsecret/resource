# Spring Boot 4 Migration Skill (Maven MVP)

Copy `.claude/skills/spring-boot-4-migration` into your target repository, or into `%USERPROFILE%\.claude\skills\spring-boot-4-migration` for user-wide access.

Invoke `/spring-boot-4-migration analyze` in Claude Code, or run the included PowerShell 7 script manually.

**MVP boundary:** The script captures discovery/build evidence and executes Maven OpenRewrite. AI-led dependency compatibility analysis, LSP queries, API/security/DB runtime checks, and report verdict require the agent. No Spring Boot project was migrated/tested while building this artifact.

**Before using:** verify company-approved OpenRewrite plugin and rewrite-spring versions are available in Nexus/Artifactory, and set Maven settings. `-Offline` requires cached dependencies.

The skill is intentionally conservative: no auto commits, no automatic Java major upgrade, no global dependency bumps, and no silent test bypass.
