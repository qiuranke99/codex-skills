[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,

    [string]$Name,

    [string]$Target,

    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$repository = Split-Path -Parent $ScriptDirectory
$python = Join-Path $repository ".venv\Scripts\python.exe"
$argumentsPrefix = @()
if ($env:AI_TVC_PYTHON) {
    if (-not (Test-Path -LiteralPath $env:AI_TVC_PYTHON -PathType Leaf)) {
        throw "AI_TVC_PYTHON does not point to a file: $env:AI_TVC_PYTHON"
    }
    $python = $env:AI_TVC_PYTHON
} elseif (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $launcher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $python = $launcher.Source
        $selected = $null
        foreach ($candidate in @("-3.12", "-3.11")) {
            & $python $candidate -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { $selected = $candidate; break }
        }
        if ($null -eq $selected) { throw "Install Python 3.11 or 3.12 before creating a project." }
        $argumentsPrefix = @($selected)
    } else {
        foreach ($candidateName in @("python3.12", "python3.11", "python3", "python")) {
            $command = Get-Command $candidateName -ErrorAction SilentlyContinue
            if ($null -ne $command) { $python = $command.Source; break }
        }
        if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
            throw "Install Python 3.11 or 3.12 before creating a project."
        }
    }
}
$arguments = @($argumentsPrefix)
$arguments += @((Join-Path $ScriptDirectory "new_project.py"), $Destination, "--format", $Format)
if ($Name) { $arguments += @("--name", $Name) }
if ($Target) { $arguments += @("--target", $Target) }
& $python @arguments
exit $LASTEXITCODE
