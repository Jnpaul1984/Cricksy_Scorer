import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import { organizationBasePath, organizationTerminology } from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type {
  FreeOrganizationType,
  OrganizationSelectionCandidate,
  OrganizationSelectionPlan,
  SchoolMembershipRole,
} from '@/types/schoolAdmin';
import OrganizationSelectionPlanView from '@/views/school/OrganizationSelectionPlanView.vue';

const routeState = vi.hoisted(() => ({ params: { teamId: 'team-a', fixtureId: 'fixture-a' } }));
const selectionPush = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({ push: selectionPush }),
}));
vi.mock('@/services/schoolAdminApi');

const team = {
  id: 'team-a',
  organization_id: 'school-a',
  name: 'First XI',
  status: 'active' as const,
  home_ground: null,
  season: null,
  owner_user_id: null,
  coach_user_id: null,
  coach_name: null,
  created_at: '',
  updated_at: '',
};
const fixture = {
  fixture_id: 'fixture-a',
  competition_id: 'cup-a',
  competition_name: 'Shared Cup',
  team_a_id: 'team-a',
  team_a_name: 'First XI',
  team_b_id: 'team-b',
  team_b_name: 'Second XI',
  match_number: 1,
  venue: 'Main Ground',
  scheduled_date: '2099-01-01T10:00:00Z',
  fixture_status: 'scheduled',
  game_id: null,
  game_status: null,
  result: null,
  publication_state: null,
  public_scorecard_available: false,
};
const basePlan: OrganizationSelectionPlan = {
  id: 'plan-a',
  organization_id: 'school-a',
  team_id: 'team-a',
  fixture_id: 'fixture-a',
  status: 'draft',
  revision: 1,
  xi_roster_membership_ids: [],
  reserve_roster_membership_ids: [],
  captain_roster_membership_id: null,
  wicketkeeper_roster_membership_id: null,
  batting_order_roster_membership_ids: [],
  bowling_plan: [],
  latest_publication_version: null,
  created_by_user_id: 'owner-a',
  updated_by_user_id: 'owner-a',
  created_at: '',
  updated_at: '',
};
const candidates: OrganizationSelectionCandidate[] = [
  ['player-a', 'Available Player', 'available'],
  ['player-b', 'Unavailable Player', 'unavailable'],
  ['player-c', 'Maybe Player', 'maybe'],
  ['player-d', 'No Response Player', null],
].map(([id, name, availability]) => ({
  roster_membership_id: id as string,
  player_profile_id: `profile-${id}`,
  player_name: name as string,
  eligible: true,
  availability_state: availability as OrganizationSelectionCandidate['availability_state'],
}));

function context(
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref('school-a'),
  organizationType: Ref<FreeOrganizationType> = ref('school'),
): SchoolContext {
  const editable = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: ref(null),
    membership: ref({
      id: 'membership-a',
      organization_id: organizationId.value,
      user_id: 'actor-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref(null),
    canManageTeams: editable,
    canManageRosterMetadata: editable,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: editable,
    canImport: editable,
    canCreateSchoolMatch: computed(() => role !== 'viewer'),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: editable,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => role !== 'viewer'),
    canPublishScorecards: computed(() => role !== 'viewer'),
    canViewEvents: computed(() => true),
    canManageEvents: editable,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: editable,
    canManageCommunity: editable,
  };
}

function mountView(
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref('school-a'),
  organizationType: Ref<FreeOrganizationType> = ref('school'),
) {
  return mount(OrganizationSelectionPlanView, {
    global: {
      provide: { [schoolContextKey as symbol]: context(role, organizationId, organizationType) },
    },
  });
}

describe('shared organization selection plan workspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    routeState.params.teamId = 'team-a';
    routeState.params.fixtureId = 'fixture-a';
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([team]);
    vi.mocked(schoolApi.listSchoolFixtures).mockResolvedValue([fixture]);
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockResolvedValue(basePlan);
    vi.mocked(schoolApi.getOrganizationSelectionCandidates).mockResolvedValue({
      organization_id: 'school-a',
      team_id: 'team-a',
      fixture_id: 'fixture-a',
      candidates,
    });
    vi.mocked(schoolApi.createOrganizationSelectionPlan).mockResolvedValue(basePlan);
    vi.mocked(schoolApi.listOrganizationSelectionPublications).mockResolvedValue([]);
    vi.mocked(schoolApi.updateOrganizationSelectionPlan).mockImplementation(
      async (_organizationId, _planId, payload) => ({
        ...basePlan,
        ...payload,
        revision: basePlan.revision + 1,
      }),
    );
  });

  it('uses only a selected published version and routes its validated context to match setup', async () => {
    const publication = {
      id: 'publication-a',
      organization_id: 'school-a',
      selection_plan_id: 'plan-a',
      team_id: 'team-a',
      fixture_id: 'fixture-a',
      plan_revision: 2,
      publication_version: 1,
      status: 'published' as const,
      captain_roster_membership_id: 'player-a',
      wicketkeeper_roster_membership_id: 'player-b',
      players: [],
      published_by_user_id: 'owner-a',
      published_at: '2026-09-28T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationSelectionPublications).mockResolvedValue([publication]);
    vi.mocked(schoolApi.prepareOrganizationSelectionHandoff).mockResolvedValue({
      organization_id: 'school-a',
      selection_plan_id: 'plan-a',
      publication_version: 1,
      fixture_id: 'fixture-a',
      fixture_team_a_id: 'team-a',
      fixture_team_b_id: 'team-b',
      selected_side: 'team_a',
      selected_team: {
        team_id: 'team-a',
        playing_xi_membership_ids: Array.from({ length: 11 }, (_, index) => `team-member-${index}`),
        captain_membership_id: 'team-member-0',
        wicketkeeper_membership_id: 'team-member-1',
      },
      planned_batting_order_membership_ids: [],
    });
    const wrapper = mountView('owner');
    await flushPromises();
    const versionButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Version 1'));
    expect(versionButton).toBeDefined();
    await versionButton!.trigger('click');
    await wrapper.get('[data-test="use-selection-in-match-setup"]').trigger('click');
    await flushPromises();

    expect(schoolApi.prepareOrganizationSelectionHandoff).toHaveBeenCalledWith(
      'school-a',
      'plan-a',
      1,
    );
    expect(selectionPush).toHaveBeenCalledWith({
      name: 'school-match-setup',
      params: { organizationId: 'school-a' },
      query: {
        selectionPlanId: 'plan-a',
        publicationVersion: '1',
        fixtureId: 'fixture-a',
      },
    });
  });

  it('distinguishes staff delivery from unresolved XI and reserve recipients', async () => {
    const publication = {
      id: 'publication-a',
      organization_id: 'school-a',
      selection_plan_id: 'plan-a',
      team_id: 'team-a',
      fixture_id: 'fixture-a',
      plan_revision: 2,
      publication_version: 1,
      status: 'published' as const,
      captain_roster_membership_id: 'player-a',
      wicketkeeper_roster_membership_id: 'player-b',
      players: [],
      published_by_user_id: 'owner-a',
      published_at: '2026-09-28T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationSelectionPublications).mockResolvedValue([publication]);
    vi.mocked(schoolApi.notifyOrganizationSelectionPublication).mockResolvedValue({
      source_type: 'selection_publication',
      source_id: 'publication-a',
      source_version: '1',
      selection_plan_id: 'plan-a',
      publication_version: 1,
      safe_user_recipient_count: 2,
      delivered_count: 2,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 13,
      xi_roster_count: 11,
      reserve_roster_count: 2,
      unresolved_xi_count: 11,
      unresolved_reserve_count: 2,
    });
    const wrapper = mountView('owner');
    await flushPromises();
    const versionButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Version 1'));
    await versionButton!.trigger('click');
    await wrapper.get('[data-test="notify-selection"]').trigger('click');
    await flushPromises();

    expect(schoolApi.notifyOrganizationSelectionPublication).toHaveBeenCalledWith(
      'school-a',
      'plan-a',
      1,
    );
    expect(wrapper.text()).toContain('sent to 2 staff Users');
    expect(wrapper.text()).toContain('11 XI');
    expect(wrapper.text()).toContain('2 reserve roster recipients are not directly reachable');
    expect(wrapper.text()).not.toContain('13 players notified');
  });

  it('shows all four advisory states and never selects or mutates Availability automatically', async () => {
    const wrapper = mountView('owner');
    await flushPromises();

    expect(wrapper.text()).toContain('Available Player');
    expect(wrapper.text()).toContain('Unavailable Player');
    expect(wrapper.text()).toContain('Maybe Player');
    expect(wrapper.text()).toContain('No Response Player');
    expect(wrapper.text()).toContain('Planned XI · 0/11');
    expect(schoolApi.updateOrganizationSelectionPlan).not.toHaveBeenCalled();
    expect(schoolApi.recordOrganizationPlayerAvailability).not.toHaveBeenCalled();

    await wrapper.get('[data-test="add-xi-player-b"]').trigger('click');
    await wrapper.get('[data-test="add-xi-player-c"]').trigger('click');
    await wrapper.get('[data-test="add-reserve-player-d"]').trigger('click');
    expect(wrapper.text()).toContain('Planned XI · 2/11');
    await wrapper.get('[data-test="save-selection-plan"]').trigger('click');
    await flushPromises();

    expect(schoolApi.updateOrganizationSelectionPlan).toHaveBeenCalledWith(
      'school-a',
      'plan-a',
      expect.objectContaining({
        expected_revision: 1,
        xi_roster_membership_ids: ['player-b', 'player-c'],
        reserve_roster_membership_ids: ['player-d'],
      }),
    );
    expect(schoolApi.recordOrganizationPlayerAvailability).not.toHaveBeenCalled();
  });

  it('does not show a Team selection trigger to a Coach after Team reassignment', async () => {
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      { ...team, coach_user_id: 'different-coach' },
    ]);
    vi.mocked(schoolApi.listOrganizationSelectionPublications).mockResolvedValue([
      {
        id: 'publication-a',
        organization_id: 'school-a',
        selection_plan_id: 'plan-a',
        team_id: 'team-a',
        fixture_id: 'fixture-a',
        plan_revision: 2,
        publication_version: 1,
        status: 'published',
        captain_roster_membership_id: null,
        wicketkeeper_roster_membership_id: null,
        players: [],
        published_by_user_id: 'owner-a',
        published_at: '2026-09-28T00:00:00Z',
      },
    ]);
    const wrapper = mountView('coach');
    await flushPromises();
    const versionButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Version 1'));
    await versionButton!.trigger('click');
    expect(wrapper.find('[data-test="notify-selection"]').exists()).toBe(false);
  });

  it.each(['owner', 'admin', 'coach'] as const)('lets %s explicitly create a missing draft', async (role) => {
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockRejectedValueOnce(
      Object.assign(new Error('missing'), { status: 404 }),
    );
    const wrapper = mountView(role);
    await flushPromises();

    expect(schoolApi.createOrganizationSelectionPlan).not.toHaveBeenCalled();
    await wrapper.get('[data-test="create-selection-plan"]').trigger('click');
    await flushPromises();
    expect(schoolApi.createOrganizationSelectionPlan).toHaveBeenCalledWith(
      'school-a',
      'team-a',
      'fixture-a',
    );
  });

  it.each(['scorer', 'viewer'] as const)('keeps %s read-only and never creates a missing plan', async (role) => {
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockRejectedValue(
      Object.assign(new Error('missing'), { status: 404 }),
    );
    const wrapper = mountView(role);
    await flushPromises();

    expect(wrapper.text()).toContain('read-only workspace');
    expect(wrapper.find('[data-test="create-selection-plan"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="save-selection-plan"]').exists()).toBe(false);
    expect(schoolApi.createOrganizationSelectionPlan).not.toHaveBeenCalled();
  });

  it('clears captain and wicketkeeper when their XI player is removed', async () => {
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockResolvedValue({
      ...basePlan,
      xi_roster_membership_ids: ['player-a'],
      captain_roster_membership_id: 'player-a',
      wicketkeeper_roster_membership_id: 'player-a',
    });
    const wrapper = mountView('coach');
    await flushPromises();
    const remove = wrapper.findAll('button').find((button) => button.text() === 'Remove');
    expect(remove).toBeDefined();
    await remove!.trigger('click');
    await wrapper.get('[data-test="save-selection-plan"]').trigger('click');
    await flushPromises();

    expect(schoolApi.updateOrganizationSelectionPlan).toHaveBeenCalledWith(
      'school-a',
      'plan-a',
      expect.objectContaining({
        xi_roster_membership_ids: [],
        captain_roster_membership_id: null,
        wicketkeeper_roster_membership_id: null,
      }),
    );
  });

  it('surfaces a revision conflict and reloads server truth without replaying local edits', async () => {
    const latest = { ...basePlan, revision: 2, xi_roster_membership_ids: ['player-a'] };
    vi.mocked(schoolApi.getOrganizationSelectionPlan)
      .mockResolvedValueOnce(basePlan)
      .mockResolvedValueOnce(latest);
    vi.mocked(schoolApi.updateOrganizationSelectionPlan).mockRejectedValue(
      Object.assign(new Error('stale revision'), { status: 409 }),
    );
    const wrapper = mountView('owner');
    await flushPromises();
    await wrapper.get('[data-test="add-xi-player-b"]').trigger('click');
    await wrapper.get('[data-test="save-selection-plan"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('latest server version was loaded');
    expect(wrapper.text()).toContain('Revision 2');
    expect(wrapper.text()).toContain('Planned XI · 1/11');
    expect(schoolApi.updateOrganizationSelectionPlan).toHaveBeenCalledTimes(1);
  });

  it('suppresses stale results and clears draft/filter state across organization changes', async () => {
    let resolveOld: (value: OrganizationSelectionPlan) => void = () => undefined;
    const oldRequest = new Promise<OrganizationSelectionPlan>((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockImplementation((organizationId) => {
      if (organizationId === 'school-a') return oldRequest;
      return Promise.resolve({ ...basePlan, organization_id: 'club-b', revision: 3 });
    });
    vi.mocked(schoolApi.listSchoolTeams).mockImplementation((organizationId) =>
      Promise.resolve([{ ...team, organization_id: organizationId }]),
    );
    vi.mocked(schoolApi.getOrganizationSelectionCandidates).mockImplementation((organizationId) =>
      Promise.resolve({
        organization_id: organizationId,
        team_id: 'team-a',
        fixture_id: 'fixture-a',
        candidates: [{ ...candidates[3], player_name: 'Current Club Player' }],
      }),
    );
    const organizationId = ref('school-a');
    const wrapper = mountView('owner', organizationId);
    await wrapper.vm.$nextTick();
    organizationId.value = 'club-b';
    await flushPromises();
    await wrapper.get('[data-test="selection-availability-filter"]').setValue('no_response');
    expect(wrapper.text()).toContain('Current Club Player');

    resolveOld({ ...basePlan, xi_roster_membership_ids: ['player-a'] });
    await flushPromises();
    expect(wrapper.text()).not.toContain('Available Player');
    expect(wrapper.text()).toContain('Revision 3');
  });

  it('suppresses a late selection notification across a Club to School switch', async () => {
    const publication = {
      id: 'publication-a',
      organization_id: 'club-a',
      selection_plan_id: 'plan-a',
      team_id: 'team-a',
      fixture_id: 'fixture-a',
      plan_revision: 2,
      publication_version: 1,
      status: 'published' as const,
      captain_roster_membership_id: 'player-a',
      wicketkeeper_roster_membership_id: 'player-b',
      players: [],
      published_by_user_id: 'owner-a',
      published_at: '2026-09-28T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationSelectionPublications).mockResolvedValue([publication]);
    let resolveNotification: (
      value: Awaited<ReturnType<typeof schoolApi.notifyOrganizationSelectionPublication>>,
    ) => void = () => undefined;
    vi.mocked(schoolApi.notifyOrganizationSelectionPublication).mockReturnValue(
      new Promise((resolve) => {
        resolveNotification = resolve;
      }),
    );
    const organizationId = ref('club-a');
    const organizationType = ref<FreeOrganizationType>('club');
    const wrapper = mountView('owner', organizationId, organizationType);
    await flushPromises();
    const versionButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Version 1'));
    await versionButton!.trigger('click');
    await wrapper.get('[data-test="notify-selection"]').trigger('click');
    organizationId.value = 'school-b';
    organizationType.value = 'school';
    await flushPromises();
    resolveNotification({
      source_type: 'selection_publication',
      source_id: publication.id,
      source_version: '1',
      selection_plan_id: publication.selection_plan_id,
      publication_version: 1,
      safe_user_recipient_count: 1,
      delivered_count: 1,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 13,
      xi_roster_count: 11,
      reserve_roster_count: 2,
      unresolved_xi_count: 11,
      unresolved_reserve_count: 2,
    });
    await flushPromises();

    expect(wrapper.text()).not.toContain('Selection notification sent to 1 staff User');
  });

  it('sanitizes 5xx details and presents controlled validation failures', async () => {
    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockRejectedValueOnce(
      Object.assign(new Error('SQL secret table fk_internal'), { status: 500 }),
    );
    const serverFailure = mountView('owner');
    await flushPromises();
    expect(serverFailure.text()).toContain('The service encountered a problem');
    expect(serverFailure.text()).not.toContain('fk_internal');

    vi.mocked(schoolApi.getOrganizationSelectionPlan).mockResolvedValueOnce(basePlan);
    vi.mocked(schoolApi.updateOrganizationSelectionPlan).mockRejectedValueOnce(
      Object.assign(new Error('Captain must be a member of the planned XI'), { status: 422 }),
    );
    const validationFailure = mountView('owner');
    await flushPromises();
    await validationFailure.get('[data-test="save-selection-plan"]').trigger('click');
    await flushPromises();
    expect(validationFailure.text()).toContain('Captain must be a member');
  });

  it('edits structured plans, publishes privately, and explicitly begins a new draft', async () => {
    const fullPlan = {
      ...basePlan,
      revision: 2,
      xi_roster_membership_ids: Array.from({ length: 11 }, (_, index) => `player-${index}`),
      captain_roster_membership_id: 'player-0',
      wicketkeeper_roster_membership_id: 'player-1',
    };
    const publication = {
      id: 'publication-a',
      organization_id: 'school-a',
      selection_plan_id: 'plan-a',
      team_id: 'team-a',
      fixture_id: 'fixture-a',
      plan_revision: 2,
      publication_version: 1,
      status: 'published' as const,
      captain_roster_membership_id: 'player-0',
      wicketkeeper_roster_membership_id: 'player-1',
      players: [],
      published_by_user_id: 'owner-a',
      published_at: '2026-09-28T00:00:00Z',
    };
    vi.mocked(schoolApi.getOrganizationSelectionPlan)
      .mockResolvedValueOnce(fullPlan)
      .mockResolvedValueOnce({ ...fullPlan, status: 'published', latest_publication_version: 1 });
    vi.mocked(schoolApi.publishOrganizationSelectionPlan).mockResolvedValue(publication);
    vi.mocked(schoolApi.beginOrganizationSelectionDraft).mockResolvedValue({
      ...fullPlan,
      revision: 3,
      status: 'draft',
      latest_publication_version: 1,
    });
    const wrapper = mountView('owner');
    await flushPromises();
    await wrapper.get('[data-test="publish-selection-plan"]').trigger('click');
    await flushPromises();
    expect(schoolApi.publishOrganizationSelectionPlan).toHaveBeenCalledWith('school-a', 'plan-a', 2);
    expect(wrapper.text()).toContain('Published selection history');
    expect(wrapper.text()).toContain('Version 1');
    await wrapper.get('[data-test="begin-selection-draft"]').trigger('click');
    await flushPromises();
    expect(schoolApi.beginOrganizationSelectionDraft).toHaveBeenCalledWith('school-a', 'plan-a', 2);
    expect(wrapper.text()).toContain('New draft started at revision 3');
  });
});
