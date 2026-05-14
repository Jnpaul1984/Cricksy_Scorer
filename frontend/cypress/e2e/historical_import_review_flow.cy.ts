const analystMatches = { items: [], total: 0 }

const candidateResponse = {
  candidate_id: 'ocr-candidate-001',
  batch_id: 'ocr-candidate-001',
  status: 'needs_review',
  status_history: ['uploaded', 'extracted', 'needs_review'],
  source_document: {
    filename: 'scorecard.pdf',
    content_type: 'application/pdf',
    size_bytes: 2048,
    storage: { storage: 'local', path: '/tmp/ocr/scorecard.pdf' },
  },
  extraction: {
    method: 'manual_candidate_json',
    confidence: 0.84,
    uncertainty_flags: ['team_name_low_confidence'],
    ocr_text: null,
    non_authoritative_notice:
      'OCR/AI extraction is non-authoritative and must be reviewed before historical import.',
  },
  candidate_json: {
    matchType: 'T20',
    teams: ['Lions', 'Falcons'],
    innings: [],
  },
  reviewed_json: null,
  reviewer_notes: null,
  rejection_reason: null,
  validation_errors: [],
  dry_run_result: null,
  dry_run_batch_id: null,
}

describe('Historical OCR review flow', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
    cy.intercept('GET', '**/analytics/matches', analystMatches).as('getAnalystMatches')
    cy.intercept('GET', '**/analytics/matches/*/case-study', {
      statusCode: 404,
      body: { detail: 'not found' },
    }).as('getCaseStudy404')
    cy.intercept('GET', '**/analytics/matches/*/registry', {
      statusCode: 200,
      body: {
        match_id: 'na',
        is_historical: false,
        competition: null,
        season: null,
        venue: null,
        teams: null,
        match_number: null,
        player_count: 0,
        innings_count: 0,
        has_deliveries: false,
        import_batch_id: null,
        source_filename: null,
        source_format: null,
        source_type: 'live',
        imported_at: null,
        validation_status: 'not_applicable',
        registration_status: 'not_registered',
        training_eligible: false,
        blocking_reason: 'not_a_historical_import',
      },
    }).as('getRegistry')

    cy.intercept('POST', '**/api/historical-import/json/ocr-review/candidates', candidateResponse).as('createCandidate')
    cy.intercept('PATCH', '**/api/historical-import/json/ocr-review/candidates/*/review', {
      ...candidateResponse,
      status: 'ready_for_dry_run',
      status_history: ['uploaded', 'extracted', 'needs_review', 'reviewed', 'ready_for_dry_run'],
      reviewed_json: {
        matchType: 'T20',
        teams: ['Lions', 'Falcons'],
        innings: [],
      },
    }).as('saveReview')
    cy.intercept('POST', '**/api/historical-import/json/ocr-review/candidates/*/dry-run', {
      candidate_id: 'ocr-candidate-001',
      status: 'dry_run_passed',
      dry_run_batch_id: 'handoff-batch-001',
      message:
        'Dry-run passed. Use /api/historical-import/json/batches/{batch_id}/apply for explicit import apply.',
      dry_run_result: {
        status: 'valid',
        detected_format: 'cricksy_fixture',
        top_level_keys: ['matchType', 'teams', 'innings'],
        detected_sections: {
          teams: true,
          players: false,
          innings: true,
          deliveries: false,
          metadata: true,
        },
        metadata_preview: {
          match_type: 'T20',
          venue: null,
          date: null,
          result: null,
          event_name: null,
          season: null,
          match_number: null,
          source_dates: [],
        },
        teams_preview: ['Lions', 'Falcons'],
        innings_count: 0,
        delivery_count: 0,
        player_names_found: [],
        innings_preview: [],
        warnings: [],
        errors: [],
        duplicate_detection: {
          source_hash_sha256: 'a'.repeat(64),
          probable_duplicate: 'not_duplicate',
          tracking_available: true,
          duplicate_batch_id: null,
          semantic_key: null,
          semantic_duplicate: false,
          message: 'No duplicate detected.',
        },
        no_persistence: true,
        record_id: null,
      },
    }).as('dryRunCandidate')
  })

  it('shows OCR review panel and executes review + dry-run handoff flow', () => {
    cy.visitWithAuth('/analyst/workspace')
    cy.wait('@getAnalystMatches')

    cy.contains('button', 'Import Data').click()
    cy.get('[data-testid="ocr-review-panel"]').should('exist')
    cy.contains('OCR/AI extraction is always non-authoritative').should('exist')

    cy.get('[data-testid="ocr-source-file"]').selectFile({
      contents: Cypress.Buffer.from('%PDF-1.7 OCR SCORECARD'),
      fileName: 'scorecard.pdf',
      mimeType: 'application/pdf',
      lastModified: Date.now(),
    }, { force: true })

    cy.get('[data-testid="ocr-candidate-json"]').clear().type(
      '{"matchType":"T20","teams":["Lions","Falcons"],"innings":[]}',
      { delay: 0 },
    )

    cy.get('[data-testid="ocr-create-candidate"]').click()
    cy.wait('@createCandidate')
    cy.get('[data-testid="ocr-candidate-summary"]').should('contain', 'needs_review')

    cy.get('[data-testid="ocr-save-review"]').click()
    cy.wait('@saveReview')

    cy.get('[data-testid="ocr-run-dry-run"]').click()
    cy.wait('@dryRunCandidate')
    cy.get('[data-testid="ocr-dry-run-result"]').should('contain', 'dry_run_passed')
    cy.get('[data-testid="ocr-dry-run-result"]').should('contain', 'handoff-batch-001')
  })
})
