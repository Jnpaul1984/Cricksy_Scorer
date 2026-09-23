const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

type Rgba = { red: number; green: number; blue: number; alpha: number }

const parseColor = (value: string): Rgba => {
  const parts = value.match(/[\d.]+/g)?.map(Number) ?? []
  return {
    red: parts[0] ?? 0,
    green: parts[1] ?? 0,
    blue: parts[2] ?? 0,
    alpha: parts[3] ?? 1,
  }
}

const composite = (foreground: Rgba, background: Rgba): Rgba => ({
  red: foreground.red * foreground.alpha + background.red * (1 - foreground.alpha),
  green: foreground.green * foreground.alpha + background.green * (1 - foreground.alpha),
  blue: foreground.blue * foreground.alpha + background.blue * (1 - foreground.alpha),
  alpha: 1,
})

const luminance = ({ red, green, blue }: Rgba): number => {
  const channel = (value: number) => {
    const normalized = value / 255
    return normalized <= 0.03928
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)
}

const contrastRatio = (foreground: Rgba, background: Rgba): number => {
  const lighter = Math.max(luminance(foreground), luminance(background))
  const darker = Math.min(luminance(foreground), luminance(background))
  return (lighter + 0.05) / (darker + 0.05)
}

const expectReadableControl = (selector: string) => {
  return cy.get(selector).should('be.visible').and('not.be.disabled').should(($control) => {
    const element = $control[0] as HTMLElement
    const panel = element.closest('.scoring-panel') as HTMLElement
    const style = getComputedStyle(element)
    const panelBackground = parseColor(getComputedStyle(panel).backgroundColor)
    const controlBackground = composite(parseColor(style.backgroundColor), panelBackground)
    const ratio = contrastRatio(parseColor(style.color), controlBackground)

    expect(
      ratio,
      `${selector} text contrast (${style.color} on ${style.backgroundColor})`,
    ).to.be.at.least(4.5)
  })
}

const setColorScheme = (value: 'dark' | 'light') =>
  cy.then(() => Cypress.automation('remote:debugger:protocol', {
    command: 'Emulation.setEmulatedMedia',
    params: {
      features: [{ name: 'prefers-color-scheme', value }],
    },
  }))

describe('Scoring gate smoke checks', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
    setColorScheme('dark')
  })

  it('keeps the scoring console read-only once the match is completed', () => {
    cy.task('seed:match').then((result: any) => {
      const gameId = String(result.gameId)
      cy.visitWithSnapshot(`/game/${gameId}/scoring`)
        .its('response.body')
        .then((snap) => {
          expect(Boolean(snap?.is_game_over), 'is_game_over flag').to.be.true
        })

      cy.get('[data-testid="scorer-controls"]')
        .should('be.visible')
        .and('have.attr', 'aria-disabled', 'true')
      cy.get('[data-testid="submit-delivery"]').should('be.disabled')
    })
  })

  it('submits a legal delivery when no gates are raised', () => {
    cy.task('seed:live-game').then((res: any) => {
      const gameId = String(res.gameId)
      cy.intercept('POST', `**/games/${gameId}/deliveries`).as('scoreDelivery')

      let startingRuns = 0
      cy.visitWithSnapshot(`/game/${gameId}/scoring`)
        .its('response.body')
        .then((snap) => {
          startingRuns = Number(snap?.total_runs ?? 0)
          expect(Boolean(snap?.needs_new_innings), 'needs_new_innings flag').to.be.false
          expect(Boolean(snap?.needs_new_over), 'needs_new_over flag').to.be.false
          expect(Boolean(snap?.needs_new_batter), 'needs_new_batter flag').to.be.false
        })

      cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
      cy.get('[data-testid="delivery-run-4"]').click()
      cy.get('[data-testid="submit-delivery"]').click()

      cy.wait('@scoreDelivery').its('response.statusCode').should('be.oneOf', [200, 201, 204])
      cy.waitForSnapshotWhere((body) => Number(body?.total_runs ?? 0) >= startingRuns + 4)
      cy.get('[data-testid="scoreboard-runs"]')
        .invoke('text')
        .then((text) => {
          expect(Number(text.trim()), 'updated total runs').to.be.at.least(startingRuns + 4)
        })
    })
  })

  it('presents the first-innings action clearly and keeps dark-theme scoring controls operable', () => {
    cy.viewport(1366, 768)
    cy.window().should(($window) => {
      expect($window.innerWidth).to.equal(1366)
      expect($window.innerHeight).to.equal(768)
    })
    const stamp = Date.now()
    const teamAName = `Visibility A ${stamp}`
    const teamBName = `Visibility B ${stamp}`

    cy.request('POST', `${API_BASE}/games`, {
      team_a_name: teamAName,
      team_b_name: teamBName,
      players_a: Array.from({ length: 11 }, (_, index) => `Visibility A ${index + 1}`),
      players_b: Array.from({ length: 11 }, (_, index) => `Visibility B ${index + 1}`),
      match_type: 'limited',
      overs_limit: 2,
      toss_winner_team: teamAName,
      decision: 'bat',
    }).then(({ body: game }) => {
      const gameId = String(game.id)
      cy.intercept('POST', `**/games/${gameId}/deliveries`).as('scoreDelivery')

      cy.visitWithSnapshot(`/game/${gameId}/scoring`).then(({ response }) => {
        expect(Number(response?.body?.current_inning ?? 0), 'real pre-first innings').to.equal(0)
        expect(Boolean(response?.body?.needs_new_innings), 'pre-first innings gate').to.be.true
      })

      cy.get('[data-testid="gate-innings"]')
        .should('be.visible')
        .and('contain.text', 'Ready to Start')
        .and('not.contain.text', 'Innings Break')
      cy.get('[data-testid="btn-open-start-innings"]')
        .should('contain.text', 'Start First Innings')
        .click({ force: true })
      cy.get('[data-testid="modal-start-innings"]')
        .should('be.visible')
        .and('have.attr', 'role', 'dialog')
      cy.get('[data-testid="confirm-start-innings"]').should('not.be.disabled').click()
      cy.waitForSnapshotFlag('needs_new_innings', false)

      cy.get('[data-testid="gate-innings"]').should('not.exist')
      cy.get('[data-testid="scorer-controls"]')
        .should('be.visible')
        .and('have.attr', 'aria-disabled', 'false')

      for (const runs of [0, 1, 2, 3, 4, 6]) {
        expectReadableControl(`[data-testid="delivery-run-${runs}"]`)
      }
      for (const extra of ['legal', 'wd', 'nb', 'b', 'lb']) {
        cy.get(`[data-testid="delivery-extra-${extra}"]`)
          .should('be.visible')
          .and('not.be.disabled')
      }
      cy.get('[data-testid="delivery-wicket"]')
        .should('be.visible')
        .and('not.be.disabled')

      cy.get('[data-testid="delivery-run-1"]')
        .focus()
        .should('be.focused')
        .then(($control) => {
          expect(getComputedStyle($control[0]).outlineStyle, 'visible keyboard focus').not.to.equal('none')
      })
      cy.get('.scoring-panel').screenshot('issue-551-scorer-controls-dark')
      cy.screenshot('issue-551-scorer-full-dark-desktop', { capture: 'viewport' })

      cy.viewport(768, 1024)
      cy.window().should(($window) => {
        expect($window.innerWidth).to.equal(768)
        expect($window.innerHeight).to.equal(1024)
      })
      cy.get('[data-testid="scorer-controls"]').should('be.visible')
      cy.get('[data-testid="submit-delivery"]').should('be.visible')
      cy.get('.scoring-panel').screenshot('issue-551-scorer-controls-dark-tablet')
      cy.screenshot('issue-551-scorer-full-dark-tablet', { capture: 'viewport' })
      cy.viewport(1366, 768)

      setColorScheme('light')
      for (const runs of [0, 1, 2, 3, 4, 6]) {
        expectReadableControl(`[data-testid="delivery-run-${runs}"]`)
      }
      cy.get('.scoring-panel').should('be.visible')
      setColorScheme('dark')

      cy.get('[data-testid="delivery-run-1"]').click()
      cy.get('[data-testid="submit-delivery"]').click()
      cy.wait('@scoreDelivery').its('response.statusCode').should('be.oneOf', [200, 201, 204])

      cy.get('[data-testid="delivery-extra-wd"]').click()
      cy.get('[data-testid="submit-delivery"]').click()
      cy.wait('@scoreDelivery').its('response.statusCode').should('be.oneOf', [200, 201, 204])
      cy.get('[data-testid="submit-delivery"]')
        .should('not.be.disabled')
        .and('contain.text', 'SUBMIT')
      cy.get('.scoring-panel').screenshot('issue-551-scorer-controls-dark-after-scoring')

      cy.get('[data-testid="delivery-wicket"]').check()
      cy.get('[data-testid="submit-delivery"]').click()
      cy.wait('@scoreDelivery').its('response.statusCode').should('be.oneOf', [200, 201, 204])

      cy.get('[data-testid="scoreboard-runs"]').invoke('text').then((text) => {
        expect(Number(text.trim()), 'ordinary run plus wide').to.be.at.least(2)
      })
      cy.get('[data-testid="gate-new-batter"]').should('be.visible')
    })
  })
})
