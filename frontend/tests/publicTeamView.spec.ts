import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const { getPublicTeam } = vi.hoisted(() => ({ getPublicTeam: vi.fn() }));
vi.mock('@/services/schoolAdminApi', () => ({ getPublicTeam }));
import PublicTeamView from '../src/views/PublicTeamView.vue';

const mountView = (props = { publicIdentifier: 'org_a', teamPublicIdentifier: 'team_a' }) =>
  mount(PublicTeamView, { props, global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } });

describe('PublicTeamView', () => {
  it('renders aggregate-only public data and treats a private route as unavailable', async () => {
    getPublicTeam.mockResolvedValueOnce({ public_identifier: 'team_a', display_name: 'First XI', aggregate_stats: { published_games: 3 } });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain('First XI');
    expect(wrapper.text()).toContain('Published games');
    expect(wrapper.text()).not.toMatch(/alice|player profile/i);
    getPublicTeam.mockRejectedValueOnce(new Error('404'));
    await wrapper.setProps({ teamPublicIdentifier: 'team_private' });
    await flushPromises();
    expect(wrapper.text()).toContain('Team page not found');
  });

  it('ignores a stale response after a public route change', async () => {
    let resolveFirst: (value: unknown) => void = () => undefined;
    getPublicTeam.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }));
    getPublicTeam.mockResolvedValueOnce({ public_identifier: 'team_new', display_name: 'New XI', aggregate_stats: { published_games: 1 } });
    const wrapper = mountView();
    await wrapper.setProps({ teamPublicIdentifier: 'team_new' });
    await flushPromises();
    resolveFirst({ public_identifier: 'team_a', display_name: 'Stale XI', aggregate_stats: { published_games: 99 } });
    await flushPromises();
    expect(wrapper.text()).toContain('New XI');
    expect(wrapper.text()).not.toContain('Stale XI');
  });
});
