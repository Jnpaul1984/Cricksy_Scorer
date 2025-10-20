import { defineConfig } from 'cypress'
import path from 'node:path'

import { seedMatch } from './cypress/support/matchSimulator'

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      on('task', {
        async 'seed:match'() {
          const apiBase: string =
            (config.env.API_BASE as string | undefined) ||
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
