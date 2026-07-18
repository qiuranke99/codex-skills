[CmdletBinding()]
param(
    [ValidateSet("json")]
    [string]$Format = "json"
)

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageRoot = Split-Path -Parent $ScriptDirectory
$PythonExecutable = $null
$PythonPrefix = @()

function Invoke-PythonCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [object[]]$ArgumentList = @(),
        [switch]$CaptureOutput
    )

    $PreviousErrorActionPreference = $ErrorActionPreference
    $Output = @()
    $ExitCode = 1
    try {
        # Windows PowerShell 5.1 promotes redirected native stderr to the
        # PowerShell error stream. Capture the process exit code explicitly so
        # expected native stderr cannot terminate this wrapper before the code
        # is inspected; PowerShell 7 follows the same deterministic path.
        $ErrorActionPreference = "Continue"
        if ($CaptureOutput) {
            $Output = @(& $FilePath @ArgumentList 2>&1)
        } else {
            & $FilePath @ArgumentList *> $null
        }
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
    return [PSCustomObject]@{
        ExitCode = $ExitCode
        Output = $Output
    }
}

if ($env:AI_AD_REFERENCE_PYTHON) {
    if (-not (Test-Path -LiteralPath $env:AI_AD_REFERENCE_PYTHON -PathType Leaf)) {
        throw "AI_AD_REFERENCE_PYTHON is not an executable file"
    }
    $PythonExecutable = $env:AI_AD_REFERENCE_PYTHON
} else {
    $BundledPython = Join-Path $HOME ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\bin\python3"
    $Candidates = @(
        @{ Command = "python3.12"; Prefix = @() },
        @{ Command = "python3.11"; Prefix = @() },
        @{ Command = "python3.10"; Prefix = @() },
        @{ Command = $BundledPython; Prefix = @() },
        @{ Command = "python3"; Prefix = @() },
        @{ Command = "python"; Prefix = @() },
        @{ Command = "py"; Prefix = @("-3") }
    )
    foreach ($Candidate in $Candidates) {
        $Resolved = $null
        if ([IO.Path]::IsPathRooted($Candidate.Command)) {
            if (Test-Path -LiteralPath $Candidate.Command -PathType Leaf) {
                $Resolved = $Candidate.Command
            }
        } else {
            $Command = Get-Command $Candidate.Command -CommandType Application -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($Command) {
                if ($Command.Path) {
                    $Resolved = $Command.Path
                } elseif ($Command.Definition) {
                    $Resolved = $Command.Definition
                } elseif ($Command.Source) {
                    $Resolved = $Command.Source
                }
            }
        }
        if ($Resolved) {
            $ProbeArguments = @($Candidate.Prefix) + @(
                "-I", "-B", "-c",
                "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
            )
            $ProbeResult = Invoke-PythonCommand -FilePath $Resolved -ArgumentList $ProbeArguments
            if ($ProbeResult.ExitCode -eq 0) {
                $PythonExecutable = $Resolved
                $PythonPrefix = @($Candidate.Prefix)
                break
            }
        }
    }
}

if (-not $PythonExecutable) {
    throw "Python 3.10 or newer is required for package-local contract tests"
}

$env:PYTHONDONTWRITEBYTECODE = "1"
$VersionArguments = @($PythonPrefix) + @(
    "-I", "-B", "-c",
    "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
)
$VersionResult = Invoke-PythonCommand -FilePath $PythonExecutable -ArgumentList $VersionArguments
if ($VersionResult.ExitCode -ne 0) {
    throw "Python 3.10 or newer is required for package-local contract tests"
}

$ContractArguments = @($PythonPrefix) + @(
    "-I", "-B", "-c",
    'import runpy, sys; sys.path.insert(0, sys.argv[1]); runpy.run_path(sys.argv[2], run_name="__main__")',
    $ScriptDirectory,
    (Join-Path $ScriptDirectory "test_contract.py")
)
$ContractResult = Invoke-PythonCommand -FilePath $PythonExecutable -ArgumentList $ContractArguments -CaptureOutput
foreach ($Line in @($ContractResult.Output)) {
    [Console]::Error.WriteLine($Line.ToString())
}
if ($ContractResult.ExitCode -ne 0) {
    throw "Package-local contract tests failed with exit $($ContractResult.ExitCode)"
}

$Standalone = [ordered]@{
    gate_mode = "standalone_package"
    package_contract_ready = $true
    ready_for_skill_workflow = $true
    proof_scope = "package_contract_only"
}
[Console]::Out.WriteLine(($Standalone | ConvertTo-Json -Compress))
