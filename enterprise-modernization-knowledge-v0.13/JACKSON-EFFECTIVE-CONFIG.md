# Jackson 2 → 3 — Effective Mapper Configuration and Behavior Preservation (v0.6)

This document is **normative** together with `EVIDENCE-POLICY.md`; it applies to all consumers of `rules/jackson-2-to-3-effective-config.yaml`. It adds new canonical rules while preserving previous v0.5 rules.

## 1. Verified upstream defaults

| Feature | Jackson 2 default | Jackson 3 default | Direction and limitation |
|---|---|---|---|
| `DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES` | `false` | `true` | JSON `null` → Java `int`, `boolean` or other primitive; NOT the same as missing property or boxed `Integer` |
| `MapperFeature.SORT_PROPERTIES_ALPHABETICALLY` | `false` | `true` | POJO serialization property order; does **not** sort `Map` entries |

A `false` POJO sorting flag means **unspecified order**, not a guaranteed source declaration order. `@JsonPropertyOrder` can take precedence. If consumer is JSON-semantic rather than byte-order-sensitive, alphabetical order usually does not require a code change.

Source references: [Jackson DeserializationFeature](https://github.com/FasterXML/jackson-databind/blob/3.x/src/main/java/tools/jackson/databind/DeserializationFeature.java), [Jackson MapperFeature](https://github.com/FasterXML/jackson-databind/blob/3.x/src/main/java/tools/jackson/databind/MapperFeature.java), [Spring Boot 4 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [Spring Boot 4 Properties](https://docs.spring.io/spring-boot/4.0/appendix/application-properties/).

## 2. Mandatory per-mapper provenance inventory

Scan Java/Kotlin source, dependency jars when inspectable, resource configuration and runtime topology. Report each construction or lookup site and its downstream consumers:

- Spring Boot auto-configured `JsonMapper` and any `@Bean JsonMapper`; mapper builder customizers and custom MVC message converters.
- Manually constructed `new ObjectMapper(...)` / `new JsonMapper(...)`, `JsonMapper.builder().build()`, factories/helpers, copies and shared/static mapper instances. Always resolve full package name because Jackson 2 and Jackson 3 can coexist.
- `application.properties`, `application.yml`, profile-specific resources, import chain, environment variables, system properties, remote config and command-line overrides.
- Programmatic `configure`, `enable`, `disable`, builder features, `@JsonPropertyOrder`, custom deserializers / serializers.
- Actual consumer: HTTP request/response, internal JSON persistence, Redis, queue events, signatures, audit logs, contract snapshots, integrations.

**Policy:** An `application.properties` setting is not proof that a locally constructed mapper is configured. The presence of a custom `@Bean ObjectMapper` under Spring Boot 4 also does not guarantee it replaces the framework's auto-configured `JsonMapper`. Validate the mapper in use.

Suggested inventory record:

```yaml
mapper_id: inventory-from-project
module: order-service
location: src/main/java/example/JsonUtil.java:24
library_major: 3
origin: MANUAL_BUILDER_CREATED_MAPPER
spring_managed: false
profiles: [prod]
uses: [OrderJsonUtil.read]   # map actual callsites
effective_features:
  FAIL_ON_NULL_FOR_PRIMITIVES:
    value: UNKNOWN
    origin: UNKNOWN
  SORT_PROPERTIES_ALPHABETICALLY:
    value: UNKNOWN
    origin: UNKNOWN
evidence: []
status: REVIEW_REQUIRED
```

## 3. Decision algorithm

1. Resolve source/target dependency graph, target Java versions, active profiles and externally supplied properties.
2. Identify **every actual mapper instance and caller**. Associate output of HTTP converters, helper classes and custom integrations with the correct mapper.
3. For each feature, resolve the effective source setting from observed runtime configuration and code-level customizers. Only use the Jackson 2 default if absence of overrides is established.
4. Resolve target value for the same functional path. `spring.jackson.*` only applies to the relevant Spring-managed mapper.
5. Run source/target contract cases. `FAIL_ON_NULL_FOR_PRIMITIVES` requires explicit JSON null, omitted field, primitive vs boxed examples; property ordering requires POJO vs Map, annotation overrides, serialized bytes and/or semantic JSON equality.
6. If effective behavior matches, **NO_CHANGE**. If behavior differs and source semantics are required, propose the **smallest appropriately scoped** property, builder or code change and require approval. If unknown, **REVIEW_REQUIRED**, no automatic patch.
7. Bind verification results to exact source/target commits, mapper origin, configuration/profile and library version.

## 4. Conditional Spring Boot property candidates — NOT mandatory

```properties
# Candidate ONLY if proven necessary for Spring-managed Jackson 3 JsonMapper:
spring.jackson.deserialization.fail-on-null-for-primitives=false
spring.jackson.mapper.sort-properties-alphabetically=false

# Alternative broad compatibility aid ONLY after reviewing side effects:
# spring.jackson.use-jackson2-defaults=true
```

These properties do **not** automatically configure manually instantiated `JsonMapper.builder().build()` or `new ObjectMapper()` instances. Do not add global settings if only a single helper mapper requires legacy behavior.

For a Jackson 3 manually built `JsonMapper`, an example of the intended local change (subject to project-specific compilation / tests) is:

```java
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.json.JsonMapper;

JsonMapper mapper = JsonMapper.builder()
    .disable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
    .disable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY)
    .build();
```

Do not blindly apply both changes: either, both or neither may be needed depending on that mapper's source effective behavior. For security, decide whether intentionally stricter target behavior should be accepted instead of preserving legacy compatibility.

## 5. Extra sorting notes

`SORT_PROPERTIES_ALPHABETICALLY` affects POJO properties. `SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS` is separate and must only be adjusted when effective configuration and a Map-specific baseline support it. `@JsonPropertyOrder` overrides should be inspected before proposing any global mapper modification. Raw string signatures, snapshots and byte-for-byte agreements are order-sensitive; most JSON consumers that parse object keys are not.

## 6. Proof status

All cases in `acceptance-cases.yaml` are **design-time / NOT_RUN**. The pack is not an executed modernization run, and the examples must be validated using the resolved exact Jackson / Spring Boot versions in a real project.
