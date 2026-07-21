[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot '.env'

Write-Host 'Configuración local de Telegram para Atlas' -ForegroundColor Cyan
Write-Host 'El token quedará en .env, archivo local excluido de Git.'
$secureToken = Read-Host 'Pega el token del bot' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr).Trim()
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($token)) {
    throw 'El token está vacío.'
}
if ($token -notmatch '^[1-9][0-9]{4,15}:[A-Za-z0-9_-]{20,}$') {
    throw 'El token no tiene el formato esperado de Telegram.'
}

$lines = @(
    '# Configuración local privada de Atlas. No compartir.'
    'ATLAS_TELEGRAM_ENABLED=true'
    "ATLAS_TELEGRAM_BOT_TOKEN=$token"
    'ATLAS_TELEGRAM_POLL_TIMEOUT=30'
    'ATLAS_TELEGRAM_LINK_CODE_TTL_SECONDS=600'
    'ATLAS_TELEGRAM_RATE_LIMIT_PER_MINUTE=20'
    'ATLAS_TELEGRAM_MAX_INPUT_CHARACTERS=8000'
    'ATLAS_TELEGRAM_MAX_CONCURRENT_OPERATIONS=4'
    'ATLAS_TELEGRAM_PROCESSING_TIMEOUT_SECONDS=120'
    'ATLAS_TELEGRAM_SESSION_TTL_SECONDS=86400'
)
[IO.File]::WriteAllLines($EnvPath, $lines, [Text.UTF8Encoding]::new($false))
$token = $null
Write-Host "Configuración guardada en: $EnvPath" -ForegroundColor Green
Write-Host 'El token no se ha mostrado en pantalla.'
