import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { FreeOrganizationType, SchoolMembershipRole } from '@/types/schoolAdmin';
import OrganizationEventsView from '@/views/school/OrganizationEventsView.vue';

vi.mock('@/services/schoolAdminApi');

function context(
  organizationType: FreeOrganizationType,
  role: SchoolMembershipRole,
): SchoolContext {
  const organizationId = `${organizationType}-a`;
  const canManage = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId),
    organizationType: computed(() => organizationType),
    organizationBasePath: computed(() => organizationBasePath(organizationType)),
    terminology: computed(() => organizationTerminology(organizationType)),
    organization: ref(null),
    membership: ref(null),
    entitlement: ref(null),
    canManageTeams: canManage,
    canManageRosterMetadata: canManage,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: canManage,
    canImport: canManage,
    canCreateSchoolMatch: computed(() => role !== 'viewer'),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: canManage,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => role !== 'viewer'),
    canPublishScorecards: computed(() => role !== 'viewer'),
    canViewEvents: computed(() => true),
    canManageEvents: canManage,
  };
}

function mountView(organizationType: FreeOrganizationType, role: SchoolMembershipRole) {
  return mount(OrganizationEventsView, {
    global: {
      provide: { [schoolContextKey as symbol]: context(organizationType, role) },
    },
  });
}

describe('shared organization events view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'fixture',
          source_id: 'fixture-a',
          title: 'First XI vs Second XI',
          start_at: '2099-04-01T14:00:00Z',
          end_at: null,
          location: 'Main Ground',
          status: 'scheduled',
          event_type: null,
          participant_scope: null,
          team_ids: ['team-a', 'team-b'],
          game_id: null,
          competition_id: 'competition-a',
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([]);
  });

  it('creates a Club event through the shared organization API and keeps fixtures read-only', async () => {
    vi.mocked(schoolApi.createOrganizationEvent).mockResolvedValue({} as never);
    const wrapper = mountView('club', 'owner');
    await flushPromises();

    expect(wrapper.text()).toContain('Shared Club calendar');
    expect(wrapper.text()).toContain('First XI vs Second XI');
    expect(wrapper.text()).toContain('Cricket fixture');
    expect(wrapper.findAll('button').map((button) => button.text())).not.toContain('Edit');

    await wrapper.get('[data-test="event-title"]').setValue('Club training');
    await wrapper.get('[data-test="event-location"]').setValue('Practice Nets');
    await wrapper.get('[data-test="event-start"]').setValue('2099-05-01T10:30');
    await wrapper.get('[data-test="save-event"]').trigger('submit');
    await flushPromises();

    expect(schoolApi.createOrganizationEvent).toHaveBeenCalledWith(
      'club-a',
      expect.objectContaining({
        event_type: 'training',
        title: 'Club training',
        location: 'Practice Nets',
        participant_scope: 'organization',
        team_ids: [],
        roster_membership_ids: [],
      }),
    );
  });

  it.each(['scorer', 'viewer'] as const)('keeps %s event access read-only', async (role) => {
    const wrapper = mountView('school', role);
    await flushPromises();
    expect(wrapper.text()).toContain('Shared School calendar');
    expect(wrapper.find('[data-test="event-form"]').exists()).toBe(false);
    expect(schoolApi.getOrganizationCalendar).toHaveBeenCalledWith('school-a', {
      includeCancelled: true,
      limit: 100,
    });
  });
});
