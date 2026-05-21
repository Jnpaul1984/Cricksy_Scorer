import { mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import HistoricalBackfillReprocessPanel from '@/components/HistoricalBackfillReprocessPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalBackfillReprocessDiagnose: vi.fn(),
  historicalBackfillReprocessAudit: vi.fn(),
  historicalBackfillReprocessApply: vi.fn(),
  historicalBackfillReattachSourceJson: vi.fn(),
  historicalImportListBatches: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const CONTROLLED_APPLY_SAFETY_WARNING =
  'Controlled apply stays disabled until every selected record is safely reprocessable.'

const auditResponse = {
  total_imported_cpl_matches: 3,
  completeness_counts: {
    metadata_only: 1,
    innings_totals_only: 1,
    delivery_data_available: 0,
    wicket_data_available: 1,
    phase_analytics_available: 0,
  },
  import_origin_counts: {
    single_json_apply: 1,
    bulk_zip_apply: 1,
    unknown: 1,
  },
  player_aggregate_scope: 'delivery-complete matches only',
  rollback_feasibility: 'rollback info',
  eligible_matches: 2,
  blocked_matches: 1,
  selected_matches: 3,
  records: [
    {
      match_id: 'match-1',
      batch_id: 'batch-1',
      import_source: 'bulk_zip_apply' as const,
      completeness: 'metadata_only',
      eligible: true,
      blocked_reason: null,
      missing_source_json: false,
      duplicate_delivery_risk: false,
      apply_deliveries_previously_run: false,
      source_json_retained: true,
      registry_people_available: true,
      registry_people_count: 14,
      players_without_source_ids: 0,
      expected_deliveries: 120,
      expected_wickets: 8,
      expected_players: 22,
      match_date: '2013-09-07',
      competition: 'Caribbean Premier League',
      season: '2013',
      team_1: 'Trinbago Knight Riders',
      team_2: 'Jamaica Tallawahs',
      venue: 'Port of Spain',
      result: 'TKR won by 5 wickets',
      status: 'completed',
      innings_1_summary: 'Jamaica Tallawahs 152/7 (20 ov)',
      innings_2_summary: 'Trinbago Knight Riders 153/5 (19.2 ov)',
      known_score_summary:
        'Jamaica Tallawahs 152/7 (20 ov) | Trinbago Knight Riders 153/5 (19.2 ov)',
      original_filename: 'cpl-2013-match-1.json',
      upload_filename: null,
      source_file_hint: 'cpl-2013-match-1.json',
      match_identity_label: 'Trinbago Knight Riders vs Jamaica Tallawahs — 2013-09-07 — Port of Spain',
    },
    {
      match_id: 'match-2',
      batch_id: 'batch-2',
      import_source: 'single_json_apply' as const,
      completeness: 'innings_totals_only',
      eligible: true,
      blocked_reason: null,
      missing_source_json: false,
      duplicate_delivery_risk: true,
      apply_deliveries_previously_run: false,
      source_json_retained: true,
      registry_people_available: false,
      registry_people_count: 0,
      players_without_source_ids: 5,
      expected_deliveries: 118,
      expected_wickets: 7,
      expected_players: 21,
      match_date: '2013-09-08',
      competition: 'Caribbean Premier League',
      season: '2013',
      team_1: 'Guyana Amazon Warriors',
      team_2: 'St Lucia Zouks',
      venue: 'Providence',
      result: null,
      status: 'completed',
      innings_1_summary: 'Guyana Amazon Warriors 148/8 (20 ov)',
      innings_2_summary: 'St Lucia Zouks 140/9 (20 ov)',
      known_score_summary: 'Guyana Amazon Warriors 148/8 (20 ov) | St Lucia Zouks 140/9 (20 ov)',
      original_filename: 'cpl-2013-match-2.json',
      upload_filename: null,
      source_file_hint: 'cpl-2013-match-2.json',
      match_identity_label: 'Guyana Amazon Warriors vs St Lucia Zouks — 2013-09-08 — Providence',
    },
    {
      match_id: 'match-3',
      batch_id: 'batch-3',
      import_source: 'unknown' as const,
      completeness: 'metadata_only',
      eligible: false,
      blocked_reason: 'missing_source_json',
      missing_source_json: true,
      duplicate_delivery_risk: false,
      apply_deliveries_previously_run: false,
      source_json_retained: false,
      registry_people_available: false,
      registry_people_count: 0,
      players_without_source_ids: 0,
      expected_deliveries: 0,
      expected_wickets: 0,
      expected_players: 0,
      match_date: null,
      competition: null,
      season: null,
      team_1: null,
      team_2: null,
      venue: null,
      result: null,
      status: null,
      innings_1_summary: null,
      innings_2_summary: null,
      known_score_summary: null,
      original_filename: null,
      upload_filename: null,
      source_file_hint: null,
      match_identity_label: null,
    },
  ],
}

const diagnosisResponse = {
  total_imported_cpl_matches: 3,
  selected_matches: 3,
  blocked_matches: 1,
  records: [
    {
      match_id: 'match-1',
      batch_id: 'batch-1',
      import_source: 'bulk_zip_apply' as const,
      completeness: 'metadata_only',
      source_json_retained: true,
      source_json_required: false,
      schema_detected: 'overs_deliveries_schema',
      innings_path_detected: true,
      delivery_path_detected: true,
      detected_delivery_path: 'innings[].overs[].deliveries[]',
      delivery_path_candidates: ['innings[].overs[].deliveries[]'],
      expected_deliveries: 120,
      expected_wickets: 8,
      registry_people_available: true,
      batter_field_detected: true,
      bowler_field_detected: true,
      non_striker_field_detected: true,
      runs_field_detected: true,
      extras_field_detected: true,
      wicket_field_detected: true,
      skip_or_failure_reason: null,
      safely_reprocessable: true,
      recommended_next_action:
        'Diagnosis indicates delivery extraction is possible. Keep controlled apply gate and proceed in staged batches.',
    },
    {
      match_id: 'match-3',
      batch_id: 'batch-3',
      import_source: 'unknown' as const,
      completeness: 'metadata_only',
      source_json_retained: false,
      source_json_required: true,
      schema_detected: 'unknown_delivery_schema',
      innings_path_detected: false,
      delivery_path_detected: false,
      detected_delivery_path: null,
      delivery_path_candidates: [],
      expected_deliveries: 0,
      expected_wickets: 0,
      registry_people_available: false,
      batter_field_detected: false,
      bowler_field_detected: false,
      non_striker_field_detected: false,
      runs_field_detected: false,
      extras_field_detected: false,
      wicket_field_detected: false,
      skip_or_failure_reason: 'missing_source_json',
      safely_reprocessable: false,
      recommended_next_action:
        'Source JSON missing. Reattach original JSON before delivery diagnosis or reprocess can run.',
    },
  ],
}

const importBatches = Array.from({ length: 30 }, (_, idx) => ({
  id: `batch-${idx + 1}`,
  owner_user_id: null,
  owner_org_id: null,
  source_filename: `source-${idx + 1}.json`,
  source_format: 'json',
  source_hash_sha256: null,
  semantic_key: null,
  status: 'dry_run_passed',
  error_count: 0,
  warning_count: 0,
  innings_count: 2,
  delivery_count: 120,
  is_finalized: true,
  applied_game_id: `match-${idx + 1}`,
  created_at: '2026-05-20T00:00:00Z',
  updated_at: '2026-05-20T00:00:00Z',
}))

const cloneAuditResponse = () => structuredClone(auditResponse)

describe('HistoricalBackfillReprocessPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.historicalImportListBatches).mockResolvedValue(importBatches)
  })

  it('uses safe default audit scope and does not send an unfiltered all-record request', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalImportListBatches).toHaveBeenCalledWith(1)
    expect(api.historicalBackfillReprocessAudit).toHaveBeenCalledWith({
      batch_ids: ['batch-1'],
      match_ids: [],
      max_batch_size: 1,
    })
  })

  it('submits manual batch IDs for audit', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-audit-scope-mode"]').setValue('manual_batch_ids')
    await wrapper.get('[data-testid="hbr-audit-manual-ids"]').setValue('batch-1')
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReprocessAudit).toHaveBeenCalledWith({
      batch_ids: ['batch-1'],
      match_ids: [],
      max_batch_size: 1,
    })
  })

  it('submits manual match IDs for audit', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-audit-scope-mode"]').setValue('manual_match_ids')
    await wrapper.get('[data-testid="hbr-audit-manual-ids"]').setValue('match-1,match-2,match-3')
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReprocessAudit).toHaveBeenCalledWith({
      batch_ids: [],
      match_ids: ['match-1', 'match-2', 'match-3'],
      max_batch_size: 5,
    })
  })

  it('disables audit button for invalid manual selection count', async () => {
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-audit-scope-mode"]').setValue('manual_match_ids')
    await wrapper.get('[data-testid="hbr-audit-manual-ids"]').setValue('match-1,match-2')
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-run-audit-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Audit selection size must be 1, 3–5, 10, or 20–25.')
  })

  it('enables audit button for valid ladder counts', async () => {
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    const runAuditButton = wrapper.get('[data-testid="hbr-run-audit-btn"]')
    expect(runAuditButton.attributes('disabled')).toBeUndefined()

    await wrapper.get('[data-testid="hbr-audit-scope-mode"]').setValue('first_3_5')
    await wrapper.get('[data-testid="hbr-audit-scope-count"]').setValue('3')
    await flushPromises()
    expect(runAuditButton.attributes('disabled')).toBeUndefined()

    await wrapper.get('[data-testid="hbr-audit-scope-mode"]').setValue('first_20_25')
    await wrapper.get('[data-testid="hbr-audit-scope-count"]').setValue('25')
    await flushPromises()
    expect(runAuditButton.attributes('disabled')).toBeUndefined()
  })

  it('disables apply for invalid controlled selection size and enables with valid size + confirmation', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await wrapper.get('[data-testid="hbr-run-diagnosis-btn"]').trigger('click')
    await flushPromises()

    const applyButton = wrapper.get('[data-testid="hbr-apply-btn"]')
    expect(applyButton.attributes('disabled')).toBeDefined()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await rowChecks[1].setValue(true)
    await flushPromises()

    expect(wrapper.text()).toContain('Selection size must be 1, 3–5, 10, or 20–25.')
    expect(applyButton.attributes('disabled')).toBeDefined()

    await rowChecks[1].setValue(false)
    await flushPromises()
    expect(applyButton.attributes('disabled')).toBeDefined()

    const confirm = wrapper.get('.hbr-confirm input[type="checkbox"]')
    await confirm.setValue(true)
    await flushPromises()

    expect(applyButton.attributes('disabled')).toBeUndefined()
  })

  it('submits apply only after valid audit selection and confirmation', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessApply).mockResolvedValue({
      status: 'applied',
      processed_matches: 1,
      skipped_matches: 0,
      failed_matches: 0,
      deliveries_rebuilt: 120,
      wickets_rebuilt: 8,
      player_mappings_updated: 3,
      unresolved_players: 0,
      unresolved_venues: 0,
      changed_match_ids: ['match-1'],
      blocked_records: [],
      results: [
        {
          match_id: 'match-1',
          batch_id: 'batch-1',
          status: 'processed',
          reason: null,
          completeness_before: 'metadata_only',
          completeness_after: 'phase_analytics_available',
          deliveries_before: 0,
          deliveries_after: 120,
          wickets_before: 0,
          wickets_after: 8,
          player_mappings_updated: 3,
          unresolved_players: 0,
          unresolved_venues: 0,
        },
      ],
      rollback_info: 'rollback info',
    })

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await wrapper.get('[data-testid="hbr-run-diagnosis-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hbr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReprocessApply).toHaveBeenCalledWith({
      confirm: true,
      batch_ids: ['batch-1'],
      max_batch_size: 25,
    })
    expect(wrapper.text()).toContain('Changed match IDs: match-1')
    expect(wrapper.text()).toContain('Open CPL Dashboard')
    expect(wrapper.find('[data-testid="hbr-mapping-diagnostics"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="hbr-apply-follow-up-message"]').text()).toContain(
      'Run dry-run audit again to verify post-apply completeness.',
    )
  })

  it('renders detailed mapping diagnostics from apply response when available', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessApply).mockResolvedValue({
      status: 'applied',
      processed_matches: 1,
      skipped_matches: 0,
      failed_matches: 0,
      deliveries_rebuilt: 120,
      wickets_rebuilt: 8,
      player_mappings_updated: 3,
      mappings_updated: 3,
      mappings_created: 2,
      resolved_players: 18,
      unresolved_players: 2,
      ambiguous_players: 2,
      resolved_venues: 0,
      unresolved_venues: 1,
      changed_match_ids: ['match-1'],
      blocked_records: [],
      results: [
        {
          match_id: 'f9261355-5662-4df8-b5e7-abe819989694',
          batch_id: 'batch-1',
          status: 'processed',
          reason: null,
          completeness_before: 'metadata_only',
          completeness_after: 'phase_analytics_available',
          deliveries_before: 0,
          deliveries_after: 254,
          wickets_before: 0,
          wickets_after: 10,
          player_mappings_updated: 3,
          mappings_updated: 3,
          mappings_created: 2,
          resolved_players: 18,
          unresolved_players: 2,
          ambiguous_players: 2,
          resolved_venues: 0,
          unresolved_venues: 1,
          unresolved_player_reasons: [
            {
              source_player_name: 'Unknown Batter',
              source_player_id: 'source-p-1',
              source_team: 'Barbados Tridents',
              reason: 'missing_source_id',
            },
          ],
          ambiguous_player_reasons: [
            {
              source_player_name: 'Chris Jordan',
              source_player_id: 'source-p-2',
              source_team: 'St Kitts and Nevis Patriots',
              reason: 'ambiguous_match',
              candidate_count: 2,
            },
          ],
          unresolved_venue_reasons: [
            {
              source_venue_name: 'Unknown Ground',
              reason: 'empty_raw_venue',
            },
          ],
        },
      ],
      rollback_info: 'rollback info',
    })

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hbr-apply-btn"]').trigger('click')
    await flushPromises()

    const diagnostics = wrapper.get('[data-testid="hbr-mapping-diagnostics"]')
    expect(diagnostics.text()).toContain('Historical identity mapping diagnostics')
    expect(diagnostics.text()).toContain('Resolved players: 18')
    expect(diagnostics.text()).toContain('Unresolved players: 2')
    expect(diagnostics.text()).toContain('Ambiguous players: 2')
    expect(diagnostics.text()).toContain('Resolved venues: 0')
    expect(diagnostics.text()).toContain('Unresolved venues: 1')
    expect(diagnostics.text()).toContain('Mappings created: 2')
    expect(diagnostics.text()).toContain('Mappings updated: 3')
    expect(diagnostics.text()).toContain('Match ID: f9261355-5662-4df8-b5e7-abe819989694 · Batch ID: batch-1')
    expect(diagnostics.text()).toContain('source_player_name: Unknown Batter')
    expect(diagnostics.text()).toContain('reason: missing_source_id')
    expect(diagnostics.text()).toContain('source_player_name: Chris Jordan')
    expect(diagnostics.text()).toContain('reason: ambiguous_match')
    expect(diagnostics.text()).toContain('candidate_count: 2')
    expect(diagnostics.text()).toContain('source_venue_name: Unknown Ground')
    expect(diagnostics.text()).toContain('reason: empty_raw_venue')
  })

  it('shows visible backend apply error details', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessApply).mockRejectedValue(
      new Error('{"detail":"confirm must be true to apply controlled delivery backfill."}'),
    )

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hbr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-error"]').text()).toContain(
      'confirm must be true to apply controlled delivery backfill.',
    )
  })

  it('shows visible network apply error details', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessApply).mockRejectedValue(new TypeError('Failed to fetch'))

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hbr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-error"]').text()).toContain('Failed to fetch')
  })

  it('prevents duplicate apply submits while loading and shows loading state', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    const pendingApply = deferred<api.HistoricalBackfillApplyResponse>()
    vi.mocked(api.historicalBackfillReprocessApply).mockReturnValue(pendingApply.promise)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    const applyButton = wrapper.get('[data-testid="hbr-apply-btn"]')
    await applyButton.trigger('click')
    await applyButton.trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReprocessApply).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="hbr-apply-loading"]').text()).toContain(
      'Submitting controlled apply request…',
    )
    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()

    pendingApply.resolve({
      status: 'applied',
      processed_matches: 1,
      skipped_matches: 0,
      failed_matches: 0,
      deliveries_rebuilt: 120,
      wickets_rebuilt: 8,
      player_mappings_updated: 3,
      unresolved_players: 0,
      unresolved_venues: 0,
      changed_match_ids: ['match-1'],
      blocked_records: [],
      results: [],
      rollback_info: 'rollback info',
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="hbr-apply-loading"]').exists()).toBe(false)
  })

  it('enables apply for eligible retained-source row after confirmation without requiring diagnosis', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).not.toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('keeps apply disabled for eligible retained-source row without confirmation and does not show safety warning', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).not.toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('keeps apply disabled for selected missing-source records even when marked eligible', async () => {
    const response = cloneAuditResponse()
    response.records[2].eligible = true
    response.records[2].blocked_reason = null
    response.records[2].missing_source_json = true
    response.records[2].source_json_retained = false
    response.records[2].expected_deliveries = 120
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(response)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[2].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('keeps apply disabled for mixed safe + blocked selections', async () => {
    const response = cloneAuditResponse()
    response.records[1].blocked_reason = 'missing_source_json'
    response.records[1].missing_source_json = true
    response.records[1].source_json_retained = false
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(response)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await rowChecks[1].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('keeps apply disabled for eligible rows with zero expected deliveries', async () => {
    const response = cloneAuditResponse()
    response.records[0].expected_deliveries = 0
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(response)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()
  })

  it('keeps controlled apply disabled when diagnosis marks selected record unsafe', async () => {
    const diagnosisUnsafe = structuredClone(diagnosisResponse)
    diagnosisUnsafe.records.unshift({
      ...diagnosisUnsafe.records[0],
      match_id: 'match-2',
      batch_id: 'batch-2',
      safely_reprocessable: false,
      skip_or_failure_reason: 'registry_people_missing',
    })
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisUnsafe)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await wrapper.get('[data-testid="hbr-run-diagnosis-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[1].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('enables apply when diagnosis explicitly marks selected record safe', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await wrapper.get('[data-testid="hbr-run-diagnosis-btn"]').trigger('click')
    await flushPromises()

    const rowChecks = wrapper.findAll('tbody input[type="checkbox"]')
    await rowChecks[0].setValue(true)
    await wrapper.get('.hbr-confirm input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(wrapper.get('[data-testid="hbr-apply-btn"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).not.toContain(CONTROLLED_APPLY_SAFETY_WARNING)
  })

  it('shows per-record reattach action and successful upload details', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReattachSourceJson).mockResolvedValue({
      record_id: 'batch-3',
      match_id: 'match-3',
      retained: true,
      status: 'reattached',
      validation_confidence: 'probable_match',
      validation_reason: 'Core identity fields appear compatible with selected record.',
      matched_identity_fields: ['teams', 'date', 'season'],
      mismatch_warnings: [],
      source_hash_sha256: 'abc123',
      uploaded_filename: 'repair.json',
      recommended_next_action: 'Run diagnosis again.',
    })
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const detailButtons = wrapper.findAll('[data-testid="hbr-view-identity-btn"]')
    await detailButtons[detailButtons.length - 1].trigger('click')
    await wrapper.get('[data-testid="hbr-reattach-row-btn"]').trigger('click')
    const fileInput = wrapper.get('[data-testid="hbr-reattach-file-input"]').element as HTMLInputElement
    Object.defineProperty(fileInput, 'files', {
      configurable: true,
      value: [new File(['{"ok":true}'], 'repair.json', { type: 'application/json' })],
    })
    await wrapper.get('[data-testid="hbr-reattach-file-input"]').trigger('change')
    await wrapper.get('[data-testid="hbr-reattach-submit-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReattachSourceJson).toHaveBeenCalledWith(
      'batch-3',
      expect.any(File),
    )
    expect(wrapper.text()).toContain('Validation confidence: probable_match')
    expect(wrapper.text()).toContain('Retained source hash: abc123')
    expect(wrapper.text()).toContain('Next action: Run diagnosis again.')
  })

  it('surfaces safe mismatch/malformed reattach errors', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    vi.mocked(api.historicalBackfillReattachSourceJson).mockRejectedValue(
      new Error('{"detail":"Uploaded JSON does not match selected record."}'),
    )
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const detailButtons = wrapper.findAll('[data-testid="hbr-view-identity-btn"]')
    await detailButtons[detailButtons.length - 1].trigger('click')
    await wrapper.get('[data-testid="hbr-reattach-row-btn"]').trigger('click')
    const fileInput = wrapper.get('[data-testid="hbr-reattach-file-input"]').element as HTMLInputElement
    Object.defineProperty(fileInput, 'files', {
      configurable: true,
      value: [new File(['{"bad":true}'], 'mismatch.json', { type: 'application/json' })],
    })
    await wrapper.get('[data-testid="hbr-reattach-file-input"]').trigger('change')
    await wrapper.get('[data-testid="hbr-reattach-submit-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Uploaded JSON does not match selected record.')
  })

  it('renders identity details and null-safe fallback values', async () => {
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)
    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    const detailButtons = wrapper.findAll('[data-testid="hbr-view-identity-btn"]')
    await detailButtons[0].trigger('click')
    await detailButtons[detailButtons.length - 1].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Trinbago Knight Riders vs Jamaica Tallawahs — 2013-09-07 — Port of Spain')
    expect(wrapper.text()).toContain('Competition/season: Caribbean Premier League / 2013')
    expect(wrapper.text()).toContain('Original filename/source hint: cpl-2013-match-1.json')
    expect(wrapper.text()).toContain(
      'Use the match identity fields below to locate the original CPL JSON before reattaching source.',
    )
    expect(wrapper.text()).toContain('Match date: —')
  })

  it('shows missing source JSON warning guidance', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)
    vi.mocked(api.historicalBackfillReprocessAudit).mockResolvedValue(auditResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-audit-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain(
      'Source JSON missing. This record requires a source-payload reattach workflow before delivery reprocess can run.',
    )
  })

  it('runs diagnosis as read-only step and shows missing source guidance', async () => {
    vi.mocked(api.historicalBackfillReprocessDiagnose).mockResolvedValue(diagnosisResponse)

    const wrapper = mount(HistoricalBackfillReprocessPanel)
    await wrapper.get('[data-testid="hbr-run-diagnosis-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalBackfillReprocessDiagnose).toHaveBeenCalledWith({
      batch_ids: ['batch-1'],
      match_ids: [],
      max_batch_size: 1,
    })
    expect(wrapper.text()).toContain('Diagnosis summary (read-only)')
    expect(wrapper.text()).toContain(
      'Source JSON missing. Reattach original JSON before delivery diagnosis or reprocess can run.',
    )
  })
})
