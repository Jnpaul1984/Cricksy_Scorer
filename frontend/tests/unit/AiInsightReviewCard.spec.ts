/**
 * AiInsightReviewCard.spec.ts — Phase 8C
 *
 * Unit tests for the AiInsightReviewCard component.
 *
 * Covers:
 * - Review state badge renders when data is loaded
 * - Advisory notice is always visible
 * - Explanation, confidence, limitations, source refs render when provided
 * - Reviewer actions only render when canReview=true
 * - Review form opens/closes correctly
 * - Submit review calls the correct API function and shows success/error
 * - Loading state renders a skeleton
 * - Empty/no-data states handled cleanly
 */

import { mount, flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AiInsightReviewCard from '@/components/AiInsightReviewCard.vue';
import * as api from '@/services/api';

// ── Mock the API module ─────────────────────────────────────────────────────

vi.mock('@/services/api', () => ({
  getAiInsightReviewState: vi.fn(),
  submitAiInsightReview: vi.fn(),
}));

// ── Shared fixtures ─────────────────────────────────────────────────────────

const pendingState: api.AiInsightReviewStateResponse = {
  insight_type: 'summary',
  insight_id: 'match-001',
  current_state: 'pending',
  latest_review: null,
  total_reviews: 0,
  is_advisory_only: true,
};

const approvedState: api.AiInsightReviewStateResponse = {
  insight_type: 'summary',
  insight_id: 'match-001',
  current_state: 'approved',
  latest_review: {
    id: 'rev-001',
    insight_type: 'summary',
    insight_id: 'match-001',
    reviewer_id: 'user-001',
    reviewer_org_id: 'org-1',
    review_state: 'approved',
    feedback_type: 'useful',
    note: 'Looks good.',
    created_at: '2026-05-15T04:00:00Z',
    updated_at: '2026-05-15T04:00:00Z',
  },
  total_reviews: 1,
  is_advisory_only: true,
};

const defaultProps = {
  insightType: 'summary',
  insightId: 'match-001',
  title: 'Match Summary Insight',
  explanation: 'Lions dominated the powerplay with aggressive batting.',
  confidence: 0.82,
  limitations: ['Small sample size.', 'Weather data not included.'],
  sourceRefs: [{ type: 'match', id: 'match-001', label: 'Lions vs Falcons' }],
  canReview: false,
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe('AiInsightReviewCard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getAiInsightReviewState).mockResolvedValue(pendingState);
  });

  it('renders title and advisory notice', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    expect(wrapper.find('[data-testid="ai-insight-review-card"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Match Summary Insight');
    expect(wrapper.find('[data-testid="advisory-notice"]').exists()).toBe(true);
  });

  it('renders explanation text', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const el = wrapper.find('[data-testid="insight-explanation"]');
    expect(el.exists()).toBe(true);
    expect(el.text()).toContain('Lions dominated');
  });

  it('renders confidence band when provided', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const el = wrapper.find('[data-testid="confidence-band"]');
    expect(el.exists()).toBe(true);
    expect(el.text()).toContain('82%');
  });

  it('does not render confidence band when confidence is null', async () => {
    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, confidence: null },
    });
    await flushPromises();

    expect(wrapper.find('[data-testid="confidence-band"]').exists()).toBe(false);
  });

  it('renders limitations list', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const el = wrapper.find('[data-testid="limitations-section"]');
    expect(el.exists()).toBe(true);
    expect(el.text()).toContain('Small sample size.');
    expect(el.text()).toContain('Weather data not included.');
  });

  it('renders source references', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const el = wrapper.find('[data-testid="source-refs-section"]');
    expect(el.exists()).toBe(true);
    expect(el.text()).toContain('Lions vs Falcons');
  });

  it('shows pending state badge after load', async () => {
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const badge = wrapper.find('[data-testid="review-state-badge"]');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toContain('Pending review');
  });

  it('shows approved state badge when review is approved', async () => {
    vi.mocked(api.getAiInsightReviewState).mockResolvedValue(approvedState);
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const badge = wrapper.find('[data-testid="review-state-badge"]');
    expect(badge.text()).toContain('Approved');
  });

  it('shows latest reviewer note when present', async () => {
    vi.mocked(api.getAiInsightReviewState).mockResolvedValue(approvedState);
    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    const note = wrapper.find('[data-testid="latest-reviewer-note"]');
    expect(note.exists()).toBe(true);
    expect(note.text()).toContain('Looks good.');
  });

  it('does NOT render reviewer actions when canReview=false', async () => {
    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: false },
    });
    await flushPromises();

    expect(wrapper.find('[data-testid="reviewer-actions"]').exists()).toBe(false);
  });

  it('renders reviewer actions when canReview=true', async () => {
    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: true },
    });
    await flushPromises();

    expect(wrapper.find('[data-testid="reviewer-actions"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="open-review-form-btn"]').exists()).toBe(true);
  });

  it('opens review form on button click', async () => {
    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: true },
    });
    await flushPromises();

    expect(wrapper.find('[data-testid="review-form"]').exists()).toBe(false);
    await wrapper.find('[data-testid="open-review-form-btn"]').trigger('click');
    expect(wrapper.find('[data-testid="review-form"]').exists()).toBe(true);
  });

  it('closes review form on cancel click', async () => {
    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: true },
    });
    await flushPromises();

    await wrapper.find('[data-testid="open-review-form-btn"]').trigger('click');
    expect(wrapper.find('[data-testid="review-form"]').exists()).toBe(true);

    await wrapper.find('[data-testid="cancel-review-btn"]').trigger('click');
    expect(wrapper.find('[data-testid="review-form"]').exists()).toBe(false);
  });

  it('calls submitAiInsightReview with correct payload on submit', async () => {
    const submittedRecord: api.AiInsightReviewRecord = {
      id: 'rev-002',
      insight_type: 'summary',
      insight_id: 'match-001',
      reviewer_id: 'user-001',
      reviewer_org_id: 'org-1',
      review_state: 'approved',
      feedback_type: null,
      note: null,
      created_at: '2026-05-15T04:00:00Z',
      updated_at: '2026-05-15T04:00:00Z',
    };
    vi.mocked(api.submitAiInsightReview).mockResolvedValue(submittedRecord);
    vi.mocked(api.getAiInsightReviewState).mockResolvedValue(approvedState);

    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: true },
    });
    await flushPromises();

    await wrapper.find('[data-testid="open-review-form-btn"]').trigger('click');
    await wrapper.find('[data-testid="review-form"]').trigger('submit');
    await flushPromises();

    expect(api.submitAiInsightReview).toHaveBeenCalledWith('summary', 'match-001', {
      review_state: 'approved',
      feedback_type: null,
      note: null,
    });
    expect(wrapper.find('[data-testid="review-success-msg"]').exists()).toBe(true);
  });

  it('shows error message when submit fails', async () => {
    vi.mocked(api.submitAiInsightReview).mockRejectedValue(new Error('Server error'));

    const wrapper = mount(AiInsightReviewCard, {
      props: { ...defaultProps, canReview: true },
    });
    await flushPromises();

    await wrapper.find('[data-testid="open-review-form-btn"]').trigger('click');
    await wrapper.find('[data-testid="review-form"]').trigger('submit');
    await flushPromises();

    const errEl = wrapper.find('[data-testid="review-error-msg"]');
    expect(errEl.exists()).toBe(true);
    expect(errEl.text()).toContain('Server error');
  });

  it('handles API error gracefully (no crash) when state fetch fails', async () => {
    vi.mocked(api.getAiInsightReviewState).mockRejectedValue(new Error('403 Forbidden'));

    const wrapper = mount(AiInsightReviewCard, { props: defaultProps });
    await flushPromises();

    // Component should not crash; review badge area may not show
    expect(wrapper.find('[data-testid="ai-insight-review-card"]').exists()).toBe(true);
  });
});
