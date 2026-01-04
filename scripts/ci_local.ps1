# ==============================================================================
# Cricksy Scorer - Local CI Runner (PowerShell)
# ==============================================================================
# Replicates GitHub Actions CI workflows locally before pushing to main.
# Safe execution: READ-ONLY checks, no auto-fixes, no file modifications.
#
# Usage:
#   .\scripts\ci_local.ps1                 # Run all checks
#   .\scripts\ci_local.ps1 -SkipPreCommit  # Skip pre-commit hooks
#   .\scripts\ci_local.ps1 -SkipFrontend   # Backend only
#   .\scripts\ci_local.ps1 -SkipBackend    # Frontend only
# ==============================================================================

param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipPreCommit
)

$ErrorActionPreference = "Stop"
$OriginalLocation = Get-Location

# ==============================================================================
# Configuration
# ==============================================================================

$REPO_ROOT = Split-Path $PSScriptRoot -Parent
$BACKEND_DIR = Join-Path $REPO_ROOT "backend"
$FRONTEND_DIR = Join-Path $REPO_ROOT "frontend"
$VENV_ACTIVATE = Join-Path $REPO_ROOT ".venv\Scripts\Activate.ps1"

# Environment variables (matches ci.yml)
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:APP_SECRET_KEY = "test-secret-key"
$env:PYTHONPATH = $REPO_ROOT

# ==============================================================================
# Results Tracking
# ==============================================================================

$script:Results = @()

function Add-Result {
    param([string]$Job, [string]$Status)
    $script:Results += [PSCustomObject]@{
        Job = $Job
        Status = $Status
    }
}

function Show-Summary {
    Write-Host "`n=============================================================================="
    Write-Host "CI LOCAL RUNNER - SUMMARY"
    Write-Host "==============================================================================`n"

    $script:Results | Format-Table -AutoSize

    $failures = ($script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
    $skipped = ($script:Results | Where-Object { $_.Status -eq "SKIP" }).Count
    $passed = ($script:Results | Where-Object { $_.Status -eq "PASS" }).Count

    Write-Host "`nTotal: $($script:Results.Count) | Passed: $passed | Failed: $failures | Skipped: $skipped"

    if ($failures -gt 0) {
        Write-Host "`n[FAIL] CI checks failed - fix issues before pushing to main`n" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "`n[PASS] All CI checks passed - safe to push to main`n" -ForegroundColor Green
        exit 0
    }
}

# ==============================================================================
# Prerequisites
# ==============================================================================

function Test-VenvActivation {
    Write-Host "`n[CHECK] Virtual environment..." -ForegroundColor Cyan
    
    if (-not (Test-Path $VENV_ACTIVATE)) {
        Write-Host "[FAIL] .venv\Scripts\Activate.ps1 not found" -ForegroundColor Red
        Write-Host "Create venv with: python -m venv .venv" -ForegroundColor Yellow
        return $false
    }
    
    try {
        & $VENV_ACTIVATE
        Write-Host "[PASS] Virtual environment activated" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[FAIL] Failed to activate venv: $_" -ForegroundColor Red
        return $false
    }
}

# ==============================================================================
# Pre-commit Job
# ==============================================================================

function Invoke-PreCommit {
    Write-Host "`n=============================================================================="
    Write-Host "[JOB] Pre-commit Hooks (CHECK-ONLY)"
    Write-Host "==============================================================================`n"

    Set-Location $REPO_ROOT

    $preCommitCmd = Get-Command pre-commit -ErrorAction SilentlyContinue
    if (-not $preCommitCmd) {
        Write-Host "[FAIL] pre-commit not installed" -ForegroundColor Red
        Write-Host "Install with: pip install pre-commit" -ForegroundColor Yellow
        Add-Result "Pre-commit" "FAIL"
        return $false
    }

    Write-Host "Running: pre-commit run --all-files --show-diff-on-failure"
    pre-commit run --all-files --show-diff-on-failure
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[FAIL] Pre-commit hooks failed" -ForegroundColor Red
        Add-Result "Pre-commit" "FAIL"
        return $false
    }
    
    Write-Host "[PASS] Pre-commit hooks passed" -ForegroundColor Green
    Add-Result "Pre-commit" "PASS"
    return $true
}

# ==============================================================================
# Backend Jobs
# ==============================================================================

function Invoke-BackendLint {
    Write-Host "`n=============================================================================="
    Write-Host "[JOB] Backend Lint"
    Write-Host "==============================================================================`n"

    Set-Location $BACKEND_DIR

    Write-Host "[1/3] ruff check ."
    ruff check .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Ruff lint errors found" -ForegroundColor Red
        Add-Result "Backend: Ruff Lint" "FAIL"
        return $false
    }
    Write-Host "[PASS] Ruff lint" -ForegroundColor Green

    Write-Host "`n[2/3] ruff format --check ."
    ruff format --check .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Code needs formatting" -ForegroundColor Red
        Add-Result "Backend: Ruff Format" "FAIL"
        return $false
    }
    Write-Host "[PASS] Ruff format" -ForegroundColor Green

    Write-Host "`n[3/3] mypy --config-file pyproject.toml --explicit-package-bases ."
    mypy --config-file pyproject.toml --explicit-package-bases .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Type checking errors" -ForegroundColor Red
        Add-Result "Backend: MyPy" "FAIL"
        return $false
    }
    Write-Host "[PASS] MyPy" -ForegroundColor Green

    Add-Result "Backend: Lint" "PASS"
    return $true
}

function Invoke-BackendTests {
    Write-Host "`n=============================================================================="
    Write-Host "[JOB] Backend Tests (matches ci.yml: fast + integration + dls)"
    Write-Host "==============================================================================`n"

    Set-Location $BACKEND_DIR

    # Job 1: Fast unit tests (matches backend-tests job in ci.yml)
    Write-Host "[1/3] Fast unit tests: tests/test_health.py tests/test_results_endpoint.py"
    pytest -q tests/test_health.py tests/test_results_endpoint.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Fast tests failed" -ForegroundColor Red
        Add-Result "Backend: Fast Tests" "FAIL"
        return $false
    }
    Write-Host "[PASS] Fast tests" -ForegroundColor Green

    # Job 2: Integration tests (matches backend-integration-tests job in ci.yml)
    Write-Host "`n[2/3] Integration tests: tests/integration/"
    pytest tests/integration/ -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Integration tests failed" -ForegroundColor Red
        Add-Result "Backend: Integration Tests" "FAIL"
        return $false
    }
    Write-Host "[PASS] Integration tests" -ForegroundColor Green

    # Job 3: DLS calculation tests (matches backend-dls-tests job in ci.yml)
    Write-Host "`n[3/3] DLS calculation tests: tests/test_dls_calculations.py"
    pytest tests/test_dls_calculations.py -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] DLS tests failed" -ForegroundColor Red
        Add-Result "Backend: DLS Tests" "FAIL"
        return $false
    }
    Write-Host "[PASS] DLS tests" -ForegroundColor Green

    Add-Result "Backend: Tests (Fast+Integration+DLS)" "PASS"
    return $true
}

# ==============================================================================
# Frontend Jobs
# ==============================================================================

function Invoke-FrontendBuild {
    Write-Host "`n=============================================================================="
    Write-Host "[JOB] Frontend Build"
    Write-Host "==============================================================================`n"

    Set-Location $FRONTEND_DIR

    Write-Host "[1/3] npm ci"
    npm ci
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] npm ci failed" -ForegroundColor Red
        Add-Result "Frontend: npm ci" "FAIL"
        return $false
    }
    Write-Host "[PASS] npm ci" -ForegroundColor Green

    Write-Host "`n[2/3] npm run type-check"
    npm run type-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Type-check failed" -ForegroundColor Red
        Add-Result "Frontend: Type-check" "FAIL"
        return $false
    }
    Write-Host "[PASS] Type-check" -ForegroundColor Green

    Write-Host "`n[3/3] npm run build-only"
    $env:VITE_API_BASE = "http://localhost:8000"
    npm run build-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Build failed" -ForegroundColor Red
        Add-Result "Frontend: Build" "FAIL"
        return $false
    }
    Write-Host "[PASS] Build" -ForegroundColor Green

    Add-Result "Frontend: Build" "PASS"
    return $true
}

# ==============================================================================
# Main Execution
# ==============================================================================

try {
    Write-Host "`n=============================================================================="
    Write-Host "CRICKSY SCORER - LOCAL CI RUNNER"
    Write-Host "==============================================================================`n"

    # Activate venv (required for backend tools)
    if (-not $SkipBackend) {
        $venvOk = Test-VenvActivation
        if (-not $venvOk) {
            Add-Result "Prerequisites" "FAIL"
            Show-Summary
        }
    }

    # Pre-commit (runs by default unless -SkipPreCommit)
    if (-not $SkipPreCommit) {
        Invoke-PreCommit | Out-Null
    } else {
        Add-Result "Pre-commit" "SKIP"
    }

    # Backend jobs
    if (-not $SkipBackend) {
        Invoke-BackendLint | Out-Null
        Invoke-BackendTests | Out-Null
    } else {
        Add-Result "Backend" "SKIP"
    }

    # Frontend jobs
    if (-not $SkipFrontend) {
        Invoke-FrontendBuild | Out-Null
    } else {
        Add-Result "Frontend" "SKIP"
    }

    # Show summary and exit
    Show-Summary

} finally {
    Set-Location $OriginalLocation
}
