import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import { organizationBasePath, organizationTerminology } from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import SchoolAdminShellView from '@/views/school/SchoolAdminShellView.vue';
import SchoolCompetitionsView from '@/views/school/SchoolCompetitionsView.vue';
import SchoolCreateView from '@/views/school/SchoolCreateView.vue';
import SchoolFixturesResultsView from '@/views/school/SchoolFixturesResultsView.vue';
import SchoolImportView from '@/views/school/SchoolImportView.vue';
import SchoolMatchSetupView from '@/views/school/SchoolMatchSetupView.vue';
import SchoolStatisticsView from '@/views/school/SchoolStatisticsView.vue';
import SchoolTeamRosterView from '@/views/school/SchoolTeamRosterView.vue';
import SchoolTeamsView from '@/views/school/SchoolTeamsView.vue';

const mocks = vi.hoisted(() => ({
  route: {
    params: { organizationId: 'club-a', teamId: 'team-a' },
    meta: { organizationType: 'club' },
    fullPath: '/clubs/club-a',
  },
  push: vi.fn(),
  setRoute: null as null | ((organizationType: 'school' | 'club', organizationId: string) => void),
}));

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', async () => {
  const { reactive } = await import('vue');
  const route = reactive(mocks.route);
  mocks.setRoute = (organizationType, organizationId) => {
    route.params.organizationId = organizationId;
    route.meta.organizationType = organizationType;
    route.fullPath = `/${organizationType === 'club' ? 'clubs' : 'schools'}/${organizationId}`;
  };
  return {
    useRoute: () => route,
    useRouter: () => ({ push: mocks.push }),
    RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
    RouterView: { template: '<div data-test="router-view" />' },
  };
});

const club = {
  id: 'club-a',
  name: 'Central Cricket Club',
  organization_type: 'club' as const,
  status: 'active' as const,
  membership_role: 'owner' as const,
  created_by_user_id: 'user-a',
  created_at: '',
  updated_at: '',
};

const membership = {
  id: 'member-a',
  organization_id: 'club-a',
  user_id: 'user-a',
  role: 'owner' as const,
  status: 'active' as const,
  created_by_user_id: null,
  created_at: '',
  updated_at: '',
};

const entitlement = {
  id: 'ent-a',
  organization_id: 'club-a',
  plan_key: 'club_free' as const,
  status: 'active' as const,
  source: 'system' as const,
  effective_from: '',
  effective_until: null,
  capabilities: [
    'school_master_roster',
    'school_persistent_teams',
    'school_team_rosters',
    'school_match_playing_xi',
    'school_basic_statistics',
    'school_fixtures_results',
    'school_live_scorecards',
    'school_competitions',
    'organization_events',
  ],
  excluded_capabilities: ['advanced_ai'],
  created_at: '',
  updated_at: '',
};

function clubContext(): SchoolContext {
  const allowed = computed(() => true);
  return {
    organizationId: computed(() => club.id),
    organizationType: computed(() => 'club'),
    organizationBasePath: computed(() => organizationBasePath('club')),
    terminology: computed(() => organizationTerminology('club')),
    organization: ref(club),
    membership: ref(membership),
    entitlement: ref(entitlement),
    canManageTeams: allowed,
    canManageRosterMetadata: allowed,
    canManageRosterLifecycle: allowed,
    canManageTeamRoster: allowed,
    canImport: allowed,
    canCreateSchoolMatch: allowed,
    canViewStatistics: allowed,
    canViewFixturesResults: allowed,
    canViewCompetitions: allowed,
    canManageCompetitions: allowed,
    canDeleteCompetitions: allowed,
    canLinkFixtures: allowed,
    canPublishScorecards: allowed,
    canViewEvents: allowed,
    canManageEvents: allowed,
  };
}

function mountClubView(component: object) {
  return mount(component, {
    global: {
      provide: { [schoolContextKey as symbol]: clubContext() },
      stubs: { RouterLink: true },
    },
  });
}

describe('Club Free shared organization views', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.route.params.organizationId = 'club-a';
    mocks.route.meta.organizationType = 'club';
    mocks.route.fullPath = '/clubs/club-a';
    vi.mocked(schoolApi.getSchool).mockResolvedValue(club);
    vi.mocked(schoolApi.getMySchoolMembership).mockResolvedValue(membership);
    vi.mocked(schoolApi.getSchoolEntitlement).mockResolvedValue(entitlement);
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([]);
    vi.mocked(schoolApi.listTeamRoster).mockResolvedValue([]);
    vi.mocked(schoolApi.getSchoolTeam).mockResolvedValue({
      id: 'team-a',
      organization_id: club.id,
      name: 'Club First XI',
      status: 'active',
      home_ground: null,
      season: null,
      owner_user_id: 'club-owner',
      coach_user_id: null,
      coach_name: null,
      created_at: '',
      updated_at: '',
    });
    vi.mocked(schoolApi.listSchoolPlayerStatistics).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolTeamStatistics).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolFixtures).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolResults).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue([]);
  });

  it('uses one frozen capability vocabulary with Club-specific terminology and routes', () => {
    expect(organizationTerminology('club').freePlanLabel).toBe('Club Free');
    expect(organizationTerminology('school').freePlanLabel).toBe('School Free');
    expect(organizationBasePath('club')).toBe('/clubs');
    expect(organizationBasePath('school')).toBe('/schools');
  });

  it('creates a Club through the shared form and routes to its Club workspace', async () => {
    vi.mocked(schoolApi.createOrganization).mockResolvedValue(club);
    const wrapper = mount(SchoolCreateView);
    await wrapper.get('input').setValue('Central Cricket Club');
    await wrapper.get('form').trigger('submit');
    await flushPromises();

    expect(wrapper.text()).toContain('Create your Club');
    expect(schoolApi.createOrganization).toHaveBeenCalledWith({
      name: 'Central Cricket Club',
      organization_type: 'club',
    });
    expect(mocks.push).toHaveBeenCalledWith('/clubs/club-a');
  });

  it('renders a verified Club workspace and Club admin links', async () => {
    const wrapper = mount(SchoolAdminShellView);
    await flushPromises();

    expect(wrapper.text()).toContain('Central Cricket Club');
    expect(wrapper.text()).toContain('Club Administration');
    expect(wrapper.get('nav').attributes('aria-label')).toBe('Club administration');
    expect(wrapper.html()).toContain('/clubs/club-a/matches/new');
    expect(wrapper.html()).toContain('/clubs/club-a/events');
    expect(wrapper.text()).toContain('Calendar');
    expect(wrapper.text()).not.toContain('School Administration');
  });

  it('renders every shared cricket workspace with Club terminology and tenant scope', async () => {
    const cases: Array<[object, string]> = [
      [SchoolTeamsView, 'Teams'],
      [SchoolTeamRosterView, 'Club master roster remains canonical.'],
      [SchoolImportView, 'Upload → Map → Preview → Resolve → Apply → Results'],
      [SchoolMatchSetupView, 'Create a Club match'],
      [SchoolStatisticsView, 'Club Free statistics'],
      [SchoolFixturesResultsView, 'Club match experience'],
      [SchoolCompetitionsView, 'Club competitions'],
    ];

    for (const [component, expectedText] of cases) {
      const wrapper = mountClubView(component);
      await flushPromises();
      expect(wrapper.text()).toContain(expectedText);
      wrapper.unmount();
    }

    expect(schoolApi.listSchoolTeams).toHaveBeenCalledWith(club.id);
    expect(schoolApi.getSchoolTeam).toHaveBeenCalledWith(club.id, 'team-a');
    expect(schoolApi.listSchoolPlayers).toHaveBeenCalledWith(club.id, 'active');
    expect(schoolApi.listSchoolPlayerStatistics).toHaveBeenCalledWith(club.id);
    expect(schoolApi.listSchoolFixtures).toHaveBeenCalledWith(club.id);
    expect(schoolApi.listSchoolCompetitions).toHaveBeenCalledWith(club.id);
  });

  it('fails closed when a Club route resolves a School organization', async () => {
    vi.mocked(schoolApi.getSchool).mockResolvedValue({
      ...club,
      organization_type: 'school',
    });
    const wrapper = mount(SchoolAdminShellView);
    await flushPromises();

    expect(wrapper.text()).toContain('Club not found or you do not have access.');
    expect(wrapper.text()).not.toContain('Central Cricket Club');
  });

  it('clears stale context while switching Club to School and back to Club', async () => {
    const school = {
      ...club,
      id: 'school-a',
      name: 'Central School',
      organization_type: 'school' as const,
    };
    vi.mocked(schoolApi.getSchool).mockImplementation(async (organizationId) =>
      organizationId === 'school-a' ? school : club,
    );
    vi.mocked(schoolApi.getMySchoolMembership).mockImplementation(async (organizationId) => ({
      ...membership,
      organization_id: organizationId,
    }));
    vi.mocked(schoolApi.getSchoolEntitlement).mockImplementation(async (organizationId) => ({
      ...entitlement,
      organization_id: organizationId,
      plan_key: organizationId === 'school-a' ? 'school_free' : 'club_free',
    }));
    const wrapper = mount(SchoolAdminShellView);
    await flushPromises();
    expect(wrapper.text()).toContain('Central Cricket Club');

    mocks.setRoute?.('school', 'school-a');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).not.toContain('Central Cricket Club');
    await flushPromises();
    expect(wrapper.text()).toContain('Central School');
    expect(wrapper.text()).toContain('School Administration');

    mocks.setRoute?.('club', 'club-a');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).not.toContain('Central School');
    await flushPromises();
    expect(wrapper.text()).toContain('Central Cricket Club');
    expect(wrapper.text()).toContain('Club Administration');
  });
});
