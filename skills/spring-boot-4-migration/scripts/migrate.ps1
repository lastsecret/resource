[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidateSet('analyze','baseline','dryrun','apply','verify','report')][string]$Stage,
 [string]$ProjectPath='.',
 [string]$RewritePluginVersion='',
 [string]$RewriteSpringVersion='',
 [string]$SettingsPath='',
 [switch]$Offline
)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath $ProjectPath).Path
$reports=Join-Path $project '.migration-reports'
New-Item -ItemType Directory -Path $reports -Force | Out-Null
$stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')
$log=Join-Path $reports "$Stage-$stamp.log"
$status=Join-Path $reports 'stage-results.jsonl'
function Record([string]$step,[int]$code,[string]$detail) {
 $obj=[ordered]@{time=(Get-Date).ToString('o'); stage=$step; exitCode=$code; detail=$detail; log=$log}
 ($obj|ConvertTo-Json -Compress)|Add-Content -LiteralPath $status -Encoding utf8
}
function Run([string]$exe,[string[]]$arguments) {
 "`$ $exe $($arguments -join ' ')" | Tee-Object -FilePath $log -Append | Out-Host
 & $exe @arguments 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append | Out-Host
 $code=$LASTEXITCODE
 if ($null -eq $code) {$code=0}
 Record $Stage $code "$exe invocation"
 if($code -ne 0) { throw "Command failed (exit $code), see $log" }
}
Push-Location $project
try {
 if(-not(Test-Path 'pom.xml')) {Record $Stage 2 'Maven pom.xml not found'; throw 'Only Maven supported for execution in v1.'}
 $mvn='mvn'
 if(Test-Path 'mvnw.cmd') {$mvn=(Join-Path $project 'mvnw.cmd')}
 elseif(Test-Path 'mvnw') {$mvn=(Join-Path $project 'mvnw')}
 $common=@('-B','-ntp')
 if($Offline){$common+= '-o'}
 if($SettingsPath){$settings=(Resolve-Path -LiteralPath $SettingsPath).Path; $common+=@('-s',$settings)}
 switch($Stage) {
  'analyze' {
   Run 'git' @('status','--short')
   Run 'java' @('-version')
   Run $mvn @($common+@('-version'))
   Run $mvn @($common+@('help:evaluate','-Dexpression=project.version','-q','-DforceStdout'))
   Run $mvn @($common+@('dependency:tree',"-DoutputFile=$reports/dependency-before.txt"))
   Write-Host "Review pom.xml, modules, Spring Boot parent/BOM and write impact-matrix.csv. No changes applied."
  }
  'baseline' { Run $mvn @($common+@('test')) }
  {$_ -in 'dryrun','apply'} {
   if(-not $RewritePluginVersion -or -not $RewriteSpringVersion) {throw 'Provide pinned approved RewritePluginVersion and RewriteSpringVersion.'}
   if($Stage -eq 'apply') {
    $changes=(& git status --porcelain 2>&1)
    if($LASTEXITCODE -ne 0) {throw 'git status failed'}
    # Ignore migration report files created by this helper; all other changes block apply.
    $dirty=@($changes | Where-Object { $_ -and $_ -notmatch '^\?\? \.migration-reports/?' })
    if($dirty.Count -gt 0) {throw 'Working tree contains modifications. Review and commit/stash them before apply.'}
    Write-Warning 'APPLY changes source files. Ensure explicit human approval was granted.'
   }
   $goal=if($Stage -eq 'dryrun'){'dryRun'}else{'run'}
   $args=@($common+@("org.openrewrite.maven:rewrite-maven-plugin:$RewritePluginVersion`:$goal", "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:$RewriteSpringVersion", '-Drewrite.activeRecipes=org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0'))
   Run $mvn $args
   if($Stage -eq 'dryrun') {Write-Host 'Inspect target/rewrite/rewrite.patch and per-module rewrite patches; record approval before apply.'}
   else {Run 'git' @('diff','--stat')}
  }
  'verify' {
   Run $mvn @($common+@('clean','verify'))
   Run $mvn @($common+@('dependency:tree',"-DoutputFile=$reports/dependency-after.txt"))
   Write-Host 'Maven verification done; runtime/API/security/database checks are separate and NOT implied by this command.'
  }
  'report' {
   Write-Host "Logs: $reports"
   if(Test-Path $status) {Get-Content $status | Out-Host}
   Write-Host 'Agent: complete impact matrix, manual runtime validation, and final PASS/PARTIAL/BLOCKED decision.'
  }
 }
} catch {Write-Error $_; exit 1} finally {Pop-Location}
