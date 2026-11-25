# Undertow → Tomcat: Configuration-aware conversion candidates

Status: **static candidate scanner implemented; automatic edits intentionally disabled**. Designed for a Spring Boot 3.5.x source project migrating to Spring Boot 4.0.x with embedded Tomcat. An external WAR/server requires a separate deployment evaluation.

## Core policy

1. Resolve the actual source container (POM declarations alone are **not** a resolved classpath).
2. Find every `application*.properties` / `application*.yml` / `.yaml` value and Undertow-specific Java customizer; keep profile and file provenance.
3. Inspect explicit settings *before* documented defaults. A missing static key is **not** proof of an effective default: environment variables, command-line flags, config server, Spring profiles, and `@Bean` customizers might override it.
4. Contrast source and target properties by **semantics**. Produce reviewed candidate target settings and test cases, never patch an unproven equivalence.
5. For all non-equivalent options, require runtime evidence and a human decision. Enforce `NO_CHANGE`, `CANDIDATE_REVIEW`, and `MANUAL_REVIEW` distinctions.
6. Test request/response behavior, access logs, load, timeouts, error status, encoded URL, headers, health and downstream effects on source and target before claiming parity.

## Mapping matrix (Spring Boot official property appendices)

| Source setting / documented default | Proposed target | Treatment |
|---|---|---|
| `server.undertow.accesslog.enabled` (`false`) | `server.tomcat.accesslog.enabled` (`false`) | Same-purpose candidate only; inspect actual file output |
| `server.undertow.accesslog.rotate` (`true`) | `server.tomcat.accesslog.rotate` (`true`) | Same-purpose candidate only |
| `server.undertow.accesslog.dir` | `server.tomcat.accesslog.directory` (`logs`) | Review path base semantics |
| `server.undertow.accesslog.pattern` (`common`) | `server.tomcat.accesslog.pattern` (`common`) | Review custom pattern token syntax |
| `server.undertow.accesslog.prefix` (`access_log.`) | `server.tomcat.accesslog.prefix` (`access_log`) | Different default filename convention |
| `server.undertow.accesslog.suffix` (`log`) | `server.tomcat.accesslog.suffix` (`.log`) | Different default filename convention |
| `server.undertow.url-charset` (`UTF-8`) | `server.tomcat.uri-encoding` (`UTF-8`) | Review URI decoding semantics |
| `server.undertow.threads.worker` (`8 × I/O`) | `server.tomcat.threads.max` (`200`) | **NO AUTOMATIC NUMERIC TRANSLATION** |
| `server.undertow.threads.io` (CPU-derived) | None | No one-to-one target property |
| `server.undertow.no-request-timeout` | `server.tomcat.keep-alive-timeout` | Different timeout semantics; **no automatic translation** |
| `server.undertow.max-http-post-size` (`2MB`) | `server.tomcat.max-http-form-post-size` (`2MB`) | Different scope; same numeric default **does not** imply same behavior |
| `server.undertow.max-parameters` | `server.tomcat.max-parameter-count` (`1000`) | Different parameter accounting; review manually |
| `server.undertow.decode-slash` | No verified exact equivalent | Encoded-slash and security behavior require dedicated tests |
| `server.undertow.options.*` | No verified direct equivalent | Undertow/XNIO options: manual API review |

`server.max-http-request-header-size` is a shared Spring Boot property; retain it where appropriate, but verify HTTP parsing and proxy semantics. Do not manufacture missing defaults for Undertow idle timeout, I/O counts, or direct buffers.

## Executable scanner

Offline once Python dependencies are installed (PyYAML only for YAML config):

```bash
python3 tools/project_scanner.py \
  --project /path/to/springboot3-project \
  --output /tmp/migration-findings
```

Outputs:

- `findings.json`: static observations, locations, candidates, default comparisons, limitations
- `report.md`: human-oriented review report
- `suggested-tomcat.properties`: **commented-out** candidate values only, not a deployable patch

This tool *never* edits the project. `source_effective` and `target_effective` remain **unverified** until runtime configuration and test evidence are supplied. Maven parsing is source declaration-level only, not effective dependency graph resolution. Regex-based Java findings require AST/LSP follow-up; profile overlays and environment-dependent configuration remain unresolved.

## Official references

- [Spring Boot 4 migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot 3.5 application properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html)
- [Spring Boot 4.0 application properties](https://docs.spring.io/spring-boot/4.0/appendix/application-properties/index.html)

Conditional source-default filename preservation candidates may be generated when Undertow accesslog.enabled=true is explicitly present in static configuration, but they must not be applied until the original effective defaults and output naming contract are verified.
