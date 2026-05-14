import { spawn } from 'node:child_process'

const frontendDir = new URL('..', import.meta.url)
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const npxCmd = process.platform === 'win32' ? 'npx.cmd' : 'npx'
const previewUrl = process.env.E2E_BASE_URL || 'http://localhost:3000'
const apiBase = process.env.API_BASE || 'http://127.0.0.1:8000'

// ---------------------------------------------------------------------------
// Suite → spec mapping
// A "suite" groups one or more specs that share CI eligibility requirements.
// CI-safe suites (analyst, coach, smoke) use intercepts only and need no
// live backend.  The scoring suite requires a seeded backend and should only
// be run in full-stack environments.
// ---------------------------------------------------------------------------
const SUITES = {
  analyst: 'cypress/e2e/analyst_workspace_data_library.cy.ts',
  coach: 'cypress/e2e/coach_workspace_smoke.cy.ts',
  smoke: 'cypress/e2e/analyst_workspace_data_library.cy.ts,cypress/e2e/coach_workspace_smoke.cy.ts',
  scoring: [
    'cypress/e2e/scoring_gate_smoke.cy.ts',
    'cypress/e2e/match_creation_flow.cy.ts',
    'cypress/e2e/next_over_flow.cy.ts',
    'cypress/e2e/wicket_new_batter_flow.cy.ts',
    'cypress/e2e/innings_flip_flow.cy.ts',
    'cypress/e2e/weather_interruption_flow.cy.ts',
  ].join(','),
}

// Resolve the spec(s) to run:
//  1. --suite <name>  flag on the CLI
//  2. CYPRESS_SPEC env var (legacy override)
//  3. Default: analyst workspace (backwards-compatible)
function resolveSpec() {
  const suiteArgIdx = process.argv.indexOf('--suite')
  if (suiteArgIdx !== -1) {
    const suiteName = process.argv[suiteArgIdx + 1]
    if (!suiteName || !SUITES[suiteName]) {
      const valid = Object.keys(SUITES).join(', ')
      throw new Error(
        `Unknown --suite "${suiteName}". Valid suites: ${valid}`,
      )
    }
    return SUITES[suiteName]
  }
  return process.env.CYPRESS_SPEC || 'cypress/e2e/analyst_workspace_data_library.cy.ts'
}

const cypressSpec = resolveSpec()

const env = {
  ...process.env,
  API_BASE: apiBase,
  VITE_API_BASE: process.env.VITE_API_BASE || apiBase,
}

let previewProcess = null

function run(command, args, extraEnv = env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: frontendDir,
      env: extraEnv,
      stdio: 'inherit',
    })

    child.on('exit', (code) => {
      if (code === 0) {
        resolve()
        return
      }
      reject(new Error(`${command} ${args.join(' ')} exited with code ${code ?? 'unknown'}`))
    })

    child.on('error', reject)
  })
}

async function waitForUrl(url, timeoutMs = 60_000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url)
      if (response.status >= 200 && response.status < 500) {
        return
      }
    } catch {
      // keep polling until the timeout expires
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

function stopPreview() {
  if (previewProcess && !previewProcess.killed) {
    previewProcess.kill('SIGTERM')
  }
}

process.on('SIGINT', () => {
  stopPreview()
  process.exit(130)
})

process.on('SIGTERM', () => {
  stopPreview()
  process.exit(143)
})

try {
  try {
    await run(npxCmd, ['cypress', 'install'])
  } catch (error) {
    throw new Error(
      `Cypress binary install failed. If download.cypress.io is blocked in this environment, rerun this command in GitHub Actions or a network-enabled local setup. ${(error instanceof Error) ? error.message : String(error)}`,
    )
  }
  await run(npmCmd, ['run', 'build-only'])

  previewProcess = spawn(npmCmd, ['run', 'preview', '--', '--port', '3000'], {
    cwd: frontendDir,
    env,
    stdio: 'inherit',
  })

  await waitForUrl(previewUrl)
  await run(npxCmd, ['cypress', 'run', '--config-file', 'cypress.config.mjs', '--spec', cypressSpec])
} finally {
  stopPreview()
}
