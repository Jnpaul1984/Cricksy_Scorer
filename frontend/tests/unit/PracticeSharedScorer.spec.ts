import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import PracticeSharedScorer from '@/components/scoring/PracticeSharedScorer.vue';

const props = {
  status: 'in_progress', totalRuns: 12, totalWickets: 1, overs: '2.1', inning: 1, target: null,
  strikerName: 'Alex Batter', nonStrikerName: 'Sam Batter', bowlerName: 'Jordan Bowler', canScore: true,
  needsNextOver: false, loading: false, publicationState: 'private' as const, canPublish: true,
  publicHref: '/practice-scorecards/practice-1', fieldZone: null,
};

describe('PracticeSharedScorer', () => {
  it('uses the broadcast scorer frame and the shared shot map instead of a separate shot-location card', () => {
    const wrapper = mount(PracticeSharedScorer, { props });
    expect(wrapper.find('[data-testid="broadcast-scorer-frame"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('LAST 6');
    expect(wrapper.text()).not.toContain('Select the field section where the ball was hit');
    expect(wrapper.find('[aria-label="Shot map"]').exists()).toBe(true);
  });

  it('keeps a selected field zone in the private delivery event only for legal deliveries', async () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, fieldZone: 6 } });
    await wrapper.get('.btn-score-4').trigger('click');
    await wrapper.get('.btn-submit').trigger('click');
    expect(wrapper.emitted('delivery')?.[0]).toEqual([{ runs: 4, extra: null, isWicket: false, dismissal: 'bowled', dismissed: 'striker', fieldZone: 6 }]);
    await wrapper.get('.btn-extra-wd').trigger('click');
    await wrapper.get('.btn-score-1').trigger('click');
    await wrapper.get('.btn-submit').trigger('click');
    expect(wrapper.emitted('delivery')?.[1]?.[0]).toMatchObject({ extra: 'wd', fieldZone: null });
  });

  it('shows publication as an explicit practice action while private remains the default', () => {
    const wrapper = mount(PracticeSharedScorer, { props });
    expect(wrapper.text()).toContain('Private by default');
    expect(wrapper.text()).toContain('Publish practice scorecard');
  });

  it('preserves selected runs and extras when a wicket is recorded', async () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, fieldZone: 3 } });
    await wrapper.get('.btn-extra-nb').trigger('click');
    await wrapper.get('.btn-score-4').trigger('click');
    await wrapper.get('[data-testid="delivery-wicket"]').setValue(true);
    await wrapper.get('.btn-submit').trigger('click');
    expect(wrapper.emitted('delivery')?.[0]).toEqual([{ runs: 4, extra: 'nb', isWicket: true, dismissal: 'bowled', dismissed: 'striker', fieldZone: 3 }]);
  });

  it('does not offer a new innings after completion and leaves undo available', () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, status: 'completed', canScore: false } });
    expect(wrapper.find('.gate-overlay').exists()).toBe(false);
    expect(wrapper.get('[data-testid="undo-ball"]').attributes('disabled')).toBeUndefined();
  });
});
