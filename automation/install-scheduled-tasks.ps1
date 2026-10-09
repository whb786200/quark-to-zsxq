param(
    [switch]$Replace
)

$ErrorActionPreference = "Stop"
$automationRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$runner = Join-Path $automationRoot "run-nightly.cmd"
$supervisor = Join-Path $automationRoot "supervise.cmd"
$taskPath = "\WorkBuddy\"
$runnerTask = "WorkBuddy-ZSXQ-Nightly"
$supervisorTask = "WorkBuddy-ZSXQ-Supervisor"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if (-not (Test-Path -LiteralPath $supervisor)) {
    throw "Supervisor not found: $supervisor"
}

function Remove-TaskIfPresent([string]$name) {
    try {
        schtasks.exe /Delete /TN "$taskPath$name" /F 2>$null | Out-Null
    }
    catch {
        # A missing task is the expected state on first installation.
    }
}

if ($Replace) {
    Remove-TaskIfPresent $runnerTask
    Remove-TaskIfPresent $supervisorTask
}

schtasks.exe /Create /SC DAILY /ST 03:00 /TN "$taskPath$runnerTask" `
    /TR "`"$runner`"" /F /IT | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register $taskPath$runnerTask"
}

schtasks.exe /Create /SC DAILY /ST 02:55 /TN "$taskPath$supervisorTask" `
    /TR "`"$supervisor`"" /F /IT | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register $taskPath$supervisorTask"
}

Write-Output "Registered $taskPath$runnerTask at 03:00"
Write-Output "Registered $taskPath$supervisorTask at 02:55"
Write-Output "Window: 03:00-04:30 Asia/Shanghai"
