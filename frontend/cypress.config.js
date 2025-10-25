import { defineConfig } from 'cypress'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'
import { seedMatch } from './cypress/support/matchSimulator.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      on('task', {
        'seed:match': async () => {
          const apiBase =
            config.env.API_BASE ||
            process.env.API_BASE ||
            'http://localhost:8000'
          const frontendDir = path.resolve(__dirname)
          const result = await seedMatch(apiBase, frontendDir)
          return result
        },
      })
      return config
    },
    baseUrl: 'http://localhost:3000',
    supportFile: false,
    specPattern: 'cypress/e2e/**/*.cy.{js,ts,jsx,tsx}',
    fixturesFolder: 'cypress/fixtures',
    video: false,
    screenshotOnRunFailure: false,
    env: {
      API_BASE: process.env.API_BASE || 'http://localhost:8000',
    },
  },
})
