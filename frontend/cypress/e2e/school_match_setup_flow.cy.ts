const organization = {
  id: 'school-a',
  name: 'Central School',
  organization_type: 'school',
  status: 'active',
  membership_role: 'scorer',
  created_by_user_id: 'owner-a',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const membership = {
  id: 'membership-scorer',
  organization_id: 'school-a',
  user_id: 'scorer-a',
  role: 'scorer',
  status: 'active',
  created_by_user_id: 'owner-a',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const entitlement = {
  id: 'ent-a',
  organization_id: 'school-a',
  plan_key: 'school_free',
  status: 'active',
  source: 'system',
  effective_from: '2026-01-01T00:00:00Z',
  effective_until: null,
  capabilities: [
    'school_master_roster',
    'school_persistent_teams',
    'school_team_rosters',
    'school_match_playing_xi',
  ],
  excluded_capabilities: ['advanced_ai', 'video_analysis'],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const teams = ['a', 'b'].map(suffix => ({
  id: `team-${suffix}`,
  organization_id: 'school-a',
  name: `Team ${suffix.toUpperCase()}`,
  status: 'active',
  home_ground: null,
  season: '2026',
  owner_user_id: null,
  coach_user_id: null,
  coach_name: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}))

function roster(teamId: string) {
  return Array.from({ length: 12 }, (_, index) => ({
    id: `${teamId}-membership-${index}`,
    organization_id: 'school-a',
    team_id: teamId,
    school_player_membership_id: `${teamId}-school-player-${index}`,
    player_profile_id: `${teamId}-profile-${index}`,
    player_name: `${teamId} Player ${index + 1}`,
    status: index === 11 ? 'inactive' : 'active',
    school_player_status: 'active',
    team_status: 'active',
    operationally_available: index !== 11,
    created_by_user_id: 'owner-a',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }))
}

describe('Phase 7I School match setup flow', () => {
  it('creates from two explicit saved-Team XIs and enters existing scoring', () => {
    cy.viewport(1440, 1000)
    cy.intercept('GET', '**/api/organizations/school-a/me', membership)
    cy.intercept('GET', '**/api/organizations/school-a/entitlements', entitlement)
    cy.intercept('GET', '**/api/organizations/school-a', organization)
    cy.intercept('GET', '**/api/organizations/school-a/teams', teams)
    cy.intercept('GET', '**/api/organizations/school-a/teams/team-a/players', roster('team-a'))
    cy.intercept('GET', '**/api/organizations/school-a/teams/team-b/players', roster('team-b'))
    cy.intercept('POST', '**/api/organizations/school-a/matches', req => {
      expect(req.body.team_a.playing_xi_membership_ids).to.deep.equal(
        roster('team-a').slice(0, 11).map(player => player.id),
      )
      expect(req.body.team_b.playing_xi_membership_ids).to.deep.equal(
        roster('team-b').slice(0, 11).map(player => player.id),
      )
      expect(req.body.team_a.captain_membership_id).to.equal('team-a-membership-0')
      expect(req.body.team_b.wicketkeeper_membership_id).to.equal('team-b-membership-1')
      expect(req.body.team_a).not.to.have.property('players')
      req.reply({
        game_id: 'game-school',
        organization_id: 'school-a',
        team_a_id: 'team-a',
        team_b_id: 'team-b',
        team_a_name: 'Team A',
        team_b_name: 'Team B',
        team_a_player_profile_ids: roster('team-a').slice(0, 11).map(player => player.player_profile_id),
        team_b_player_profile_ids: roster('team-b').slice(0, 11).map(player => player.player_profile_id),
      })
    }).as('createSchoolMatch')

    cy.visitWithAuth('/schools/school-a/matches/new')
    cy.contains('Team roster is not a playing XI.').should('be.visible')
    cy.get('[data-testid="school-team-a"]').select('team-a')
    cy.get('[data-testid="school-team-b"]').select('team-b')
    cy.get('input[type=checkbox]:checked').should('have.length', 0)
    cy.get('ul[aria-label="Team A roster"] input[type=checkbox]:not(:disabled)').each(input => {
      cy.wrap(input).check()
    })
    cy.get('ul[aria-label="Team B roster"] input[type=checkbox]:not(:disabled)').each(input => {
      cy.wrap(input).check()
    })
    cy.get('#captain-a').select('team-a-membership-0')
    cy.get('#keeper-a').select('team-a-membership-1')
    cy.get('#captain-b').select('team-b-membership-0')
    cy.get('#keeper-b').select('team-b-membership-1')
    cy.get('[data-testid="create-school-match"]').click()
    cy.wait('@createSchoolMatch')
    cy.url().should('include', '/game/game-school/scoring')
  })

  it('creates a saved School Team match against an external opponent', () => {
    cy.viewport(1440, 1200)
    cy.intercept('GET', '**/api/organizations/school-a/me', membership)
    cy.intercept('GET', '**/api/organizations/school-a/entitlements', entitlement)
    cy.intercept('GET', '**/api/organizations/school-a', organization)
    cy.intercept('GET', '**/api/organizations/school-a/teams', teams)
    cy.intercept('GET', '**/api/organizations/school-a/teams/team-a/players', roster('team-a'))
    cy.intercept('POST', '**/api/organizations/school-a/matches', req => {
      expect(req.body.mode).to.equal('school_vs_external')
      expect(req.body.school_side).to.equal('team_a')
      expect(req.body.team_a.team_id).to.equal('team-a')
      expect(req.body.team_b).to.equal(null)
      expect(req.body.external_opponent.team_name).to.equal('Westhaven College First XI')
      expect(req.body.external_opponent.player_names).to.deep.equal(
        Array.from({ length: 11 }, (_, index) => `Westhaven Player ${index + 1}`),
      )
      req.reply({
        game_id: 'game-external',
        organization_id: 'school-a',
        team_a_id: 'team-a',
        team_b_id: null,
        team_a_name: 'Team A',
        team_b_name: 'Westhaven College First XI',
        team_a_player_profile_ids: roster('team-a')
          .slice(0, 11)
          .map(player => player.player_profile_id),
        team_b_player_profile_ids: [],
      })
    }).as('createExternalMatch')

    cy.visitWithAuth('/schools/school-a/matches/new')
    cy.get('[data-testid="mode-school-vs-external"]').click()
    cy.get('[data-testid="school-team-a"]').select('team-a')
    cy.get('ul[aria-label="Team A roster"] input[type=checkbox]:not(:disabled)').each(input => {
      cy.wrap(input).check()
    })
    cy.get('#captain-a').select('team-a-membership-0')
    cy.get('#keeper-a').select('team-a-membership-1')
    cy.get('[data-testid="external-team-name"]').type('Westhaven College First XI')
    for (let index = 0; index < 11; index += 1) {
      cy.get(`[data-testid="external-player-${index}"]`).type(`Westhaven Player ${index + 1}`)
    }
    cy.get('[data-testid="create-school-match"]').click()
    cy.wait('@createExternalMatch')
    cy.url().should('include', '/game/game-external/scoring')
  })
})
