import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { reactive } from 'vue';

import TeamSelectionView from '@/views/TeamSelectionView.vue';

const GAME_ID = '00000000-0000-4000-8000-000000000001';
const API = 'http://api.synthetic.test';
const SYNTHETIC_TOKEN = 'synthetic-token-not-a-credential';

const push = vi.fn();
const replace = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { gameId: GAME_ID }, fullPath: `/game/${GAME_ID}/select-xi` }),
  useRouter: () => ({ push, replace }),
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}));

vi.mock('@/utils/api', () => ({ API_BASE: 'http://api.synthetic.test' }));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    token: 'present',
    user: { id: 'synthetic-user', role: 'org_pro' },
    loading: false,
    loadUser: vi.fn(),
    requireRole: () => true,
  }),
}));

function team(prefix: string) {
  return {
    name: `${prefix} Synthetic`,
    players: Array.from({ length: 11 }, (_, i) => ({ id: `${prefix}-${i}`, name: `${prefix} ${i}` })),
  };
}

const gameStore = reactive({
  currentGame: { id: GAME_ID, team_a: team('a'), team_b: team('b') },
  loadGame: vi.fn(async () => undefined),
});
vi.mock('@/stores/gameStore', () => ({ useGameStore: () => gameStore }));

function seedSavedXi() {
  localStorage.setItem(
    `cricksy.xi.${GAME_ID}`,
    JSON.stringify({
      team_a_xi: team('a').players.map((p) => p.id),
      team_b_xi: team('b').players.map((p) => p.id),
      captain_a: 'a-0',
      keeper_a: 'a-1',
      captain_b: 'b-0',
      keeper_b: 'b-1',
    }),
  );
}

async function saveXi() {
  const wrapper = mount(TeamSelectionView);
  await flushPromises();
  await wrapper.get('[data-testid="btn-save-xi"]').trigger('click');
  await flushPromises();
  return wrapper;
}

describe('TeamSelectionView playing XI persistence', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    push.mockReset();
    replace.mockReset();
    fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ ok: true }) }));
    vi.stubGlobal('fetch', fetchMock);
    seedSavedXi();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('sends the stored bearer token with the playing-XI request', async () => {
    localStorage.setItem('cricksy_token', SYNTHETIC_TOKEN);

    await saveXi();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${API}/games/${GAME_ID}/playing-xi`);
    expect(init.method).toBe('POST');
    expect(init.headers).toMatchObject({
      Authorization: `Bearer ${SYNTHETIC_TOKEN}`,
      'Content-Type': 'application/json',
    });
    expect(JSON.parse(String(init.body))).toMatchObject({ captain_a: 'a-0', keeper_b: 'b-1' });
    expect(push).toHaveBeenCalledWith({ name: 'GameScoringView', params: { gameId: GAME_ID } });
  });

  it('omits the Authorization header when no token is stored', async () => {
    await saveXi();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.headers).not.toHaveProperty('Authorization');
  });

  it('surfaces a refused save instead of navigating to scoring', async () => {
    localStorage.setItem('cricksy_token', SYNTHETIC_TOKEN);
    fetchMock.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });

    const wrapper = await saveXi();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('Failed to set XI: 401');
  });
});
