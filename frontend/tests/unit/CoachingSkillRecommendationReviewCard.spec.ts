import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import CoachingSkillRecommendationReviewCard from '@/components/CoachingSkillRecommendationReviewCard.vue';

const defaultProps = {
  planId: 'plan-123',
  playerProfileId: 'player-456',
  sessionTitle: 'Front-foot batting review',
  sessionId: 'session-789',
  jobId: 'job-321',
  analysisMode: 'Batting',
  approvalState: 'pending_review' as const,
  coachApproved: false,
  confidenceScore: 0.74,
  recommendationText: 'Keep the head stable through contact and repeat the front-foot stride.',
  focusAreas: ['Head stability', 'Front-foot stride'],
  suggestedDrills: ['Mirror batting', 'Step-through contact drill'],
  limitations: ['Single camera angle only.'],
  evidenceRefs: [{ type: 'video_session', id: 'session-789', label: 'Front-foot batting review' }],
  evidenceStatusText: '3 timestamped markers across 2 moments and 1 segment.',
  canReview: true,
};

describe('CoachingSkillRecommendationReviewCard', () => {
  it('renders governed review context and advisory notice', () => {
    const wrapper = mount(CoachingSkillRecommendationReviewCard, {
      props: defaultProps,
    });

    expect(wrapper.find('[data-testid="coaching-skill-review-card"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="review-approval-badge"]').text()).toContain('Pending review');
    expect(wrapper.find('[data-testid="review-visibility-notice"]').text())
      .toContain('Coach approval controls player-facing visibility');
    expect(wrapper.find('[data-testid="review-context"]').text()).toContain('session-789');
    expect(wrapper.find('[data-testid="review-summary"]').text())
      .toContain('Keep the head stable through contact');
    expect(wrapper.find('[data-testid="review-focus-areas"]').text()).toContain('Head stability');
    expect(wrapper.find('[data-testid="review-suggested-drills"]').text()).toContain('Mirror batting');
    expect(wrapper.find('[data-testid="review-evidence-refs"]').text())
      .toContain('Front-foot batting review');
  });

  it('hides review controls when caller cannot review', () => {
    const wrapper = mount(CoachingSkillRecommendationReviewCard, {
      props: {
        ...defaultProps,
        canReview: false,
      },
    });

    expect(wrapper.find('[data-testid="review-controls"]').exists()).toBe(false);
  });

  it('emits approve, reject, and request-changes with trimmed notes', async () => {
    const wrapper = mount(CoachingSkillRecommendationReviewCard, {
      props: defaultProps,
    });

    const notes = wrapper.get('textarea');
    await notes.setValue('  Evidence is strong, but tighten wording for players.  ');

    const buttons = wrapper.findAll('button');
    await buttons[0].trigger('click');
    await buttons[1].trigger('click');
    await buttons[2].trigger('click');

    expect(wrapper.emitted('request-changes')?.[0]).toEqual([
      'Evidence is strong, but tighten wording for players.',
    ]);
    expect(wrapper.emitted('reject')?.[0]).toEqual([
      'Evidence is strong, but tighten wording for players.',
    ]);
    expect(wrapper.emitted('approve')?.[0]).toEqual([
      'Evidence is strong, but tighten wording for players.',
    ]);
  });

  it('shows latest review activity and success state when provided', () => {
    const wrapper = mount(CoachingSkillRecommendationReviewCard, {
      props: {
        ...defaultProps,
        approvalState: 'approved',
        coachApproved: true,
        reviewSuccess: 'Review saved: Approved.',
        reviewerNotes: 'Approved after checking the evidence markers.',
        reviewedByUserId: 'coach-plus-user',
        reviewedAt: '2026-05-17T00:00:00Z',
      },
    });

    expect(wrapper.find('[data-testid="review-success"]').text()).toContain('Review saved');
    expect(wrapper.find('[data-testid="review-latest-review"]').text())
      .toContain('coach-plus-user');
    expect(wrapper.find('[data-testid="review-visibility-notice"]').text())
      .toContain('Coach approved');
  });
});
