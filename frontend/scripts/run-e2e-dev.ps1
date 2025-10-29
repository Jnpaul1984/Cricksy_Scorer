param()
$ErrorActionPreference = 'Stop'

function Wait-ForUrl($url, $timeoutSec=40) {
  $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
  while ($stopwatch.Elapsed.TotalSeconds -lt $timeoutSec) {
    try {
      $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
    } catch {}
    Start-Sleep -Milliseconds 300
  }
  return $false
}

Write-Host 'Starting Vite dev server on port 3000...'
$frontendDir = Resolve-Path (Join-Path $PSScriptRoot '..')

$apiBase = $Env:API_BASE
if (-not $apiBase -or $apiBase -match 'localhost') {
  $apiBase = 'http://127.0.0.1:8000'
}
$Env:API_BASE = $apiBase
if (-not $Env:VITE_API_BASE) {
  $Env:VITE_API_BASE = $apiBase
}

$dev = Start-Process -FilePath cmd -ArgumentList "/c","npm","run","dev","--","--port","3000","--strictPort" -PassThru -WindowStyle Hidden -WorkingDirectory $frontendDir

try {
  if (-not (Wait-ForUrl 'http://localhost:3000' 60)) {
    throw 'Dev server did not start in time.'
  }

  Write-Host 'Running Cypress E2E tests against dev server...'
  Push-Location $frontendDir
  try {
    Write-Host 'Ensuring Cypress binary is installed...'
    cmd /c "npx cypress install" | Out-Host
    cmd /c "npx cypress run --config-file cypress.config.mjs" | Out-Host
  } finally {
    Pop-Location
  }
} finally {
  if ($dev -and -not $dev.HasExited) {
    Write-Host 'Stopping dev server...'
    Stop-Process -Id $dev.Id -Force -ErrorAction SilentlyContinue
  }
}
