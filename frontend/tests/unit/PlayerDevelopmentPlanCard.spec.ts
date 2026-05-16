/**
 * PlayerDevelopmentPlanCard.spec.ts — Phase 9D tests
 *
 * Covers all 10 required test cases from the Phase 9D issue spec.
 */

import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PlayerDevelopmentPlanCard from '@/components/PlayerDevelopmentPlanCard.vue'
import * as playerDevApi from '@/services/playerDevelopmentApi'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makePlan = (overrides: Partial<typeof basePlan> = {}) => ({
  ...basePlan,
  ...overrides,
})

const basePlan: playerDevApi.PlayerDevelopmentPlanRead = {
  id: 'plan-001',
  player_profile_id: 'player-001',
  coach_user_id: 'coach-001',
  org_id: 'org-001',
  title: 'Draft Development Plan — Jamie Smith',
  summary: 'Focus on off-side technique and bowling economy.',
  status: 'draft',
  source_type: 'ai_insight',
  coach_approved: false,
  approval_state: 'pending_review',
  confidence_score: 0.68,
  evidence_refs: [{ type: 'match', id: 'match-001', label: 'Recent match scorecard' }],
  ai_metadata: {
    output_type: 'development_plan',
    is_official_truth: false,
    limitations: ['Limited bowling data — only 3 innings sampled.'],
  },
  activated_at: null,
  completed_at: null,
  created_at: '2026-05-10T10:00:00Z',
  updated_at: '2026-05-10T10:00:00Z',
}

const baseBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
  plan: basePlan,
  goals: [
    {
      id: 'goal-001',
      plan_id: 'plan-001',
      title: 'Improve off-side shot conversion',
      description: 'Target 70% conversion rate on off-side shots within 6 weeks.',
      target_metric: 'off_side_conversion',
      baseline_value: 0.52,
      target_value: 0.70,
      current_value: null,
      unit: 'ratio',
      status: 'draft',
      due_date: '2026-06-20',
      evidence_refs: [],
      created_at: '2026-05-10T10:00:00Z',
      updated_at: '2026-05-10T10:00:00Z',
    },
  ],
  strength_tags: [
    {
      id: 'str-001',
      plan_id: 'plan-001',
      player_profile_id: 'player-001',
      category: 'batting',
      label: 'Consistent mid-on placement',
      confidence_score: 0.72,
      source_type: 'ai_generated',
      evidence_refs: [],
      ai_metadata: {},
      created_at: '2026-05-10T10:00:00Z',
      updated_at: '2026-05-10T10:00:00Z',
    },
  ],
  weakness_tags: [
    {
      id: 'wk-001',
      plan_id: 'plan-001',
      player_profile_id: 'player-001',
      category: 'batting',
      label: 'weak_offside_conversion',
      safe_display_label: 'Developing off-side shot selection',
      severity: 'medium',
      confidence_score: 0.68,
      source_type: 'ai_generated',
      evidence_refs: [],
      ai_metadata: {},
      created_at: '2026-05-10T10:00:00Z',
      updated_at: '2026-05-10T10:00:00Z',
    },
  ],
  drill_assignments: [
    {
      id: 'drill-001',
      plan_id: 'plan-001',
      player_profile_id: 'player-001',
      coach_user_id: 'coach-001',
      drill_category: 'batting',
      drill_name: 'Off-side shadow batting drill',
      drill_description: '20 mins daily — shadow drive and cut shots off-side.',
      frequency: '5x per week',
      status: 'draft',
      assigned_at: null,
      due_date: null,
      completed_at: null,
      evidence_refs: [],
      created_at: '2026-05-10T10:00:00Z',
      updated_at: '2026-05-10T10:00:00Z',
    },
  ],
  progress_checkpoints: [
    {
      id: 'cp-001',
      plan_id: 'plan-001',
      player_profile_id: 'player-001',
      coach_user_id: 'coach-001',
      checkpoint_date: '2026-06-01',
      summary: 'Mid-point review of off-side technique.',
      progress_status: 'planned',
      confidence_score: null,
      evidence_refs: [],
      ai_metadata: {},
      coach_notes: null,
      created_at: '2026-05-10T10:00:00Z',
      updated_at: '2026-05-10T10:00:00Z',
    },
  ],
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PlayerDevelopmentPlanCard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // Test 1: Draft status and coach-review-required badge always visible
  it('always shows Draft and Coach review required badges on a draft plan', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    expect(wrapper.find('[data-testid="plan-draft-badge"]').text()).toContain('Draft')
    expect(wrapper.find('[data-testid="plan-review-badge"]').text()).toContain(
      'Coach review required',
    )
    expect(wrapper.find('[data-testid="plan-status-badge"]').text()).toContain('Draft')
  })

  // Test 2: Approval state is displayed correctly
  it('shows approval state and coach-approved status', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const approvalEl = wrapper.find('[data-testid="plan-approval-state"]')
    expect(approvalEl.exists()).toBe(true)
    expect(approvalEl.text()).toContain('Pending review')

    expect(wrapper.find('[data-testid="plan-not-approved"]').exists()).toBe(true)
  })

  // Test 3: Confidence score and limitations are visible
  it('renders confidence score and limitations', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const confidence = wrapper.find('[data-testid="plan-confidence"]')
    expect(confidence.exists()).toBe(true)
    expect(confidence.text()).toContain('68%')

    const limitations = wrapper.find('[data-testid="plan-limitations"]')
    expect(limitations.exists()).toBe(true)
    expect(limitations.text()).toContain('Limited bowling data')
  })

  // Test 4: Evidence references are visible
  it('renders evidence references', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const refs = wrapper.find('[data-testid="plan-evidence-refs"]')
    expect(refs.exists()).toBe(true)
    expect(refs.text()).toContain('Recent match scorecard')
  })

  // Test 5: Strengths render from API response
  it('renders strengths from the plan bundle', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const strengths = wrapper.find('[data-testid="plan-strengths"]')
    expect(strengths.exists()).toBe(true)
    expect(strengths.text()).toContain('Consistent mid-on placement')
  })

  // Test 6: Development areas use safe_display_label, not raw internal label
  it('renders development areas using safe_display_label (not raw label)', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const devAreas = wrapper.find('[data-testid="plan-dev-areas"]')
    expect(devAreas.exists()).toBe(true)

    // Must show safe_display_label
    const devAreaLabels = wrapper.findAll('[data-testid="dev-area-label"]')
    expect(devAreaLabels.length).toBeGreaterThan(0)
    expect(devAreaLabels[0].text()).toContain('Developing off-side shot selection')

    // Must NOT show raw internal label
    expect(wrapper.text()).not.toContain('weak_offside_conversion')
  })

  // Test 7: Goals render from API response
  it('renders goals from the plan bundle', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const goals = wrapper.find('[data-testid="plan-goals"]')
    expect(goals.exists()).toBe(true)
    expect(goals.text()).toContain('Improve off-side shot conversion')
  })

  // Test 8: Drills render from API response
  it('renders drills as draft/assigned status from API', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const drills = wrapper.find('[data-testid="plan-drills"]')
    expect(drills.exists()).toBe(true)
    expect(drills.text()).toContain('Off-side shadow batting drill')
    // Status must reflect backend value, not fabricated
    expect(drills.text()).toContain('draft')
  })

  // Test 9: Checkpoints render as planned/advisory
  it('renders checkpoints as planned/advisory from API', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    const checkpoints = wrapper.find('[data-testid="plan-checkpoints"]')
    expect(checkpoints.exists()).toBe(true)
    expect(checkpoints.text()).toContain('Mid-point review')
    expect(checkpoints.text()).toContain('planned')

    // Advisory note must be present
    expect(wrapper.text()).toContain('planned / advisory')
  })

  // Test 10: No activation or approval controls are shown
  it('does not render any activation or approval mutation controls', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle },
    })

    // Should not find any activate/approve/reject buttons
    const buttons = wrapper.findAll('button')
    const buttonTexts = buttons.map((b) => b.text().toLowerCase())
    expect(buttonTexts).not.toContain(expect.stringContaining('activate'))
    expect(buttonTexts).not.toContain(expect.stringContaining('approve'))
    expect(buttonTexts).not.toContain(expect.stringContaining('reject'))

    // Advisory footer must be present
    expect(wrapper.find('[data-testid="plan-advisory-footer"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-advisory-footer"]').text()).toContain('draft')
  })

  // Test 11: Empty sections show constructive empty-state messages (no fake data)
  it('shows empty states when no goals/drills/checkpoints are present', () => {
    const emptyBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      goals: [],
      strength_tags: [],
      weakness_tags: [],
      drill_assignments: [],
      progress_checkpoints: [],
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: emptyBundle },
    })

    expect(wrapper.find('[data-testid="plan-goals-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-drills-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-checkpoints-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-strengths-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-dev-areas-empty"]').exists()).toBe(true)
  })

  // Test 12: Approved plan shows correct approval state
  it('shows Approved approval state correctly', () => {
    const approvedBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      plan: makePlan({ approval_state: 'approved', coach_approved: true }),
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: approvedBundle },
    })

    const approvalEl = wrapper.find('[data-testid="plan-approval-state"]')
    expect(approvalEl.text()).toContain('Approved')
    // coach_approved=true means the "not approved" badge should not appear
    expect(wrapper.find('[data-testid="plan-not-approved"]').exists()).toBe(false)
  })

  // Test 13: AI-assisted badge shown when source_type is ai_insight
  it('shows AI-assisted advisory badge for source_type ai_insight plans', () => {
    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: baseBundle }, // source_type: 'ai_insight'
    })

    expect(wrapper.find('[data-testid="plan-ai-badge"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-ai-badge"]').text()).toContain('AI-assisted advisory')
  })

  // Test 14: Manual plan does not show AI badge
  it('does not show AI badge for manual source_type plans', () => {
    const manualBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      plan: makePlan({ source_type: 'manual' }),
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: manualBundle },
    })

    expect(wrapper.find('[data-testid="plan-ai-badge"]').exists()).toBe(false)
  })

  // Test 15: source_type "video_analysis" does not show AI badge and renders without error
  it('renders without error for source_type video_analysis (no AI badge)', () => {
    const videoBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      plan: makePlan({ source_type: 'video_analysis' }),
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: videoBundle },
    })

    // Should render (no TypeScript/runtime error)
    expect(wrapper.find('[data-testid="player-development-plan-card"]').exists()).toBe(true)
    // No AI badge for video_analysis
    expect(wrapper.find('[data-testid="plan-ai-badge"]').exists()).toBe(false)
  })

  // Test 16: status "paused" renders a visible status badge safely
  it('renders status "paused" safely with a status badge', () => {
    const pausedBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      plan: makePlan({ status: 'paused' }),
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: pausedBundle },
    })

    const statusBadge = wrapper.find('[data-testid="plan-status-badge"]')
    expect(statusBadge.exists()).toBe(true)
    expect(statusBadge.text()).toContain('Paused')
  })

  // Test 17: approval_state "changes_requested" renders safely with a clear label
  it('renders approval_state "changes_requested" with a clear human-readable label', () => {
    const changesBundle: playerDevApi.PlayerDevelopmentPlanDraftBundle = {
      ...baseBundle,
      plan: makePlan({ approval_state: 'changes_requested' }),
    }

    const wrapper = mount(PlayerDevelopmentPlanCard, {
      props: { bundle: changesBundle },
    })

    const approvalEl = wrapper.find('[data-testid="plan-approval-state"]')
    expect(approvalEl.exists()).toBe(true)
    expect(approvalEl.text()).toContain('Changes requested')
  })
})

// ---------------------------------------------------------------------------
// Inline API service tests — verify typed functions exist and can be called
// ---------------------------------------------------------------------------

describe('playerDevelopmentApi service', () => {
  it('exports the required API functions', () => {
    expect(typeof playerDevApi.generateDraftPlayerDevelopmentPlan).toBe('function')
    expect(typeof playerDevApi.getPlayerDevelopmentPlan).toBe('function')
    expect(typeof playerDevApi.listPlayerDevelopmentPlans).toBe('function')
    expect(typeof playerDevApi.listCoachAssignedPlayers).toBe('function')
  })

  it('PlayerDevelopmentApiError has expected helper methods', () => {
    const err = new playerDevApi.PlayerDevelopmentApiError('Forbidden', 403)
    expect(err.isUnauthorized()).toBe(true)
    expect(err.isUnauthenticated()).toBe(false)
    expect(err.isNotFound()).toBe(false)

    const err404 = new playerDevApi.PlayerDevelopmentApiError('Not found', 404)
    expect(err404.isNotFound()).toBe(true)

    const err401 = new playerDevApi.PlayerDevelopmentApiError('Unauthorized', 401)
    expect(err401.isUnauthenticated()).toBe(true)
  })
})
