import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, nextTick, ref } from 'vue';

import { organizationBasePath, organizationTerminology } from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import router from '@/router';
import type {
  FreeOrganizationType,
  OrganizationCommunitySettings,
  PublicOrganizationCommunity,
} from '@/types/schoolAdmin';
import OrganizationCommunityView from '@/views/OrganizationCommunityView.vue';
import OrganizationCommunitySettingsView from '@/views/school/OrganizationCommunitySettingsView.vue';

const api = vi.hoisted(() => ({
  getOrganizationCommunitySettings: vi.fn(),
  publishOrganizationCommunity: vi.fn(),
  unpublishOrganizationCommunity: vi.fn(),
  updateOrganizationCommunityBranding: vi.fn(),
  setOrganizationCompetitionCommunityPublication: vi.fn(),
  getOrganizationSponsorReporting: vi.fn(),
  getPublicOrganizationCommunity: vi.fn(),
}));

vi.mock('@/services/schoolAdminApi', () => api);

const routerStubs = {
  RouterLink: { template: '<a><slot /></a>' },
};

function settings(organizationId: string, name = 'Community Cup'): OrganizationCommunitySettings {
  return {
    organization_id: organizationId,
    public_identifier: 'org_0123456789abcdef01234567',
    publication_state: 'unpublished',
    logo_url: null,
    logo_alt_text: null,
    branding_version: 1,
    branding_updated_at: null,
    competitions: [
      {
        competition_id: `${organizationId}-competition`,
        competition_name: name,
        publication_state: 'unpublished',
        publication_version: 1,
        published_at: null,
        unpublished_at: null,
        updated_by_user_id: null,
      },
    ],
  };
}

function community(organizationType: FreeOrganizationType): PublicOrganizationCommunity {
  return {
    public_identifier: 'org_0123456789abcdef01234567',
    display_name: organizationType === 'school' ? 'North School' : 'North Club',
    organization_type: organizationType,
    branding: {
      logo_url: null,
      logo_alt_text: `North ${organizationType} logo`,
      fallback_text: 'N',
    },
    competitions: [
      {
        name: 'Community Cup',
        tournament_type: 'league',
        start_date: '2026-09-30T12:00:00Z',
        end_date: null,
        status: 'ongoing',
        team_names: ['First XI', 'Second XI'],
        fixtures: [
          {
            team_a_name: 'First XI',
            team_b_name: 'Second XI',
            match_number: 1,
            venue: 'Main Ground',
            scheduled_date: '2026-10-01T12:00:00Z',
            fixture_status: 'completed',
            game_status: 'completed',
            result: 'First XI won by 8 runs',
            public_scorecard_path: '/school-scorecards/public-game',
          },
        ],
        standings: [
          {
            team_name: 'First XI',
            matches_played: 1,
            matches_won: 1,
            matches_lost: 0,
            matches_drawn: 0,
            points: 2,
          },
        ],
      },
    ],
  };
}

function context(
  organizationId = ref('school-a'),
  organizationType = ref<FreeOrganizationType>('school'),
  canManageCommunity = ref(true),
): SchoolContext {
  const allowed = computed(() => true);
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: ref(null),
    membership: ref(null),
    entitlement: ref(null),
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
    canViewAnnouncements: allowed,
    canManageAnnouncements: allowed,
    canManageCommunity: computed(() => canManageCommunity.value),
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(resolver => {
    resolve = resolver;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.resetAllMocks();
  api.getOrganizationSponsorReporting.mockResolvedValue(null);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('OrganizationCommunityView', () => {
  it.each(['school', 'club'] as const)(
    'renders one accessible responsive %s community component with public cricket only',
    async organizationType => {
      api.getPublicOrganizationCommunity.mockResolvedValue(community(organizationType));
      const wrapper = mount(OrganizationCommunityView, {
        props: { publicIdentifier: 'org_0123456789abcdef01234567' },
        global: { stubs: routerStubs },
      });
      await flushPromises();

      expect(wrapper.get('h1').text()).toBe(
        organizationType === 'school' ? 'North School' : 'North Club',
      );
      expect(wrapper.text()).toContain(`${organizationType === 'school' ? 'School' : 'Club'} cricket community`);
      expect(wrapper.text()).toContain('First XI won by 8 runs');
      expect(wrapper.text()).toContain('View published scorecard');
      expect(wrapper.find('table').exists()).toBe(true);
      expect(wrapper.text().toLowerCase()).not.toContain('roster');
      expect(wrapper.text().toLowerCase()).not.toContain('player profile');
      expect(wrapper.get('main').classes()).toContain('community-page');
    },
  );

  it('uses the same anonymous router component and a safe not-found state', async () => {
    api.getPublicOrganizationCommunity.mockRejectedValue(Object.assign(new Error('missing'), { status: 404 }));
    const wrapper = mount(OrganizationCommunityView, {
      props: { publicIdentifier: 'org_000000000000000000000000' },
      global: { stubs: routerStubs },
    });
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('Community page not found');
    expect(router.resolve('/community/org_0123456789abcdef01234567').name).toBe(
      'organization-community',
    );
  });
});

describe('OrganizationCommunitySettingsView', () => {
  it('shows only the current organization\'s aggregate report and its UTC date window', async () => {
    const organizationId = ref('school-a');
    api.getOrganizationCommunitySettings
      .mockResolvedValueOnce(settings('school-a'))
      .mockResolvedValueOnce(settings('school-b'));
    api.getOrganizationSponsorReporting
      .mockResolvedValueOnce({
        start_date: '2026-09-01',
        end_date: '2026-09-30',
        buckets: [{ date: '2026-09-30', displays: 7, clicks: 2 }],
      })
      .mockResolvedValueOnce(null);
    const wrapper = mount(OrganizationCommunitySettingsView, {
      global: {
        provide: { [schoolContextKey as symbol]: context(organizationId) },
        stubs: routerStubs,
      },
    });
    await flushPromises();

    expect(api.getOrganizationSponsorReporting).toHaveBeenCalledWith('school-a');
    expect(wrapper.get('[data-test="sponsor-aggregate-report"]').text()).toContain(
      'UTC reporting window: 2026-09-01 to 2026-09-30',
    );
    expect(wrapper.text()).toContain('7 displays, 2 clicks');

    organizationId.value = 'school-b';
    await nextTick();
    await flushPromises();
    expect(api.getOrganizationSponsorReporting).toHaveBeenLastCalledWith('school-b');
    expect(wrapper.get('[data-test="sponsor-aggregate-report"]').text()).toContain(
      'Aggregate reporting is not enabled for this organization.',
    );
    expect(wrapper.text()).not.toContain('7 displays, 2 clicks');
  });

  it('copies the configured router href with hash mode and deployment base intact', async () => {
    const configuredHref = '/cricksy/#/community/org_0123456789abcdef01234567';
    const resolve = vi.spyOn(router, 'resolve').mockReturnValue({
      href: configuredHref,
    } as ReturnType<typeof router.resolve>);
    api.getOrganizationCommunitySettings.mockResolvedValue({
      ...settings('school-a'),
      publication_state: 'published',
    });
    const wrapper = mount(OrganizationCommunitySettingsView, {
      global: {
        provide: { [schoolContextKey as symbol]: context() },
        stubs: routerStubs,
      },
    });
    await flushPromises();

    const absoluteUrl = new URL(configuredHref, window.location.origin).toString();
    expect(wrapper.get('#community-link').attributes('value')).toBe(absoluteUrl);
    expect(resolve).toHaveBeenCalledWith({
      name: 'organization-community',
      params: { publicIdentifier: 'org_0123456789abcdef01234567' },
    });
    await wrapper.get('.share-row button').trigger('click');
    await flushPromises();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(absoluteUrl);
  });

  it('shows enabled publication, branding, link, and competition controls only to managers', async () => {
    api.getOrganizationCommunitySettings.mockResolvedValue(settings('school-a'));
    api.publishOrganizationCommunity.mockResolvedValue({});
    const wrapper = mount(OrganizationCommunitySettingsView, {
      global: {
        provide: { [schoolContextKey as symbol]: context() },
        stubs: routerStubs,
      },
    });
    await flushPromises();
    expect(wrapper.text()).toContain('Publish homepage');
    expect(wrapper.text()).toContain('Save logo');
    expect(wrapper.text()).toContain('Community Cup');
    await wrapper.get('button').trigger('click');
    await flushPromises();
    expect(api.publishOrganizationCommunity).toHaveBeenCalledWith('school-a');

    const readOnlyContext = context(ref('school-a'), ref('school'), ref(false));
    const readOnly = mount(OrganizationCommunitySettingsView, {
      global: {
        provide: { [schoolContextKey as symbol]: readOnlyContext },
        stubs: routerStubs,
      },
    });
    await flushPromises();
    expect(readOnly.text()).toContain('Only a current Owner or Admin');
    expect(readOnly.text()).not.toContain('Publish homepage');
    expect(readOnly.text()).not.toContain('Save logo');
  });

  it.each([
    ['school', 'school-a', 'club', 'club-b'],
    ['club', 'club-a', 'school', 'school-b'],
    ['school', 'school-a', 'school', 'school-b'],
    ['club', 'club-a', 'club', 'club-b'],
  ] as const)(
    'suppresses a stale %s %s response after switching to %s %s',
    async (fromType, fromId, toType, toId) => {
      const organizationId = ref(fromId);
      const organizationType = ref<FreeOrganizationType>(fromType);
      const first = deferred<OrganizationCommunitySettings>();
      const second = deferred<OrganizationCommunitySettings>();
      api.getOrganizationCommunitySettings
        .mockImplementationOnce(() => first.promise)
        .mockImplementationOnce(() => second.promise);
      const wrapper = mount(OrganizationCommunitySettingsView, {
        global: {
          provide: {
            [schoolContextKey as symbol]: context(organizationId, organizationType),
          },
          stubs: routerStubs,
        },
      });
      organizationId.value = toId;
      organizationType.value = toType;
      await nextTick();
      second.resolve(settings(toId, 'Current Cup'));
      await flushPromises();
      first.resolve(settings(fromId, 'Stale Cup'));
      await flushPromises();

      expect(wrapper.text()).toContain('Current Cup');
      expect(wrapper.text()).not.toContain('Stale Cup');
      expect(wrapper.get('input[readonly]').attributes('value')).toContain(
        'org_0123456789abcdef01234567',
      );
    },
  );

  it.each(
    (
      [
        ['school', 'school-a', 'club', 'club-b'],
        ['club', 'club-a', 'school', 'school-b'],
        ['school', 'school-a', 'school', 'school-b'],
        ['club', 'club-a', 'club', 'club-b'],
      ] as const
    ).flatMap(([fromType, fromId, toType, toId]) =>
      (['publication', 'branding', 'competition'] as const).map(
        (mutation) => [mutation, fromType, fromId, toType, toId] as const,
      ),
    ),
  )(
    'clears stale %s saving state after switching from %s %s to %s %s',
    async (mutation, fromType, fromId, toType, toId) => {
      const organizationId = ref(fromId);
      const organizationType = ref<FreeOrganizationType>(fromType);
      const inFlight = deferred<unknown>();
      api.getOrganizationCommunitySettings
        .mockResolvedValueOnce(settings(fromId, 'Stale Cup'))
        .mockResolvedValueOnce(settings(toId, 'Current Cup'));
      api.publishOrganizationCommunity.mockReturnValueOnce(inFlight.promise);
      api.updateOrganizationCommunityBranding.mockReturnValueOnce(inFlight.promise);
      api.setOrganizationCompetitionCommunityPublication.mockReturnValueOnce(inFlight.promise);

      const wrapper = mount(OrganizationCommunitySettingsView, {
        global: {
          provide: {
            [schoolContextKey as symbol]: context(organizationId, organizationType),
          },
          stubs: routerStubs,
        },
      });
      await flushPromises();

      if (mutation === 'publication') {
        await wrapper.get('[data-test="community-homepage-toggle"]').trigger('click');
      } else if (mutation === 'branding') {
        await wrapper.get('#community-logo-url').setValue('https://cdn.example.com/logo.png');
        await wrapper.get('#community-logo-alt').setValue('Organization crest');
        await wrapper.get('[data-test="community-branding-form"]').trigger('submit');
      } else {
        await wrapper.get('[data-test="community-competition-toggle"]').trigger('click');
      }
      expect(
        wrapper.get('[data-test="community-homepage-toggle"]').attributes('disabled'),
      ).toBeDefined();

      organizationId.value = toId;
      organizationType.value = toType;
      await nextTick();
      await flushPromises();

      expect(wrapper.text()).toContain('Current Cup');
      expect(wrapper.text()).not.toContain('Stale Cup');
      expect(
        wrapper.get('[data-test="community-homepage-toggle"]').attributes('disabled'),
      ).toBeUndefined();
      expect(
        wrapper.get('[data-test="community-branding-form"] button').attributes('disabled'),
      ).toBeUndefined();
      expect(
        wrapper.get('[data-test="community-competition-toggle"]').attributes('disabled'),
      ).toBeUndefined();

      inFlight.resolve({});
      await flushPromises();
      expect(wrapper.text()).toContain('Current Cup');
      expect(
        wrapper.get('[data-test="community-homepage-toggle"]').attributes('disabled'),
      ).toBeUndefined();
      expect(api.getOrganizationCommunitySettings).toHaveBeenCalledTimes(2);
    },
  );
});
