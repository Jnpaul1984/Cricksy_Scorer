import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import BulkZipSourcePayloadRecoveryPanel from '@/components/BulkZipSourcePayloadRecoveryPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalBulkZipSourcePayloadDryRun: vi.fn(),
  historicalBulkZipSourcePayloadApply: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

const zipFile = new File(['PK'], 'cpl_batch.zip', { type: 'application/zip' })

const uploadZip = async (wrapper: ReturnType<typeof mount>) => {
  const input = wrapper.get('[data-testid="bzsr-file-input"]').element as HTMLInputElement
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [zipFile],
  })
  await wrapper.get('[data-testid="bzsr-file-input"]').trigger('change')
}

const exactFileEntry: api.HistoricalSourcePayloadReattachDryRunFileResult = {
  file_name: '1018873.json',
  status: 'ready',
  match_confidence: 'exact_match',
  blocked_from_apply: false,
  message: 'Deterministic exact match found.',
  metadata: {
    competition_name: 'Caribbean Premier League',
    season: '2013',
    match_number: 1,
    date: '2013-07-31',
    teams: ['Barbados Tridents', 'Guyana Amazon Warriors'],
    venue: 'Kensington Oval',
    city: 'Bridgetown',
    source_filename: '1018873.json',
    registry_people_available: true,
    expected_deliveries: 246,
    expected_wickets: 13,
  },
  matched_target: {
    match_id: 'match-1',
    batch_id: 'batch-1',
    confidence: 'exact_match',
    matched_on: ['date', 'teams', 'competition', 'season', 'venue'],
    source_json_retained: false,
    metadata: {
      competition_name: 'Caribbean Premier League',
      season: '2013',
      match_number: 1,
      date: '2013-07-31',
      teams: ['Barbados Tridents', 'Guyana Amazon Warriors'],
      venue: 'Kensington Oval',
      city: 'Bridgetown',
      source_filename: null,
      registry_people_available: false,
      expected_deliveries: 0,
      expected_wickets: 0,
    },
  },
  candidate_matches: [],
  warnings: [],
}

const ambiguousFileEntry: api.HistoricalSourcePayloadReattachDryRunFileResult = {
  file_name: 'ambig.json',
  status: 'ready',
  match_confidence: 'ambiguous',
  blocked_from_apply: true,
  message: 'Multiple historical matches satisfy the deterministic matching rules; apply is blocked.',
  metadata: {
    competition_name: 'Caribbean Premier League',
    season: '2013',
    match_number: 2,
    date: '2013-08-01',
    teams: ['Team A', 'Team B'],
    venue: null,
    city: null,
    source_filename: 'ambig.json',
    registry_people_available: false,
    expected_deliveries: 0,
    expected_wickets: 0,
  },
  matched_target: null,
  candidate_matches: [],
  warnings: [],
}

const dryRunResponse: api.HistoricalBulkZipSourcePayloadDryRunResponse = {
  status: 'preview_ready',
  source_filename: 'cpl_batch.zip',
  summary: {
    candidate_json_count: 2,
    exact_match_count: 1,
    likely_match_count: 0,
    ambiguous_count: 1,
    no_match_count: 0,
    already_retained_count: 0,
    malformed_count: 0,
    unsafe_count: 0,
  },
  files: [exactFileEntry, ambiguousFileEntry],
}

const applyResponse: api.HistoricalBulkZipSourcePayloadApplyResponse = {
  status: 'applied',
  source_filename: 'cpl_batch.zip',
  selected_count: 1,
  applied_count: 1,
  skipped_count: 0,
  ambiguous_count: 1,
  no_match_count: 0,
  malformed_count: 0,
  error_count: 0,
  results: [
    {
      file_name: '1018873.json',
      status: 'reattached',
      message: 'Source payload reattached. Run delivery backfill/reprocess separately.',
      match_id: 'match-1',
      batch_id: 'batch-1',
      match_confidence: 'exact_match',
    },
  ],
  follow_up_message:
    'Source payload reattach does not run delivery reprocess automatically. ' +
    'Run Historical Backfill Audit + Reprocess after successful reattach.',
}

describe('BulkZipSourcePayloadRecoveryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the section title', () => {
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    expect(wrapper.text()).toContain('Bulk ZIP Source Payload Recovery')
  })

  it('renders warning banner about no delivery insertion', () => {
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    expect(wrapper.text()).toContain('No delivery rows are inserted')
  })

  it('dry-run button is disabled when no file is selected', () => {
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    const btn = wrapper.get('[data-testid="bzsr-run-dry-run-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('dry-run summary renders after successful dry-run', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    const summary = wrapper.get('[data-testid="bzsr-dry-run-summary"]')
    expect(summary.text()).toContain('Exact matches')
    expect(wrapper.get('[data-testid="bzsr-exact-count"]').text()).toBe('1')
    expect(wrapper.get('[data-testid="bzsr-likely-count"]').text()).toBe('0')
  })

  it('candidate mapping table renders file entries', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    const table = wrapper.get('[data-testid="bzsr-mapping-table"]')
    expect(table.text()).toContain('1018873.json')
    expect(table.text()).toContain('exact_match')
    expect(table.text()).toContain('246')
    expect(table.text()).toContain('13')
    expect(table.text()).toContain('Barbados Tridents')
    expect(table.text()).toContain('match-1')
    expect(table.text()).toContain('batch-1')
  })

  it('ambiguous mappings cannot be selected or applied', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    // Ambiguous row should NOT have a checkbox
    expect(wrapper.find('[data-testid="bzsr-select-ambig.json"]').exists()).toBe(false)
  })

  it('exact match checkbox can be selected', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockResolvedValue(dryRunResponse)
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    const checkbox = wrapper.find('[data-testid="bzsr-select-1018873.json"]')
    expect(checkbox.exists()).toBe(true)
    await checkbox.trigger('change')
    await flushPromises()

    // Apply section should now appear
    expect(wrapper.find('[data-testid="bzsr-apply-section"]').exists()).toBe(true)
  })

  it('apply response renders summary and follow-up instruction', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockResolvedValue(dryRunResponse)
    vi.mocked(api.historicalBulkZipSourcePayloadApply).mockResolvedValue(applyResponse)
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    // Select exact match
    await wrapper.find('[data-testid="bzsr-select-1018873.json"]').trigger('change')
    await flushPromises()

    // Check confirm checkbox
    await wrapper.get('[data-testid="bzsr-confirm-checkbox"]').setValue(true)
    await flushPromises()

    // Click apply
    await wrapper.get('[data-testid="bzsr-apply-btn"]').trigger('click')
    await flushPromises()

    const result = wrapper.get('[data-testid="bzsr-apply-result"]')
    expect(result.text()).toContain('applied')
    expect(result.text()).toContain('Applied: 1')

    const followUp = wrapper.get('[data-testid="bzsr-follow-up-message"]')
    expect(followUp.text()).toContain('reprocess')
    expect(followUp.text()).toContain('delivery')
  })

  it('shows error when dry-run fails', async () => {
    vi.mocked(api.historicalBulkZipSourcePayloadDryRun).mockRejectedValue(
      new Error('Server error'),
    )
    const wrapper = mount(BulkZipSourcePayloadRecoveryPanel)
    await uploadZip(wrapper)
    await wrapper.get('[data-testid="bzsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="bzsr-error"]').text()).toContain('Server error')
  })
})
