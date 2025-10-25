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
$dev = Start-Process -FilePath cmd -ArgumentList "/c","npm","run","dev","--","--port","3000","--strictPort" -PassThru -WindowStyle Hidden

try {
  if (-not (Wait-ForUrl 'http://localhost:3000' 60)) {
    throw 'Dev server did not start in time.'
  }

  Write-Host 'Running Cypress E2E tests against dev server...'
  cmd /c "npx cypress run" | Out-Host
} finally {
  if ($dev -and -not $dev.HasExited) {
    Write-Host 'Stopping dev server...'
    Stop-Process -Id $dev.Id -Force -ErrorAction SilentlyContinue
  }
}
