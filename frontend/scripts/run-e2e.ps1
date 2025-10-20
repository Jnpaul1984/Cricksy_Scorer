param()
$ErrorActionPreference = 'Stop'

function Wait-ForUrl($url, $timeoutSec=30) {
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

$apiBase = $Env:API_BASE
if (-not $apiBase) {
  $apiBase = 'http://localhost:8000'
}
$Env:API_BASE = $apiBase
if (-not $Env:VITE_API_BASE) {
  $Env:VITE_API_BASE = $apiBase
}

Write-Host "Using API base: $apiBase"

Write-Host 'Building app...'
cmd /c "npm run build" | Out-Host

Write-Host 'Starting preview on port 3000...'
$preview = Start-Process -FilePath cmd -ArgumentList "/c","npm","run","preview","--","--port","3000" -PassThru -WindowStyle Hidden

try {
  if (-not (Wait-ForUrl 'http://localhost:3000' 40)) {
    throw 'Preview server did not start in time.'
  }

  Write-Host 'Running Cypress E2E tests...'
  cmd /c "npx cypress run" | Out-Host
} finally {
  if ($preview -and -not $preview.HasExited) {
    Write-Host 'Stopping preview server...'
    Stop-Process -Id $preview.Id -Force -ErrorAction SilentlyContinue
  }
}
