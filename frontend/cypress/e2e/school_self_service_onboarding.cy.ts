describe('School Free self-service onboarding', () => {
  it('takes a new representative from public discovery to first-run guidance', () => {
    const user = { id: 'new-owner', email: 'school@example.test', role: 'free', is_active: true }
    const school = { id: 'new-school', name: 'New School', organization_type: 'school', status: 'active', membership_role: 'owner', created_by_user_id: 'new-owner', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
    cy.intercept('POST', '**/auth/register', req => { expect(req.body).to.deep.equal({ email: user.email, password: 'password1' }); req.reply({ statusCode: 201, body: {} }) })
    cy.intercept('POST', '**/auth/login', { access_token: 'token', token_type: 'bearer' })
    cy.intercept('GET', '**/auth/me', user)
    cy.intercept('POST', '**/api/organizations', req => { expect(req.body).to.deep.equal({ name: 'New School', organization_type: 'school' }); req.reply({ statusCode: 201, body: school }) }).as('createSchool')
    cy.intercept('GET', '**/api/organizations/new-school', school)
    cy.intercept('GET', '**/api/organizations/new-school/me', { id: 'membership', organization_id: 'new-school', user_id: 'new-owner', role: 'owner', status: 'active', created_by_user_id: 'new-owner', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' })
    cy.intercept('GET', '**/api/organizations/new-school/entitlements', { id: 'entitlement', organization_id: 'new-school', plan_key: 'school_free', status: 'active', source: 'system', effective_from: '2026-01-01T00:00:00Z', effective_until: null, capabilities: ['school_matches_unlimited', 'school_master_roster', 'school_persistent_teams', 'school_team_rosters', 'school_match_playing_xi', 'school_basic_statistics', 'school_fixtures_results', 'school_live_scorecards', 'school_competitions'], excluded_capabilities: ['advanced_ai', 'video_analysis', 'advanced_analytics', 'analyst_tooling', 'premium_coaching', 'premium_broadcast_video'], created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' })
    cy.intercept('GET', '**/api/organizations/new-school/players?status=active', [])
    cy.intercept('GET', '**/api/organizations/new-school/teams', [])
    cy.visit('/landing'); cy.contains('a', 'Schools').click(); cy.location('pathname').should('eq', '/schools/free')
    cy.contains('a', 'Get School Free').click(); cy.location('pathname').should('eq', '/register')
    cy.get('input[type=email]').type(user.email); cy.get('input[autocomplete=new-password]').first().type('password1'); cy.get('input[autocomplete=new-password]').last().type('password1'); cy.contains('button', 'Create account').click()
    cy.location('pathname').should('eq', '/schools/create'); cy.get('input').type('New School'); cy.contains('button', 'Create School Free').click(); cy.wait('@createSchool')
    cy.location('pathname').should('eq', '/schools/new-school'); cy.contains('Start your School workspace').should('be.visible'); cy.contains('Upload Players').should('be.visible'); cy.contains('Create Teams').should('be.visible'); cy.contains('Assign Players').should('be.visible'); cy.contains('a', 'Create First Match').should('be.visible').and('have.attr', 'href', '/schools/new-school/matches/new')
  })
})
