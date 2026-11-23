# Java API Test Engineer — Architecture

Version 0.1.0. Script-first, static-first, no implicit LLM/tool execution.

## Components

| Command | Inputs | Output | Implementation |
|---|---|---|---|
| inspect | Java project directory | capabilities.json | Bounded files, POM XML, Gradle text, annotations |
| discover | Explicit method and file/project/docs URL | endpoints.json | OpenAPI 3 parser, JDK Compiler AST, runtime Springdoc fetch |
| generate | Endpoint catalog, optional fixtures | cases.jsonl, quality report | Deterministic schema/example/fixture values |
| execute | Frozen cases, HTTP base URL, optional Java JAR | results.jsonl; optional jacoco.exec | urllib replay, optional JVM launcher |
| coverage | JaCoCo CLI/JAR/XML and classes | XML/HTML/coverage-summary.json | JaCoCo CLI wrapper and XML parser |
| compare | Results A/B or frozen cases and URLs | diff.json, diff.html | Type-aware recursive matching |
| explore | OpenAPI contract and server URL | External Schemathesis reports | Opt-in child process |
| enrich | Java source/catalog/coverage | context-bundle.json | Bounded source extraction for an external agent |

## Operational guarantees

1. `inspect` never runs the application, build or Maven dependency resolution.
2. `discover` requires an explicit adapter; there is no silent fallback to LLM analysis.
3. Remote HTTP requires `--allow-remote`, mutation methods require `--allow-mutation`.
4. All A/B comparisons use frozen cases. Transport failures are inconclusive, never equal.
5. Neither a passing A/B test nor JaCoCo branch coverage proves functional equivalence.
6. Low confidence inputs and non-intentional Null/empty arrays are reflected in artifacts.
7. All artifacts are machine-readable, and no stage relies on the model's conversation state.

## Artifacts

`endpoints.json` stores HTTP method, path, parameters, request body, responses and schema components, with origin and confidence. `cases.jsonl` freezes a concrete HTTP request, expected statuses, input warnings, intentional special-case annotations and blocking reasons. `results.jsonl` stores status, response headers, captured body Base64, error state and input warnings. `diff.json` stores policy, per-case outcomes and warning provenance.

Response content is retained locally because raw A/B comparison requires identical byte-level evidence; treat reports as sensitive artifacts. Outbound auth values provided through env variables are not copied to result artifacts.

## Planned extensions

- Classpath-aware AST/SymbolSolver resolver, generated OpenAPI cross-check, multi-module schema provenance.
- Branch isolation with JaCoCo reset/dump between serialized requests; source-to-endpoint coverage map.
- Schemathesis HAR/VCR promotion into replay-safe, validated frozen request fixtures.
- oasdiff compatibility checks, CI workflow adapters, schema/assertion validation and JUnit export.
- Human-reviewed branch-targeted Agent suggestions and fixture management.

Implementation details and runnable commands: `README.md`.
