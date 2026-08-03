[CmdletBinding()]
param(
    [string]$OldProjectRoot = 'REDACTED_001b039044f8\04 - Python\atlas_core'
)

$ErrorActionPreference = 'Stop'
$NewProjectRoot = Split-Path -Parent $PSScriptRoot
$OldEnv = Join-Path $OldProjectRoot '.env'
$NewEnv = Join-Path $NewProjectRoot '.env'

if (Test-Path $NewEnv) {
    Write-Host "Ya existe $NewEnv. No se sobrescribe." -ForegroundColor Yellow
    exit 0
}
if (-not (Test-Path $OldEnv)) {
    throw "No existe el .env antiguo en $OldEnv"
}

Copy-Item -LiteralPath $OldEnv -Destination $NewEnv
Write-Host "Configuración copiada a $NewEnv" -ForegroundColor Green
Write-Warning 'Revisa el archivo .env y no lo añadas a Git.'
