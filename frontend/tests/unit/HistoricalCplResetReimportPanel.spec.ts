import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HistoricalCplResetReimportPanel from '@/components/HistoricalCplResetReimportPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  runCplResetReimportDryRun: vi.fn(),
  applyCplResetReimport: vi.fn(),
  getErrorMessage: vi.fn((err: unknown) => (err instanceof Error ? err.message : String(err))),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

const sourceFile = new File(['{"mock":true}'], 'cpl.json', { type: 'application/json' })

const uploadFile = async (wrapper: ReturnType<typeof mount>) => {
  const input = wrapper.get('[data-testid="hcrr-file-input"]').element as HTMLInputElement
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [sourceFile],
  })
  await wrapper.get('[data-testid="hcrr-file-input"]').trigger('change')
}

const dryRunResponse = {
  status: 'preview_ready' as const,
  operation: 'cpl_reset_reimport_dry_run' as const,
  scope: { match_ids: [], batch_ids: ['batch-1'], max_batch_size: 1 },
  total_candidate_existing_historical_records: 2,
  records_safe_to_reset: 1,
  records_blocked_from_reset: 1,
  expected_matches_to_import: 1,
  expected_deliveries: 120,
  expected_wickets: 8,
  expected_players: 22,
  duplicate_risks: 0,
  destructive_action_summary: {
    matches_to_reset: 1,
    historical_batches_in_scope: 2,
    delivery_rows_to_rebuild: 120,
    blocked_records: 1,
  },
  blocked_records: [{ match_id: 'match-2', batch_id: 'batch-2', reason: 'missing_source_json' }],
  source_bundle_preview: null,
  source_file_mapping: [
    {
      file_name: 'cpl.json',
      status: 'ready',
      match_confidence: 'exact_match' as const,
      blocked_from_apply: false,
      batch_id: 'batch-1',
      match_id: 'match-1',
    },
  ],
  audit: {
    total_imported_cpl_matches: 2,
    completeness_counts: {},
    import_origin_counts: {},
    player_aggregate_scope: 'scope',
    rollback_feasibility: 'safe',
    eligible_matches: 1,
    blocked_matches: 1,
    selected_matches: 2,
    records: [
      {
        match_id: 'match-1',
        batch_id: 'batch-1',
        import_source: 'single_json_apply' as const,
        completeness: 'metadata_only',
        eligible: true,
        blocked_reason: null,
        missing_source_json: false,
        duplicate_delivery_risk: false,
        apply_deliveries_previously_run: false,
        source_json_retained: true,
        registry_people_available: true,
        registry_people_count: 14,
        players_without_source_ids: 1,
        expected_deliveries: 120,
        expected_wickets: 8,
        expected_players: 22,
        venue: null,
      },
    ],
  },
}

describe('HistoricalCplResetReimportPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders with the required panel title', () => {
    const wrapper = mount(HistoricalCplResetReimportPanel)
    expect(wrapper.text()).toContain('Clean Historical CPL Reset + Reimport')
  })

  it('keeps apply disabled before a dry-run exists', async () => {
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    expect(wrapper.get('[data-testid="hcrr-apply-btn"]').attributes('disabled')).toBeDefined()
  })

  it('renders safe/blocked dry-run counts and destructive summary', async () => {
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()

    expect(api.runCplResetReimportDryRun).toHaveBeenCalledWith({
      file: sourceFile,
      max_batch_size: 1,
      season: '',
    })
    expect(wrapper.text()).toContain('Safe reset records: 1')
    expect(wrapper.text()).toContain('Blocked records: 1')
    expect(wrapper.text()).toContain('Matches to reset: 1')
  })

  it('enables apply only after successful dry-run + explicit confirmation', async () => {
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()

    const applyButton = wrapper.get('[data-testid="hcrr-apply-btn"]')
    expect(applyButton.attributes('disabled')).toBeDefined()

    await wrapper.get('.hcrr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hcrr-confirmation-phrase"]').setValue(
      'I confirm this controlled CPL reset/reimport operation',
    )
    expect(applyButton.attributes('disabled')).toBeUndefined()
  })

  it('renders final import report on apply success', async () => {
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(dryRunResponse)
    vi.mocked(api.applyCplResetReimport).mockResolvedValue({
      status: 'applied',
      operation: 'cpl_reset_reimport_apply',
      operation_id: 'op-123',
      scope: { match_ids: [], batch_ids: ['batch-1'], max_batch_size: 1 },
      source_payload_retention: { attempted: true, report: { status: 'applied', reattached_count: 1, skipped_count: 0, error_count: 0 } },
      reimport_report: { status: 'applied', selected_batches: 1, selected_matches: 0 },
    })
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()
    await wrapper.get('.hcrr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hcrr-confirmation-phrase"]').setValue(
      'I confirm this controlled CPL reset/reimport operation',
    )
    await wrapper.get('[data-testid="hcrr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Final import report')
    expect(wrapper.text()).toContain('Operation ID: op-123')
    expect(wrapper.text()).toContain('Matches reset (selected batches): 1')
    expect(wrapper.text()).toContain('Deliveries — Expected from dry-run: 120')
    expect(wrapper.text()).toContain('Players — Expected from dry-run: 22')
    expect(wrapper.text()).toContain('Source payloads reattached (apply report): 1')
    expect(wrapper.text()).toContain('Venue extraction count: Not reported by current apply response')
    expect(wrapper.text()).not.toContain('Deliveries imported/restored (expected)')
    expect(wrapper.text()).not.toContain('Venues extracted')
  })

  it('uses dry-run scope values when calling apply', async () => {
    const scopedDryRunResponse = {
      ...dryRunResponse,
      scope: {
        match_ids: ['match-dry-run-1', 'match-dry-run-2'],
        batch_ids: ['batch-dry-run-9'],
        max_batch_size: 7,
      },
    }
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(scopedDryRunResponse)
    vi.mocked(api.applyCplResetReimport).mockResolvedValue({
      status: 'applied',
      operation: 'cpl_reset_reimport_apply',
      operation_id: 'op-scope',
      scope: scopedDryRunResponse.scope,
      source_payload_retention: { attempted: true, report: { status: 'applied', reattached_count: 1, skipped_count: 0, error_count: 0 } },
      reimport_report: { status: 'applied', selected_batches: 1, selected_matches: 2 },
    })

    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-max-records"]').setValue('3')
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()
    await wrapper.get('.hcrr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hcrr-confirmation-phrase"]').setValue(
      'I confirm this controlled CPL reset/reimport operation',
    )
    await wrapper.get('[data-testid="hcrr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(api.applyCplResetReimport).toHaveBeenCalledWith({
      confirm: true,
      file: sourceFile,
      match_ids: ['match-dry-run-1', 'match-dry-run-2'],
      batch_ids: ['batch-dry-run-9'],
      max_batch_size: 7,
      season: '',
    })
  })

  it('renders readable apply failure error', async () => {
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(dryRunResponse)
    vi.mocked(api.applyCplResetReimport).mockRejectedValue(new Error('Request failed'))
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()
    await wrapper.get('.hcrr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hcrr-confirmation-phrase"]').setValue(
      'I confirm this controlled CPL reset/reimport operation',
    )
    await wrapper.get('[data-testid="hcrr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Request failed')
  })

  it('shows verification links/instructions after successful apply', async () => {
    vi.mocked(api.runCplResetReimportDryRun).mockResolvedValue(dryRunResponse)
    vi.mocked(api.applyCplResetReimport).mockResolvedValue({
      status: 'applied',
      operation: 'cpl_reset_reimport_apply',
      operation_id: 'op-verify',
      scope: { match_ids: [], batch_ids: ['batch-1'], max_batch_size: 1 },
      source_payload_retention: { attempted: true, report: { status: 'applied', reattached_count: 1, skipped_count: 0, error_count: 0 } },
      reimport_report: { status: 'applied', selected_batches: 1, selected_matches: 0 },
    })
    const wrapper = mount(HistoricalCplResetReimportPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hcrr-dry-run-btn"]').trigger('click')
    await flushPromises()
    await wrapper.get('.hcrr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hcrr-confirmation-phrase"]').setValue(
      'I confirm this controlled CPL reset/reimport operation',
    )
    await wrapper.get('[data-testid="hcrr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="hcrr-verification-links"]').text()).toContain(
      'Open Analyst Workspace',
    )
    expect(wrapper.text()).toContain('Verify now in Analyst Workspace tabs')
  })
})
