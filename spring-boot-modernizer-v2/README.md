# Spring Boot Modernizer v2 (Claude Code Plugin)

A local-first, Maven-first, Windows PowerShell-friendly migration plugin for Spring Boot 3.5.x -> 4.x. Java 21 can remain unchanged. This is an **MVP**: verify against your organization's own repository and Java project before production usage. Not a fork of Anthropic Code Modernization.

## Install (no GitHub or marketplace required)

1. Extract this ZIP; keep the entire `spring-boot-modernizer-v2` directory.
2. In your terminal, launch Claude Code with:
   `claude --plugin-dir "C:\\tools\\spring-boot-modernizer-v2"`
   or `claude --plugin-dir /path/to/spring-boot-modernizer-v2`.
3. From your **target Spring Boot repository**, use `/spring-boot-modernizer:analyze` and then `/spring-boot-modernizer:plan`.
4. Approve the written plan before `/spring-boot-modernizer:migrate`; run `/spring-boot-modernizer:verify` afterward.

To inspect the hidden `.claude-plugin` manifest, enable hidden files in your file manager. Slash command namespace is the `name` from plugin.json.

## Requirements
- Maven 3.9+, JDK 21, PowerShell 7+ (`pwsh`) recommended, Git, Claude Code.
- A working Maven mirror for all required artifacts. **Pin** versions of `rewrite-maven-plugin` and `rewrite-spring` explicitly. Recipe licensing, authentication, and repository availability vary: verify them in your organization.
- Spring Boot 3.5.x project (for earlier Boot 3 versions, first establish supported migration route).
- Java LSP integration in Claude Code is **optional**; see `skills/spring-boot-upgrade/references/java-lsp.md`. No LSP invocation is faked by the scripts.
- Run on a new git branch/worktree, not on uncommitted production changes.

## PowerShell stages (explicit actions)
From *target repository*:
```powershell
$plugin = 'C:\tools\spring-boot-modernizer-v2'
$script = Join-Path $plugin 'scripts/migrate.ps1'
pwsh -NoProfile -File $script -Stage preflight -ProjectPath .
pwsh -NoProfile -File $script -Stage baseline -ProjectPath .
pwsh -NoProfile -File $script -Stage analyze -ProjectPath .
# requires approved plan, approved versions and clean git status
pwsh -NoProfile -File $script -Stage dryrun -ProjectPath . -RewritePluginVersion 'PINNED' -RewriteSpringVersion 'PINNED'
pwsh -NoProfile -File $script -Stage apply -ProjectPath . -RewritePluginVersion 'PINNED' -RewriteSpringVersion 'PINNED' -Approved
pwsh -NoProfile -File $script -Stage verify -ProjectPath .
pwsh -NoProfile -File $script -Stage report -ProjectPath .
```
Replace `PINNED` with versions available in your internal artifact registry. Do not copy `PINNED` literally.

## Evidence
All generated files live in `.migration/` in the target repo: `runs/<timestamp>/`, `state.json`, `reports/` and logs. Add `.migration/` to `.gitignore` if desired (for audit, consider committing curated markdown reports instead). The scripts do not generate behavior baselines automatically: the Test Verifier agent writes baseline cases and comparison results, explicitly labeling untested areas.

## Deliberate limits
- No automatic batch rewrite across unrelated repositories; pilot first.
- `dryrun` may generate build artifacts/patches in `target/` but should not change source; review with `git status`.
- `apply` changes source files and is guarded by approval and clean git state.
- The script performs Maven compile/test and dependency-tree collection but cannot prove runtime equivalence or security correctness by itself.
- Do not mark a migration complete unless independent verification evidence exists.

## License/source design
Original workflow inspired by Anthropic Code Modernization and community migration skills; no copied source code included. See `references/sources.md`.
