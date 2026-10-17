import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { PlayerImportPreview, SchoolMembershipRole } from '@/types/schoolAdmin';
import SchoolAdminShellView from '@/views/school/SchoolAdminShellView.vue';
import SchoolImportView from '@/views/school/SchoolImportView.vue';
import SchoolOverviewView from '@/views/school/SchoolOverviewView.vue';
import SchoolPlayersView from '@/views/school/SchoolPlayersView.vue';
import SchoolTeamRosterView from '@/views/school/SchoolTeamRosterView.vue';
import SchoolTeamsView from '@/views/school/SchoolTeamsView.vue';

vi.mock('@/services/schoolAdminApi');
const { routeState } = vi.hoisted(() => ({
  routeState: {
    value: {
      params: { organizationId: 'school-a', teamId: 'team-a' },
      meta: { organizationType: 'school' },
      fullPath: '/schools/school-a',
      name: 'school-overview',
      query: {} as Record<string, string>,
    },
  },
}));
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRoute: () => routeState.value,
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
  RouterView: { template: '<div data-test="router-view" />' },
}));

const school = {
  id: 'school-a',
  name: 'Central School',
  organization_type: 'school' as const,
  status: 'active' as const,
  membership_role: 'owner' as const,
  created_by_user_id: 'user-a',
  created_at: '',
  updated_at: '',
};
const entitlement = {
  id: 'ent-a',
  organization_id: 'school-a',
  plan_key: 'school_free' as const,
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
    'organization_availability',
  ],
  excluded_capabilities: ['advanced_ai'],
  created_at: '',
  updated_at: '',
};

function context(role: SchoolMembershipRole, organizationId = ref('school-a')): SchoolContext {
  const writes = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => 'school'),
    organizationBasePath: computed(() => organizationBasePath('school')),
    terminology: computed(() => organizationTerminology('school')),
    organization: ref({ ...school, id: organizationId.value, membership_role: role }),
    membership: ref({
      id: 'member-a',
      organization_id: organizationId.value,
      user_id: 'user-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref(entitlement),
    canManageTeams: writes,
    canManageRosterMetadata: writes,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: writes,
    canImport: writes,
    canCreateSchoolMatch: computed(() => ['owner', 'admin', 'coach', 'scorer'].includes(role)),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: writes,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => ['owner', 'admin', 'coach', 'scorer'].includes(role)),
    canPublishScorecards: computed(() => ['owner', 'admin', 'coach', 'scorer'].includes(role)),
    canViewEvents: computed(() => true),
    canManageEvents: writes,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: writes,
    canManageCommunity: writes,
  };
}

function mountWithContext(
  component: object,
  role: SchoolMembershipRole,
  organizationId = ref('school-a'),
) {
  return mount(component, {
    global: { provide: { [schoolContextKey as symbol]: context(role, organizationId) } },
  });
}

const preview: PlayerImportPreview = {
  import_id: 'import-a',
  file_type: 'csv',
  original_filename: 'players.csv',
  content_sha256: 'hash',
  row_count: 1,
  column_mapping: { player_name: 'player_name' },
  expires_at: '2099-01-01T00:00:00Z',
  rows: [
    {
      source_row_number: 2,
      values: {
        player_name: 'Alex Lee',
        student_identifier: null,
        year_group: '8',
        team_name: 'First XI',
      },
      classification: 'ambiguous_needs_review',
      validation_errors: [],
      warnings: ['Names are never treated as proof of identity'],
      ambiguity_reason: 'same-name candidates require review',
      resolution_required: true,
      candidate_memberships: [
        {
          school_player_membership_id: 'member-player-a',
          player_name: 'Alex Lee',
          status: 'active',
        },
      ],
      resolved_school_player_membership_id: null,
      team_candidates: [{ team_id: 'team-a', team_name: 'First XI' }],
      resolved_team_id: 'team-a',
    },
  ],
};

describe('Phase 7H School administration views', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    routeState.value = {
      params: { organizationId: 'school-a', teamId: 'team-a' },
      meta: { organizationType: 'school' },
      fullPath: '/schools/school-a',
      name: 'school-overview',
      query: {},
    };
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([]);
    vi.mocked(schoolApi.listTeamRoster).mockResolvedValue([]);
    vi.mocked(schoolApi.getSchoolTeam).mockResolvedValue({
      id: 'team-a',
      organization_id: 'school-a',
      name: 'First XI',
      status: 'active',
      home_ground: null,
      season: null,
      owner_user_id: null,
      coach_user_id: null,
      coach_name: null,
      created_at: '',
      updated_at: '',
    });
    vi.mocked(schoolApi.getSchool).mockResolvedValue(school);
    vi.mocked(schoolApi.getMySchoolMembership).mockResolvedValue({
      id: 'member-a',
      organization_id: 'school-a',
      user_id: 'user-a',
      role: 'owner',
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    });
    vi.mocked(schoolApi.getSchoolEntitlement).mockResolvedValue(entitlement);
  });

  it('opens the route-scoped School shell from organization, membership, and entitlement contracts', async () => {
    const wrapper = mount(SchoolAdminShellView, { global: { stubs: { RouterView: true } } });
    await flushPromises();
    expect(wrapper.text()).toContain('Central School');
    expect(schoolApi.getSchool).toHaveBeenCalledWith('school-a');
    expect(schoolApi.getMySchoolMembership).toHaveBeenCalledWith('school-a');
    expect(schoolApi.getSchoolEntitlement).toHaveBeenCalledWith('school-a');
    expect(wrapper.text()).toContain('Statistics');
    expect(wrapper.text()).toContain('Fixtures / Results');
    expect(wrapper.text()).toContain('Competitions');
    expect(wrapper.text()).toContain('Calendar');
  });

  it('uses a full-width scorer shell only for an active practice game while retaining the verified route context', async () => {
    routeState.value = {
      ...routeState.value,
      fullPath: '/schools/school-a/practice?gameId=practice-1',
      name: 'school-practice',
      query: { gameId: 'practice-1' },
    };
    const wrapper = mount(SchoolAdminShellView, { global: { stubs: { RouterView: true } } });
    await flushPromises();
    expect(wrapper.get('[data-testid="active-practice-scorer-shell"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="school-admin-shell"]').exists()).toBe(false);
    expect(wrapper.find('.school-nav').exists()).toBe(false);
    expect(wrapper.get('[data-testid="practice-scorer-return"]').attributes('href')).toContain('/schools/school-a/practice');
    expect(wrapper.text()).toContain('Private practice');
    expect(schoolApi.getSchool).toHaveBeenCalledWith('school-a');
    expect(schoolApi.getMySchoolMembership).toHaveBeenCalledWith('school-a');
    expect(schoolApi.getSchoolEntitlement).toHaveBeenCalledWith('school-a');
  });

  it('keeps practice setup in the normal administration shell when no game is active', async () => {
    routeState.value = {
      ...routeState.value,
      fullPath: '/schools/school-a/practice',
      name: 'school-practice',
      query: {},
    };
    const wrapper = mount(SchoolAdminShellView, { global: { stubs: { RouterView: true } } });
    await flushPromises();
    expect(wrapper.get('[data-testid="school-admin-shell"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="active-practice-scorer-shell"]').exists()).toBe(false);
    expect(wrapper.get('.school-nav').exists()).toBe(true);
  });

  it('denies a nonmember or cross-tenant School route without metadata leakage', async () => {
    vi.mocked(schoolApi.getSchool).mockRejectedValue(
      Object.assign(new Error('hidden school metadata'), { status: 404 }),
    );
    const wrapper = mount(SchoolAdminShellView, { global: { stubs: { RouterView: true } } });
    await flushPromises();
    expect(wrapper.text()).toContain('School not found or you do not have access.');
    expect(wrapper.text()).not.toContain('hidden school metadata');
  });

  it.each<SchoolMembershipRole>(['owner', 'admin', 'coach', 'scorer', 'viewer'])(
    'renders School Free entitlement for %s',
    (role) => {
      const wrapper = mountWithContext(SchoolOverviewView, role);
      expect(wrapper.text()).toContain('Central School');
      expect(wrapper.text()).toContain(role);
      expect(wrapper.text()).toContain('school_free');
      expect(wrapper.text()).toContain('school master roster');
    },
  );

  it.each<SchoolMembershipRole>(['owner', 'admin', 'coach'])(
    'shows governed Team writes for %s',
    async (role) => {
      const wrapper = mountWithContext(SchoolTeamsView, role);
      await flushPromises();
      expect(wrapper.text()).toContain('Create team');
    },
  );

  it.each<SchoolMembershipRole>(['scorer', 'viewer'])(
    'keeps Teams read-only for %s',
    async (role) => {
      const wrapper = mountWithContext(SchoolTeamsView, role);
      await flushPromises();
      expect(wrapper.text()).not.toContain('Create team');
    },
  );

  it('calls scoped Team create, edit, and archive contracts without roster JSON', async () => {
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
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([team]);
    vi.mocked(schoolApi.createSchoolTeam).mockResolvedValue(team);
    vi.mocked(schoolApi.updateSchoolTeam).mockResolvedValue(team);
    vi.mocked(schoolApi.archiveSchoolTeam).mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const wrapper = mountWithContext(SchoolTeamsView, 'owner');
    await flushPromises();
    await wrapper.get('input').setValue('Second XI');
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(schoolApi.createSchoolTeam).toHaveBeenCalledWith(
      'school-a',
      expect.objectContaining({ name: 'Second XI' }),
    );
    const editButton = wrapper.findAll('button').find((button) => button.text() === 'Edit')!;
    await editButton.trigger('click');
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(schoolApi.updateSchoolTeam).toHaveBeenCalledWith(
      'school-a',
      'team-a',
      expect.not.objectContaining({ players: expect.anything() }),
    );
    const archiveButton = wrapper.findAll('button').find((button) => button.text() === 'Archive')!;
    await archiveButton.trigger('click');
    await flushPromises();
    expect(schoolApi.archiveSchoolTeam).toHaveBeenCalledWith('school-a', 'team-a');
  });

  it('lets coach edit player metadata but exposes no lifecycle action', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([
      {
        id: 'sp-a',
        organization_id: 'school-a',
        player_profile_id: 'profile-a',
        player_name: 'Asha',
        status: 'inactive',
        student_identifier: 'S1',
        year_group: '8',
        created_by_user_id: null,
        created_at: '',
        updated_at: '',
      },
    ]);
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await wrapper.find('select').setValue('inactive');
    await flushPromises();
    expect(wrapper.text()).toContain('Edit metadata');
    expect(wrapper.text()).not.toContain('Reactivate');
    expect(wrapper.text()).not.toContain('Deactivate');
  });

  it.each<SchoolMembershipRole>(['owner', 'admin'])(
    'discovers inactive player and reactivates exact membership for %s',
    async (role) => {
      vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([
        {
          id: 'sp-retained',
          organization_id: 'school-a',
          player_profile_id: 'profile-retained',
          player_name: 'Retained Player',
          status: 'inactive',
          student_identifier: 'S1',
          year_group: '8',
          created_by_user_id: null,
          created_at: '',
          updated_at: '',
        },
      ]);
      vi.mocked(schoolApi.updateSchoolPlayer).mockResolvedValue({} as never);
      const wrapper = mountWithContext(SchoolPlayersView, role);
      await wrapper.find('select').setValue('inactive');
      await flushPromises();
      await wrapper.get('button:nth-of-type(2)').trigger('click');
      await flushPromises();
      expect(schoolApi.updateSchoolPlayer).toHaveBeenCalledWith('school-a', 'sp-retained', {
        status: 'active',
      });
    },
  );

  it('assigns and reactivates Team memberships using School membership identity', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([
      {
        id: 'sp-a',
        organization_id: 'school-a',
        player_profile_id: 'profile-a',
        player_name: 'Asha',
        status: 'active',
        student_identifier: null,
        year_group: null,
        created_by_user_id: null,
        created_at: '',
        updated_at: '',
      },
    ]);
    const wrapper = mountWithContext(SchoolTeamRosterView, 'coach');
    await flushPromises();
    await wrapper.find('select').setValue('sp-a');
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(schoolApi.addTeamRosterPlayer).toHaveBeenCalledWith('school-a', 'team-a', 'sp-a');
  });

  it('supports governed Team-roster deactivate and reactivate operations', async () => {
    vi.mocked(schoolApi.listTeamRoster).mockResolvedValue([
      {
        id: 'tr-active',
        organization_id: 'school-a',
        team_id: 'team-a',
        school_player_membership_id: 'sp-active',
        player_profile_id: 'p-active',
        player_name: 'Active',
        status: 'active',
        school_player_status: 'active',
        team_status: 'active',
        operationally_available: true,
        created_by_user_id: null,
        created_at: '',
        updated_at: '',
      },
      {
        id: 'tr-inactive',
        organization_id: 'school-a',
        team_id: 'team-a',
        school_player_membership_id: 'sp-inactive',
        player_profile_id: 'p-inactive',
        player_name: 'Inactive',
        status: 'inactive',
        school_player_status: 'active',
        team_status: 'active',
        operationally_available: false,
        created_by_user_id: null,
        created_at: '',
        updated_at: '',
      },
    ]);
    vi.mocked(schoolApi.deactivateTeamRosterPlayer).mockResolvedValue(undefined);
    vi.mocked(schoolApi.setTeamRosterPlayerStatus).mockResolvedValue({} as never);
    const wrapper = mountWithContext(SchoolTeamRosterView, 'coach');
    await flushPromises();
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Deactivate')!
      .trigger('click');
    await flushPromises();
    expect(schoolApi.deactivateTeamRosterPlayer).toHaveBeenCalledWith(
      'school-a',
      'team-a',
      'tr-active',
    );
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Reactivate')!
      .trigger('click');
    await flushPromises();
    expect(schoolApi.setTeamRosterPlayerStatus).toHaveBeenCalledWith(
      'school-a',
      'team-a',
      'tr-inactive',
      'active',
    );
  });

  it.each(['players.csv', 'players.xlsx'])(
    'previews %s with zero-mutation messaging and explicit resolution',
    async (filename) => {
      vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue({
        ...preview,
        file_type: filename.endsWith('xlsx') ? 'xlsx' : 'csv',
        original_filename: filename,
      });
      const wrapper = mountWithContext(SchoolImportView, 'owner');
      const input = wrapper.get('input[type=file]');
      Object.defineProperty(input.element, 'files', {
        value: [new File(['player_name\nAlex'], filename)],
        configurable: true,
      });
      await input.trigger('change');
      await wrapper.get('[data-test="preview-import"]').trigger('click');
      await flushPromises();
      expect(wrapper.text()).toContain('Preview does not add or change players.');
      expect(wrapper.text()).toContain('same-name candidates require review');
      expect(wrapper.get('[data-test="apply-import"]').attributes('disabled')).toBeDefined();
    },
  );

  it('restricts apply IDs to preview candidates and renders row results', async () => {
    vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue(preview);
    vi.mocked(schoolApi.applyPlayerImport).mockResolvedValue({
      import_id: 'import-a',
      status: 'applied',
      applied_at: '',
      summary: {
        created_players: 0,
        linked_existing_players: 1,
        reactivated_memberships: 0,
        team_assignments_created: 1,
        team_assignments_reactivated: 0,
        no_op_rows: 0,
        skipped_rows: 0,
        failed_rows: 0,
      },
      rows: [
        {
          source_row_number: 2,
          outcome: 'team_assigned',
          school_player_membership_id: 'member-player-a',
          player_profile_id: 'profile-a',
          team_id: 'team-a',
          detail: 'Row applied successfully',
        },
      ],
    });
    const wrapper = mountWithContext(SchoolImportView, 'owner');
    const input = wrapper.get('input[type=file]');
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'players.csv')],
      configurable: true,
    });
    await input.trigger('change');
    await wrapper.get('[data-test="preview-import"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-test="action-2"]').setValue('use_existing');
    await wrapper.get('#player-2').setValue('member-player-a');
    await wrapper.get('[data-test="apply-import"]').trigger('click');
    await flushPromises();
    expect(schoolApi.applyPlayerImport).toHaveBeenCalledWith('school-a', 'import-a', [
      {
        source_row_number: 2,
        action: 'use_existing',
        school_player_membership_id: 'member-player-a',
        team_id: 'team-a',
      },
    ]);
    expect(wrapper.text()).toContain('Row applied successfully');
  });

  it('does not offer coach inactive-membership reactivation', async () => {
    vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue({
      ...preview,
      rows: [
        {
          ...preview.rows[0],
          candidate_memberships: [
            { school_player_membership_id: 'inactive-a', player_name: 'Alex', status: 'inactive' },
          ],
        },
      ],
    });
    const wrapper = mountWithContext(SchoolImportView, 'coach');
    const input = wrapper.get('input[type=file]');
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'players.csv')],
      configurable: true,
    });
    await input.trigger('change');
    await wrapper.get('[data-test="preview-import"]').trigger('click');
    await flushPromises();
    expect(wrapper.text()).not.toContain('Reactivate inactive player');
  });

  it('handles expired and consumed previews without automatic retry', async () => {
    vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue({
      ...preview,
      rows: [
        {
          ...preview.rows[0],
          resolution_required: false,
          classification: 'create_new',
          values: { ...preview.rows[0].values, team_name: null },
        },
      ],
    });
    const expired = Object.assign(new Error('expired'), { status: 410 });
    vi.mocked(schoolApi.applyPlayerImport).mockRejectedValueOnce(expired);
    const wrapper = mountWithContext(SchoolImportView, 'owner');
    const input = wrapper.get('input[type=file]');
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'players.csv')],
      configurable: true,
    });
    await input.trigger('change');
    await wrapper.get('[data-test="preview-import"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-test="apply-import"]').trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('preview expired');
    expect(schoolApi.applyPlayerImport).toHaveBeenCalledTimes(1);
  });

  it('shows a controlled already-consumed conflict and does not replay apply', async () => {
    vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue({
      ...preview,
      rows: [
        {
          ...preview.rows[0],
          resolution_required: false,
          classification: 'create_new',
          values: { ...preview.rows[0].values, team_name: null },
        },
      ],
    });
    vi.mocked(schoolApi.applyPlayerImport).mockRejectedValue(
      Object.assign(new Error('already applied'), { status: 409 }),
    );
    const wrapper = mountWithContext(SchoolImportView, 'owner');
    const input = wrapper.get('input[type=file]');
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'players.csv')],
      configurable: true,
    });
    await input.trigger('change');
    await wrapper.get('[data-test="preview-import"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-test="apply-import"]').trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('already applied or is being applied');
    expect(schoolApi.applyPlayerImport).toHaveBeenCalledTimes(1);
  });

  it('clears preview and candidate state when organization route context changes', async () => {
    vi.mocked(schoolApi.previewPlayerImport).mockResolvedValue(preview);
    const organizationId = ref('school-a');
    const wrapper = mountWithContext(SchoolImportView, 'owner', organizationId);
    const input = wrapper.get('input[type=file]');
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'players.csv')],
      configurable: true,
    });
    await input.trigger('change');
    await wrapper.get('[data-test="preview-import"]').trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Alex Lee');
    organizationId.value = 'school-b';
    await flushPromises();
    expect(wrapper.text()).not.toContain('Alex Lee');
  });
});

describe('Issue 608 Workstream A: name-only School and Club player entry', () => {
  const legacyPlayer = {
    id: 'sp-legacy',
    organization_id: 'school-a',
    player_profile_id: 'profile-legacy',
    player_name: 'Asha',
    status: 'active' as const,
    student_identifier: 'Legacy  S1',
    year_group: 'Year 8',
    created_by_user_id: null,
    created_at: '',
    updated_at: '',
  };

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([]);
    vi.mocked(schoolApi.createSchoolPlayer).mockResolvedValue({} as never);
    vi.mocked(schoolApi.updateSchoolPlayer).mockResolvedValue({} as never);
  });

  function mountClub(role: SchoolMembershipRole) {
    const clubContext: SchoolContext = {
      ...context(role),
      organizationType: computed(() => 'club'),
      organizationBasePath: computed(() => organizationBasePath('club')),
      terminology: computed(() => organizationTerminology('club')),
    };
    return mount(SchoolPlayersView, {
      global: { provide: { [schoolContextKey as symbol]: clubContext } },
    });
  }

  it.each(['school', 'club'] as const)(
    'adds a %s player with a name only and sends no identifier, group or role',
    async (kind) => {
      const wrapper =
        kind === 'club' ? mountClub('coach') : mountWithContext(SchoolPlayersView, 'coach');
      await flushPromises();
      const form = wrapper.get('form.editor');
      const requiredInputs = form.findAll('input[required]');
      expect(requiredInputs).toHaveLength(1);
      expect(form.text()).toContain('Player name');
      expect(form.text()).not.toMatch(/Local player/i);
      expect(form.text()).not.toMatch(/captain|wicketkeeper/i);
      // Optional details are collapsed by default and nothing outside them is an ID field.
      const optional = form.get('[data-test="add-player-optional-details"]');
      expect(optional.attributes('open')).toBeUndefined();
      expect(
        form.findAll('input').filter((input) => !optional.element.contains(input.element)),
      ).toHaveLength(1);

      await requiredInputs[0].setValue('Maya Singh');
      await form.trigger('submit');
      await flushPromises();

      expect(schoolApi.createSchoolPlayer).toHaveBeenCalledTimes(1);
      expect(schoolApi.createSchoolPlayer).toHaveBeenCalledWith('school-a', {
        player_name: 'Maya Singh',
      });
      expect(wrapper.text()).toContain(
        `Player added to the ${kind === 'club' ? 'Club' : 'School'} master roster.`,
      );
    },
  );

  it('still accepts an optional group and external reference without requiring them', async () => {
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await flushPromises();
    const form = wrapper.get('form.editor');
    const optional = form.get('[data-test="add-player-optional-details"]');
    expect(optional.text()).toContain('External reference');
    expect(optional.text()).toContain('need not be unique');
    const [group, reference] = optional.findAll('input');
    await form.get('input[required]').setValue('Maya Singh');
    await group.setValue('Year 9');
    await reference.setValue('REG-7');
    await form.trigger('submit');
    await flushPromises();

    expect(schoolApi.createSchoolPlayer).toHaveBeenCalledWith('school-a', {
      player_name: 'Maya Singh',
      year_group: 'Year 9',
      student_identifier: 'REG-7',
    });
  });

  it('lists same-name players as distinct rows without a technical ID column', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([
      { ...legacyPlayer, id: 'sp-one', player_profile_id: 'profile-one', student_identifier: null },
      { ...legacyPlayer, id: 'sp-two', player_profile_id: 'profile-two', student_identifier: 'S1' },
    ]);
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await flushPromises();
    const headers = wrapper.findAll('th').map((th) => th.text());
    expect(headers).toEqual(['Player', 'Group', 'Status', 'Actions']);
    const rows = wrapper.findAll('tbody tr');
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain('Asha');
    expect(rows[0].text()).not.toContain('Ref:');
    expect(rows[1].text()).toContain('Ref: S1');
    expect(wrapper.text()).not.toContain('profile-one');
    expect(wrapper.text()).not.toContain('sp-one');
  });

  it('shows automatic IDs read-only and leaves untouched legacy references unchanged', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([legacyPlayer]);
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await flushPromises();
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Edit metadata')!
      .trigger('click');

    const dialog = wrapper.get('dialog');
    expect(dialog.text()).toContain('External reference (optional)');
    expect(dialog.text()).not.toContain('Local player identifier');
    const support = dialog.get('[data-test="player-support-details"]');
    expect(support.text()).toContain('sp-legacy');
    expect(support.text()).toContain('profile-legacy');
    expect(support.findAll('input')).toHaveLength(0);

    // Change only the group: the legacy reference (with its original spacing) is not resent.
    await dialog.findAll('input')[0].setValue('Year 9');
    await dialog.get('form').trigger('submit');
    await flushPromises();
    expect(schoolApi.updateSchoolPlayer).toHaveBeenCalledWith('school-a', 'sp-legacy', {
      year_group: 'Year 9',
    });
  });

  it('makes no update request when nothing was changed', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([legacyPlayer]);
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await flushPromises();
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Edit metadata')!
      .trigger('click');
    await wrapper.get('dialog form').trigger('submit');
    await flushPromises();
    expect(schoolApi.updateSchoolPlayer).not.toHaveBeenCalled();
    expect(wrapper.find('dialog form').exists()).toBe(false);
  });

  it('clears an external reference only when the coach explicitly empties it', async () => {
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([legacyPlayer]);
    const wrapper = mountWithContext(SchoolPlayersView, 'coach');
    await flushPromises();
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Edit metadata')!
      .trigger('click');
    await wrapper.get('dialog').findAll('input')[1].setValue('');
    await wrapper.get('dialog form').trigger('submit');
    await flushPromises();
    expect(schoolApi.updateSchoolPlayer).toHaveBeenCalledWith('school-a', 'sp-legacy', {
      student_identifier: null,
    });
  });

  it('relabels the import identifier column as an optional external reference', async () => {
    const wrapper = mountWithContext(SchoolImportView, 'coach');
    await flushPromises();
    expect(wrapper.text()).toContain('External reference header (optional)');
    expect(wrapper.text()).not.toContain('Student ID header');
  });
});
