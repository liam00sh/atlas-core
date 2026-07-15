param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'

function Remove-PythonCache {
    param([string]$Root)

    Get-ChildItem -Path $Root -Directory -Filter '__pycache__' -Recurse -Force |
        Sort-Object FullName -Descending |
        ForEach-Object {
            $path = $_.FullName
            $removed = $false

            for ($attempt = 1; $attempt -le 5 -and -not $removed; $attempt++) {
                try {
                    Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
                    $removed = $true
                }
                catch [System.IO.IOException], [System.UnauthorizedAccessException] {
                    if ($attempt -eq 5) {
                        Write-Warning "No se pudo eliminar '$path' porque otro proceso mantiene un archivo abierto. Cierra terminales Python, depuradores y vistas previas de VS Code, espera a que Google Drive termine de sincronizar y vuelve a ejecutar este script."
                    }
                    else {
                        Start-Sleep -Milliseconds (300 * $attempt)
                    }
                }
            }
        }
}

Write-Host 'Cerrando cachés de Python antiguas...' -ForegroundColor Cyan
Remove-PythonCache -Root $PSScriptRoot

Write-Host 'Comprobando sintaxis sin forzar la sustitución concurrente de todos los .pyc...' -ForegroundColor Cyan
python -m compileall core assistant_identity identity tests
if ($LASTEXITCODE -ne 0) {
    throw "compileall terminó con código $LASTEXITCODE"
}

if (-not $SkipTests) {
    Write-Host 'Ejecutando la suite completa...' -ForegroundColor Cyan
    python -m unittest discover -s tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) {
        throw "La suite de tests terminó con código $LASTEXITCODE"
    }
}

Write-Host 'Limpieza, compilación y pruebas terminadas correctamente.' -ForegroundColor Green
