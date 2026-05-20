import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HistoricalSourcePayloadReattachPanel from '@/components/HistoricalSourcePayloadReattachPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalSourcePayloadReattachDryRun: vi.fn(),
  historicalSourcePayloadReattachApply: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

const repairFile = new File(['{"hello":"world"}'], 'repair.json', { type: 'application/json' })

const uploadFile = async (wrapper: ReturnType<typeof mount>) => {
  const input = wrapper.get('[data-testid="hsr-file-input"]').element as HTMLInputElement
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [repairFile],
  })
  await wrapper.get('[data-testid="hsr-file-input"]').trigger('change')
}

const dryRunResponse = {
  status: 'preview_ready' as const,
  source_filename: 'repair.json',
  total_candidates: 2,
  ready_candidates: 1,
  blocked_candidates: 1,
  files: [
    {
      file_name: 'repair.json',
      status: 'ready' as const,
      match_confidence: 'exact_match' as const,
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
        source_filename: 'repair.json',
        registry_people_available: true,
        expected_deliveries: 120,
        expected_wickets: 7,
      },
      matched_target: {
        match_id: 'match-1',
        batch_id: 'batch-1',
        confidence: 'exact_match' as const,
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
          source_filename: 'legacy.json',
          registry_people_available: false,
          expected_deliveries: 0,
          expected_wickets: 0,
        },
      },
      candidate_matches: [],
      warnings: [],
    },
    {
      file_name: 'ambiguous.json',
      status: 'ready' as const,
      match_confidence: 'ambiguous' as const,
      blocked_from_apply: true,
      message: 'Multiple historical matches satisfy the deterministic matching rules; apply is blocked.',
      metadata: {
        competition_name: 'Caribbean Premier League',
        season: '2013',
        match_number: null,
        date: '2013-07-31',
        teams: ['Barbados Tridents', 'Guyana Amazon Warriors'],
        venue: 'Kensington Oval',
        city: null,
        source_filename: 'ambiguous.json',
        registry_people_available: false,
        expected_deliveries: 118,
        expected_wickets: 6,
      },
      matched_target: null,
      candidate_matches: [
        {
          match_id: 'match-1',
          batch_id: 'batch-1',
          confidence: 'likely_match' as const,
          matched_on: ['date', 'teams', 'competition', 'season'],
          source_json_retained: false,
          metadata: {
            competition_name: 'Caribbean Premier League',
            season: '2013',
            match_number: 1,
            date: '2013-07-31',
            teams: ['Barbados Tridents', 'Guyana Amazon Warriors'],
            venue: 'Kensington Oval',
            city: 'Bridgetown',
            source_filename: 'legacy-a.json',
            registry_people_available: false,
            expected_deliveries: 0,
            expected_wickets: 0,
          },
        },
        {
          match_id: 'match-2',
          batch_id: 'batch-2',
          confidence: 'likely_match' as const,
          matched_on: ['date', 'teams', 'competition', 'season'],
          source_json_retained: false,
          metadata: {
            competition_name: 'Caribbean Premier League',
            season: '2013',
            match_number: 2,
            date: '2013-07-31',
            teams: ['Barbados Tridents', 'Guyana Amazon Warriors'],
            venue: 'Providence Stadium',
            city: 'Providence',
            source_filename: 'legacy-b.json',
            registry_people_available: false,
            expected_deliveries: 0,
            expected_wickets: 0,
          },
        },
      ],
      warnings: [],
    },
  ],
}

describe('HistoricalSourcePayloadReattachPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('uploads a file and runs dry-run matching', async () => {
    vi.mocked(api.historicalSourcePayloadReattachDryRun).mockResolvedValue(dryRunResponse)

    const wrapper = mount(HistoricalSourcePayloadReattachPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalSourcePayloadReattachDryRun).toHaveBeenCalledWith(repairFile)
    expect(wrapper.text()).toContain('Ready exact/likely matches: 1')
    expect(wrapper.text()).toContain('Ambiguous and no-match files are blocked from apply.')
  })

  it('applies only selected exact/likely mappings after confirmation', async () => {
    vi.mocked(api.historicalSourcePayloadReattachDryRun).mockResolvedValue(dryRunResponse)
    vi.mocked(api.historicalSourcePayloadReattachApply).mockResolvedValue({
      status: 'applied',
      source_filename: 'repair.json',
      selected_count: 1,
      reattached_count: 1,
      skipped_count: 0,
      error_count: 0,
      results: [
        {
          file_name: 'repair.json',
          status: 'reattached',
          message: 'Source payload reattached.',
          match_id: 'match-1',
          batch_id: 'batch-1',
          match_confidence: 'exact_match',
        },
      ],
      follow_up_message:
        'Source payload reattach does not run delivery reprocess automatically. Use Historical Backfill Audit + Reprocess after successful reattach.',
    })

    const wrapper = mount(HistoricalSourcePayloadReattachPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    const checkboxes = wrapper.findAll('tbody input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await wrapper.get('.hsr-confirm input[type="checkbox"]').setValue(true)
    await wrapper.get('[data-testid="hsr-apply-btn"]').trigger('click')
    await flushPromises()

    expect(api.historicalSourcePayloadReattachApply).toHaveBeenCalledWith(repairFile, [
      { file_name: 'repair.json', batch_id: 'batch-1' },
    ])
    expect(wrapper.text()).toContain('Reattached: 1')
    expect(wrapper.text()).toContain('does not run delivery reprocess automatically')
  })

  it('keeps ambiguous rows blocked from selection', async () => {
    vi.mocked(api.historicalSourcePayloadReattachDryRun).mockResolvedValue(dryRunResponse)

    const wrapper = mount(HistoricalSourcePayloadReattachPanel)
    await uploadFile(wrapper)
    await wrapper.get('[data-testid="hsr-run-dry-run-btn"]').trigger('click')
    await flushPromises()

    const checkboxes = wrapper.findAll('tbody input[type="checkbox"]')
    expect(checkboxes[1].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('2 candidates')
  })
})
