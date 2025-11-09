const path = require('node:path')
const { defineConfig } = require('cypress')
const { seedMatch } = require('./cypress/support/matchSimulator.runtime.js')

module.exports = defineConfig({
  e2e: {
    async setupNodeEvents(on, config) {
      const projectRoot = config.projectRoot || process.cwd()
      const frontendDir = path.resolve(projectRoot)
      global.__dirname = frontendDir

      on('task', {
        'seed:match': async () => {
          console.log('[cypress.config.cjs] seed:match handler invoked')
          const __dirname = frontendDir
          const apiBase =
            (typeof config.env.API_BASE === 'string' ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            'http://localhost:8000'
          console.log('[cypress.config.cjs] seed:match cwd:', process.cwd(), 'frontendDir:', frontendDir)
          try {
            return await seedMatch(apiBase, frontendDir)
          } catch (err) {
            console.error('[matchSimulator] seedMatch error', err)
            throw err
          }
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
