---
name: java-api-test-engineer
description: Inspect Java REST projects, select endpoint extraction methods, generate reproducible HTTP requests, run tests with JaCoCo support and compare A/B responses. Delegate deterministic work to the japi CLI.
---

# Java API Test Engineer

Use `japi` or `python -m japi` for all deterministic operations. Do not manually parse repositories or generate dozens of HTTP requests in LLM context. Keep outputs in separate artifact directories; avoid editing the target project. All stages are independently runnable.

## Discovery: inspect, then select

1. Run `japi inspect --project <path> --output <artifact-dir>/inspection`.
2. Read only the compact summary and `capabilities.json`. Present detected existing OpenAPI, Springdoc, build system, REST controllers and available offline JDK AST adapter.
3. Ask once which method to use: existing `openapi-file`, `static-jdk`, or `springdoc-runtime`. Do not automatically select merely because a provider is installed. Explain that Springdoc needs a running app.
4. Run `japi discover --mode <selection> --openapi <path>` or `--project <path>` or `--docs-url <url>` with explicit authorization for remote URLs. If an adapter fails, report diagnostics and offer alternatives; never silently call an agent.

## Frozen cases

Default to `japi generate --catalog <endpoints.json>` (GET only). For other methods, ask and then pass `--methods GET,POST,...`. Add verified business identifiers via `--fixtures`. Inspect `case-quality.json`: warn about inferred values, unintended Null or `[]`; never silently treat fabricated request IDs as real. `--block-low-confidence` is available at execution time. Explicit test intentions must identify paths, reasons and expected behaviors.

## Execute and coverage

Ask whether to target a running URL or launch a local JAR. Execute only when the target and effects are approved. Run `japi execute --cases ... --base-url ...`. For a local launch, use explicit `--launch-jar`, optionally `--jacoco-agent` and `--jacoco-cli` for an instrumented JVM. Never expose JaCoCo TCP outside localhost. Report response status failures separately from coverage and data-confidence warnings. `japi coverage report` requires the JaCoCo CLI, compiled classes and optional source paths; `japi coverage summarize` parses an existing XML without Java.

## A/B

Replay one frozen case set against two URLs with `japi compare --cases ... --a-url ... --b-url ...` or use `--a-results`/`--b-results` for offline comparison. Offer `raw_exact`, `json_exact`, `semantic` default and user-defined custom combinations. Never enable ignore-case, array reordering, ignore fields, tolerance or Null/Missing equivalence without an explicit policy. Use `diff.json` for truth and `diff.html` for review. Transport errors and blocked requests are `inconclusive`. Warn when even equal responses are based on low-confidence cases.

## Agent step (explicit opt-in only)

For costly source reasoning run `japi enrich --project ... --catalog ... [--coverage-xml ...]`. Read the bounded `context-bundle.json` and delegate only its selected source excerpts to a coding agent. Agent suggestions are *candidate cases* requiring human approval, not automatic changes to frozen cases.

## Optional Schemathesis

`japi explore --openapi ... --base-url ...` uses an independently installed Schemathesis CLI and defaults to GET only. Exploration results are not stable A/B replay cases until separately reviewed and frozen.

## Reports and limitations

Return only paths, count summaries, notable failures, confidence warnings and unresolved schema diagnostics. Avoid copying whole responses or source files to conversational context. Do not claim static scanner covers framework-specific runtime routes or that JaCoCo provides endpoint-to-branch attribution. See `README.md` for exact CLI options and limitations.
