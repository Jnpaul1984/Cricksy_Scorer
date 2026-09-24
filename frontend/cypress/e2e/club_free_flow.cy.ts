const timestamp = '2026-01-01T00:00:00Z'

describe('Club Free shared organization journey', () => {
  it('creates a Club, reuses roster and Team workflows, and enters the scorer', () => {
    const user = { id: 'club-owner', email: 'club@example.test', role: 'free', is_active: true }
    const club = {
      id: 'club-a',
      name: 'Central Cricket Club',
      organization_type: 'club',
      status: 'active',
      membership_role: 'owner',
      created_by_user_id: user.id,
      created_at: timestamp,
      updated_at: timestamp,
    }
    const team = {
      id: 'team-a',
      organization_id: club.id,
      name: 'First XI',
      status: 'active',
      home_ground: null,
      season: null,
      owner_user_id: user.id,
      coach_user_id: null,
      coach_name: null,
      created_at: timestamp,
      updated_at: timestamp,
    }
    const player = {
      id: 'club-player-a',
      organization_id: club.id,
      player_profile_id: 'profile-a',
      player_name: 'Asha Khan',
      status: 'active',
      student_identifier: 'C-1',
      year_group: 'Senior',
      created_by_user_id: user.id,
      created_at: timestamp,
      updated_at: timestamp,
    }
    const importedPlayer = {
      ...player,
      id: 'club-player-b',
      player_profile_id: 'profile-b',
      player_name: 'Maya Singh',
      student_identifier: 'C-2',
    }
    const teams: typeof team[] = []
    const players = [player]
    const playingRoster = Array.from({ length: 11 }, (_, index) => ({
      id: `team-membership-${index}`,
      organization_id: club.id,
      team_id: team.id,
      school_player_membership_id: `club-playing-player-${index}`,
      player_profile_id: `club-profile-${index}`,
      player_name: `Club Player ${index + 1}`,
      status: 'active',
      school_player_status: 'active',
      team_status: 'active',
      operationally_available: true,
      created_by_user_id: user.id,
      created_at: timestamp,
      updated_at: timestamp,
    }))

    cy.intercept('POST', '**/auth/register', req => {
      expect(req.body).to.deep.equal({ email: user.email, password: 'password1' })
      req.reply({ statusCode: 201, body: {} })
    })
    cy.intercept('POST', '**/auth/login', { access_token: 'club-token', token_type: 'bearer' })
    cy.intercept('GET', '**/auth/me', user)
    cy.intercept('POST', '**/api/organizations', req => {
      expect(req.body).to.deep.equal({ name: club.name, organization_type: 'club' })
      req.reply({ statusCode: 201, body: club })
    }).as('createClub')
    cy.intercept('GET', '**/api/organizations/club-a', club)
    cy.intercept('GET', '**/api/organizations/club-a/me', {
      id: 'club-membership',
      organization_id: club.id,
      user_id: user.id,
      role: 'owner',
      status: 'active',
      created_by_user_id: user.id,
      created_at: timestamp,
      updated_at: timestamp,
    })
    cy.intercept('GET', '**/api/organizations/club-a/entitlements', {
      id: 'club-entitlement',
      organization_id: club.id,
      plan_key: 'club_free',
      status: 'active',
      source: 'system',
      effective_from: timestamp,
      effective_until: null,
      capabilities: [
        'school_matches_unlimited',
        'school_master_roster',
        'school_persistent_teams',
        'school_team_rosters',
        'school_match_playing_xi',
        'school_basic_statistics',
        'school_fixtures_results',
        'school_live_scorecards',
        'school_competitions',
      ],
      excluded_capabilities: [
        'advanced_ai',
        'video_analysis',
        'advanced_analytics',
        'analyst_tooling',
        'premium_coaching',
        'premium_broadcast_video',
      ],
      created_at: timestamp,
      updated_at: timestamp,
    })
    cy.intercept('GET', '**/api/organizations/club-a/teams', req => req.reply(teams))
    cy.intercept('POST', '**/api/organizations/club-a/teams', req => {
      expect(req.body).to.deep.equal({
        name: team.name,
        home_ground: null,
        season: null,
        coach_name: null,
      })
      teams.push(team)
      req.reply({ statusCode: 201, body: team })
    }).as('createTeam')
    cy.intercept('GET', '**/api/organizations/club-a/players?status=active', req =>
      req.reply(players),
    )
    cy.intercept('POST', '**/api/organizations/club-a/players', req => {
      expect(req.body.player_name).to.equal(player.player_name)
      req.reply({ statusCode: 201, body: player })
    }).as('createPlayer')
    cy.intercept('POST', '**/api/organizations/club-a/player-imports/preview', {
      statusCode: 201,
      body: {
        import_id: 'club-import',
        file_type: 'csv',
        original_filename: 'club-players.csv',
        content_sha256: 'club-hash',
        row_count: 1,
        column_mapping: { player_name: 'player_name' },
        expires_at: '2099-01-01T00:00:00Z',
        rows: [
          {
            source_row_number: 2,
            values: {
              player_name: importedPlayer.player_name,
              student_identifier: importedPlayer.student_identifier,
              year_group: importedPlayer.year_group,
              team_name: null,
            },
            classification: 'new_player',
            validation_errors: [],
            warnings: [],
            ambiguity_reason: null,
            resolution_required: false,
            candidate_memberships: [],
            resolved_school_player_membership_id: null,
            team_candidates: [],
            resolved_team_id: null,
          },
        ],
      },
    }).as('previewClubImport')
    cy.intercept('POST', '**/api/organizations/club-a/player-imports/club-import/apply', req => {
      expect(req.body.resolutions).to.deep.equal([])
      players.push(importedPlayer)
      req.reply({
        import_id: 'club-import',
        status: 'applied',
        applied_at: timestamp,
        summary: {
          created_players: 1,
          linked_existing_players: 0,
          reactivated_memberships: 0,
          team_assignments_created: 0,
          team_assignments_reactivated: 0,
          no_op_rows: 0,
          skipped_rows: 0,
          failed_rows: 0,
        },
        rows: [
          {
            source_row_number: 2,
            outcome: 'player_created',
            school_player_membership_id: importedPlayer.id,
            player_profile_id: importedPlayer.player_profile_id,
            team_id: null,
            detail: 'Row applied successfully',
          },
        ],
      })
    }).as('applyClubImport')
    cy.intercept('GET', '**/api/organizations/club-a/teams/team-a', team)
    cy.intercept('GET', '**/api/organizations/club-a/teams/team-a/players', playingRoster)
    cy.intercept('POST', '**/api/organizations/club-a/teams/team-a/players', req => {
      expect(req.body).to.deep.equal({ school_player_membership_id: importedPlayer.id })
      req.reply({ statusCode: 201, body: { ...playingRoster[0], id: 'assigned-import' } })
    }).as('assignClubPlayer')
    cy.intercept('POST', '**/api/organizations/club-a/matches', req => {
      expect(req.body.mode).to.equal('school_vs_external')
      expect(req.body.team_a.team_id).to.equal(team.id)
      expect(req.body.team_a.playing_xi_membership_ids).to.have.length(11)
      expect(req.body.external_opponent.player_names).to.have.length(11)
      req.reply({
        statusCode: 201,
        body: {
          game_id: 'club-game',
          organization_id: club.id,
          team_a_id: team.id,
          team_b_id: null,
          team_a_name: team.name,
          team_b_name: 'Visitors XI',
          team_a_player_profile_ids: playingRoster.map(item => item.player_profile_id),
          team_b_player_profile_ids: [],
        },
      })
    }).as('createClubMatch')

    cy.visit('/clubs/free')
    cy.contains('h1', 'Club Free').should('be.visible')
    cy.contains('a', 'Get Club Free').click()
    cy.location('pathname').should('eq', '/register')
    cy.get('input[type=email]').type(user.email)
    cy.get('input[autocomplete=new-password]').first().type('password1')
    cy.get('input[autocomplete=new-password]').last().type('password1')
    cy.contains('button', 'Create account').click()
    cy.location('pathname').should('eq', '/clubs/create')
    cy.contains('h1', 'Create your Club').should('be.visible')
    cy.get('input').type(club.name)
    cy.contains('button', 'Create Club Free').click()
    cy.wait('@createClub')
    cy.location('pathname').should('eq', '/clubs/club-a')
    cy.contains('Club Administration').should('be.visible')
    cy.contains('club_free').should('be.visible')

    cy.contains('a', 'Teams').click()
    cy.contains('label', 'Team name').find('input').type(team.name)
    cy.contains('button', 'Create team').click()
    cy.wait('@createTeam')

    cy.contains('a', 'Players').click()
    cy.contains('label', 'Player name').find('input').type(player.player_name)
    cy.contains('button', 'Add to roster').click()
    cy.wait('@createPlayer')
    cy.contains('Club master roster').should('be.visible')

    cy.contains('a', 'Import').click()
    cy.get('input[type=file]').selectFile({
      contents: Cypress.Buffer.from('player_name,student_identifier\nMaya Singh,C-2\n'),
      fileName: 'club-players.csv',
      mimeType: 'text/csv',
    })
    cy.contains('button', 'Create preview').click()
    cy.wait('@previewClubImport')
    cy.contains('Preview does not add or change players.').should('be.visible')
    cy.contains('button', 'Apply reviewed import').click()
    cy.wait('@applyClubImport')

    cy.visitWithAuth('/clubs/club-a/teams/team-a')
    cy.contains('The Club master roster remains canonical.').should('be.visible')
    cy.get('select').select(importedPlayer.id)
    cy.contains('button', 'Assign player').click()
    cy.wait('@assignClubPlayer')

    cy.visitWithAuth('/clubs/club-a/matches/new')
    cy.get('[data-testid="mode-school-vs-external"]').click()
    cy.get('[data-testid="school-team-a"]').select(team.id)
    cy.get('ul[aria-label="Team A roster"] input[type=checkbox]:not(:disabled)').each(input => {
      cy.wrap(input).check()
    })
    cy.get('#captain-a').select(playingRoster[0].id)
    cy.get('#keeper-a').select(playingRoster[1].id)
    cy.get('[data-testid="external-team-name"]').type('Visitors XI')
    for (let index = 0; index < 11; index += 1) {
      cy.get(`[data-testid="external-player-${index}"]`).type(`Visitor ${index + 1}`)
    }
    cy.get('[data-testid="create-school-match"]').click()
    cy.wait('@createClubMatch')
    cy.location('pathname').should('eq', '/game/club-game/scoring')
  })
})
