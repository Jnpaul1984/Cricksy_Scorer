import { flushPromises, mount } from '@vue/test-utils';
import { computed, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { organizationBasePath, organizationTerminology } from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as api from '@/services/schoolAdminApi';
import PracticeMatchView from '@/views/school/PracticeMatchView.vue';

const { routeQuery, replace } = vi.hoisted(() => ({ routeQuery: { value: {} as Record<string, string> }, replace: vi.fn() }));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery.value }),
  useRouter: () => ({ replace }),
}));
vi.mock('@/services/schoolAdminApi');

const organizationIdRef = ref('org-1');
const context: SchoolContext = {
  organizationId: computed(() => organizationIdRef.value), organizationType: computed(() => 'school'),
  organizationBasePath: computed(() => organizationBasePath('school')),
  terminology: computed(() => organizationTerminology('school')),
  organization: ref(null), membership: ref(null), entitlement: ref(null),
  canManageTeams: computed(() => true), canManageRosterMetadata: computed(() => true),
  canManageRosterLifecycle: computed(() => true), canManageTeamRoster: computed(() => true),
  canImport: computed(() => true), canCreateSchoolMatch: computed(() => true),
  canViewStatistics: computed(() => true), canViewFixturesResults: computed(() => true),
  canViewCompetitions: computed(() => true), canManageCompetitions: computed(() => true),
  canDeleteCompetitions: computed(() => true), canLinkFixtures: computed(() => true),
  canPublishScorecards: computed(() => true), canViewEvents: computed(() => true),
  canManageEvents: computed(() => true), canViewAnnouncements: computed(() => true),
  canManageAnnouncements: computed(() => true), canManageCommunity: computed(() => true),
};
const contextForOrganization = (organizationId: ReturnType<typeof ref<string>>): SchoolContext => ({
  ...context,
  organizationId: computed(() => organizationId.value),
});
const roster = (team: string) => [0, 1].map((index) => ({
  id: `${team}-member-${index}`, player_profile_id: `${team}-player-${index}`,
  player_name: `${team} ${index}`, operationally_available: true,
}));
const state = (revision = 2, status = 'in_progress', inning = 1, first = 'team_a' as const, bowler: string | null = 'b-player-0') => ({ game_id: 'practice-1', organization_id: 'org-1', match_purpose: 'practice' as const, publication_state: 'private' as const, status, revision, practice_start_context: { version: 1 as const, first_batting_side: first }, frozen_sides: { team_a: [{ id: 'a-player-0', label: 'A 0' }, { id: 'a-player-1', label: 'A 1' }], team_b: [{ id: 'b-player-0', label: 'B 0' }, { id: 'b-player-1', label: 'B 1' }] }, snapshot: { current_inning: inning, total_runs: 0, total_wickets: 0, target: inning === 2 ? 1 : undefined, current_striker_id: inning === 1 ? 'a-player-0' : 'b-player-0', current_non_striker_id: inning === 1 ? 'a-player-1' : 'b-player-1', current_bowler_id: bowler } });

describe('PracticeMatchView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    organizationIdRef.value = 'org-1';
    routeQuery.value = {};
    vi.mocked(api.listSchoolTeams).mockResolvedValue([{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }] as any);
    vi.mocked(api.listTeamRoster).mockImplementation(async (_org, team) => roster(team) as any);
    vi.mocked(api.createPracticeMatch).mockResolvedValue({ game_id: 'practice-1' });
    vi.mocked(api.startPracticeMatch).mockResolvedValue({ game_id: 'practice-1' });
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(1));
    vi.mocked(api.startPracticeInnings).mockResolvedValue(state());
  });
  it('creates through private API and refetches after a stale scoring revision', async () => {
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    await wrapper.get('[data-testid="practice-team-a"]').setValue('a');
    await wrapper.get('[data-testid="practice-team-b"]').setValue('b');
    await flushPromises();
    await wrapper.get('[data-testid="create-practice"]').trigger('click');
    await flushPromises();
    expect(api.createPracticeMatch).toHaveBeenCalledWith('org-1', expect.objectContaining({ overs: 2 }));
    expect(api.startPracticeInnings).toHaveBeenCalledWith('org-1', 'practice-1', expect.objectContaining({ expected_revision: 1 }));
    vi.mocked(api.scorePracticeDelivery).mockRejectedValue(Object.assign(new Error('conflict'), { status: 409 }));
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(3));
    await wrapper.get('button').trigger('click');
    await flushPromises();
    expect(api.getPracticeMatch).toHaveBeenLastCalledWith('org-1', 'practice-1');
    expect(wrapper.text()).toContain('latest private state');
  });
  it('renders the familiar private scorer from frozen labels and sends supported runs, extras, and wicket only to private endpoints', async () => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(4, 'in_progress'));
    vi.mocked(api.scorePracticeDelivery).mockResolvedValue(state(5, 'in_progress'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    expect(wrapper.get('[data-testid="practice-familiar-scorer"]').text()).toContain('PRACTICE SCORER');
    expect(wrapper.text()).toContain('A 0');
    expect(wrapper.text()).toContain('B 0');
    for (const runs of [0, 1, 2, 3, 4, 5, 6]) expect(wrapper.get(`[data-testid="score-${runs}"]`).exists()).toBe(true);
    for (const extra of ['wd', 'nb', 'b', 'lb']) expect(wrapper.get(`[data-testid="extra-${extra}"]`).exists()).toBe(true);
    await wrapper.get('[data-testid="extra-wd"]').trigger('click');
    await flushPromises();
    expect(api.scorePracticeDelivery).toHaveBeenLastCalledWith('org-1', 'practice-1', expect.objectContaining({ expected_revision: 4, extra: 'wd', runs_scored: 1 }));
    await wrapper.get('[data-testid="wicket"]').trigger('click');
    await wrapper.get('[data-testid="confirm-wicket"]').trigger('click');
    await flushPromises();
    expect(api.scorePracticeDelivery).toHaveBeenLastCalledWith('org-1', 'practice-1', expect.objectContaining({ is_wicket: true, dismissal_type: 'bowled', dismissed_player_id: 'a-player-0' }));
    expect(api.createPracticeMatch).not.toHaveBeenCalled();
  });
  it('keeps practice private by default and gives an authorized coach an explicit publication toggle', async () => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(4, 'in_progress'));
    vi.mocked(api.updateSchoolMatchPublication).mockResolvedValue({ game_id: 'practice-1', organization_id: 'org-1', publication_state: 'published_live' });
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    expect(wrapper.text()).toContain('Private by default');
    await wrapper.get('[data-testid="publish-practice"]').trigger('click');
    await flushPromises();
    expect(api.updateSchoolMatchPublication).toHaveBeenCalledWith('org-1', 'practice-1', 'published_live');
    expect(wrapper.get('[data-testid="unpublish-practice"]').exists()).toBe(true);
  });
  it('recovers a persisted started practice by starting its first innings once', async () => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(1, 'started', 1, 'team_a', null));
    vi.mocked(api.startPracticeInnings).mockResolvedValue(state(2, 'in_progress'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    await wrapper.get('[data-testid="start-first-innings"]').trigger('click');
    await flushPromises();
    expect(api.createPracticeMatch).not.toHaveBeenCalled();
    expect(api.startPracticeInnings).toHaveBeenCalledTimes(1);
    expect(api.startPracticeInnings).toHaveBeenCalledWith('org-1', 'practice-1', expect.objectContaining({
      expected_revision: 1, striker_id: 'a-player-0', non_striker_id: 'a-player-1', opening_bowler_id: 'b-player-0',
    }));
    expect(wrapper.text()).toContain('Revision 2');
  });
  it('does not repeat an uncertain first-innings mutation before the user reloads', async () => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(1, 'started', 1, 'team_a', null));
    vi.mocked(api.startPracticeInnings).mockRejectedValue(new Error('network unavailable'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    await wrapper.get('[data-testid="start-first-innings"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="start-first-innings"]').trigger('click');
    expect(api.startPracticeInnings).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[data-testid="start-first-innings"]').attributes('disabled')).toBeDefined();
  });
  it('permits another first-innings attempt only after a reload confirms it is still started', async () => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValue(state(1, 'started', 1, 'team_a', null));
    vi.mocked(api.startPracticeInnings).mockRejectedValue(new Error('network unavailable'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    await wrapper.get('[data-testid="start-first-innings"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="reload-practice"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="start-first-innings"]').trigger('click');
    expect(api.startPracticeInnings).toHaveBeenCalledTimes(2);
  });
  it('does not let a deferred reload from an old organization lock the new workflow', async () => {
    const organizationId = ref('org-1'); let resolveOldReload!: (value: any) => void;
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValueOnce(state(1, 'started', 1, 'team_a', null))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOldReload = resolve; }) as any)
      .mockResolvedValueOnce(state(2, 'started', 1, 'team_a', null));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: contextForOrganization(organizationId) } } });
    await flushPromises(); await wrapper.get('[data-testid="reload-practice"]').trigger('click');
    organizationId.value = 'org-2'; await flushPromises(); resolveOldReload(state(1, 'started', 1, 'team_a', null)); await flushPromises();
    expect(wrapper.get('[data-testid="start-first-innings"]').attributes('disabled')).toBeUndefined();
  });
  it.each(['school', 'club'])('continues %s through next over and a winning second-innings chase', async () => {
    vi.mocked(api.scorePracticeDelivery).mockResolvedValueOnce(state(3, 'innings_break'))
      .mockResolvedValueOnce(state(6, 'completed', 2, 'team_a', 'a-player-0'));
    vi.mocked(api.startPracticeInnings).mockResolvedValueOnce(state())
      .mockResolvedValueOnce(state(4, 'in_progress', 2, 'team_a', 'a-player-0'));
    vi.mocked(api.startPracticeOver).mockResolvedValue(state(5, 'in_progress', 2, 'team_a', 'a-player-0'));
    vi.mocked(api.undoLastPracticeDelivery).mockResolvedValue(state(7, 'in_progress', 2, 'team_a', 'a-player-0'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises(); await wrapper.get('[data-testid="practice-team-a"]').setValue('a'); await wrapper.get('[data-testid="practice-team-b"]').setValue('b'); await flushPromises(); await wrapper.get('[data-testid="create-practice"]').trigger('click'); await flushPromises();
    await wrapper.get('[data-testid="score-0"]').trigger('click'); await flushPromises();
    await wrapper.get('[data-testid="start-second-innings"]').trigger('click'); await flushPromises();
    expect(api.startPracticeInnings).toHaveBeenLastCalledWith('org-1', 'practice-1', expect.objectContaining({ striker_id: 'b-player-0', opening_bowler_id: 'a-player-0' }));
    await wrapper.get('[data-testid="score-1"]').trigger('click'); await flushPromises();
    await wrapper.get('[data-testid="undo-ball"]').trigger('click'); await flushPromises();
    expect(api.undoLastPracticeDelivery).toHaveBeenCalled();
  });
  it.each(['team_a', 'team_b'] as const)('reloads %s batting order at an innings break and next-over prompt', async (first) => {
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValueOnce(state(3, 'innings_break', 1, first))
      .mockResolvedValueOnce(state(4, 'in_progress', 2, first, null));
    vi.mocked(api.startPracticeInnings).mockResolvedValue(state(4, 'in_progress', 2, first, null));
    vi.mocked(api.startPracticeOver).mockResolvedValue(state(5, 'in_progress', 2, first, 'a-player-0'));
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: context } } });
    await flushPromises();
    await wrapper.get('[data-testid="start-second-innings"]').trigger('click');
    await flushPromises();
    const secondBattingId = first === 'team_a' ? 'b-player-0' : 'a-player-0';
    const secondBowlingId = first === 'team_a' ? 'a-player-0' : 'b-player-0';
    expect(api.startPracticeInnings).toHaveBeenCalledWith('org-1', 'practice-1', expect.objectContaining({ striker_id: secondBattingId, opening_bowler_id: secondBowlingId }));
    expect(wrapper.get('[data-testid="next-over-bowler"]').text()).toContain(secondBowlingId.slice(0, 1).toUpperCase());
    await wrapper.get('[data-testid="start-next-over"]').trigger('click');
    expect(api.startPracticeOver).toHaveBeenCalledWith('org-1', 'practice-1', expect.objectContaining({ bowler_id: secondBowlingId }));
  });
  it('clears organization-scoped teams and ignores a delayed old roster after switching organizations', async () => {
    const organizationId = ref('org-1');
    let resolveOldRoster!: (value: any) => void;
    vi.mocked(api.listSchoolTeams).mockImplementation(async (organizationId) => ([{ id: `${organizationId}-team`, name: `Team ${organizationId}` }] as any));
    vi.mocked(api.listTeamRoster).mockImplementation((organizationId) => {
      if (organizationId === 'org-1') return new Promise((resolve) => { resolveOldRoster = resolve; }) as any;
      return Promise.resolve(roster('new')) as any;
    });
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: contextForOrganization(organizationId) } } });
    await flushPromises();
    expect(wrapper.text()).toContain('Team org-1');
    await wrapper.get('[data-testid="practice-team-a"]').setValue('org-1-team');
    organizationId.value = 'org-2';
    await flushPromises();
    resolveOldRoster(roster('old'));
    await flushPromises();
    expect(api.listSchoolTeams).toHaveBeenLastCalledWith('org-2');
    expect(wrapper.text()).toContain('Team org-2');
    expect(wrapper.text()).not.toContain('Team org-1');
    expect(wrapper.text()).not.toContain('old 0');
    expect(wrapper.get('[data-testid="create-practice"]').attributes('disabled')).toBeDefined();
  });
  it('keeps the new organization workflow when a prior organization score resolves late', async () => {
    const organizationId = ref('org-1');
    let resolveOldScore!: (value: any) => void;
    routeQuery.value = { gameId: 'practice-1' };
    vi.mocked(api.getPracticeMatch).mockResolvedValueOnce(state(1))
      .mockResolvedValueOnce(state(20));
    vi.mocked(api.scorePracticeDelivery).mockImplementation(() => new Promise((resolve) => { resolveOldScore = resolve; }) as any);
    const wrapper = mount(PracticeMatchView, { global: { provide: { [schoolContextKey as symbol]: contextForOrganization(organizationId) } } });
    await flushPromises();
    await wrapper.get('[data-testid="score-0"]').trigger('click');
    organizationId.value = 'org-2';
    await flushPromises();
    expect(api.getPracticeMatch).toHaveBeenLastCalledWith('org-2', 'practice-1');
    await vi.waitFor(() => expect(wrapper.text()).toContain('Revision 20'));
    resolveOldScore(state(2));
    await flushPromises();
    await vi.waitFor(() => expect(wrapper.text()).toContain('Revision 20'));
    expect(wrapper.text()).not.toMatch(/Private revision 2 ·/);
  });
});
