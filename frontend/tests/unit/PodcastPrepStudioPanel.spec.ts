import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PodcastPrepStudioPanel from '@/components/PodcastPrepStudioPanel.vue'
import {
  generateMatchPodcastPack,
  generateTournamentPodcastPack,
  generateArchivePodcastPack,
  generateRosterPodcastPack,
  listPodcastPrepReports,
  createPodcastPrepReport,
  updatePodcastPrepReport,
  type PodcastResearchPack,
  type PodcastPrepReportListResponse,
  type PodcastPrepReportResponse,
} from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    generateMatchPodcastPack: vi.fn(),
    generateTournamentPodcastPack: vi.fn(),
    generateArchivePodcastPack: vi.fn(),
    generateRosterPodcastPack: vi.fn(),
    listPodcastPrepReports: vi.fn(),
    createPodcastPrepReport: vi.fn(),
    updatePodcastPrepReport: vi.fn(),
  }
})

const matchPackMock = vi.mocked(generateMatchPodcastPack)
const tournamentPackMock = vi.mocked(generateTournamentPodcastPack)
const archivePackMock = vi.mocked(generateArchivePodcastPack)
const rosterPackMock = vi.mocked(generateRosterPodcastPack)
const listReportsMock = vi.mocked(listPodcastPrepReports)
const createReportMock = vi.mocked(createPodcastPrepReport)
const updateReportMock = vi.mocked(updatePodcastPrepReport)

const samplePack: PodcastResearchPack = {
  topic_type: 'match',
  title: 'CPL 2024 Final — TKR vs Barbados Royals',
  subtitle: 'T20 match — 2024-09-01',
  overall_confidence: 'high',
  trust_note: 'Match facts are derived from imported match data.',
  generated_at: '2024-09-02T10:00:00Z',
  sections: [
    {
      label: 'Episode Topic',
      content: 'CPL 2024 Final — TKR vs Barbados Royals',
      source_note: 'Match registry',
      confidence: 'high',
    },
    {
      label: 'Key Facts',
      content: 'TKR won by 7 wickets. Kieron Pollard scored 45 runs.',
      source_note: 'Derived from delivery data',
      confidence: 'high',
    },
    {
      label: 'Trust Note',
      content: 'Match facts are derived from imported match data.',
      source_note: null,
      confidence: 'high',
    },
  ],
}

const sampleReport: PodcastPrepReportResponse = {
  id: 'report-001',
  title: 'Test Report',
  topic_type: 'match',
  source_match_id: 'match-abc',
  source_competition_code: 'CPL_MEN',
  source_season: '2024',
  source_team_name: null,
  generated_markdown: '# Test Report\n\nContent here.',
  generated_plain_text: 'TEST REPORT\n\nContent here.',
  trust_summary: 'Match facts are derived from imported match data.',
  status: 'draft',
  created_by_id: null,
  created_at: '2024-09-01T10:00:00Z',
  updated_at: '2024-09-01T10:00:00Z',
}

const emptyListResponse: PodcastPrepReportListResponse = { reports: [], total: 0 }
const listWithReport: PodcastPrepReportListResponse = { reports: [sampleReport], total: 1 }

describe('PodcastPrepStudioPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listReportsMock.mockResolvedValue(emptyListResponse)
  })

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  describe('initial render', () => {
    it('renders the panel title', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Podcast Prep Studio')
    })

    it('shows topic type buttons', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Match')
      expect(wrapper.text()).toContain('Tournament')
      expect(wrapper.text()).toContain('Archive')
      expect(wrapper.text()).toContain('Roster')
    })

    it('shows provenance trust bar', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('derived from imported data')
    })

    it('shows saved reports section', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Saved Reports')
    })

    it('loads saved reports on mount', async () => {
      mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(listReportsMock).toHaveBeenCalledOnce()
    })
  })

  // ---------------------------------------------------------------------------
  // Generate button state
  // ---------------------------------------------------------------------------

  describe('generate button', () => {
    it('is disabled when no match id is provided', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const btn = wrapper.find('.pps-generate-btn')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('is enabled when match id is provided', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const input = wrapper.find('#pps-match-id')
      await input.setValue('match-abc-123')
      const btn = wrapper.find('.pps-generate-btn')
      expect(btn.attributes('disabled')).toBeUndefined()
    })
  })

  // ---------------------------------------------------------------------------
  // Research pack generation
  // ---------------------------------------------------------------------------

  describe('match pack generation', () => {
    it('calls generateMatchPodcastPack with the match id', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(matchPackMock).toHaveBeenCalledWith({ match_id: 'match-abc' })
    })

    it('displays pack title after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain(samplePack.title)
    })

    it('displays trust note after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Trust note:')
      expect(wrapper.text()).toContain(samplePack.trust_note)
    })

    it('displays all section labels after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      for (const section of samplePack.sections) {
        expect(wrapper.text()).toContain(section.label)
      }
    })

    it('shows confidence badge', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Confidence: high')
    })

    it('shows error message when generation fails', async () => {
      matchPackMock.mockRejectedValue(new Error('Server error'))
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Server error')
    })
  })

  describe('tournament pack generation', () => {
    it('switches to tournament topic and calls correct API', async () => {
      tournamentPackMock.mockResolvedValue({ ...samplePack, topic_type: 'tournament', title: 'CPL_MEN 2024 Season' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      // Click tournament topic button
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const tournamentBtn = topicBtns.find(b => b.text().includes('Tournament'))
      await tournamentBtn?.trigger('click')
      await wrapper.find('#pps-comp-code').setValue('CPL_MEN')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(tournamentPackMock).toHaveBeenCalledWith(
        expect.objectContaining({ competition_code: 'CPL_MEN' })
      )
    })
  })

  describe('roster pack generation', () => {
    it('calls generateRosterPodcastPack with competition and season', async () => {
      rosterPackMock.mockResolvedValue({ ...samplePack, topic_type: 'roster', title: 'CPL_MEN 2025 Roster' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const rosterBtn = topicBtns.find(b => b.text().includes('Roster'))
      await rosterBtn?.trigger('click')
      await wrapper.find('#pps-ros-comp').setValue('CPL_MEN')
      await wrapper.find('#pps-ros-season').setValue('2025')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(rosterPackMock).toHaveBeenCalledWith(
        expect.objectContaining({ competition_code: 'CPL_MEN', season: '2025' })
      )
    })

    it('is disabled without season when topic is roster', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const rosterBtn = topicBtns.find(b => b.text().includes('Roster'))
      await rosterBtn?.trigger('click')
      await wrapper.find('#pps-ros-comp').setValue('CPL_MEN')
      // No season provided
      const btn = wrapper.find('.pps-generate-btn')
      expect(btn.attributes('disabled')).toBeDefined()
    })
  })

  // ---------------------------------------------------------------------------
  // Copy / export
  // ---------------------------------------------------------------------------

  describe('copy and export', () => {
    it('shows copy markdown and copy plain text buttons after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      const exportRow = wrapper.find('.pps-export-row')
      expect(exportRow.text()).toContain('Copy Markdown')
      expect(exportRow.text()).toContain('Copy Plain Text')
    })

    it('shows save report button after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.find('.pps-save-btn').exists()).toBe(true)
    })
  })

  // ---------------------------------------------------------------------------
  // Save report
  // ---------------------------------------------------------------------------

  describe('save report', () => {
    it('calls createPodcastPrepReport with correct payload', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      createReportMock.mockResolvedValue(sampleReport)
      listReportsMock.mockResolvedValue(listWithReport)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      // Open save form
      await wrapper.find('.pps-save-btn').trigger('click')
      await flushPromises()
      // Set title
      await wrapper.find('#pps-report-title').setValue('My Test Report')
      // Submit
      const confirmBtn = wrapper.findAll('.pps-generate-btn').find(b => b.text().includes('Confirm'))
      await confirmBtn?.trigger('click')
      await flushPromises()
      expect(createReportMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'My Test Report',
          topic_type: 'match',
          trust_summary: samplePack.trust_note,
        })
      )
    })
  })

  // ---------------------------------------------------------------------------
  // Saved reports list
  // ---------------------------------------------------------------------------

  describe('saved reports list', () => {
    it('shows empty state when no reports', async () => {
      listReportsMock.mockResolvedValue(emptyListResponse)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('No saved reports found')
    })

    it('shows saved report title and status', async () => {
      listReportsMock.mockResolvedValue(listWithReport)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain(sampleReport.title)
      expect(wrapper.text()).toContain(sampleReport.status)
    })

    it('shows trust summary in saved report card', async () => {
      listReportsMock.mockResolvedValue(listWithReport)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain(sampleReport.trust_summary!)
    })

    it('shows competition code and season in card meta', async () => {
      listReportsMock.mockResolvedValue(listWithReport)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('CPL_MEN')
      expect(wrapper.text()).toContain('2024')
    })

    it('calls updatePodcastPrepReport when status changes', async () => {
      listReportsMock.mockResolvedValue(listWithReport)
      updateReportMock.mockResolvedValue({ ...sampleReport, status: 'approved' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const statusSelect = wrapper.find('.pps-saved-card-actions select')
      await statusSelect.setValue('approved')
      await flushPromises()
      expect(updateReportMock).toHaveBeenCalledWith('report-001', { status: 'approved' })
    })

    it('filters reports by status', async () => {
      listReportsMock.mockResolvedValue(emptyListResponse)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const filterSelect = wrapper.find('.pps-saved-filters select')
      await filterSelect.setValue('approved')
      await flushPromises()
      expect(listReportsMock).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'approved' })
      )
    })
  })

  // ---------------------------------------------------------------------------
  // Trust note
  // ---------------------------------------------------------------------------

  describe('trust note', () => {
    it('trust note is visible in pack output', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-id').setValue('match-abc')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      const trustEl = wrapper.find('.pps-trust-note')
      expect(trustEl.exists()).toBe(true)
      expect(trustEl.text()).toContain(samplePack.trust_note)
    })

    it('trust note is present in saved report card', async () => {
      listReportsMock.mockResolvedValue(listWithReport)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      expect(wrapper.find('.pps-saved-card-trust').text()).toContain(
        sampleReport.trust_summary!
      )
    })
  })
})
