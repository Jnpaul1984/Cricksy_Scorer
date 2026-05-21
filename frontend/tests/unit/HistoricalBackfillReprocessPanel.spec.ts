import { mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import HistoricalBackfillReprocessPanel from '@/components/HistoricalBackfillReprocessPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalBackfillReprocessDiagnose: vi.fn(),
  historicalBackfillReprocessAudit: vi.fn(),
  historicalBackfillReprocessApply: vi.fn(),
  historicalImportListBatches: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

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
