import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PublicCompetitionView from '@/views/PublicCompetitionView.vue';
import PublicFixtureView from '@/views/PublicFixtureView.vue';

const api = vi.hoisted(() => ({ getPublicCompetition: vi.fn(), getPublicFixture: vi.fn() }));
vi.mock('@/services/schoolAdminApi', () => api);

const publicIdentifier = 'org_0123456789abcdef01234567';
const competitionPublicKey = 'cmp_0123456789abcdef01234567';
const fixturePublicIdentifier = 'fix_0123456789abcdef01234567';
const stubs = {
  RouterLink: { template: '<a><slot /></a>' },
  PublicShareLinkButton: { props: ['path'], template: '<button class="share-link" :data-path="path"><slot /></button>' },
};

beforeEach(() => vi.resetAllMocks());

describe('direct public entity views', () => {
  it('renders only the direct opaque competition projection', async () => {
    api.getPublicCompetition.mockResolvedValue({
      public_identifier: publicIdentifier,
      public_key: competitionPublicKey,
      canonical_path: `/community/${publicIdentifier}/competitions/${competitionPublicKey}`,
      name: 'Autumn Cup', tournament_type: 'league', status: 'ongoing', start_date: null, end_date: null,
      team_names: [], standings: [],
      fixtures: [{ public_identifier: fixturePublicIdentifier, team_a_name: 'North XI', team_b_name: 'South XI', match_number: 1, venue: null, scheduled_date: null, fixture_status: 'scheduled', game_status: null, result: null, canonical_path: `/community/${publicIdentifier}/competitions/${competitionPublicKey}/fixtures/${fixturePublicIdentifier}`, public_result_path: null, public_scorecard_path: null, canonical_scorecard_path: null }],
    });
    const wrapper = mount(PublicCompetitionView, { props: { publicIdentifier, competitionPublicKey }, global: { stubs } });
    await flushPromises();
    expect(api.getPublicCompetition).toHaveBeenCalledWith(publicIdentifier, competitionPublicKey);
    expect(wrapper.text()).toContain('Autumn Cup');
    expect(wrapper.text()).toContain('North XI vs South XI');
  });

  it('shows a neutral unavailable state after public access is revoked', async () => {
    api.getPublicFixture.mockRejectedValue({ status: 404 });
    const wrapper = mount(PublicFixtureView, { props: { publicIdentifier, competitionPublicKey, fixturePublicIdentifier }, global: { stubs } });
    await flushPromises();
    expect(wrapper.text()).toContain('Fixture unavailable');
    expect(wrapper.text()).not.toContain('North XI');
  });

  it('requests the result-only endpoint for a result share route', async () => {
    api.getPublicFixture.mockResolvedValue({
      competition_public_key: competitionPublicKey, competition_name: 'Autumn Cup', public_identifier: fixturePublicIdentifier,
      team_a_name: 'North XI', team_b_name: 'South XI', match_number: 1, venue: null, scheduled_date: null,
      fixture_status: 'completed', game_status: 'completed', result: 'North XI won',
      canonical_path: `/community/${publicIdentifier}/competitions/${competitionPublicKey}/fixtures/${fixturePublicIdentifier}`,
      public_result_path: `/community/${publicIdentifier}/competitions/${competitionPublicKey}/results/${fixturePublicIdentifier}`,
      public_scorecard_path: null, canonical_scorecard_path: null,
    });
    const wrapper = mount(PublicFixtureView, { props: { publicIdentifier, competitionPublicKey, fixturePublicIdentifier, resultOnly: true }, global: { stubs } });
    await flushPromises();
    expect(api.getPublicFixture).toHaveBeenCalledWith(publicIdentifier, competitionPublicKey, fixturePublicIdentifier, true);
    expect(wrapper.text()).toContain('North XI won');
  });

  it('offers only the opaque canonical scorecard path for a fixture share', async () => {
    const scorecardPath = `/community/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/sc_0123456789abcdef01234567`;
    api.getPublicFixture.mockResolvedValue({
      competition_public_key: competitionPublicKey, competition_name: 'Autumn Cup', public_identifier: fixturePublicIdentifier,
      team_a_name: 'North XI', team_b_name: 'South XI', match_number: 1, venue: null, scheduled_date: null,
      fixture_status: 'completed', game_status: 'completed', result: 'North XI won',
      canonical_path: `/community/${publicIdentifier}/competitions/${competitionPublicKey}/fixtures/${fixturePublicIdentifier}`,
      public_result_path: null, public_scorecard_path: scorecardPath, canonical_scorecard_path: scorecardPath,
    });
    const wrapper = mount(PublicFixtureView, { props: { publicIdentifier, competitionPublicKey, fixturePublicIdentifier }, global: { stubs } });
    await flushPromises();
    expect(wrapper.findAll('.share-link').map(item => item.attributes('data-path'))).toContain(scorecardPath);
    expect(wrapper.text()).not.toContain('school-scorecards');
  });
});
