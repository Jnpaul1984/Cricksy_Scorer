import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { SchoolTeam, SchoolTeamRosterPlayer } from '@/types/schoolAdmin';
import SchoolMatchSetupView from '@/views/school/SchoolMatchSetupView.vue';

const push = vi.fn();

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

const teams: SchoolTeam[] = ['a', 'b', 'c'].map((suffix) => ({
  id: `team-${suffix}`,
  organization_id: 'school-a',
  name: `Team ${suffix.toUpperCase()}`,
  status: 'active',
  home_ground: null,
  season: null,
  owner_user_id: null,
  coach_user_id: null,
  coach_name: null,
  created_at: '',
  updated_at: '',
}));

function roster(teamId: string): SchoolTeamRosterPlayer[] {
  return Array.from({ length: 12 }, (_, index) => ({
    id: `${teamId}-membership-${index}`,
    organization_id: 'school-a',
    team_id: teamId,
    school_player_membership_id: `${teamId}-school-player-${index}`,
    player_profile_id: `${teamId}-profile-${index}`,
    player_name: `${teamId} Player ${index + 1}`,
    status: index === 11 ? 'inactive' : 'active',
    school_player_status: 'active',
    team_status: 'active',
    operationally_available: index !== 11,
    created_by_user_id: 'owner-a',
    created_at: '',
    updated_at: '',
  }));
}

function context(
  organizationId = ref('school-a'),
  canCreate: boolean | Ref<boolean> = true,
): SchoolContext {
  const writes = computed(() => true);
  return {
    organizationId: computed(() => organizationId.value),
    organization: ref(null),
    membership: ref(null),
    entitlement: ref(null),
    canManageTeams: writes,
    canManageRosterMetadata: writes,
    canManageRosterLifecycle: writes,
    canManageTeamRoster: writes,
    canImport: writes,
    canCreateSchoolMatch: computed(() =>
      typeof canCreate === 'boolean' ? canCreate : canCreate.value,
    ),
  };
}

function mountView(schoolContext = context()) {
  return mount(SchoolMatchSetupView, {
    global: { provide: { [schoolContextKey as symbol]: schoolContext } },
  });
}

async function chooseTeams(wrapper: VueWrapper) {
  await wrapper.get('[data-testid="school-team-a"]').setValue('team-a');
  await wrapper.get('[data-testid="school-team-b"]').setValue('team-b');
  await flushPromises();
}

describe('Phase 7I School match setup', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue(teams);
    vi.mocked(schoolApi.listTeamRoster).mockImplementation(async (_organizationId, teamId) =>
      roster(teamId),
    );
    vi.mocked(schoolApi.createSchoolMatch).mockResolvedValue({
      game_id: 'game-a',
      organization_id: 'school-a',
      team_a_id: 'team-a',
      team_b_id: 'team-b',
      team_a_name: 'Team A',
      team_b_name: 'Team B',
      team_a_player_profile_ids: roster('team-a').slice(0, 11).map((player) => player.player_profile_id),
      team_b_player_profile_ids: roster('team-b').slice(0, 11).map((player) => player.player_profile_id),
    });
  });

  it('loads route-scoped saved Teams and does not auto-select a playing XI', async () => {
    const wrapper = mountView();
    await flushPromises();
    expect(schoolApi.listSchoolTeams).toHaveBeenCalledWith('school-a');

    await chooseTeams(wrapper);

    expect(schoolApi.listTeamRoster).toHaveBeenCalledWith('school-a', 'team-a');
    expect(schoolApi.listTeamRoster).toHaveBeenCalledWith('school-a', 'team-b');
    expect(wrapper.findAll('input[type="checkbox"]:checked')).toHaveLength(0);
    const unavailable = wrapper.findAll('input[type="checkbox"]').filter((input) =>
      input.attributes('disabled') !== undefined,
    );
    expect(unavailable).toHaveLength(2);
    expect(wrapper.get('[data-testid="create-school-match"]').attributes('disabled')).toBeDefined();
  });

  it('loads Teams when asynchronous School context grants match authority', async () => {
    const canCreate = ref(false);
    const wrapper = mountView(context(ref('school-a'), canCreate));
    await flushPromises();
    expect(schoolApi.listSchoolTeams).not.toHaveBeenCalled();

    canCreate.value = true;
    await flushPromises();

    expect(schoolApi.listSchoolTeams).toHaveBeenCalledWith('school-a');
    expect(wrapper.find('[data-testid="school-team-a"]').exists()).toBe(true);
  });

  it('submits two explicit XIs and opens the existing scoring route', async () => {
    const wrapper = mountView();
    await flushPromises();
    await chooseTeams(wrapper);

    const sideA = wrapper.get('ul[aria-label="Team A roster"]');
    const sideB = wrapper.get('ul[aria-label="Team B roster"]');
    for (const checkbox of sideA.findAll('input[type="checkbox"]').slice(0, 11)) {
      await checkbox.trigger('change');
    }
    for (const checkbox of sideB.findAll('input[type="checkbox"]').slice(0, 11)) {
      await checkbox.trigger('change');
    }
    await wrapper.get('#captain-a').setValue('team-a-membership-0');
    await wrapper.get('#keeper-a').setValue('team-a-membership-1');
    await wrapper.get('#captain-b').setValue('team-b-membership-0');
    await wrapper.get('#keeper-b').setValue('team-b-membership-1');
    await wrapper.get('[data-testid="create-school-match"]').trigger('submit');
    await flushPromises();

    expect(schoolApi.createSchoolMatch).toHaveBeenCalledWith(
      'school-a',
      expect.objectContaining({
        team_a: {
          team_id: 'team-a',
          playing_xi_membership_ids: roster('team-a').slice(0, 11).map((player) => player.id),
          captain_membership_id: 'team-a-membership-0',
          wicketkeeper_membership_id: 'team-a-membership-1',
        },
        team_b: {
          team_id: 'team-b',
          playing_xi_membership_ids: roster('team-b').slice(0, 11).map((player) => player.id),
          captain_membership_id: 'team-b-membership-0',
          wicketkeeper_membership_id: 'team-b-membership-1',
        },
      }),
    );
    expect(push).toHaveBeenCalledWith({ name: 'GameScoringView', params: { gameId: 'game-a' } });
  });

  it('clears XI and role selections when a saved Team changes', async () => {
    const wrapper = mountView();
    await flushPromises();
    await chooseTeams(wrapper);
    const first = wrapper.get('ul[aria-label="Team A roster"] input[type="checkbox"]');
    await first.trigger('change');
    expect(wrapper.text()).toContain('Selected 1/11');

    await wrapper.get('[data-testid="school-team-a"]').setValue('team-c');
    await flushPromises();

    expect(wrapper.text()).not.toContain('Selected 1/11');
    expect(wrapper.get('#captain-a').element).toHaveProperty('value', '');
    expect(wrapper.get('#keeper-a').element).toHaveProperty('value', '');
  });

  it('clears all match state when the route organization changes', async () => {
    const organizationId = ref('school-a');
    const wrapper = mountView(context(organizationId));
    await flushPromises();
    await chooseTeams(wrapper);

    organizationId.value = 'school-b';
    await flushPromises();

    expect(schoolApi.listSchoolTeams).toHaveBeenLastCalledWith('school-b');
    expect(wrapper.get('[data-testid="school-team-a"]').element).toHaveProperty('value', '');
    expect(wrapper.get('[data-testid="school-team-b"]').element).toHaveProperty('value', '');
  });

  it('does not expose or call match setup for a viewer', async () => {
    const wrapper = mountView(context(ref('school-a'), false));
    await flushPromises();
    expect(wrapper.text()).toContain('does not permit match setup');
    expect(wrapper.find('form').exists()).toBe(false);
    expect(schoolApi.listSchoolTeams).not.toHaveBeenCalled();
    expect(schoolApi.createSchoolMatch).not.toHaveBeenCalled();
  });
});
