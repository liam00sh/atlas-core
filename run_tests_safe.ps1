param(
    [switch]$KeepTemp,
    [switch]$SkipDependencyCheck
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$TempDir = Join-Path $ProjectRoot ".pytest_runtime"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

Write-Host "Proyecto: $ProjectRoot"
Write-Host "Temporal pytest: $TempDir"

Set-Location -LiteralPath $ProjectRoot

function Test-PythonModule {
    param([Parameter(Mandatory = $true)][string]$ModuleName)

    & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)"
    return ($LASTEXITCODE -eq 0)
}

if (-not $SkipDependencyCheck) {
    $MissingModules = @()

    foreach ($ModuleName in @("pytest", "psutil", "tzdata")) {
        if (-not (Test-PythonModule -ModuleName $ModuleName)) {
            $MissingModules += $ModuleName
        }
    }

    if ($MissingModules.Count -gt 0) {
        if (-not (Test-Path -LiteralPath $RequirementsFile)) {
            throw "Faltan dependencias ($($MissingModules -join ', ')) y no existe requirements.txt."
        }

        Write-Warning (
            "Faltan dependencias de Python: " +
            ($MissingModules -join ", ") +
            ". Se instalarán desde requirements.txt."
        )

        & python -m pip install -r $RequirementsFile
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudieron instalar las dependencias de requirements.txt."
        }
    }
}

if (-not (Test-PythonModule -ModuleName "pytest")) {
    throw "pytest no está disponible en el entorno virtual activo."
}

if (-not (Test-PythonModule -ModuleName "psutil")) {
    throw "psutil no está disponible en el entorno virtual activo. Ejecuta: python -m pip install -r requirements.txt"
}

if (Test-Path $TempDir) {
    try {
        Get-ChildItem -LiteralPath $TempDir -Force -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    $_.Attributes = 'Normal'
                } catch {
                }
            }

        Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction Stop
    }
    catch {
        $Fallback = Join-Path $env:LOCALAPPDATA (
            "Atlas\pytest_runtime_" + [DateTime]::Now.ToString("yyyyMMdd_HHmmss")
        )
        Write-Warning (
            "No se pudo limpiar .pytest_runtime. " +
            "Se usará una carpeta local alternativa: $Fallback"
        )
        New-Item -ItemType Directory -Path $Fallback -Force | Out-Null

        & python -m pytest -q --tb=short --basetemp="$Fallback"
        $ExitCode = $LASTEXITCODE

        if (-not $KeepTemp -and (Test-Path $Fallback)) {
            try {
                Remove-Item -LiteralPath $Fallback -Recurse -Force -ErrorAction SilentlyContinue
            }
            catch {
            }
        }

        exit $ExitCode
    }
}

New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

& python -m pytest -q --tb=short --basetemp="$TempDir"
$ExitCode = $LASTEXITCODE

if (-not $KeepTemp -and (Test-Path $TempDir)) {
    try {
        Get-ChildItem -LiteralPath $TempDir -Force -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    $_.Attributes = 'Normal'
                } catch {
                }
            }

        Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    catch {
    }
}

exit $ExitCode
