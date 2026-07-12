[CmdletBinding()]
param(
    [string]$Venv,

    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$arguments = @()
$launcherSource = $null

if ($env:AI_TVC_PYTHON) {
    if (-not (Test-Path -LiteralPath $env:AI_TVC_PYTHON -PathType Leaf)) {
        throw "AI_TVC_PYTHON does not point to a file: $env:AI_TVC_PYTHON"
    }
    $launcherSource = $env:AI_TVC_PYTHON
} else {
    $launcher = Get-Command "py" -ErrorAction SilentlyContinue
}

if ($null -eq $launcherSource -and $null -ne $launcher) {
    $launcherSource = $launcher.Source
    $version = $null
    foreach ($candidate in @("-3.12", "-3.11")) {
        & $launcherSource $candidate -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $version = $candidate; break }
    }
    if ($null -eq $version) { throw "Install Python 3.11 or 3.12 before creating the suite runtime." }
    $arguments += $version
} elseif ($null -eq $launcherSource) {
    $launcher = Get-Command "python" -ErrorAction SilentlyContinue
    if ($null -eq $launcher) { throw "Install Python 3.11 or 3.12 before creating the suite runtime." }
    $launcherSource = $launcher.Source
}

$arguments += (Join-Path $ScriptDirectory "setup_runtime.py")
$arguments += @("--format", $Format)
if ($Venv) { $arguments += @("--venv", $Venv) }
& $launcherSource @arguments
exit $LASTEXITCODE
