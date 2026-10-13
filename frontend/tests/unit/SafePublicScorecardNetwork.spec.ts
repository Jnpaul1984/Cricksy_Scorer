import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';

const scorecardResponse = {
  public_identifier: 'sc_0123456789abcdef01234567',
  organization_type: 'club',
  publication_state: 'published_live',
  status: 'in_progress',
  team_a: { name: 'Synthetic Adult XI', players: [{ name: 'Synthetic Player A' }] },
  team_b: { name: 'Practice Adults', players: [{ name: 'Synthetic Player B' }] },
  match_type: 'limited',
  overs_limit: 20,
  days_limit: null,
  overs_per_day: null,
  toss_winner_team: 'Synthetic Adult XI',
  decision: 'bat',
  batting_team_name: 'Synthetic Adult XI',
  bowling_team_name: 'Practice Adults',
  total_runs: 42,
  total_wickets: 2,
  overs_completed: 7,
  balls_this_over: 3,
  current_inning: 1,
  result: null,
  batting_scorecard: [{ player_name: 'Synthetic Player A', runs: 42 }],
  bowling_scorecard: [{ player_name: 'Synthetic Player B', wickets_taken: 2 }],
};

describe('safe public scorecard network boundary', () => {
  afterEach(() => {
    localStorage.clear();
    window.history.replaceState(null, '', '/');
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it('boots with only the canonical public request, ignoring saved auth and apiBase query overrides', async () => {
    const endpoint = '/api/public/organizations/org_0123456789abcdef01234567/competitions/cmp_0123456789abcdef01234567/scorecards/sc_0123456789abcdef01234567';
    window.history.replaceState(null, '', `/?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`);
    localStorage.setItem('cricksy_token', 'synthetic-overlay-test-token');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => scorecardResponse,
    });
    vi.stubGlobal('fetch', fetchMock);

    const { default: SchoolPublicScorecardView } = await import('@/views/school/SchoolPublicScorecardView.vue');
    const wrapper = mount(SchoolPublicScorecardView, {
      props: {
        overlay: true,
        publicIdentifier: 'org_0123456789abcdef01234567',
        competitionPublicKey: 'cmp_0123456789abcdef01234567',
        scorecardPublicIdentifier: 'sc_0123456789abcdef01234567',
        gameId: 'must-never-be-used',
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain('42/2');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const url = new URL(requestedUrl);
    expect(url.pathname).toBe(endpoint);
    expect(url.origin).toBe(window.location.origin);
    expect(requestedUrl).not.toContain('unsafe.example.invalid');
    const headers = new Headers(requestInit.headers);
    expect(headers.has('Authorization')).toBe(false);
    expect(requestedUrl).not.toMatch(/\/games\/|\/snapshots|\/deliveries|socket\.io|private/i);
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([requestedUrl]);
    expect(wrapper.text()).not.toContain('Synthetic Player A');
    expect(wrapper.text()).not.toContain('Synthetic Player B');
    wrapper.unmount();
  });
});
