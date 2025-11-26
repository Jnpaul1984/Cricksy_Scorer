// Custom Cypress commands for Cricksy Scorer E2E tests

/**
 * Wait for game state to be ready after page load/reload
 */
Cypress.Commands.add(
  "waitForGameReady",
  (gameId: string, timeout = 10000) => {
    // Wait for scoreboard elements to appear, which indicates game data is loaded
    cy.get("[data-testid='scoreboard-runs']", { timeout }).should("exist")
    cy.get("[data-testid='scoreboard-wkts']", { timeout }).should("exist")

    // Small additional wait to let WebSocket state settle
    cy.wait(500)
  }
)

/**
 * Inject player IDs directly into the game store to enable scoring
 * Workaround for WebSocket race condition where UI state isn't initialized from backend
 */
Cypress.Commands.add(
  "setGamePlayers",
  (strikerId: string, nonStrikerId: string, bowlerId?: string | null) => {
    cy.window()
      .its("app", { timeout: 10000 })
      .then((app: any) => {
        try {
          const pinia = app.config.globalProperties.$pinia
          const gameStore = pinia?._s?.get("game")
          if (gameStore) {
            gameStore.setSelectedStriker(strikerId)
            gameStore.setSelectedNonStriker(nonStrikerId)
            if (bowlerId !== undefined) {
              gameStore.setSelectedBowler(bowlerId)
            }
          }
        } catch (e) {
          cy.log("Failed to set game players:", e)
        }
      })

    cy.wait(100)
  }
)

const TOKEN_KEY = "cricksy_token"
type SnapshotBody = Record<string, any>
type SnapshotFlag =
  | "needs_new_batter"
  | "needs_new_over"
  | "needs_new_innings"
  | "is_game_over"

/**
 * Visit a route with fake authentication
 */
Cypress.Commands.add("visitWithAuth", (path: string, role = "org_pro") => {
  cy.intercept("GET", "**/auth/me", {
    id: "cypress-user",
    email: "cypress@example.com",
    role,
    is_superuser: role === "superuser",
  }).as("authMe")

  cy.visit(path, {
    onBeforeLoad(win) {
      win.localStorage.setItem(TOKEN_KEY, "e2e-token")
    },
  })

  cy.wait("@authMe")
})

/**
 * Visit a page & wait for the first snapshot response.
 */
Cypress.Commands.add("visitWithSnapshot", (path: string, role = "org_pro") => {
  cy.intercept("GET", "**/games/*").as("snapshot")
  cy.visitWithAuth(path, role)

  return cy.wait("@snapshot", { timeout: 20000 }).then((interception) => {
    const body = interception?.response?.body as SnapshotBody
    expect(interception?.response?.statusCode, "snapshot status").to.eq(200)
    expect(body, "snapshot body").to.exist
    return interception
  })
})

/**
 * Wait for a snapshot that satisfies a predicate
 */
Cypress.Commands.add(
  "waitForSnapshotWhere",
  (predicate: (body: SnapshotBody) => boolean, maxAttempts = 6) => {
    const poll = (remaining: number): any => {
      return cy.wait("@snapshot", { timeout: 20000 }).then((interception) => {
        const body = interception.response?.body as SnapshotBody | undefined

        expect(interception.response?.statusCode, "snapshot status").to.eq(200)
        expect(body, "snapshot body").to.exist

        if (body && predicate(body)) {
          return body
        }

        if (remaining <= 0) {
          throw new Error("Snapshot condition not met")
        }

        return poll(remaining - 1)
      })
    }

    return poll(maxAttempts)
  }
)

/**
 * Wait for a specific snapshot flag to reach a value
 */
Cypress.Commands.add(
  "waitForSnapshotFlag",
  (flag: SnapshotFlag, expected: boolean, maxAttempts = 6) => {
    return cy.waitForSnapshotWhere(
      (body) => Boolean(body?.[flag]) === expected,
      maxAttempts
    )
  }
)

// TypeScript type declarations
declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Wait for game state to be ready (WebSocket connected and game loaded)
       * @param gameId - The game ID to wait for
       * @param timeout - Maximum time to wait in milliseconds (default: 10000)
       */
      waitForGameReady(gameId: string, timeout?: number): Chainable<void>

      /**
       * Inject player IDs into the game store to enable scoring
       * @param strikerId - Current striker ID
       * @param nonStrikerId - Current non-striker ID
       * @param bowlerId - Current bowler ID (optional)
       */
      setGamePlayers(
        strikerId: string,
        nonStrikerId: string,
        bowlerId?: string | null
      ): Chainable<void>

      /**
       * Visit a route while faking auth so protected pages load without manual login
       */
      visitWithAuth(path: string, role?: string): Chainable<void>

      /**
       * Visit a route that triggers /games/:id/snapshot and wait for the first response
       */
      visitWithSnapshot(path: string, role?: string): Chainable<any>

      /**
       * Wait for the next snapshot response that satisfies the provided predicate.
       */
      waitForSnapshotWhere(
        predicate: (body: Record<string, any>) => boolean,
        maxAttempts?: number
      ): Chainable<any>

      /**
       * Wait for a specific gate flag in the snapshot payload to match the desired value.
       */
      waitForSnapshotFlag(
        flag: SnapshotFlag,
        expected: boolean,
        maxAttempts?: number
      ): Chainable<any>
    }
  }
}

export {}
