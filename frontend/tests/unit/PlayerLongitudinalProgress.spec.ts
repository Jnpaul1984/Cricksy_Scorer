import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

import PlayerLongitudinalProgress from '@/components/PlayerLongitudinalProgress.vue';
import {
  getPlayerLongitudinalProgress,
  type PlayerLongitudinalProgressResponse,
} from '@/services/coachPlusVideoService';

vi.mock('@/services/coachPlusVideoService', () => ({
  getPlayerLongitudinalProgress: vi.fn(),
}));

async function flushAsync() {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
}

function response(
  playerPresentation: PlayerLongitudinalProgressResponse['player_presentation'],
  sessionCount = 1,
): PlayerLongitudinalProgressResponse {
  return {
    analysis_version: 'player_longitudinal_progress.v1',
    generated_at: null,
    player_id: 'player-1',
    discipline_filter: 'batting',
    session_count: sessionCount,
    series_count: 1,
    summary: {
      improving: 0,
      regressing: 0,
      stable: 0,
      mixed: 0,
      insufficient_data: 1,
      non_comparable: 0,
    },
    sessions_considered: [],
    series: [],
    player_presentation: playerPresentation,
  };
}

describe('PlayerLongitudinalProgress', () => {
  beforeEach(() => vi.resetAllMocks());

  it('shows the backend player wording instead of a technical table for one session', async () => {
    vi.mocked(getPlayerLongitudinalProgress).mockResolvedValue(
      response({
        state: 'Not enough sessions yet',
        summary: 'Complete another comparable session to start tracking progress.',
        items: [],
      }),
    );

    const presentation = {
      state: 'Baseline established',
      summary:
        "This is the player's first recorded assessment. Future comparable sessions will show what improved, stayed consistent, or needs more work.",
      items: [],
    };

    const wrapper = mount(PlayerLongitudinalProgress, {
      props: { playerId: 'player-1', discipline: 'batting', visible: true, presentation },
    });
    await flushAsync();

    expect(wrapper.text()).toContain('Baseline established');
    expect(wrapper.text()).toContain('first recorded assessment');
    expect(wrapper.text()).not.toContain('Not enough sessions yet');
    expect(wrapper.text()).not.toContain('History');
    expect(wrapper.find('table').exists()).toBe(false);
    expect(getPlayerLongitudinalProgress).toHaveBeenCalledTimes(1);
  });

  it('prefers real endpoint history over embedded baseline wording for a returning player', async () => {
    vi.mocked(getPlayerLongitudinalProgress).mockResolvedValue(
      response(
        {
          state: 'Improving',
          summary: 'Comparable session evidence is moving in the intended direction.',
          items: [
            {
              metric_id: 'batting_downswing_head_stability_score',
              title: 'Head stability during downswing',
              discipline: 'Batting',
              state: 'Improving',
              baseline: '61%',
              latest: '72%',
              comparable_session_count: 2,
              limitations: [],
            },
          ],
        },
        2,
      ),
    );

    const wrapper = mount(PlayerLongitudinalProgress, {
      props: {
        playerId: 'player-1',
        discipline: 'batting',
        visible: true,
        presentation: {
          state: 'Baseline established',
          summary: "This is the player's first recorded assessment.",
          items: [],
        },
      },
    });
    await flushAsync();

    const text = wrapper.text();
    expect(text).toContain('Improving');
    expect(text).toContain('Head stability during downswing');
    expect(text).not.toContain('Baseline established');
    expect(text).not.toContain('first recorded assessment');
  });

  it('shows readable deterministic progress once two sessions are comparable', async () => {
    vi.mocked(getPlayerLongitudinalProgress).mockResolvedValue(
      response(
        {
          state: 'Improving',
          summary: 'Comparable session evidence is moving in the intended direction.',
          items: [
            {
              metric_id: 'batting_downswing_head_stability_score',
              title: 'Head stability during downswing',
              discipline: 'Batting',
              state: 'Improving',
              baseline: '61%',
              latest: '72%',
              comparable_session_count: 2,
              limitations: [],
            },
          ],
        },
        2,
      ),
    );

    const wrapper = mount(PlayerLongitudinalProgress, {
      props: { playerId: 'player-1', discipline: 'batting', visible: true },
    });
    await flushAsync();

    const text = wrapper.text();
    expect(text).toContain('Improving');
    expect(text).toContain('Head stability during downswing');
    expect(text).toContain('61%');
    expect(text).toContain('72%');
    expect(text).not.toContain('batting_downswing_head_stability_score');
  });
});
