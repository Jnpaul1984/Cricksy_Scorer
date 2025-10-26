import path from "node:path";
import { defineConfig } from "cypress";
import { seedMatch } from "./cypress/support/matchSimulator.runtime.js";

export default defineConfig({
  e2e: {
    // Helps with sticky/fixed headers and slow async renders
    viewportWidth: 1600,
    viewportHeight: 1200,
    defaultCommandTimeout: 15000,

    async setupNodeEvents(on, config) {
      const projectRoot = config.projectRoot || process.cwd();
      const frontendDir = path.resolve(projectRoot);

      on("task", {
        "seed:match": async () => {
          console.log("[cypress.config.mjs] seed:match handler invoked");
          const apiBase =
            (typeof config.env.API_BASE === "string" ? config.env.API_BASE : undefined) ||
            process.env.API_BASE ||
            "http://localhost:8000";
          console.log("[cypress.config.mjs] seed:match cwd:", process.cwd(), "frontendDir:", frontendDir);
          try {
            return await seedMatch(apiBase, frontendDir);
          } catch (err) {
            console.error("[matchSimulator] seedMatch error", err);
            throw err;
          }
        },
      });

      return config;
    },
    baseUrl: "http://localhost:3000",
    supportFile: false,
    specPattern: "cypress/e2e/**/*.cy.{js,ts,jsx,tsx}",
    fixturesFolder: "cypress/fixtures",
    video: false,
    screenshotOnRunFailure: false,
    env: {
      API_BASE: process.env.API_BASE || "http://localhost:8000",
    },
  },
});
