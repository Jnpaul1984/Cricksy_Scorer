import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type {
  FreeOrganizationType,
  OrganizationAnnouncementFeedItem,
  SchoolMembershipRole,
} from '@/types/schoolAdmin';
import OrganizationAnnouncementsView from '@/views/school/OrganizationAnnouncementsView.vue';

vi.mock('@/services/schoolAdminApi');

const published: OrganizationAnnouncementFeedItem = {
  announcement_id: 'announcement-a',
  organization_id: 'school-a',
  title: 'Published update',
  body: 'Training starts at 17:00.',
  audience_type: 'organization',
  team_id: null,
  status: 'published',
  revision: 1,
  publication_version: 1,
  published_by_user_id: 'owner-a',
  published_at: '2026-09-29T17:00:00Z',
  eligible_recipient_count: 5,
  delivered_count: 4,
  suppressed_by_preference_count: 1,
  unresolved_recipient_count: 0,
  created_by_user_id: 'owner-a',
  created_at: '2026-09-29T16:00:00Z',
  updated_at: '2026-09-29T17:00:00Z',
};

function context(
  organizationType: FreeOrganizationType,
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref(`${organizationType}-a`),
): SchoolContext {
  const writes = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType),
    organizationBasePath: computed(() => organizationBasePath(organizationType)),
    terminology: computed(() => organizationTerminology(organizationType)),
    organization: ref(null),
    membership: ref({
      id: 'membership-a',
      organization_id: organizationId.value,
      user_id: role === 'coach' ? 'coach-a' : 'owner-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref(null),
    canManageTeams: writes,
    canManageRosterMetadata: writes,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: writes,
    canImport: writes,
    canCreateSchoolMatch: computed(() => role !== 'viewer'),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: writes,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => role !== 'viewer'),
    canPublishScorecards: computed(() => role !== 'viewer'),
    canViewEvents: computed(() => true),
    canManageEvents: writes,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: writes,
  };
}

function mountView(
  organizationType: FreeOrganizationType,
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref(`${organizationType}-a`),
) {
  return mount(OrganizationAnnouncementsView, {
    global: {
      provide: {
        [schoolContextKey as symbol]: context(organizationType, role, organizationId),
      },
    },
  });
}

describe('shared organization announcements view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listOrganizationAnnouncements).mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      {
        id: 'team-a',
        organization_id: 'school-a',
        name: 'First XI',
        status: 'active',
        home_ground: null,
        season: null,
        owner_user_id: 'owner-a',
        coach_user_id: 'coach-a',
        coach_name: 'Coach A',
        created_at: '',
        updated_at: '',
      },
    ]);
  });

  (['school', 'club'] as const).forEach((organizationType) => {
    it(`creates and previews a ${organizationType} draft without publishing`, async () => {
      vi.mocked(schoolApi.createOrganizationAnnouncement).mockResolvedValue({
        id: 'draft-a',
        organization_id: `${organizationType}-a`,
        title: 'Training update',
        body: 'Meet at the main ground.',
        audience_type: 'organization',
        team_id: null,
        status: 'draft',
        revision: 1,
        last_published_version: 0,
        created_by_user_id: 'owner-a',
        updated_by_user_id: 'owner-a',
        created_at: '',
        updated_at: '',
      });
      const wrapper = mountView(organizationType, 'owner');
      await flushPromises();
      await wrapper.get('[data-test=announcement-title]').setValue('Training update');
      await wrapper.get('[data-test=announcement-body]').setValue('Meet at the main ground.');
      expect(wrapper.get('[aria-label="Announcement preview"]').text()).toContain(
        'Training update',
      );
      await wrapper.get('[data-test=save-announcement]').trigger('submit');
      await flushPromises();
      expect(schoolApi.createOrganizationAnnouncement).toHaveBeenCalledWith(
        `${organizationType}-a`,
        {
          title: 'Training update',
          body: 'Meet at the main ground.',
          audience_type: 'organization',
          team_id: null,
        },
      );
      expect(schoolApi.publishOrganizationAnnouncement).not.toHaveBeenCalled();
      expect(wrapper.text()).toContain('No notifications were sent');
    });
  });

  it('selects a saved Team and publishes explicitly with delivery counts', async () => {
    const draft: OrganizationAnnouncementFeedItem = {
      ...published,
      announcement_id: 'team-draft',
      title: 'First XI update',
      audience_type: 'team',
      team_id: 'team-a',
      status: 'draft',
      publication_version: null,
      published_by_user_id: null,
      published_at: null,
      eligible_recipient_count: null,
      delivered_count: null,
      suppressed_by_preference_count: null,
      unresolved_recipient_count: null,
    };
    vi.mocked(schoolApi.listOrganizationAnnouncements)
      .mockResolvedValueOnce({ items: [draft], total: 1, limit: 100, offset: 0 })
      .mockResolvedValue({
        items: [{ ...published, audience_type: 'team', team_id: 'team-a' }],
        total: 1,
        limit: 100,
        offset: 0,
      });
    vi.mocked(schoolApi.publishOrganizationAnnouncement).mockResolvedValue({
      id: 'publication-a',
      announcement_id: draft.announcement_id,
      organization_id: 'school-a',
      publication_version: 1,
      announcement_revision: 1,
      title: draft.title,
      body: draft.body,
      audience_type: 'team',
      team_id: 'team-a',
      published_by_user_id: 'owner-a',
      published_at: published.published_at!,
      eligible_recipient_count: 3,
      delivered_count: 2,
      suppressed_by_preference_count: 1,
      unresolved_recipient_count: 0,
    });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const wrapper = mountView('school', 'owner');
    await flushPromises();
    expect(wrapper.text()).toContain('First XI');
    await wrapper.get('[data-test=publish-announcement]').trigger('click');
    await flushPromises();
    expect(schoolApi.publishOrganizationAnnouncement).toHaveBeenCalledWith(
      'school-a',
      'team-draft',
      1,
    );
    expect(wrapper.text()).toContain('2 delivered, 1 suppressed');
  });

  it('prevents duplicate draft submission while the first request is pending', async () => {
    let resolveCreate: (
      value: Awaited<ReturnType<typeof schoolApi.createOrganizationAnnouncement>>,
    ) => void = () => undefined;
    vi.mocked(schoolApi.createOrganizationAnnouncement).mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = resolve;
      }),
    );
    const wrapper = mountView('school', 'owner');
    await flushPromises();
    await wrapper.get('[data-test=announcement-title]').setValue('One draft');
    await wrapper.get('[data-test=announcement-body]').setValue('One submission only.');
    await wrapper.get('[data-test=save-announcement]').trigger('submit');
    await wrapper.get('[data-test=save-announcement]').trigger('submit');
    expect(schoolApi.createOrganizationAnnouncement).toHaveBeenCalledTimes(1);
    resolveCreate({
      id: 'draft-a',
      organization_id: 'school-a',
      title: 'One draft',
      body: 'One submission only.',
      audience_type: 'organization',
      team_id: null,
      status: 'draft',
      revision: 1,
      last_published_version: 0,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      created_at: '',
      updated_at: '',
    });
    await flushPromises();
  });

  it('only offers a coach Teams currently assigned to that coach', async () => {
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      {
        id: 'team-a',
        organization_id: 'school-a',
        name: 'Assigned XI',
        status: 'active',
        home_ground: null,
        season: null,
        owner_user_id: 'owner-a',
        coach_user_id: 'coach-a',
        coach_name: 'Coach A',
        created_at: '',
        updated_at: '',
      },
      {
        id: 'team-b',
        organization_id: 'school-a',
        name: 'Foreign XI',
        status: 'active',
        home_ground: null,
        season: null,
        owner_user_id: 'owner-a',
        coach_user_id: 'coach-b',
        coach_name: 'Coach B',
        created_at: '',
        updated_at: '',
      },
    ]);
    const wrapper = mountView('school', 'coach');
    await flushPromises();
    await wrapper.get('[data-test=announcement-audience]').setValue('team');
    expect(wrapper.get('[data-test=announcement-team]').text()).toContain('Assigned XI');
    expect(wrapper.get('[data-test=announcement-team]').text()).not.toContain('Foreign XI');
  });

  (['scorer', 'viewer'] as const).forEach((role) => {
    it(`keeps ${role} read-only`, async () => {
      vi.mocked(schoolApi.listOrganizationAnnouncements).mockResolvedValue({
        items: [published],
        total: 1,
        limit: 100,
        offset: 0,
      });
      const wrapper = mountView('school', role);
      await flushPromises();
      expect(wrapper.text()).toContain('Published update');
      expect(wrapper.find('[data-test=announcement-form]').exists()).toBe(false);
      expect(wrapper.find('[data-test=publish-announcement]').exists()).toBe(false);
      expect(wrapper.text()).not.toContain('Reply');
    });
  });

  it('creates a new draft revision without rewriting the published card', async () => {
    vi.mocked(schoolApi.listOrganizationAnnouncements).mockResolvedValue({
      items: [published],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.createOrganizationAnnouncementRevision).mockResolvedValue({
      id: published.announcement_id,
      organization_id: 'school-a',
      title: published.title,
      body: published.body,
      audience_type: published.audience_type,
      team_id: null,
      status: 'draft',
      revision: 2,
      last_published_version: 1,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      created_at: published.created_at,
      updated_at: published.updated_at,
    });
    const wrapper = mountView('school', 'coach');
    await flushPromises();
    await wrapper.get('button.secondary').trigger('click');
    await flushPromises();
    expect(schoolApi.createOrganizationAnnouncementRevision).toHaveBeenCalledWith(
      'school-a',
      published.announcement_id,
      1,
    );
    expect(wrapper.get('[data-test=announcement-title]').element).toHaveProperty(
      'value',
      'Published update',
    );
    expect(wrapper.text()).toContain('Published versions remain unchanged');
  });

  it('clears draft/feed and suppresses a stale response after an organization switch', async () => {
    let resolveOld: (
      value: Awaited<ReturnType<typeof schoolApi.listOrganizationAnnouncements>>,
    ) => void = () => undefined;
    const oldRequest = new Promise<
      Awaited<ReturnType<typeof schoolApi.listOrganizationAnnouncements>>
    >((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.listOrganizationAnnouncements)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValueOnce({
        items: [{ ...published, announcement_id: 'new', title: 'New organization' }],
        total: 1,
        limit: 100,
        offset: 0,
      });
    const organizationId = ref('school-a');
    const wrapper = mountView('school', 'owner', organizationId);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-test=announcement-title]').setValue('Old organization draft');
    organizationId.value = 'school-b';
    await flushPromises();
    expect(wrapper.text()).toContain('New organization');
    expect(wrapper.text()).not.toContain('Old organization draft');
    resolveOld({ items: [published], total: 1, limit: 100, offset: 0 });
    await flushPromises();
    expect(wrapper.text()).not.toContain('Published update');
  });

  it.each([
    [403, 'do not have permission'],
    [404, 'not found'],
    [409, 'revision conflict'],
    [422, 'body was not accepted'],
    [500, 'service encountered a problem'],
  ])('renders a controlled %s load error', async (status, expected) => {
    vi.mocked(schoolApi.listOrganizationAnnouncements).mockRejectedValue(
      Object.assign(new Error(status === 500 ? 'sensitive SQL detail' : expected), { status }),
    );
    const wrapper = mountView('club', 'owner');
    await flushPromises();
    expect(wrapper.get('[role=alert]').text().toLowerCase()).toContain(expected);
    expect(wrapper.text()).not.toContain('sensitive SQL detail');
  });

  it('renders a connection-safe error', async () => {
    vi.mocked(schoolApi.listOrganizationAnnouncements).mockRejectedValue(
      new TypeError('network failed'),
    );
    const wrapper = mountView('school', 'owner');
    await flushPromises();
    expect(wrapper.get('[role=alert]').text()).toContain('could not be reached');
  });
});
