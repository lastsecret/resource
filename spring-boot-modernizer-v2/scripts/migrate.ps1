[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('preflight','baseline','analyze','dryrun','apply','verify','report')]
  [string]$Stage,
  [string]$ProjectPath='.',
  [string]$RewritePluginVersion='',
  [string]$RewriteSpringVersion='',
  [string]$Recipe='org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0',
  [string]$MavenExecutable='mvn',
  [switch]$Approved
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $ProjectPath).Path
if (-not (Test-Path (Join-Path $root 'pom.xml'))) { throw "Missing pom.xml in $root. Maven-only MVP." }
$evidence=Join-Path $root '.migration'
$runId=(Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6)
$runDir=Join-Path $evidence "runs/$runId"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$statePath=Join-Path $evidence 'state.json'
if (Test-Path $statePath) { $state=Get-Content -Raw $statePath | ConvertFrom-Json } else { $state=[pscustomobject]@{schema=1;project=$root;history=@()} }
function Save-State([string]$status,[string]$message) {
  $entry=[pscustomobject]@{runId=$runId;stage=$Stage;status=$status;message=$message;timestamp=(Get-Date).ToUniversalTime().ToString('o');path=$runDir}
  $state.history=@($state.history)+@($entry)
  $state | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 -Path $statePath
}
function Invoke-Logged([string]$name,[string]$executable,[string[]]$arguments) {
  $log=Join-Path $runDir "$name.log"
  "Executable: $executable`nArgs: $($arguments -join ' ')" | Set-Content -Path $log -Encoding utf8
  Push-Location $root
  try {
    & $executable @arguments 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
    $rc=$LASTEXITCODE
  } finally { Pop-Location }
  if ($rc -ne 0) { throw "$name failed with exit code $rc. Log: $log" }
  Write-Host "$name OK: $log"
}
function Assert-GitClean {
  Push-Location $root
  try {
    & git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Not a git repo; use a dedicated git worktree.' }
    $changes=@(& git status --porcelain --untracked-files=normal -- . ':!.migration')
    if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
    if ($changes.Count -gt 0) { throw "Working tree has changes outside .migration; commit/stash them first: $($changes -join '; ')" }
  } finally { Pop-Location }
}
function Assert-RewriteParams {
  if ($RewritePluginVersion -notmatch '^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$' -or $RewriteSpringVersion -notmatch '^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$') { throw 'Provide pinned -RewritePluginVersion and -RewriteSpringVersion (no RELEASE/LATEST/PINNED).' }
}
function Invoke-Rewrite([string]$goal) {
  Assert-RewriteParams
  $args=@('-B',"org.openrewrite.maven:rewrite-maven-plugin:${RewritePluginVersion}:$goal", "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:$RewriteSpringVersion", "-Drewrite.activeRecipes=$Recipe", '-Drewrite.exportDatatables=true')
  Invoke-Logged "rewrite-$goal" $MavenExecutable $args
}
try {
  switch ($Stage) {
    'preflight' {
      Invoke-Logged 'java-version' 'java' @('-version')
      Invoke-Logged 'maven-version' $MavenExecutable @('-version')
      Invoke-Logged 'git-version' 'git' @('--version')
      Invoke-Logged 'mvn-validate' $MavenExecutable @('-B','-DskipTests','validate')
    }
    'baseline' {
      Invoke-Logged 'baseline-test' $MavenExecutable @('-B','test')
      Invoke-Logged 'baseline-dependencies' $MavenExecutable @('-B','dependency:tree',"-DoutputFile=$runDir/dependency-tree.txt")
    }
    'analyze' {
      Invoke-Logged 'effective-pom' $MavenExecutable @('-B','help:effective-pom',"-Doutput=$runDir/effective-pom.xml")
      Invoke-Logged 'dependency-tree' $MavenExecutable @('-B','dependency:tree',"-DoutputFile=$runDir/dependency-tree.txt")
    }
    'dryrun' {
      Assert-GitClean
      Invoke-Rewrite 'dryRun'
      Assert-GitClean
    }
    'apply' {
      if (-not $Approved) { throw 'Source mutation requires -Approved after explicit user authorization and approved plan.' }
      Assert-GitClean
      $plan=Join-Path $evidence 'MIGRATION_PLAN.md'
      if (-not (Test-Path $plan)) { throw 'Approved migration plan file missing: .migration/MIGRATION_PLAN.md' }
      Invoke-Rewrite 'run'
    }
    'verify' {
      Invoke-Logged 'verify-test' $MavenExecutable @('-B','test')
      Invoke-Logged 'verify-package' $MavenExecutable @('-B','-DskipTests','package')
      Invoke-Logged 'verify-dependencies' $MavenExecutable @('-B','dependency:tree',"-DoutputFile=$runDir/dependency-tree.txt")
    }
    'report' {
      $report=Join-Path $evidence 'STATUS.md'
      $lines=@('# Spring Boot migration stage status','','Generated automatically from execution events; does not prove behavioral equivalence.','')
      foreach ($item in @($state.history)) { $lines += "- $($item.timestamp) | $($item.stage) | $($item.status) | $($item.message)" }
      $lines | Set-Content -Path $report -Encoding utf8
      Write-Host "Report: $report"
    }
  }
  Save-State 'PASS' 'Stage command completed; review evidence and independent verification.'
} catch {
  Save-State 'FAIL' $_.Exception.Message
  Write-Error $_
  exit 1
}
