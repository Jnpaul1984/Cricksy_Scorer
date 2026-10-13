import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';

const scorecardResponse = {
  public_identifier: 'sc_0123456789abcdef01234567',
  youtube_video_id: 'AbCdEf123_-',
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
    (window as any).app?.unmount?.();
    const mount = document.getElementById('app') as (HTMLElement & { __vue_app__?: unknown }) | null;
    if (mount) delete mount.__vue_app__;
    delete (window as any).app;
    document.body.innerHTML = '';
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

  it.each([
    ['query', (path: string) => `${path}?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`],
    ['hash', (path: string) => `${path}#/?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`],
  ])('isolates the real app startup from saved auth and hostile %s apiBase overrides', async (_overrideType, makeUrl) => {
    const publicIdentifier = 'org_0123456789abcdef01234567';
    const competitionPublicKey = 'cmp_0123456789abcdef01234567';
    const scorecardPublicIdentifier = 'sc_0123456789abcdef01234567';
    const endpoint = `/api/public/organizations/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${scorecardPublicIdentifier}`;
    const overlayPath = `/community/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${scorecardPublicIdentifier}/overlay`;
    window.history.replaceState(null, '', makeUrl(overlayPath));
    localStorage.setItem('cricksy_token', 'synthetic-overlay-test-token');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => scorecardResponse,
    });
    const webSocketMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', webSocketMock);
    document.body.innerHTML = '<div id="app"></div>';

    await import('@/main');
    await vi.waitFor(() => {
      expect(document.querySelector('.app--obs-overlay')).not.toBeNull();
    });
    await flushPromises();

    expect(document.querySelector('.app-header')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const url = new URL(requestedUrl);
    expect(url.pathname).toBe(endpoint);
    expect(url.origin).toBe(window.location.origin);
    expect(requestedUrl).not.toContain('unsafe.example.invalid');
    expect(new Headers(requestInit.headers).has('Authorization')).toBe(false);
    expect(requestedUrl).not.toMatch(/\/games\/|\/snapshots|\/deliveries|\/api\/ai-usage|socket\.io|private/i);
    expect(webSocketMock).not.toHaveBeenCalled();

    (window as any).app?.unmount?.();
    document.body.innerHTML = '';
    delete (window as any).app;
  });

  it('continues mounting the regular app shell after normal initial navigation', async () => {
    window.history.replaceState(null, '', '/help');
    vi.stubGlobal('fetch', vi.fn());
    document.body.innerHTML = '<div id="app"></div>';

    await import('@/main');
    await vi.waitFor(() => {
      expect(document.querySelector('.app-header')).not.toBeNull();
    });
    await flushPromises();

    expect(document.querySelector('.app--obs-overlay')).toBeNull();
    expect(document.querySelector('.app-footer')).not.toBeNull();

  });

  it('keeps the canonical scorecard request no-auth and delays the provider iframe until activation', async () => {
    const publicIdentifier = 'org_0123456789abcdef01234567';
    const competitionPublicKey = 'cmp_0123456789abcdef01234567';
    const scorecardPublicIdentifier = 'sc_0123456789abcdef01234567';
    const endpoint =
      `/api/public/organizations/${publicIdentifier}/competitions/${competitionPublicKey}` +
      `/scorecards/${scorecardPublicIdentifier}`;
    const scorecardPath =
      `/community/${publicIdentifier}/competitions/${competitionPublicKey}` +
      `/scorecards/${scorecardPublicIdentifier}`;
    window.history.replaceState(
      null,
      '',
      `${scorecardPath}?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`,
    );
    localStorage.setItem('cricksy_token', 'synthetic-scorecard-test-token');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => scorecardResponse,
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', vi.fn());
    document.body.innerHTML = '<div id="app"></div>';

    await import('@/main');
    await vi.waitFor(() => {
      expect(document.querySelector('.youtube-player')).not.toBeNull();
    });
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new URL(requestedUrl).pathname).toBe(endpoint);
    expect(requestedUrl).not.toContain('unsafe.example.invalid');
    expect(new Headers(requestInit.headers).has('Authorization')).toBe(false);
    expect(document.querySelector('iframe')).toBeNull();
    expect(
      document.querySelector('a[href="https://www.youtube.com/watch?v=AbCdEf123_-"]')
        ?.getAttribute('rel'),
    ).toBe('noopener noreferrer');

    (document.querySelector('button[aria-describedby="youtube-player-help"]') as HTMLButtonElement)
      .click();
    await flushPromises();
    const iframe = document.querySelector('iframe');
    expect(iframe?.getAttribute('src')).toBe(
      'https://www.youtube-nocookie.com/embed/AbCdEf123_-',
    );
    expect(iframe?.getAttribute('allow')).not.toContain('autoplay');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const router = (window as any).app.config.globalProperties.$router;
    await router.push({
      name: 'public-competition-scorecard',
      params: {
        publicIdentifier,
        competitionPublicKey,
        scorecardPublicIdentifier: 'sc_1123456789abcdef01234567',
      },
    });
    await flushPromises();
    expect(document.querySelector('iframe')).toBeNull();

    (window as any).app?.unmount?.();
    document.body.innerHTML = '';
    delete (window as any).app;
  });

  it('clears the activated player and watch link when revalidation removes the association', async () => {
    const publicIdentifier = 'org_0123456789abcdef01234567';
    const competitionPublicKey = 'cmp_0123456789abcdef01234567';
    const scorecardPublicIdentifier = 'sc_0123456789abcdef01234567';
    window.history.replaceState(
      null,
      '',
      `/community/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${scorecardPublicIdentifier}`,
    );
    const response = (body: unknown) => ({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => body,
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(scorecardResponse))
      .mockResolvedValueOnce(response({ ...scorecardResponse, youtube_video_id: null }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', vi.fn());
    document.body.innerHTML = '<div id="app"></div>';

    await import('@/main');
    await vi.waitFor(() => expect(document.querySelector('.youtube-player')).not.toBeNull());
    (document.querySelector('button[aria-describedby="youtube-player-help"]') as HTMLButtonElement)
      .click();
    await flushPromises();
    expect(document.querySelector('iframe')).not.toBeNull();

    document.dispatchEvent(new Event('visibilitychange'));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    await flushPromises();
    expect(document.querySelector('iframe')).toBeNull();
    expect(
      document.querySelector('a[href="https://www.youtube.com/watch?v=AbCdEf123_-"]'),
    ).toBeNull();

    (window as any).app?.unmount?.();
    document.body.innerHTML = '';
    delete (window as any).app;
  });

  it('does not restore a previous-match video when its delayed response arrives after navigation', async () => {
    const publicIdentifier = 'org_0123456789abcdef01234567';
    const competitionPublicKey = 'cmp_0123456789abcdef01234567';
    const firstScorecard = 'sc_0123456789abcdef01234567';
    const nextScorecard = 'sc_1123456789abcdef01234567';
    window.history.replaceState(
      null,
      '',
      `/community/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${firstScorecard}`,
    );
    localStorage.setItem('cricksy_token', 'synthetic-scorecard-race-token');
    let resolveFirstRequest!: (value: unknown) => void;
    const firstRequest = new Promise((resolve) => {
      resolveFirstRequest = resolve;
    });
    const response = (body: unknown) => ({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => body,
    });
    const fetchMock = vi.fn()
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValueOnce(response({ ...scorecardResponse, youtube_video_id: null }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', vi.fn());
    document.body.innerHTML = '<div id="app"></div>';

    await import('@/main');
    await flushPromises();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const router = (window as any).app.config.globalProperties.$router;
    await router.push({
      name: 'public-competition-scorecard',
      params: {
        publicIdentifier,
        competitionPublicKey,
        scorecardPublicIdentifier: nextScorecard,
      },
    });
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    await flushPromises();
    expect(document.querySelector('.youtube-player')).toBeNull();

    resolveFirstRequest(response(scorecardResponse));
    await flushPromises();
    expect(document.querySelector('.youtube-player')).toBeNull();

    (window as any).app?.unmount?.();
    document.body.innerHTML = '';
    delete (window as any).app;
  });
});
