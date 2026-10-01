import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

const api = vi.hoisted(() => ({
  getSchoolTeam: vi.fn().mockResolvedValue({ id: 'team-1', name: 'First XI', status: 'active' }),
  listTeamRoster: vi.fn().mockResolvedValue([]), listSchoolPlayers: vi.fn().mockResolvedValue([]),
  getOrganizationCommunitySettings: vi.fn().mockResolvedValue({ public_identifier: 'org_public' }),
  getTeamPublicPublication: vi.fn().mockResolvedValue({ public_identifier: 'team_public', publication_state: 'unpublished', publication_version: 1 }),
  setTeamPublicPublication: vi.fn(),
}));
vi.mock('@/services/schoolAdminApi', () => ({ ...api, addTeamRosterPlayer: vi.fn(), deactivateTeamRosterPlayer: vi.fn(), setTeamRosterPlayerStatus: vi.fn() }));
vi.mock('@/composables/useSchoolContext', () => ({ useSchoolContext: () => ({ organizationId: computed(() => 'org-1'), organizationBasePath: computed(() => '/schools'), terminology: computed(() => ({ kindLabel: 'School' })), canManageTeamRoster: computed(() => true), canManageCommunity: computed(() => true) }) }));
vi.mock('@/router', () => ({ default: { resolve: vi.fn(() => ({ href: '#/base/community/org_public/teams/team_public' })) } }));
vi.mock('vue-router', () => ({ RouterLink: { template: '<a><slot /></a>' }, useRoute: () => ({ params: { teamId: 'team-1' } }) }));
import View from '../src/views/school/SchoolTeamRosterView.vue';

describe('SchoolTeamRosterView publication controls', () => {
  it('owner publishes, copies router-resolved hash/base link, then revokes', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const wrapper = mount(View);
    await flushPromises();
    api.setTeamPublicPublication.mockResolvedValueOnce({ public_identifier: 'team_public', publication_state: 'published', publication_version: 2 });
    await wrapper.get('[data-test="team-publication-controls"] button').trigger('click');
    await flushPromises();
    expect(api.setTeamPublicPublication).toHaveBeenCalledWith('org-1', 'team-1', true);
    expect((wrapper.get('[aria-label="Public Team link"]').element as HTMLInputElement).value).toContain('#/base/community/org_public/teams/team_public');
    await wrapper.get('button.compact').trigger('click');
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('#/base/community/org_public/teams/team_public'));
    api.setTeamPublicPublication.mockResolvedValueOnce({ public_identifier: 'team_public', publication_state: 'unpublished', publication_version: 3 });
    await wrapper.get('[data-test="team-publication-controls"] button').trigger('click');
    await flushPromises();
    expect(api.setTeamPublicPublication).toHaveBeenLastCalledWith('org-1', 'team-1', false);
  });
});
