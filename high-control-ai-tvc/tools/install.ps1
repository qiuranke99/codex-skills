[CmdletBinding()]
param(
    [ValidateSet("sync", "check", "install", "adopt", "status", "audit", "uninstall")]
    [string]$Action = "sync",

    [ValidateSet("auto", "junction", "symlink", "copy")]
    [string]$Mode = "auto",

    [ValidateSet("all", "core")]
    [string]$Profile = "all",

    [string]$Target,

    [ValidateSet("text", "json")]
    [string]$Format = "text",

    [string[]]$Confirm = @(),

    [switch]$AutomaticOnly,

    [switch]$AllowMissing
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-SuitePython {
    if ($env:AI_TVC_PYTHON) {
        if (Test-Path -LiteralPath $env:AI_TVC_PYTHON -PathType Leaf) {
            return @{ Executable = $env:AI_TVC_PYTHON; Prefix = @() }
        }
        throw "AI_TVC_PYTHON does not point to a file: $env:AI_TVC_PYTHON"
    }
    $venvPython = Join-Path (Split-Path -Parent $ScriptDirectory) ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        return @{ Executable = $venvPython; Prefix = @() }
    }
    $py = Get-Command "py" -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        $pySource = $py.Source
        foreach ($version in @("-3.12", "-3.11")) {
            & $pySource $version -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @{ Executable = $pySource; Prefix = @($version) }
            }
        }
    }
    foreach ($name in @("python3.12", "python3.11", "python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return @{ Executable = $command.Source; Prefix = @() }
        }
    }
    throw "Python 3.11 or 3.12 was not found. Install it before running the optional aggregate tooling."
}

$python = Resolve-SuitePython
$arguments = @($python.Prefix)
if ($Action -in @("sync", "check")) {
    if ($Profile -ne "all") {
        throw "Aggregate sync/check supports only Profile=all; core is an install-only compatibility subset."
    }
    $arguments += (Join-Path $ScriptDirectory "release_control.py")
    $arguments += @($Action, "--format", $Format)
    if ($Target) { $arguments += @("--target", $Target) }
    if ($Action -eq "sync") { $arguments += @("--mode", $Mode) }
} elseif ($Action -eq "audit") {
    if ($Profile -ne "all") {
        throw "Aggregate audit supports only Profile=all; core is an install-only compatibility subset."
    }
    $arguments += (Join-Path $ScriptDirectory "preflight.py")
    $arguments += @("--profile", $Profile, "--format", $Format)
    if ($Target) { $arguments += @("--target", $Target) }
    foreach ($gate in $Confirm) { $arguments += @("--confirm", $gate) }
    if ($AutomaticOnly) { $arguments += "--automatic-only" }
} else {
    $arguments += (Join-Path $ScriptDirectory "manage_skills.py")
    $arguments += @($Action, "--profile", $Profile, "--format", $Format)
    if ($Target) { $arguments += @("--target", $Target) }
    if ($Action -eq "install") { $arguments += @("--mode", $Mode) }
    if ($Action -eq "adopt" -and $AllowMissing) { $arguments += "--allow-missing" }
}

$pythonExecutable = $python.Executable
& $pythonExecutable @arguments
exit $LASTEXITCODE
