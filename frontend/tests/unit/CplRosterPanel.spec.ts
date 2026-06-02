import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CplRosterPanel from '@/components/CplRosterPanel.vue'
import {
  listCplTeams,
  listCplPlayers,
  createCplTeam,
  createCplPlayer,
  updateCplPlayer,
  rosterImportPreview,
  rosterImportApply,
  type CplTeamListResponse,
  type CplPlayerListResponse,
  type CplTeamResponse,
  type CplPlayerResponse,
  type RosterImportPreviewResponse,
  type RosterImportApplyResponse,
} from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    listCplTeams: vi.fn(),
    listCplPlayers: vi.fn(),
    createCplTeam: vi.fn(),
    createCplPlayer: vi.fn(),
    updateCplPlayer: vi.fn(),
    rosterImportPreview: vi.fn(),
    rosterImportApply: vi.fn(),
  }
})

const listTeamsMock = vi.mocked(listCplTeams)
const listPlayersMock = vi.mocked(listCplPlayers)
const createTeamMock = vi.mocked(createCplTeam)
const createPlayerMock = vi.mocked(createCplPlayer)
const updatePlayerMock = vi.mocked(updateCplPlayer)
const previewMock = vi.mocked(rosterImportPreview)
const applyMock = vi.mocked(rosterImportApply)

const sampleTeam: CplTeamResponse = {
  id: 'team-001',
  competition_code: 'CPL_MEN',
  season: '2025',
  team_name: 'Trinbago Knight Riders',
  normalized_team_name: 'trinbago knight riders',
  short_name: 'TKR',
  source_note: 'Manual entry',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

const samplePlayer: CplPlayerResponse = {
  id: 'player-001',
  competition_code: 'CPL_MEN',
  season: '2025',
  player_name: 'Kieron Pollard',
  normalized_player_name: 'kieron pollard',
  display_name: 'K. Pollard',
  aliases: ['Pollard'],
  team_name: 'Trinbago Knight Riders',
  role: 'all-rounder',
  batting_style: 'right-hand bat',
  bowling_style: 'right-arm medium',
  status: 'active',
  is_returning: true,
  prior_season: '2024',
  source_note: 'Official squad',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

const emptyTeams: CplTeamListResponse = { teams: [], total: 0 }
const emptyPlayers: CplPlayerListResponse = {
  players: [], total: 0, returning_count: 0, new_count: 0,
  trust_note: 'Roster data is user-maintained.',
}
const teamsWithOne: CplTeamListResponse = { teams: [sampleTeam], total: 1 }
const playersWithOne: CplPlayerListResponse = {
  players: [samplePlayer], total: 1, returning_count: 1, new_count: 0,
  trust_note: 'Roster data is user-maintained.',
}

const samplePreview: RosterImportPreviewResponse = {
  competition_code: 'CPL_MEN',
  season: '2025',
  new_teams: [{ team_name: 'New Team A', normalized: 'new team a' }],
  existing_teams_matched: ['Trinbago Knight Riders'],
  new_players: [{ player_name: 'New Player', normalized: 'new player', team_name: 'New Team A', status: 'active' }],
  existing_players_matched: ['Kieron Pollard'],
  duplicates: [],
  returning_players: ['Kieron Pollard'],
  warnings: [],
  blockers: [],
  total_rows: 3,
}

const sampleApplyResult: RosterImportApplyResponse = {
  teams_created: 1,
  players_created: 1,
  players_updated: 1,
  returning_flagged: 1,
  skipped_duplicates: 0,
  warnings: [],
  errors: [],
}

describe('CplRosterPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listTeamsMock.mockResolvedValue(emptyTeams)
    listPlayersMock.mockResolvedValue(emptyPlayers)
  })

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  describe('initial render', () => {
    it('renders the panel title', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('CPL Roster Registry')
    })

    it('shows mode buttons: Teams, Players, Import', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Teams')
      expect(wrapper.text()).toContain('Players')
      expect(wrapper.text()).toContain('Import')
    })

    it('shows user-maintained trust note', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('user-maintained')
    })

    it('loads teams and players on mount', async () => {
      mount(CplRosterPanel)
      await flushPromises()
      expect(listTeamsMock).toHaveBeenCalledOnce()
      expect(listPlayersMock).toHaveBeenCalledOnce()
    })
  })

  // ---------------------------------------------------------------------------
  // Teams mode
  // ---------------------------------------------------------------------------

  describe('teams mode', () => {
    it('shows team names in table', async () => {
      listTeamsMock.mockResolvedValue(teamsWithOne)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Trinbago Knight Riders')
      expect(wrapper.text()).toContain('TKR')
    })

    it('shows empty state when no teams', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('No teams found')
    })

    it('shows Add Team button', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.text()).toContain('Add Team')
    })

    it('calls createCplTeam with correct payload', async () => {
      createTeamMock.mockResolvedValue(sampleTeam)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      // Open add team form
      await wrapper.find('.crp-add-btn').trigger('click')
      await wrapper.find('#at-season').setValue('2025')
      await wrapper.find('#at-name').setValue('Trinbago Knight Riders')
      await wrapper.find('#at-short').setValue('TKR')
      await wrapper.find('.crp-save-btn').trigger('click')
      await flushPromises()
      expect(createTeamMock).toHaveBeenCalledWith(
        expect.objectContaining({
          season: '2025',
          team_name: 'Trinbago Knight Riders',
          short_name: 'TKR',
        })
      )
    })

    it('add team button is disabled without team name', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await wrapper.find('.crp-add-btn').trigger('click')
      await wrapper.find('#at-season').setValue('2025')
      // No team name
      expect(wrapper.find('.crp-save-btn').attributes('disabled')).toBeDefined()
    })
  })

  // ---------------------------------------------------------------------------
  // Players mode
  // ---------------------------------------------------------------------------

  describe('players mode', () => {
    beforeEach(() => {
      listTeamsMock.mockResolvedValue(emptyTeams)
      listPlayersMock.mockResolvedValue(playersWithOne)
    })

    it('switches to players mode', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      const playersBtn = modeBtns.find(b => b.text().includes('Player'))
      await playersBtn?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Kieron Pollard')
    })

    it('shows returning player indicator', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('2024') // prior season
    })

    it('shows returning count badge in header', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('1 returning')
    })

    it('shows player role and status', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('all-rounder')
      expect(wrapper.text()).toContain('active')
    })

    it('calls createCplPlayer with correct payload', async () => {
      createPlayerMock.mockResolvedValue(samplePlayer)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      await wrapper.find('.crp-add-btn').trigger('click')
      await wrapper.find('#ap-season').setValue('2025')
      await wrapper.find('#ap-name').setValue('Kieron Pollard')
      await wrapper.find('.crp-save-btn').trigger('click')
      await flushPromises()
      expect(createPlayerMock).toHaveBeenCalledWith(
        expect.objectContaining({ season: '2025', player_name: 'Kieron Pollard' })
      )
    })

    it('shows inline edit controls when Edit is clicked', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      await wrapper.find('.crp-edit-btn').trigger('click')
      expect(wrapper.find('.crp-inline-edit').exists()).toBe(true)
    })

    it('calls updateCplPlayer when inline edit is saved', async () => {
      updatePlayerMock.mockResolvedValue({ ...samplePlayer, status: 'inactive' })
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Player'))?.trigger('click')
      await flushPromises()
      await wrapper.find('.crp-edit-btn').trigger('click')
      // Save inline edit
      await wrapper.find('.crp-save-btn.crp-save-btn--sm').trigger('click')
      await flushPromises()
      expect(updatePlayerMock).toHaveBeenCalledWith('player-001', expect.objectContaining({ status: 'active' }))
    })
  })

  // ---------------------------------------------------------------------------
  // Import mode
  // ---------------------------------------------------------------------------

  describe('import mode', () => {
    async function switchToImport(wrapper: ReturnType<typeof mount>) {
      const modeBtns = wrapper.findAll('.crp-mode-btn')
      await modeBtns.find(b => b.text().includes('Import'))?.trigger('click')
      await flushPromises()
    }

    it('shows import instructions', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      expect(wrapper.text()).toContain('competition,season,team,player')
    })

    it('preview button is disabled without season', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard,all-rounder,,,,')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      expect(previewBtn?.attributes('disabled')).toBeDefined()
    })

    it('calls rosterImportPreview with parsed rows', async () => {
      previewMock.mockResolvedValue(samplePreview)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue(
        'competition,season,team,player,role,batting_style,bowling_style,status,source_note\nCPL_MEN,2025,TKR,Pollard,all-rounder,right-hand bat,,active,Manual'
      )
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      expect(previewMock).toHaveBeenCalledWith(
        expect.objectContaining({ season: '2025', rows: expect.any(Array) })
      )
    })

    it('shows preview stats after preview', async () => {
      previewMock.mockResolvedValue(samplePreview)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('New Teams')
      expect(wrapper.text()).toContain('New Players')
      expect(wrapper.text()).toContain('Returning Players')
    })

    it('shows returning players detected in preview', async () => {
      previewMock.mockResolvedValue(samplePreview)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Kieron Pollard')
    })

    it('shows blockers and disables apply when blockers present', async () => {
      previewMock.mockResolvedValue({ ...samplePreview, blockers: ['Duplicate player name conflict'] })
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Blockers')
      expect(wrapper.text()).toContain('Duplicate player name conflict')
      const applyBtn = wrapper.findAll('button').find(b => b.text().includes('Apply'))
      expect(applyBtn?.attributes('disabled')).toBeDefined()
    })

    it('calls rosterImportApply with confirmed=true', async () => {
      previewMock.mockResolvedValue(samplePreview)
      applyMock.mockResolvedValue(sampleApplyResult)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      const applyBtn = wrapper.findAll('button').find(b => b.text().includes('Apply'))
      await applyBtn?.trigger('click')
      await flushPromises()
      expect(applyMock).toHaveBeenCalledWith(
        expect.objectContaining({ confirmed: true, season: '2025' })
      )
    })

    it('shows apply result summary after apply', async () => {
      previewMock.mockResolvedValue(samplePreview)
      applyMock.mockResolvedValue(sampleApplyResult)
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      await switchToImport(wrapper)
      await wrapper.find('#imp-season').setValue('2025')
      await wrapper.find('#imp-raw').setValue('CPL_MEN,2025,TKR,Pollard')
      const previewBtn = wrapper.findAll('button').find(b => b.text().includes('Preview'))
      await previewBtn?.trigger('click')
      await flushPromises()
      const applyBtn = wrapper.findAll('button').find(b => b.text().includes('Apply'))
      await applyBtn?.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Import Applied')
      expect(wrapper.text()).toContain('Teams created')
      expect(wrapper.text()).toContain('Players created')
      expect(wrapper.text()).toContain('Returning flagged')
    })
  })

  // ---------------------------------------------------------------------------
  // Trust note
  // ---------------------------------------------------------------------------

  describe('trust note', () => {
    it('trust note is always visible regardless of mode', async () => {
      const wrapper = mount(CplRosterPanel)
      await flushPromises()
      expect(wrapper.find('.crp-trust-note').exists()).toBe(true)
      expect(wrapper.find('.crp-trust-note').text()).toContain('user-maintained')
    })
  })
})
