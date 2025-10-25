<#
One‑click local dev helper for Cricksy Scorer (Windows/PowerShell).

What it does:
- Starts the dev docker compose stack (-d, hot reload)
- Waits for API health at http://localhost:8000/health
- Creates a sample game (Alpha vs Bravo, 20 overs by default)
- Opens scorer and viewer tabs in your default browser

Usage (from repo root):
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-oneclick.ps1

Optional args:
  -TeamA "Team A" -TeamB "Team B" -Overs 20
#>

param(
  [string]$TeamA = "Alpha",
  [string]$TeamB = "Bravo",
  [int]$Overs = 20
)

function Write-Info($msg) { Write-Host "[dev] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[dev] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[dev] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[dev] $msg" -ForegroundColor Red }

$ErrorActionPreference = 'Stop'

# 1) Bring up dev stack (db, cache, api, web)
Write-Info "Starting docker compose (dev) …"
docker compose -f docker-compose.dev.yml up -d --build | Out-Null

# 2) Wait for API health
Write-Info "Waiting for API health at http://localhost:8000/health …"
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
    if ($resp.StatusCode -eq 200) { $healthy = $true; break }
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $healthy) {
  Write-Err "API did not become healthy in time. Check docker logs and retry."
  exit 1
}
Write-Ok "API is healthy."

# 3) Create a sample game
Write-Info "Creating sample game: $TeamA vs $TeamB ($Overs overs) …"
$playersA = @(1..11 | ForEach-Object { "A$_" })
$playersB = @(1..11 | ForEach-Object { "B$_" })

$body = @{
  team_a_name      = $TeamA
  team_b_name      = $TeamB
  players_a        = $playersA
  players_b        = $playersB
  match_type       = "limited"
  overs_limit      = $Overs
  dls_enabled      = $false
  toss_winner_team = $TeamA
  decision         = "bat"
} | ConvertTo-Json -Depth 4

try {
  $g = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/games" -Body $body -ContentType 'application/json'
} catch {
  Write-Err "Failed to create game: $($_.Exception.Message)"
  exit 1
}

# Extract id or game_id
$gid = $null
if ($g.PSObject.Properties.Name -contains 'id' -and $g.id) { $gid = $g.id }
elseif ($g.PSObject.Properties.Name -contains 'game_id' -and $g.game_id) { $gid = $g.game_id }
if (-not $gid) { Write-Err "Could not determine game id from response:"; $g | ConvertTo-Json -Depth 4 | Write-Host; exit 1 }
Write-Ok "Game created: $gid"

# 4) Open scorer + viewer
Start-Process "http://localhost:5173/game/$gid/scoring"
Start-Process "http://localhost:5173/view/$gid"

Write-Ok "Opened scorer and viewer tabs. Happy scoring!"
