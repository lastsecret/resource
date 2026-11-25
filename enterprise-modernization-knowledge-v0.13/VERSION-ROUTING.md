# Spring Boot 3.5 → 4.1 Version Routing and Evidence Policy

## Version route

| Source | Target | Chosen stages | Notes |
|---|---|---|---|
| 3.5.x | 4.0.x | 3.5→4.0 | Original v0.7 candidate set |
| 3.5.x | 4.1.x | 3.5→4.0 + 4.0→4.1 | Two knowledge deltas, **not** two required deployments |
| 4.0.x | 4.1.x | 4.0→4.1 | Does not reapply initial 3.5→4.0 rules |
| 4.2.x | any | unsupported | Add verified deltas before marking compatible |

For 3.5→4.1, rules referencing Boot 4.0 represent the **historical transition**, but their exact triggers and suggested actions must be recomputed for the *final 4.1.3* dependency graph and effective settings. Example: an Undertow→Tomcat worker setting is not a 1:1 numeric mapping under either target.

## New 4.1 delta candidates

The 4.1 release notes confirm removal of Boot 4.0 deprecated APIs and the layertools jar mode, an AOT / skipTests behavior change, changed deferred/lazy JPA bootstrapping, Tomcat temporary directory cleanup, Reactor Netty system-proxy defaults, jOOQ minimum JDK concerns, Gradle build-info filename changes, and Jackson auto-configuration enhancements. Each candidate is separately represented in `deltas/spring-boot-4.0-to-4.1.json`.

## Rule classification & resolution

1. Select the version-stage rules; all start as **CANDIDATE**.
2. Resolve Maven/Gradle effective dependency graph and actual JDK, INCLUDING dependency editions (jOOQ OSS vs commercial).
3. Collect source effective config across Spring profiles, env vars, custom beans, manual mappers, etc.
4. Inspect source symbol references with AST / JDT LS / compiler. Text matches only produce `REVIEW_REQUIRED`, never `CHANGE_NEEDED`.
5. Obtain old behavior baseline + new behavior verification (or reviewed contractual spec).
6. `NO_CHANGE`, `REVIEW_REQUIRED`, `CHANGE_NEEDED` require explicit evidence; no auto patch in this release.

### jOOQ with Java 17

Spring Boot 4.1.3 requires Java >=17. However, the *open-source* `org.jooq:jooq` artifact in the 3.20+ line requires Java 21. If your project has **resolved jOOQ OSS** 3.20+ while preserving target Java17, **BLOCK**. Distinct commercial Java17-compatible coordinates exist: do not apply the OSS constraint blindly across editions. Never silently upgrade the JDK. (Verify effective coordinates, licenses and plugin / code-generation versions.)

### Recipe choices

- `UpgradeSpringBoot_4_0`: confirm in local rewrite-spring artifact; run dryRun and review diff.
- `UpgradeSpringBoot_4_1`: *candidate discovery only*: check installed versions and edition-specific availability with the local recipe discovery command. Do not assume the recipe exists or covers all 4.1 changes.
- Direct BOM + version changes should be reviewed and verified; a dependency version rewrite is not an API or behavior migration proof.

## Sources

- Spring Boot 4.1 release notes: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes
- Spring Boot 4.1.3 system requirements: https://docs.spring.io/spring-boot/4.1/system-requirements.html
- Spring Boot 4.0 migration guide: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- jOOQ JDK matrix: https://www.jooq.org/download/support-matrix-jdk
- MyBatis-Spring Boot Starter matrix: https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/

**Status:** Library documentation checked 2026-11-25; project specific code / regression proofs NOT_RUN.
