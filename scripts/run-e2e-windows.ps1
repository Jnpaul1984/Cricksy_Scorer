# PowerShell script to run repo-specific E2E flow (in-memory backend)
# Usage: .\scripts\run-e2e-windows.ps1 [cypress-spec]
param(
  [string]$CypressSpec = "cypress/e2e/**/*.cy.{js,ts}"
)

set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Get-Location).Path
Write-Host "[run-e2e-windows] repoRoot = $repoRoot"

function Wait-ForUrl {
  param([string]$Url, [int]$TimeoutSeconds = 60)
  for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
      if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    Start-Sleep -Seconds 1
  }
  return $false
}

# Step 1: Run backend test to seed data (in-memory)
Push-Location (Join-Path $repoRoot 'backend')
Write-Host "==> Running backend pytest (seeding) in in-memory mode"
$env:CRICKSY_IN_MEMORY_DB = '1'
& python -m pytest -q tests\test_simulated_t20_match.py
Pop-Location

# Step 2: Start in-memory backend
Write-Host "==> Starting backend (in-memory) via scripts/run_backend_in_memory.py"
$backendScript = Join-Path $repoRoot 'scripts\run_backend_in_memory.py'
$backendProc = Start-Process -FilePath python -ArgumentList $backendScript -WorkingDirectory $repoRoot -PassThru
Start-Sleep -Seconds 1

try {
  # Wait for backend health
  $healthUrl = 'http://127.0.0.1:8000/health'
  Write-Host "Waiting for backend at $healthUrl ..."
  if (-not (Wait-ForUrl -Url $healthUrl -TimeoutSeconds 60)) {
    throw "Backend did not become ready within timeout"
  }
  Write-Host "Backend is healthy."

  # Step 3: Build and preview frontend
  Push-Location (Join-Path $repoRoot 'frontend')
  Write-Host "==> Installing frontend deps"
  $env:VITE_API_BASE = 'http://127.0.0.1:8000'
  $env:API_BASE = 'http://127.0.0.1:8000'
  npm ci

  Write-Host "==> Building frontend"
  npm run build

  Write-Host "==> Starting preview on port 3000"
  $previewProc = Start-Process -FilePath npm -ArgumentList 'run','preview','--','--port','3000' -WorkingDirectory (Join-Path $repoRoot 'frontend') -PassThru

  Pop-Location

  # Wait for frontend preview
  $frontUrl = 'http://127.0.0.1:3000'
  Write-Host "Waiting for frontend at $frontUrl ..."
  if (-not (Wait-ForUrl -Url $frontUrl -TimeoutSeconds 60)) {
    throw "Frontend preview did not become ready within timeout"
  }
  Write-Host "Frontend is ready."

  # Step 4: Run Cypress
  Write-Host "==> Running Cypress specs: $CypressSpec"
  $env:CYPRESS_BASE_URL = 'http://localhost:3000'
  npx cypress run --spec $CypressSpec
}
finally {
  Write-Host "==> Cleaning up processes"
  try { if ($previewProc -and $previewProc.Id) { Stop-Process -Id $previewProc.Id -ErrorAction SilentlyContinue } } catch {}
  try { if ($backendProc -and $backendProc.Id) { Stop-Process -Id $backendProc.Id -ErrorAction SilentlyContinue } } catch {}
}
