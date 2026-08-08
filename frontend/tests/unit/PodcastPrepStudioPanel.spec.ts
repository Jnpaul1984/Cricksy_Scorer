import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PodcastPrepStudioPanel from '@/components/PodcastPrepStudioPanel.vue'
import {
  generateMatchPodcastPack,
  generateTournamentPodcastPack,
  generateArchivePodcastPack,
  generateRosterPodcastPack,
  getAnalystRegistry,
  getTournamentGroups,
  listCplTeams,
  listPodcastPrepReports,
  createPodcastPrepReport,
  updatePodcastPrepReport,
  type AnalystMatchRegistryListResponse,
  type TournamentGroupsResponse,
  type CplTeamListResponse,
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
    getAnalystRegistry: vi.fn(),
    getTournamentGroups: vi.fn(),
    listCplTeams: vi.fn(),
    listPodcastPrepReports: vi.fn(),
    createPodcastPrepReport: vi.fn(),
    updatePodcastPrepReport: vi.fn(),
  }
})

const matchPackMock = vi.mocked(generateMatchPodcastPack)
const tournamentPackMock = vi.mocked(generateTournamentPodcastPack)
const archivePackMock = vi.mocked(generateArchivePodcastPack)
const rosterPackMock = vi.mocked(generateRosterPodcastPack)
const analystRegistryMock = vi.mocked(getAnalystRegistry)
const tournamentGroupsMock = vi.mocked(getTournamentGroups)
const cplTeamsMock = vi.mocked(listCplTeams)
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

const registryResponse: AnalystMatchRegistryListResponse = {
  entries: [
    {
      match_id: 'match-abc',
      match_title: 'Trinbago Knight Riders vs St Lucia Kings',
      team_a: 'Trinbago Knight Riders',
      team_b: 'St Lucia Kings',
      canonical_team_a: 'trinbago knight riders',
      canonical_team_b: 'st lucia kings',
      competition_name: 'Caribbean Premier League',
      competition_code: 'CPL_MEN',
      season: '2025',
      season_year: 2025,
      gender_category: 'men',
      age_category: 'senior',
      format: 'T20',
      venue_raw: 'Providence Stadium',
      venue_canonical: 'Providence Stadium',
      match_date: '2025-08-23',
      source_type: 'historical_import',
      data_completeness: 'delivery_complete',
      has_delivery_data: true,
      has_phase_data: true,
      has_scorecard_data: true,
      result: 'Trinbago Knight Riders won by 7 wickets',
      analyst_ready: true,
    },
    {
      match_id: 'match-def',
      match_title: 'Trinbago Knight Riders vs St Lucia Kings',
      team_a: 'Trinbago Knight Riders',
      team_b: 'St Lucia Kings',
      canonical_team_a: 'trinbago knight riders',
      canonical_team_b: 'st lucia kings',
      competition_name: 'Caribbean Premier League',
      competition_code: 'CPL_MEN',
      season: '2024',
      season_year: 2024,
      gender_category: 'men',
      age_category: 'senior',
      format: 'T20',
      venue_raw: 'Queen’s Park Oval',
      venue_canonical: 'Queen’s Park Oval',
      match_date: '2024-08-18',
      source_type: 'historical_import',
      data_completeness: 'delivery_complete',
      has_delivery_data: true,
      has_phase_data: true,
      has_scorecard_data: true,
      result: 'St Lucia Kings won by 2 runs',
      analyst_ready: true,
    },
  ],
  total: 2,
  diagnostics: {},
}

const tournamentGroupsResponse: TournamentGroupsResponse = {
  groups: [
    {
      group_key: {
        competition_code: 'CPL_MEN',
        competition_name: 'Caribbean Premier League',
        season: '2025',
        season_year: 2025,
        gender_category: 'men',
        format_family: 'T20',
        source_type: 'historical_import',
      },
      match_count: 34,
      teams_count: 6,
      has_result_data: true,
      has_delivery_data: true,
      champion_detected: true,
      champion_team: 'Trinbago Knight Riders',
      confidence: 'high',
    },
  ],
  total_groups: 1,
  total_matches: 34,
}

const rosterTeamsResponse: CplTeamListResponse = {
  teams: [
    {
      id: 'team-1',
      competition_code: 'CPL_MEN',
      season: '2025',
      team_name: 'Trinbago Knight Riders',
      normalized_team_name: 'trinbago knight riders',
      short_name: 'TKR',
      source_note: null,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
  ],
  total: 1,
}

describe('PodcastPrepStudioPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listReportsMock.mockResolvedValue(emptyListResponse)
    analystRegistryMock.mockResolvedValue(registryResponse)
    tournamentGroupsMock.mockResolvedValue(tournamentGroupsResponse)
    cplTeamsMock.mockResolvedValue(rosterTeamsResponse)
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
    it('is disabled when no match is selected', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const btn = wrapper.find('.pps-generate-btn')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('is enabled when a match result is selected', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const resultBtn = wrapper.findAll('.pps-match-result').at(0)
      await resultBtn?.trigger('click')
      const btn = wrapper.find('.pps-generate-btn')
      expect(btn.attributes('disabled')).toBeUndefined()
    })

    it('does not require raw match UUID input in normal workflow', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(matchPackMock).toHaveBeenCalledWith({ match_id: 'match-abc' })
    })
  })

  // ---------------------------------------------------------------------------
  // Research pack generation
  // ---------------------------------------------------------------------------

  describe('match pack generation', () => {
    it('calls generateMatchPodcastPack with selected internal match id', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(matchPackMock).toHaveBeenCalledWith({ match_id: 'match-abc' })
    })

    it('disambiguates repeated fixtures by date and competition context', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const results = wrapper.findAll('.pps-match-result')
      expect(results).toHaveLength(2)
      expect(results.at(0)?.text()).toContain('2025-08-23')
      expect(results.at(1)?.text()).toContain('2024-08-18')
      expect(results.at(0)?.text()).toContain('Caribbean Premier League')
    })

    it('filters imported fixtures by team name search', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-team').setValue('St Lucia Kings')
      await flushPromises()
      expect(wrapper.findAll('.pps-match-result')).toHaveLength(2)
      await wrapper.find('#pps-match-date').setValue('2025-08-23')
      await flushPromises()
      expect(wrapper.findAll('.pps-match-result')).toHaveLength(1)
    })

    it('displays pack title after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain(samplePack.title)
    })

    it('displays trust note after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Trust note:')
      expect(wrapper.text()).toContain(samplePack.trust_note)
    })

    it('displays all section labels after generation', async () => {
      matchPackMock.mockResolvedValue(samplePack)
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
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
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Confidence: high')
    })

    it('shows friendly error message when generation fails', async () => {
      matchPackMock.mockRejectedValue(new Error('Server error'))
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Unable to generate this match pack')
      expect(wrapper.text()).not.toContain('check the match_id')
    })

    it('shows safe empty state when no imported match filters match', async () => {
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      await wrapper.find('#pps-match-team').setValue('No Such Team')
      await flushPromises()
      expect(wrapper.text()).toContain('No imported matches match these filters.')
    })
  })

  describe('tournament pack generation', () => {
    it('switches to tournament topic and resolves competition-season selection', async () => {
      tournamentPackMock.mockResolvedValue({ ...samplePack, topic_type: 'tournament', title: 'CPL_MEN 2024 Season' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      // Click tournament topic button
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const tournamentBtn = topicBtns.find(b => b.text().includes('Tournament'))
      await tournamentBtn?.trigger('click')
      await wrapper.find('#pps-comp-code').setValue('CPL_MEN')
      await wrapper.find('#pps-season').setValue('2025')
      await wrapper.find('#pps-gender').setValue('men')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(tournamentPackMock).toHaveBeenCalledWith(
        expect.objectContaining({ competition_code: 'CPL_MEN', season: '2025', gender_category: 'men' })
      )
    })
  })

  describe('archive pack generation', () => {
    it('sends archive filters aligned to archive explorer fields', async () => {
      archivePackMock.mockResolvedValue({ ...samplePack, topic_type: 'archive', title: 'Archive Story' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const archiveBtn = topicBtns.find(b => b.text().includes('Archive'))
      await archiveBtn?.trigger('click')
      await wrapper.find('#pps-arch-comp').setValue('CPL_MEN')
      await wrapper.find('#pps-arch-season-start').setValue('2020')
      await wrapper.find('#pps-arch-season-end').setValue('2025')
      await wrapper.find('#pps-arch-format').setValue('T20')
      await wrapper.find('#pps-arch-gender').setValue('men')
      await wrapper.find('#pps-arch-min').setValue('7')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(archivePackMock).toHaveBeenCalledWith(
        expect.objectContaining({
          competition_code: 'CPL_MEN',
          season_start: 2020,
          season_end: 2025,
          format_family: 'T20',
          gender_category: 'men',
          minimum_matches: 7,
        }),
      )
    })
  })

  describe('roster pack generation', () => {
    it('calls generateRosterPodcastPack with roster-backed team selection', async () => {
      rosterPackMock.mockResolvedValue({ ...samplePack, topic_type: 'roster', title: 'CPL_MEN 2025 Roster' })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const rosterBtn = topicBtns.find(b => b.text().includes('Roster'))
      await rosterBtn?.trigger('click')
      await wrapper.find('#pps-ros-comp').setValue('CPL_MEN')
      await wrapper.find('#pps-ros-season').setValue('2025')
      await flushPromises()
      await wrapper.find('#pps-ros-team').setValue('Trinbago Knight Riders')
      await wrapper.find('.pps-generate-btn').trigger('click')
      await flushPromises()
      expect(rosterPackMock).toHaveBeenCalledWith(
        expect.objectContaining({
          competition_code: 'CPL_MEN',
          season: '2025',
          team_name: 'Trinbago Knight Riders',
        })
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

    it('shows missing roster guidance when no records exist for competition/season', async () => {
      cplTeamsMock.mockResolvedValue({ teams: [], total: 0 })
      const wrapper = mount(PodcastPrepStudioPanel)
      await flushPromises()
      const topicBtns = wrapper.findAll('.pps-topic-btn')
      const rosterBtn = topicBtns.find(b => b.text().includes('Roster'))
      await rosterBtn?.trigger('click')
      await wrapper.find('#pps-ros-comp').setValue('CPL_MEN')
      await wrapper.find('#pps-ros-season').setValue('2026')
      await flushPromises()
      expect(wrapper.text()).toContain('Import a roster first')
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
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
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
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
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
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
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
      await wrapper.findAll('.pps-match-result').at(0)?.trigger('click')
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
