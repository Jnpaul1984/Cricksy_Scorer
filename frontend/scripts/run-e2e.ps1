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
if (-not $apiBase -or $apiBase -match 'localhost') {
  $apiBase = 'http://127.0.0.1:8000'
}
$Env:API_BASE = $apiBase
if (-not $Env:VITE_API_BASE) {
  $Env:VITE_API_BASE = $apiBase
}

# Cypress needs the Electron binary to run in browser mode.
if ($Env:ELECTRON_RUN_AS_NODE) {
  Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
}

Write-Host "Using API base: $apiBase"

$frontendDir = Resolve-Path (Join-Path $PSScriptRoot '..')
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$backendScript = Join-Path $repoRoot 'scripts/run_backend_in_memory.py'
Write-Host 'Starting backend API in in-memory mode...'
$backendProcess = Start-Process -FilePath python -ArgumentList $backendScript -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden

Push-Location $frontendDir
try {
  if (-not (Wait-ForUrl 'http://127.0.0.1:8000/health' 40)) {
    throw 'Backend API did not start in time.'
  }

  Write-Host 'Ensuring Cypress binary is installed...'
  cmd /c "npx cypress install" | Out-Host

  Write-Host 'Building app with VITE_API_BASE...'
  Write-Host "VITE_API_BASE = $Env:VITE_API_BASE"
  # Explicitly pass the env var to npm run build
  $buildEnv = @{
    VITE_API_BASE = $Env:VITE_API_BASE
  }
  foreach ($key in $buildEnv.Keys) {
    [Environment]::SetEnvironmentVariable($key, $buildEnv[$key], 'Process')
  }
  npm run build | Out-Host

  Write-Host 'Starting preview on port 3000...'
  $preview = Start-Process -FilePath cmd -ArgumentList "/c","npm","run","preview","--","--port","3000" -PassThru -WindowStyle Hidden -WorkingDirectory $frontendDir

  try {
    if (-not (Wait-ForUrl 'http://localhost:3000' 40)) {
      throw 'Preview server did not start in time.'
    }

    Write-Host 'Running Cypress E2E tests...'
    cmd /c "npx cypress run --config-file cypress.config.mjs" | Out-Host
  } finally {
    if ($preview -and -not $preview.HasExited) {
      Write-Host 'Stopping preview server...'
      Stop-Process -Id $preview.Id -Force -ErrorAction SilentlyContinue
    }
  }
} finally {
  if ($backendProcess -and -not $backendProcess.HasExited) {
    Write-Host 'Stopping backend API...'
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
  }

  Pop-Location
}
