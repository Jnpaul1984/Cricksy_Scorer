const organization = {
  id: 'school-a',
  name: 'Central School',
  organization_type: 'school',
  status: 'active',
  membership_role: 'owner',
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
  capabilities: ['school_master_roster', 'school_persistent_teams', 'school_team_rosters'],
  excluded_capabilities: ['advanced_ai', 'video_analysis'],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const membership = {
  id: 'membership-owner',
  organization_id: 'school-a',
  user_id: 'owner-a',
  role: 'owner',
  status: 'active',
  created_by_user_id: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const team = {
  id: 'team-a',
  organization_id: 'school-a',
  name: 'First XI',
  status: 'active',
  home_ground: 'School Oval',
  season: '2026',
  owner_user_id: 'owner-a',
  coach_user_id: null,
  coach_name: 'Coach Green',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const activePlayer = {
  id: 'school-player-active',
  organization_id: 'school-a',
  player_profile_id: 'profile-active',
  player_name: 'Asha Khan',
  status: 'active',
  student_identifier: 'S-1',
  year_group: 'Year 8',
  created_by_user_id: 'owner-a',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const inactivePlayer = {
  ...activePlayer,
  id: 'school-player-inactive',
  player_profile_id: 'profile-inactive',
  player_name: 'Alex Lee',
  status: 'inactive',
  student_identifier: 'S-2',
}

function stubSchool(role = 'owner') {
  cy.intercept('GET', '**/api/organizations/school-a/me', { ...membership, role }).as('membership')
  cy.intercept('GET', '**/api/organizations/school-a/entitlements', entitlement).as('entitlement')
  cy.intercept('GET', '**/api/organizations/school-a', { ...organization, membership_role: role }).as('organization')
  cy.intercept('GET', '**/api/organizations/school-a/teams', [team]).as('teams')
  cy.intercept('GET', '**/api/organizations/school-a/players?status=active', [activePlayer]).as('activePlayers')
  cy.intercept('GET', '**/api/organizations/school-a/players?status=inactive', [inactivePlayer]).as('inactivePlayers')
  cy.intercept('GET', '**/api/organizations/school-a/players?status=all', [activePlayer, inactivePlayer]).as('allPlayers')
}

describe('Phase 7H School administration flow', () => {
  it('supports owner Team, retained-player, and reviewed CSV import workflows on desktop', () => {
    cy.viewport(1440, 1000)
    stubSchool('owner')
    cy.intercept('POST', '**/api/organizations/school-a/teams', req => {
      expect(req.body).to.deep.equal({ name: 'Second XI', home_ground: null, season: null, coach_name: null })
      expect(req.body).not.to.have.property('players')
      req.reply({ ...team, id: 'team-b', name: 'Second XI' })
    }).as('createTeam')
    cy.intercept('PATCH', '**/api/organizations/school-a/players/school-player-inactive', req => {
      expect(req.body).to.deep.equal({ status: 'active' })
      req.reply({ ...inactivePlayer, status: 'active' })
    }).as('reactivatePlayer')
    cy.intercept('POST', '**/api/organizations/school-a/player-imports/preview', {
      statusCode: 201,
      body: {
        import_id: 'import-a',
        file_type: 'csv',
        original_filename: 'players.csv',
        content_sha256: 'hash',
        row_count: 1,
        column_mapping: { player_name: 'player_name', team_name: 'team_name' },
        expires_at: '2099-01-01T00:00:00Z',
        rows: [{
          source_row_number: 2,
          values: { player_name: 'Alex Lee', student_identifier: 'S-2', year_group: 'Year 8', team_name: 'First XI' },
          classification: 'ambiguous_needs_review',
          validation_errors: [],
          warnings: ['Names are never treated as proof of identity'],
          ambiguity_reason: 'inactive membership requires explicit reactivation',
          resolution_required: true,
          candidate_memberships: [{ school_player_membership_id: 'school-player-inactive', player_name: 'Alex Lee', status: 'inactive' }],
          resolved_school_player_membership_id: 'school-player-inactive',
          team_candidates: [{ team_id: 'team-a', team_name: 'First XI' }],
          resolved_team_id: 'team-a',
        }],
      },
    }).as('previewImport')
    cy.intercept('POST', '**/api/organizations/school-a/player-imports/import-a/apply', req => {
      expect(req.body.resolutions).to.deep.equal([{ source_row_number: 2, action: 'reactivate_existing', school_player_membership_id: 'school-player-inactive', team_id: 'team-a' }])
      req.reply({ import_id: 'import-a', status: 'applied', applied_at: '2026-01-01T00:00:00Z', summary: { created_players: 0, linked_existing_players: 0, reactivated_memberships: 1, team_assignments_created: 1, team_assignments_reactivated: 0, no_op_rows: 0, skipped_rows: 0, failed_rows: 0 }, rows: [{ source_row_number: 2, outcome: 'team_assigned', school_player_membership_id: 'school-player-inactive', player_profile_id: 'profile-inactive', team_id: 'team-a', detail: 'Row applied successfully' }] })
    }).as('applyImport')

    cy.visitWithAuth('/schools/school-a')
    cy.contains('h1', 'Central School').should('be.visible')
    cy.contains('school_free').should('be.visible')

    cy.contains('a', 'Teams').click()
    cy.contains('h2', 'Teams').should('be.visible')
    cy.get('input[required]').type('Second XI')
    cy.contains('button', 'Create team').click()
    cy.wait('@createTeam')

    cy.contains('a', 'Players').click()
    cy.get('select').select('inactive')
    cy.wait('@inactivePlayers')
    cy.contains('tr', 'Alex Lee').contains('button', 'Reactivate').click()
    cy.wait('@reactivatePlayer')

    cy.contains('a', 'Import').click()
    cy.get('input[type=file]').selectFile({ contents: Cypress.Buffer.from('player_name,team_name\nAlex Lee,First XI\n'), fileName: 'players.csv', mimeType: 'text/csv' })
    cy.contains('button', 'Create preview').click()
    cy.wait('@previewImport')
    cy.contains('Preview does not add or change players.').should('be.visible')
    cy.get('[data-test="action-2"]').select('reactivate_existing')
    cy.get('#player-2').select('school-player-inactive')
    cy.contains('button', 'Apply reviewed import').click()
    cy.wait('@applyImport')
    cy.contains('Row applied successfully').should('be.visible')
  })

  it('keeps scorer controls read-only on tablet', () => {
    cy.viewport(1024, 768)
    stubSchool('scorer')
    cy.visitWithAuth('/schools/school-a/players')
    cy.contains('h2', 'School master roster').should('be.visible')
    cy.contains('button', 'Add to roster').should('not.exist')
    cy.contains('button', 'Edit metadata').should('not.exist')
    cy.contains('button', 'Deactivate').should('not.exist')
    cy.contains('a', 'Import').should('not.exist')
  })
})
