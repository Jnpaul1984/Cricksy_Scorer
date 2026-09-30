import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import {
  organizationNotificationShellKey,
  type OrganizationNotificationShellContext,
} from '@/composables/useOrganizationNotificationShell';
import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type {
  FreeOrganizationType,
  OrganizationNotification,
  OrganizationNotificationCategory,
  OrganizationNotificationPreference,
  SchoolMembershipRole,
} from '@/types/schoolAdmin';
import OrganizationNotificationsView from '@/views/school/OrganizationNotificationsView.vue';

vi.mock('@/services/schoolAdminApi');

const categories: OrganizationNotificationCategory[] = [
  'organization_announcement',
  'team_announcement',
  'event',
  'selection',
  'availability_reminder',
];

function notification(id: string, organizationId = 'school-a'): OrganizationNotification {
  return {
    id,
    organization_id: organizationId,
    recipient_user_id: 'user-a',
    category: 'event',
    source_type: 'organization_event',
    source_id: 'event-a',
    source_version: '1',
    source_key: 'event:event-a:update',
    idempotency_key: `event:${id}`,
    title: `Notification ${id}`,
    summary: 'Training starts at 17:00.',
    origin: 'actor',
    actor_user_id: 'owner-a',
    created_at: '2026-09-29T17:00:00Z',
    read_at: null,
  };
}

function preference(
  category: OrganizationNotificationCategory,
  enabled = true,
  organizationId = 'school-a',
): OrganizationNotificationPreference {
  return {
    organization_id: organizationId,
    user_id: 'user-a',
    category,
    enabled,
    created_at: null,
    updated_at: null,
  };
}

function context(
  organizationId: Ref<string>,
  organizationType: Ref<FreeOrganizationType>,
  role: SchoolMembershipRole = 'owner',
): SchoolContext {
  const writes = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: ref(null),
    membership: ref({
      id: 'membership-a',
      organization_id: organizationId.value,
      user_id: 'user-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref({
      id: 'entitlement-a',
      organization_id: organizationId.value,
      plan_key: organizationType.value === 'club' ? 'club_free' : 'school_free',
      status: 'active',
      source: 'system',
      effective_from: '',
      effective_until: null,
      capabilities: ['organization_notifications'],
      excluded_capabilities: [],
      created_at: '',
      updated_at: '',
    }),
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
    canManageCommunity: writes,
  };
}

function mountView(
  organizationId = ref('school-a'),
  organizationType = ref<FreeOrganizationType>('school'),
  role: SchoolMembershipRole = 'owner',
) {
  const unreadCount = ref(2);
  const shell: OrganizationNotificationShellContext = {
    unreadCount,
    refreshUnreadCount: vi.fn().mockResolvedValue(undefined),
    clearPrivateState: vi.fn(() => {
      unreadCount.value = 0;
    }),
  };
  return {
    shell,
    wrapper: mount(OrganizationNotificationsView, {
      global: {
        provide: {
          [schoolContextKey as symbol]: context(organizationId, organizationType, role),
          [organizationNotificationShellKey as symbol]: shell,
        },
      },
    }),
  };
}

describe('shared organization notification inbox', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listOrganizationNotifications).mockResolvedValue({
      items: [notification('one')],
      total: 1,
      limit: 20,
      offset: 0,
    });
    vi.mocked(schoolApi.listOrganizationNotificationPreferences).mockResolvedValue({
      items: categories.map((category) => preference(category)),
    });
  });

  (['school', 'club'] as const).forEach((organizationType) => {
    it(`renders the current User's private ${organizationType} inbox and all preferences`, async () => {
      const { wrapper } = mountView(
        ref(`${organizationType}-a`),
        ref<FreeOrganizationType>(organizationType),
        'viewer',
      );
      await flushPromises();
      expect(wrapper.text()).toContain(
        `Private ${organizationType === 'club' ? 'Club' : 'School'} delivery`,
      );
      expect(wrapper.get('[data-test=notification-one]').attributes('aria-label')).toContain(
        'Unread notification',
      );
      expect(wrapper.findAll('.preference-row')).toHaveLength(5);
      expect(wrapper.text()).toContain('future logical deliveries only');
      expect(wrapper.text()).not.toContain('SMS');
      expect(wrapper.text()).not.toContain('WhatsApp');
    });
  });

  it.each(['owner', 'admin', 'coach', 'scorer', 'viewer'] as const)(
    'allows an active %s to use only their own recipient-scoped inbox and preferences',
    async (role) => {
      const { wrapper } = mountView(ref('school-a'), ref<FreeOrganizationType>('school'), role);
      await flushPromises();
      expect(wrapper.text()).toContain('Notification one');
      expect(wrapper.findAll('.preference-row')).toHaveLength(5);
      expect(schoolApi.listOrganizationNotifications).toHaveBeenCalledWith(
        'school-a',
        expect.objectContaining({ limit: 20, offset: 0 }),
      );
    },
  );

  it('uses bounded category/unread pagination and appends the next page', async () => {
    vi.mocked(schoolApi.listOrganizationNotifications)
      .mockResolvedValueOnce({ items: [notification('one')], total: 2, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [notification('filtered')], total: 2, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [notification('page-two')], total: 2, limit: 20, offset: 1 });
    const { wrapper } = mountView();
    await flushPromises();
    await wrapper.get('[data-test=notification-category-filter]').setValue('event');
    await flushPromises();
    expect(schoolApi.listOrganizationNotifications).toHaveBeenLastCalledWith('school-a', {
      category: 'event',
      unreadOnly: false,
      limit: 20,
      offset: 0,
    });
    await wrapper.get('[data-test=load-more-notifications]').trigger('click');
    await flushPromises();
    expect(schoolApi.listOrganizationNotifications).toHaveBeenLastCalledWith('school-a', {
      category: 'event',
      unreadOnly: false,
      limit: 20,
      offset: 1,
    });
    expect(wrapper.text()).toContain('Notification filtered');
    expect(wrapper.text()).toContain('Notification page-two');
  });

  it('marks a notification read only after the authoritative response and refreshes the badge', async () => {
    const updated = { ...notification('one'), read_at: '2026-09-29T18:00:00Z' };
    vi.mocked(schoolApi.markOrganizationNotificationRead).mockResolvedValue(updated);
    const { wrapper, shell } = mountView();
    await flushPromises();
    await wrapper.get('[data-test=mark-read-one]').trigger('click');
    await flushPromises();
    expect(schoolApi.markOrganizationNotificationRead).toHaveBeenCalledWith('school-a', 'one');
    expect(wrapper.get('[data-test=notification-read-state]').text()).toBe('Read');
    expect(shell.refreshUnreadCount).toHaveBeenCalled();
  });

  it('does not optimistically change read-state or preferences after a rejected mutation', async () => {
    vi.mocked(schoolApi.markOrganizationNotificationRead).mockRejectedValue(
      Object.assign(new Error('revision conflict'), { status: 409 }),
    );
    vi.mocked(schoolApi.updateOrganizationNotificationPreference).mockRejectedValue(
      Object.assign(new Error('validation failed'), { status: 422 }),
    );
    const { wrapper } = mountView();
    await flushPromises();
    await wrapper.get('[data-test=mark-read-one]').trigger('click');
    await flushPromises();
    expect(wrapper.get('[data-test=notification-read-state]').text()).toBe('Unread');
    const checkbox = wrapper.get('[data-test=preference-event]');
    await checkbox.setValue(false);
    await flushPromises();
    expect((checkbox.element as HTMLInputElement).checked).toBe(true);
  });

  it('updates an in-app preference with explicit future-only semantics', async () => {
    vi.mocked(schoolApi.updateOrganizationNotificationPreference).mockResolvedValue(
      preference('event', false),
    );
    const { wrapper } = mountView();
    await flushPromises();
    await wrapper.get('[data-test=preference-event]').setValue(false);
    await flushPromises();
    expect(schoolApi.updateOrganizationNotificationPreference).toHaveBeenCalledWith(
      'school-a',
      'event',
      false,
    );
    expect(wrapper.text()).toContain('preference updated for future deliveries');
  });

  it.each([
    ['school', 'club'],
    ['club', 'school'],
    ['school', 'school'],
    ['club', 'club'],
  ] as const)(
    'suppresses late private responses across %s to %s context switches',
    async (fromType, toType) => {
      let resolveOld: (
        value: Awaited<ReturnType<typeof schoolApi.listOrganizationNotifications>>,
      ) => void = () => undefined;
      const oldRequest = new Promise<
        Awaited<ReturnType<typeof schoolApi.listOrganizationNotifications>>
      >((resolve) => {
        resolveOld = resolve;
      });
      vi.mocked(schoolApi.listOrganizationNotifications)
        .mockReturnValueOnce(oldRequest)
        .mockResolvedValueOnce({
          items: [notification('new', `${toType}-b`)],
          total: 1,
          limit: 20,
          offset: 0,
        });
      let resolveOldPreferences: (
        value: Awaited<ReturnType<typeof schoolApi.listOrganizationNotificationPreferences>>,
      ) => void = () => undefined;
      const oldPreferenceRequest = new Promise<
        Awaited<ReturnType<typeof schoolApi.listOrganizationNotificationPreferences>>
      >((resolve) => {
        resolveOldPreferences = resolve;
      });
      vi.mocked(schoolApi.listOrganizationNotificationPreferences)
        .mockReturnValueOnce(oldPreferenceRequest)
        .mockResolvedValueOnce({
          items: categories.map((value) => preference(value, true, `${toType}-b`)),
        });
      const organizationId = ref(`${fromType}-a`);
      const organizationType = ref<FreeOrganizationType>(fromType);
      const { wrapper, shell } = mountView(organizationId, organizationType);
      await wrapper.vm.$nextTick();
      organizationId.value = `${toType}-b`;
      organizationType.value = toType;
      await flushPromises();
      expect(wrapper.text()).toContain('Notification new');
      expect(
        (wrapper.get('[data-test=notification-category-filter]').element as HTMLSelectElement)
          .value,
      ).toBe('');
      resolveOld({ items: [notification('old', `${fromType}-a`)], total: 1, limit: 20, offset: 0 });
      resolveOldPreferences({
        items: categories.map((value) => preference(value, value !== 'event', `${fromType}-a`)),
      });
      await flushPromises();
      expect(wrapper.text()).not.toContain('Notification old');
      expect(
        (wrapper.get('[data-test=preference-event]').element as HTMLInputElement).checked,
      ).toBe(true);
      expect(shell.clearPrivateState).toHaveBeenCalled();
    },
  );

  it.each([403, 404])(
    'clears protected data after a controlled %s access failure',
    async (status) => {
      vi.mocked(schoolApi.markOrganizationNotificationRead).mockRejectedValue(
        Object.assign(new Error('access revoked'), { status }),
      );
      const { wrapper, shell } = mountView();
      await flushPromises();
      await wrapper.get('[data-test=mark-read-one]').trigger('click');
      await flushPromises();
      expect(wrapper.find('[data-test=notification-one]').exists()).toBe(false);
      expect(shell.clearPrivateState).toHaveBeenCalled();
      expect(wrapper.get('[role=alert]').text()).not.toContain('access revoked');
    },
  );

  it.each([403, 404])(
    'settles an inbox refresh after a controlled %s access failure without a success notice',
    async (status) => {
      vi.mocked(schoolApi.listOrganizationNotifications)
        .mockResolvedValueOnce({ items: [notification('one')], total: 1, limit: 20, offset: 0 })
        .mockRejectedValueOnce(Object.assign(new Error('private backend detail'), { status }));
      const { wrapper, shell } = mountView();
      await flushPromises();

      await wrapper.get('[data-test=refresh-notifications]').trigger('click');
      await flushPromises();

      expect(wrapper.find('[data-test=notification-one]').exists()).toBe(false);
      expect(wrapper.find('[data-test=preference-event]').exists()).toBe(false);
      expect(shell.unreadCount.value).toBe(0);
      expect(shell.clearPrivateState).toHaveBeenCalled();
      expect(wrapper.text()).not.toContain('Loading notifications…');
      expect(wrapper.text()).not.toContain('Loading notification preferences…');
      expect(wrapper.text()).not.toContain('Notification inbox refreshed.');
      expect(wrapper.get('[role=alert]').text()).not.toContain('private backend detail');
      expect(wrapper.get('[role=alert]').text()).toMatch(/permission|not found/i);
      const state = wrapper.vm as unknown as {
        loading: boolean;
        loadingMore: boolean;
        preferencesLoading: boolean;
      };
      expect(state.loading).toBe(false);
      expect(state.loadingMore).toBe(false);
      expect(state.preferencesLoading).toBe(false);
    },
  );

  it.each([403, 404])(
    'settles a preference refresh after a controlled %s access failure without stale defaults',
    async (status) => {
      vi.mocked(schoolApi.listOrganizationNotificationPreferences)
        .mockResolvedValueOnce({ items: categories.map((value) => preference(value)) })
        .mockRejectedValueOnce(Object.assign(new Error('private preference detail'), { status }));
      const { wrapper, shell } = mountView();
      await flushPromises();

      await wrapper.get('[data-test=refresh-notifications]').trigger('click');
      await flushPromises();

      expect(wrapper.find('[data-test=notification-one]').exists()).toBe(false);
      expect(wrapper.findAll('.preference-row')).toHaveLength(0);
      expect(shell.unreadCount.value).toBe(0);
      expect(wrapper.text()).not.toContain('Loading notifications…');
      expect(wrapper.text()).not.toContain('Loading notification preferences…');
      expect(wrapper.text()).not.toContain('Notification inbox refreshed.');
      expect(wrapper.get('[role=alert]').text()).not.toContain('private preference detail');
      expect(wrapper.get('[role=alert]').text()).toMatch(/permission|not found/i);
      const state = wrapper.vm as unknown as {
        loading: boolean;
        loadingMore: boolean;
        preferencesLoading: boolean;
      };
      expect(state.loading).toBe(false);
      expect(state.loadingMore).toBe(false);
      expect(state.preferencesLoading).toBe(false);
    },
  );

  it('settles an in-progress load-more request when access is revoked', async () => {
    let rejectNextPage: (reason: unknown) => void = () => undefined;
    const nextPage = new Promise<
      Awaited<ReturnType<typeof schoolApi.listOrganizationNotifications>>
    >((_resolve, reject) => {
      rejectNextPage = reject;
    });
    vi.mocked(schoolApi.listOrganizationNotifications)
      .mockResolvedValueOnce({ items: [notification('one')], total: 2, limit: 20, offset: 0 })
      .mockReturnValueOnce(nextPage);
    const { wrapper } = mountView();
    await flushPromises();

    await wrapper.get('[data-test=load-more-notifications]').trigger('click');
    await wrapper.vm.$nextTick();
    expect((wrapper.vm as unknown as { loadingMore: boolean }).loadingMore).toBe(true);

    rejectNextPage(Object.assign(new Error('membership revoked'), { status: 403 }));
    await flushPromises();

    const state = wrapper.vm as unknown as {
      loading: boolean;
      loadingMore: boolean;
      preferencesLoading: boolean;
    };
    expect(state.loading).toBe(false);
    expect(state.loadingMore).toBe(false);
    expect(state.preferencesLoading).toBe(false);
    expect(wrapper.find('[data-test=notification-one]').exists()).toBe(false);
    expect(wrapper.get('[role=alert]').text()).toContain('do not have permission');
  });

  it.each(['inbox', 'preferences'] as const)(
    'does not restore private data from a late stale %s response after access failure',
    async (lateResponse) => {
      let resolveInbox: (
        value: Awaited<ReturnType<typeof schoolApi.listOrganizationNotifications>>,
      ) => void = () => undefined;
      let resolvePreferences: (
        value: Awaited<ReturnType<typeof schoolApi.listOrganizationNotificationPreferences>>,
      ) => void = () => undefined;
      const pendingInbox = new Promise<
        Awaited<ReturnType<typeof schoolApi.listOrganizationNotifications>>
      >((resolve) => {
        resolveInbox = resolve;
      });
      const pendingPreferences = new Promise<
        Awaited<ReturnType<typeof schoolApi.listOrganizationNotificationPreferences>>
      >((resolve) => {
        resolvePreferences = resolve;
      });
      const accessFailure = Object.assign(new Error('membership revoked'), { status: 403 });
      vi.mocked(schoolApi.listOrganizationNotifications)
        .mockResolvedValueOnce({ items: [notification('one')], total: 1, limit: 20, offset: 0 })
        [lateResponse === 'inbox' ? 'mockReturnValueOnce' : 'mockRejectedValueOnce'](
          lateResponse === 'inbox' ? pendingInbox : accessFailure,
        );
      vi.mocked(schoolApi.listOrganizationNotificationPreferences)
        .mockResolvedValueOnce({ items: categories.map((value) => preference(value)) })
        [lateResponse === 'preferences' ? 'mockReturnValueOnce' : 'mockRejectedValueOnce'](
          lateResponse === 'preferences' ? pendingPreferences : accessFailure,
        );
      const { wrapper } = mountView();
      await flushPromises();

      await wrapper.get('[data-test=refresh-notifications]').trigger('click');
      await flushPromises();
      if (lateResponse === 'inbox') {
        resolveInbox({ items: [notification('late')], total: 1, limit: 20, offset: 0 });
      } else {
        resolvePreferences({ items: categories.map((value) => preference(value, true)) });
      }
      await flushPromises();

      expect(wrapper.find('[data-test=notification-one]').exists()).toBe(false);
      expect(wrapper.find('[data-test=notification-late]').exists()).toBe(false);
      expect(wrapper.findAll('.preference-row')).toHaveLength(0);
      expect(wrapper.text()).not.toContain('Notification inbox refreshed.');
      expect(wrapper.get('[role=alert]').text()).toContain('do not have permission');
    },
  );

  it('does not persist or log notification contents in the browser', async () => {
    const localStorage = vi.spyOn(Storage.prototype, 'setItem');
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => undefined);
    const { wrapper } = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain('Training starts at 17:00.');
    expect(localStorage).not.toHaveBeenCalled();
    expect(consoleLog).not.toHaveBeenCalled();
  });
});
