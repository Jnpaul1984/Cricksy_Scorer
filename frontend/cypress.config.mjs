import path from "node:path";

import { defineConfig } from "cypress";

import {
  seedMatch,
  createLiveGame,
  seedOverComplete,
  seedInningsBreak,
  seedWeatherDelay,
} from "./cypress/support/matchSimulator.runtime.js";

export default defineConfig({
  e2e: {
    // Helps with sticky/fixed headers and slow async renders
    viewportWidth: 1600,
    viewportHeight: 1200,
    defaultCommandTimeout: 15000,
    taskTimeout: 120000, // 2 minutes for complex tasks like seed:match

    async setupNodeEvents(on, config) {
      const projectRoot = config.projectRoot || process.cwd();
      const frontendDir = path.resolve(projectRoot);

      on("task", {
        "seed:match": async () => {
          console.log("[cypress.config.mjs] seed:match handler invoked");
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://127.0.0.1:8000";
          console.log("[cypress.config.mjs] seed:match cwd:", process.cwd(), "frontendDir:", frontendDir);
          try {
            return await seedMatch(apiBase, frontendDir);
          } catch (err) {
            console.error("[matchSimulator] seedMatch error", err);
            throw err;
          }
        },
        "seed:live-game": async () => {
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://127.0.0.1:8000";
          return await createLiveGame(apiBase);
        },
        "seed:over-complete": async () => {
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://127.0.0.1:8000";
          return await seedOverComplete(apiBase);
        },
        "seed:innings-break": async () => {
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://127.0.0.1:8000";
          return await seedInningsBreak(apiBase);
        },
        "seed:weather-delay": async () => {
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://127.0.0.1:8000";
          return await seedWeatherDelay(apiBase);
        },
      });

      return config;
    },
    baseUrl: "http://localhost:3000",
    supportFile: "cypress/support/e2e.ts",
    specPattern: "cypress/e2e/**/*.cy.{js,ts,jsx,tsx}",
    fixturesFolder: "cypress/fixtures",
    video: false,
    screenshotOnRunFailure: false,
    env: {
      API_BASE: process.env.API_BASE || "http://127.0.0.1:8000",
    },
  },
});
