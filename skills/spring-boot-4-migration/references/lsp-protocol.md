# Java LSP integration contract

This skill does not install or call JDT LS itself. The agent must first check whether a Java LSP tool is connected and initialized for the project, and whether its workspace matches the current source tree.

After rewrite and Maven compiler errors:
1. Save compiler error output.
2. Ask Java LSP for diagnostics on the affected file; locate symbol definition and references; inspect actual resolved signature and import candidates.
3. Compare target library JAR classes or official docs when LSP indexes are stale.
4. Apply the smallest semantic fix, run focused Maven test + compile, then re-request LSP diagnostics.
5. If LSP is missing or stale, fall back to Maven compiler diagnostics and local source search; mark LSP_NOT_AVAILABLE or LSP_STALE.

Never use LSP diagnostics alone as passing verification. Avoid assuming a specific Claude Code MCP/LSP tool name: discover tools exposed by the runtime.
