"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const cypress_1 = require("cypress");
const node_path_1 = require("node:path");
// @ts-expect-error - runtime helper is generated JS without type declarations
const matchSimulator_runtime_js_1 = require("./cypress/support/matchSimulator.runtime.js");
exports.default = (0, cypress_1.defineConfig)({
    e2e: {
        async setupNodeEvents(on, config) {
            const projectRoot = config.projectRoot || process.cwd();
            const frontendDir = node_path_1.default.resolve(projectRoot);
            on('task', {
                'seed:match': async () => {
                    console.log('[cypress.config.ts] seed:match handler invoked');
                    const apiBase = (typeof config.env.API_BASE === 'string' ? config.env.API_BASE : undefined) ||
                        process.env.API_BASE ||
                        'http://localhost:8000';
                    console.log('[cypress.config.ts] seed:match cwd:', process.cwd(), 'frontendDir:', frontendDir);
                    try {
                        return await (0, matchSimulator_runtime_js_1.seedMatch)(apiBase, frontendDir);
                    }
                    catch (err) {
                        console.error('[matchSimulator] seedMatch error', err);
                        throw err;
                    }
                },
            });
            return config;
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
});
