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
    expect(wrapper.text()).not.toContain('LAST 6');
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
    expect(wrapper.emitted('delivery')?.[0]).toEqual([{ runs: 4, extra: 'nb', isWicket: true, dismissal: 'run_out', dismissed: 'striker', fieldZone: 3 }]);
  });

  it('clears a selected field zone when it is tapped again', async () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, fieldZone: 3 } });
    await wrapper.get('[aria-label="Field zone 3"]').trigger('click');
    expect(wrapper.emitted('update:fieldZone')).toEqual([[null]]);
  });

  it('labels duplicate-name batting ends and prevents incompatible non-striker dismissals', async () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, strikerName: 'Alex Lee', nonStrikerName: 'Alex Lee' } });
    await wrapper.get('[data-testid="delivery-wicket"]').setValue(true);
    const dismissed = wrapper.get('[data-testid="dismissed-batter"]');
    expect(dismissed.text()).toContain('Alex Lee (striker)');
    expect(dismissed.text()).toContain('Alex Lee (non-striker)');
    expect(dismissed.get('option[value="non_striker"]').attributes('disabled')).toBeDefined();
    await wrapper.get('.wicket-details select').setValue('run_out');
    expect(dismissed.get('option[value="non_striker"]').attributes('disabled')).toBeUndefined();
    await dismissed.setValue('non_striker');
    await wrapper.get('.wicket-details select').setValue('bowled');
    await wrapper.get('[data-testid="submit-delivery"]').trigger('click');
    expect(wrapper.emitted('delivery')?.[0]?.[0]).toMatchObject({ dismissal: 'bowled', dismissed: 'striker' });
  });

  it('does not render inert practice footer tabs', () => {
    const wrapper = mount(PracticeSharedScorer, { props });
    expect(wrapper.findAll('.tabs-nav button')).toHaveLength(1);
    expect(wrapper.get('.tabs-nav button').text()).toBe('RECENT');
  });

  it('does not offer a new innings after completion and leaves undo available', () => {
    const wrapper = mount(PracticeSharedScorer, { props: { ...props, status: 'completed', canScore: false } });
    expect(wrapper.find('.gate-overlay').exists()).toBe(false);
    expect(wrapper.get('[data-testid="undo-ball"]').attributes('disabled')).toBeUndefined();
  });
});
