[CmdletBinding()]
param(
    [ValidateSet("all")]
    [string]$Profile = "all",

    [string]$Target,

    [ValidateSet("text", "json")]
    [string]$Format = "text",

    [string[]]$Confirm = @(),

    [switch]$AutomaticOnly,

    [switch]$RepositoryOnly
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$subsystem = Split-Path -Parent $ScriptDirectory
$pythonExecutable = Join-Path $subsystem ".venv\Scripts\python.exe"
$pythonPrefix = @()
if ($env:AI_TVC_PYTHON) {
    if (-not (Test-Path -LiteralPath $env:AI_TVC_PYTHON -PathType Leaf)) {
        throw "AI_TVC_PYTHON does not point to a file: $env:AI_TVC_PYTHON"
    }
    $pythonExecutable = $env:AI_TVC_PYTHON
} elseif (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    $py = Get-Command "py" -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        $pythonExecutable = $py.Source
        $selected = $null
        foreach ($candidate in @("-3.12", "-3.11")) {
            & $pythonExecutable $candidate -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { $selected = $candidate; break }
        }
        if ($null -ne $selected) { $pythonPrefix = @($selected) }
    }
    if ($pythonPrefix.Count -eq 0) {
        $command = Get-Command "python" -ErrorAction SilentlyContinue
        if ($null -eq $command) { throw "Python was not found." }
        $pythonExecutable = $command.Source
    }
}

$arguments = @($pythonPrefix)
$arguments += (Join-Path $ScriptDirectory "preflight.py")
$arguments += @("--profile", $Profile, "--format", $Format)
if ($Target) { $arguments += @("--target", $Target) }
if ($AutomaticOnly) { $arguments += "--automatic-only" }
if ($RepositoryOnly) { $arguments += "--repository-only" }
foreach ($gate in $Confirm) { $arguments += @("--confirm", $gate) }
& $pythonExecutable @arguments
exit $LASTEXITCODE
