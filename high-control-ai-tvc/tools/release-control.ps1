[CmdletBinding()]
param(
    [ValidateSet("check", "sync")]
    [string]$Action = "check",

    [ValidateSet("text", "json")]
    [string]$Format = "json",

    [string]$Target,

    [string]$ProjectRoot,

    [ValidateSet("auto", "junction", "symlink", "copy")]
    [string]$Mode = "auto"
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$Subsystem = Split-Path -Parent $ScriptDirectory
$CodexHome = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
} else {
    Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
}
$ReleaseReceipt = Join-Path $CodexHome ".ai-tvc-releases\release-receipt.json"
$PythonExecutable = $null

if ($env:AI_TVC_PYTHON) {
    $PythonExecutable = $env:AI_TVC_PYTHON
} elseif (Test-Path -LiteralPath $ReleaseReceipt -PathType Leaf) {
    $Receipt = Get-Content -LiteralPath $ReleaseReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -ne $Receipt.validation) {
        $PythonExecutable = $Receipt.validation.python_executable
    }
}

if (-not $PythonExecutable) {
    $LocalRuntime = Join-Path $Subsystem ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $LocalRuntime -PathType Leaf) {
        $PythonExecutable = $LocalRuntime
    }
}

if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Pinned High-Control runtime is unavailable. Run setup-runtime.ps1 and release sync before production."
}

$env:PYTHONDONTWRITEBYTECODE = "1"
$Arguments = @((Join-Path $ScriptDirectory "release_control.py"), $Action, "--format", $Format)
if ($Target) { $Arguments += @("--target", $Target) }
if ($Action -eq "check" -and $ProjectRoot) { $Arguments += @("--project-root", $ProjectRoot) }
if ($Action -eq "sync") { $Arguments += @("--mode", $Mode) }

Push-Location -LiteralPath $CodexHome
try {
    & $PythonExecutable @Arguments
    $ExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $ExitCode
