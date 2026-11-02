# Dependency and code impact checklist

For each item, record: module, path/symbol, current resolved version, approved target version, official evidence URL, risk, owner, mitigation, verification.

1. Java runtime, Maven wrapper, BOM parent hierarchy, dependencyManagement, overridden versions, repositories and pluginRepositories.
2. Multi-module parent + children, internal libraries, company starters, generated source and annotation processors.
3. Spring Framework 7, modular Spring Boot starters and module relocations; auto-configuration; properties and config binding.
4. Spring Security 7: filter chain, authorization matchers, method security, OAuth2/OIDC, test security.
5. Jackson 3: imports, ObjectMapper configuration, JSON contracts, serializers, date/time, API client compatibility.
6. Spring Data JPA/Hibernate, transactional semantics, DB migrations, datasource drivers, repositories.
7. MyBatis starter interoperability, custom interceptors/type handlers.
8. Spring MVC/WebFlux, servlet containers, validation, error response, HTTP clients.
9. Actuator/metrics/tracing/logging and health endpoints.
10. Tests: mocking annotations, Spring test slices, JUnit/Mockito compatibility, test containers, H2 differences.
11. CI build image, Java bytecode, Docker base image, Kubernetes probes/config; startup flags.
12. `mvn dependency:tree` post-change conflicts, managed vs explicit versions, native-image if used.

Classifications: AUTO_REWRITE, AI_ASSIST, MANUAL, UNKNOWN. No impact without evidence; unknown is risk, not safe.
