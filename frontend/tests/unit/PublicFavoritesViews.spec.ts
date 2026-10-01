import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

import { useAuthStore } from '@/stores/authStore';
import PublicTeamView from '@/views/PublicTeamView.vue';
import SavedPublicPagesView from '@/views/SavedPublicPagesView.vue';

const api = vi.hoisted(() => ({
  getPublicTeam: vi.fn(), listAllMyPublicFavorites: vi.fn(), listMyPublicFavorites: vi.fn(),
  saveMyPublicFavorite: vi.fn(), removeMyPublicFavorite: vi.fn(),
}));
vi.mock('@/services/schoolAdminApi', () => api);
const stubs = { RouterLink: { template: '<a><slot /></a>' } };
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }

beforeEach(() => { vi.resetAllMocks(); setActivePinia(createPinia()); });

describe('PublicTeamView', () => {
  it('saves and removes an opaque public Team reference', async () => {
    useAuthStore().user = { id: 'staff-a' } as never;
    api.getPublicTeam.mockResolvedValue({ public_identifier: 'team_0123456789abcdef01234567', display_name: 'First XI', aggregate_stats: { published_games: 3 } });
    api.listAllMyPublicFavorites.mockResolvedValue([]);
    api.saveMyPublicFavorite.mockResolvedValue({ id: 'fav-team' });
    const wrapper = mount(PublicTeamView, { props: { publicIdentifier: 'org_0123456789abcdef01234567', teamPublicIdentifier: 'team_0123456789abcdef01234567' }, global: { stubs } });
    await flushPromises();
    expect(wrapper.text()).toContain('Published games3');
    await wrapper.get('.favorite-button').trigger('click'); await flushPromises();
    expect(api.saveMyPublicFavorite).toHaveBeenCalledWith('team', 'team_0123456789abcdef01234567');
    await wrapper.get('.favorite-button').trigger('click'); await flushPromises();
    expect(api.removeMyPublicFavorite).toHaveBeenCalledWith('fav-team');
  });

  it('does not render a stale Team response after route change', async () => {
    let resolve!: (value: object) => void;
    const first = new Promise<object>(done => { resolve = done; });
    api.getPublicTeam.mockImplementation((_org: string, team: string) => team === 'team_aaaaaaaaaaaaaaaaaaaaaaaa' ? first : Promise.resolve({ public_identifier: 'team_bbbbbbbbbbbbbbbbbbbbbbbb', display_name: 'Current XI', aggregate_stats: { published_games: 0 } }));
    const wrapper = mount(PublicTeamView, { props: { publicIdentifier: 'org_0123456789abcdef01234567', teamPublicIdentifier: 'team_aaaaaaaaaaaaaaaaaaaaaaaa' }, global: { stubs } });
    await wrapper.setProps({ teamPublicIdentifier: 'team_bbbbbbbbbbbbbbbbbbbbbbbb' });
    resolve({ public_identifier: 'team_aaaaaaaaaaaaaaaaaaaaaaaa', display_name: 'Stale XI', aggregate_stats: { published_games: 9 } });
    await flushPromises();
    expect(wrapper.text()).toContain('Current XI');
    expect(wrapper.text()).not.toContain('Stale XI');
  });

  it('clears Team saved state on logout and ignores a delayed prior-session favorite response', async () => {
    const pending = deferred<Array<{ id: string; subject_kind: string; public_key: string }>>();
    useAuthStore().user = { id: 'staff-a' } as never;
    api.getPublicTeam.mockResolvedValue({ public_identifier: 'team_0123456789abcdef01234567', display_name: 'First XI', aggregate_stats: { published_games: 3 } });
    api.listAllMyPublicFavorites.mockReturnValue(pending.promise);
    const wrapper = mount(PublicTeamView, { props: { publicIdentifier: 'org_0123456789abcdef01234567', teamPublicIdentifier: 'team_0123456789abcdef01234567' }, global: { stubs } });
    await nextTick();
    useAuthStore().user = null; await nextTick();
    pending.resolve([{ id: 'a-team', subject_kind: 'team', public_key: 'team_0123456789abcdef01234567' }]);
    await flushPromises();
    expect(wrapper.get('.favorite-button').text()).toBe('Save this team');
  });

  it('ignores a delayed Team save after an account switch', async () => {
    const pending = deferred<{ id: string }>();
    useAuthStore().user = { id: 'staff-a' } as never;
    api.getPublicTeam.mockResolvedValue({ public_identifier: 'team_0123456789abcdef01234567', display_name: 'First XI', aggregate_stats: { published_games: 3 } });
    api.listAllMyPublicFavorites.mockResolvedValue([]);
    api.saveMyPublicFavorite.mockReturnValue(pending.promise);
    const wrapper = mount(PublicTeamView, { props: { publicIdentifier: 'org_0123456789abcdef01234567', teamPublicIdentifier: 'team_0123456789abcdef01234567' }, global: { stubs } });
    await flushPromises(); await wrapper.get('.favorite-button').trigger('click');
    useAuthStore().user = { id: 'staff-b' } as never; await nextTick();
    pending.resolve({ id: 'stale-a' }); await flushPromises();
    expect(wrapper.get('.favorite-button').text()).toBe('Save this team');
  });
});

describe('SavedPublicPagesView', () => {
  it('lists only server-resolved saved entries and removes the owner entry', async () => {
    useAuthStore().user = { id: 'staff-a' } as never;
    api.listMyPublicFavorites.mockResolvedValueOnce({ items: Array.from({ length: 20 }, (_, index) => ({ id: `fav-${index}`, subject_kind: 'team', public_key: `team_${index.toString(16).padStart(24, '0')}`, display_name: `Team ${index}`, canonical_path: '/community/org/teams/team', created_at: '2026-10-01T00:00:00Z' })), next_offset: 20 }).mockResolvedValueOnce({ items: [{ id: 'fav-20', subject_kind: 'team', public_key: 'team_ffffffffffffffffffffffff', display_name: 'Team 20', canonical_path: '/community/org/teams/team', created_at: '2026-10-01T00:00:00Z' }], next_offset: null }).mockResolvedValue({ items: [], next_offset: null });
    const wrapper = mount(SavedPublicPagesView, { global: { stubs } }); await flushPromises();
    expect(wrapper.text()).toContain('Team 0');
    const loadMore = wrapper.findAll('button').find(button => button.text() === 'Load more');
    expect(loadMore).toBeDefined();
    await loadMore!.trigger('click'); await flushPromises();
    expect(wrapper.text()).toContain('Team 20');
    const remove = wrapper.findAll('li button')[0];
    await remove.trigger('click'); await flushPromises();
    expect(api.removeMyPublicFavorite).toHaveBeenCalledWith('fav-0');
  });

  it('clears user A saved names before loading user B on the same route', async () => {
    useAuthStore().user = { id: 'staff-a' } as never;
    api.listMyPublicFavorites.mockResolvedValue({ items: [{ id: 'a', subject_kind: 'organization', public_key: 'org_a', display_name: 'User A Club', canonical_path: '/community/org_a', created_at: '2026-10-01T00:00:00Z' }], next_offset: null });
    const wrapper = mount(SavedPublicPagesView, { global: { stubs } }); await flushPromises();
    expect(wrapper.text()).toContain('User A Club');
    api.listMyPublicFavorites.mockResolvedValue({ items: [{ id: 'b', subject_kind: 'team', public_key: 'team_b', display_name: 'User B XI', canonical_path: '/community/org_b/teams/team_b', created_at: '2026-10-01T00:00:00Z' }], next_offset: null });
    useAuthStore().user = { id: 'staff-b' } as never;
    await nextTick();
    expect(wrapper.text()).not.toContain('User A Club');
    await flushPromises();
    expect(wrapper.text()).toContain('User B XI');
  });
});
