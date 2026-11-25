# Evidence-Based Migration Policy — v0.5

This file is **normative** and overrides older handbook/reference statements when they conflict.

## Four mutually exclusive rule classifications

| Class | Meaning | Allowed output |
|---|---|---|
| `BREAKING_CHANGE` | A documented incompatible API/dependency/configuration contract for a specific version interval | Conditional remediation recommendation after project applicability and evidence checks |
| `BEHAVIOR_CHANGE` | Documented old/new behavior difference, with actual outcome dependent on effective configuration | Measure baseline, compare target, propose only minimum necessary change |
| `REGRESSION` | Upstream-confirmed defect affecting a specified target version/build | Avoid known affected version or propose approved workaround |
| `VALIDATION_ONLY` | No specific upstream-confirmed incompatible change for this exact interval; plausible integration/operational risk | Targeted verification only; **never patch** |

## Critical distinctions

* A link to documentation is not proof that the entire rule is a breaking change.
* A framework/component *version matrix* is a compatibility requirement, **not** proof that all users must change source code.
* `OFFICIAL_DOC_SECTION_CHECKED` means that a matching official documentation section was checked, **not** that the specific project was affected.
* `REQUIRES_CLAIM_LEVEL_SOURCE_REVIEW` cannot be used to trigger automated modification. Retain for expert review.
* `NO_EXACT_VERSION_DELTA_ESTABLISHED` means the rule is a verification probe, not a version delta. Absence of evidence is not a guarantee of compatibility.
* Every rule must be evaluated against **exact effective dependency versions** and actual source/target application behavior, including overrides and profiles. A default applies only after confirming no relevant override.
* No configured version is inherently 'required' unless the component matrix or runtime target demands it.
* All auto remediation in this v0.5 is **disabled by default**; confirmed changes may produce reviewed patch proposals only.
* Actual integration tests are **NOT_RUN**. The test catalog specifies expected checks, not observed results.

## Action / quality gate algorithm

1. Resolve source and target exact versions, full dependency tree, source Java release, profiles, external property sources and project configuration.
2. If class `VALIDATION_ONLY` -> route exclusively to `verification-catalog.yaml`.
3. If class `REGRESSION` -> apply only when **affected exact target version** and usage conditions match.
4. For `BREAKING_CHANGE` or `BEHAVIOR_CHANGE`, require cited source clause for that *specific claim*; reject unreviewed `REQUIRES_CLAIM_LEVEL_SOURCE_REVIEW` entries.
5. Confirm affected feature, source effective configuration, baseline behavior, and expected target contract. Resolve unknowns via tests or human review rather than guessing.
6. Propose least invasive remedy; evaluate OpenRewrite availability and license; require human approval for code/config/dependency edits.
7. Verify compiler, functional/contract behavior, security, operational gates as relevant; attach exact revision/config/versions and proof.
8. Only mark a project `PROVEN` after actual evidence is captured; all catalog entries in this ZIP remain `NOT_RUN`.

## Component-specific constraints

* **HikariCP 6.x → 7.x:** Hikari 7.0.1 changelog documents a `setSchema` regression fix. `HCP7-SCHEMA-001` is applicable **only to 7.0.0** and affected projects. For 7.0.2, do not recommend a fix for this resolved defect. Other Hikari checks are validation only.
* **Oracle JDBC 23.7.x → 23.9.x:** no broad, project-independent code edit is substantiated by the reviewed vendor sources. Preserve mapping and configuration; check driver/JDK/DB/companion library versions; execute relevant tests.
* **Spring Boot dependency BOM:** distinguish managed/transitive dependencies from explicit versions; do not add a direct pin solely to force a version already provided by an approved BOM.
* **Jackson / Hibernate / Security:** preserve measured source behavior and security authorization matrix; security changes require explicit approval even when new defaults are stricter.
* **Java:** keep `mode=preserve` or approved `mode=explicit` from each migration config; no implicit Java 21/17 edits. The dynamic Java policy from v0.4 is retained.

## Recipe policy

`recipes/recipe-availability.yaml` describes public catalog evidence and caveats. No dedicated HikariCP 6→7 or Oracle 23.7→23.9 code-migration recipe was established in the reviewed catalog; absence does **not** prove none exists anywhere. A generic OpenRewrite `UpgradeDependencyVersion` updates declarations, **not** runtime semantics. `recipes/explicit-version-upgrades.REVIEW-REQUIRED.yml` is illustrative only and must never be launched by an unattended agent.


## Jackson 2→3 v0.6 normative addendum

1. `JCK3-NULL-PRIMITIVES-001` and `JCK3-POJO-ORDER-002` are **documented default differences**, not proof that a particular application has changed behavior.
2. Resolve **each actual Mapper instance and consumer**, including `new ObjectMapper(...)`, `new JsonMapper(...)` (where supported), `JsonMapper.builder().build()`, factories, custom beans, serializers, and any Jackson 2/3 coexistence.
3. `spring.jackson.*` affects Spring auto-configured or properly integrated mappers; **do not** assume it configures manually instantiated instances. Resolve source/target effective feature values per mapper and profile.
4. For null→primitive test explicit JSON null separately from missing field and boxed `Integer`. For property sorting distinguish POJO properties, Map entries, and `@JsonPropertyOrder`. Unsorted Jackson 2 POJO properties are **not guaranteed** to follow declaration order.
5. `spring.jackson.use-jackson2-defaults=true` is a possible Spring-managed compatibility aid, not a default or universal fix; do not unconditionally add it. Propose the smallest change and seek approval.
6. Both source and target behavior must be proven, or the finding stays `REVIEW_REQUIRED`. No automatic patch; all new cases are `NOT_RUN`.

Full decision model: `JACKSON-EFFECTIVE-CONFIG.md`.
