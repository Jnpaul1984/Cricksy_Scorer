import { mount } from '@vue/test-utils';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import PlayerDevelopmentTeamOverviewCard from '@/components/PlayerDevelopmentTeamOverviewCard.vue';
import type { PlayerDevelopmentTeamOverview } from '@/services/playerDevelopmentApi';

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}));

const overviewFixture: PlayerDevelopmentTeamOverview = {
  total_assigned_players: 4,
  players_with_draft_plans: 3,
  players_without_plans: 1,
  plans_requiring_review: 2,
  players_with_goals: 3,
  players_with_drills: 2,
  players_with_checkpoints: 2,
  plans_by_status: [
    { status: 'active', count: 1 },
    { status: 'draft', count: 2 },
  ],
  players_without_plan_details: [
    { player_profile_id: 'player-002', player_name: 'Ben Builder' },
  ],
  review_required_players: [
    {
      player_profile_id: 'player-001',
      player_name: 'Ava Support',
      plan_id: 'plan-001',
      plan_status: 'draft',
      confidence_score: 0.8,
      advisory_note: 'Coach review is still needed before this draft is treated as a working plan.',
    },
  ],
  common_development_areas: [
    { category: 'batting', safe_display_label: 'Batting tempo', player_count: 2 },
    { category: 'mindset', safe_display_label: 'Reset between balls', player_count: 1 },
  ],
  drill_assignment_summary: {
    total_assignments: 3,
    by_status: [
      { status: 'active', count: 1 },
      { status: 'draft', count: 2 },
    ],
    by_category: [
      { category: 'batting', count: 2 },
      { category: 'mindset', count: 1 },
    ],
  },
  evidence_coverage_summary: {
    players_with_confident_recommendations: 2,
    players_needing_more_evidence: 1,
    players_needing_more_evidence_details: [
      {
        player_profile_id: 'player-003',
        player_name: 'Cara Growth',
        plan_id: 'plan-003',
        plan_status: 'active',
        confidence_score: 0.45,
        advisory_note: 'More recent match evidence would strengthen this draft.',
      },
    ],
  },
  upcoming_checkpoints: [
    {
      checkpoint_id: 'checkpoint-001',
      plan_id: 'plan-001',
      player_profile_id: 'player-001',
      player_name: 'Ava Support',
      checkpoint_date: '2026-05-14',
      progress_status: 'needs_review',
      advisory_label: 'Review overdue',
      is_overdue: true,
      confidence_score: 0.7,
    },
    {
      checkpoint_id: 'checkpoint-002',
      plan_id: 'plan-003',
      player_profile_id: 'player-003',
      player_name: 'Cara Growth',
      checkpoint_date: '2026-05-20',
      progress_status: 'planned',
      advisory_label: 'Upcoming review this week',
      is_overdue: false,
      confidence_score: 0.45,
    },
  ],
  most_recent_development_activity_at: '2026-05-09T13:00:00Z',
};

describe('PlayerDevelopmentTeamOverviewCard', () => {
  beforeEach(() => {
    push.mockReset();
  });

  it('renders loading state', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: true,
        error: null,
        overview: null,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-loading"]').text()).toContain(
      'Loading team development overview',
    );
  });

  it('renders empty state when no players are assigned', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: null,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-empty"]').text()).toContain(
      'No players are currently assigned',
    );
  });

  it('renders no-plan state without fake fallback data', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: {
          ...overviewFixture,
          players_with_draft_plans: 0,
          players_without_plans: 4,
          plans_requiring_review: 0,
          players_with_goals: 0,
          players_with_drills: 0,
          players_with_checkpoints: 0,
          plans_by_status: [],
          players_without_plan_details: [
            { player_profile_id: 'player-001', player_name: 'Ava Support' },
          ],
          review_required_players: [],
          common_development_areas: [],
          drill_assignment_summary: {
            total_assignments: 0,
            by_status: [],
            by_category: [],
          },
          evidence_coverage_summary: {
            players_with_confident_recommendations: 0,
            players_needing_more_evidence: 0,
            players_needing_more_evidence_details: [],
          },
          upcoming_checkpoints: [],
        },
      },
    });

    expect(wrapper.get('[data-testid="team-dev-no-plans"]').text()).toContain(
      'No draft plans are available yet',
    );
    expect(wrapper.text()).toContain('4');
    expect(wrapper.text()).not.toContain('Math.random');
  });

  it('renders permission or api errors', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: 'You do not have permission to view this development overview.',
        overview: null,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-error"]').text()).toContain(
      'You do not have permission',
    );
  });

  it('renders coverage summary from real api data', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: overviewFixture,
      },
    });

    expect(wrapper.text()).toContain('Assigned players');
    expect(wrapper.text()).toContain('Players with draft plans');
    expect(wrapper.text()).toContain('Players without draft plans yet');
    expect(wrapper.text()).toContain('Plans requiring coach review');
    expect(wrapper.text()).toContain('3 players with goals');
    expect(wrapper.text()).toContain('2 players with drills');
  });

  it('uses constructive needs-support wording', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: overviewFixture,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-attention"]').text()).toContain(
      'Needs Coach Attention',
    );
    expect(wrapper.text()).toContain('More evidence needed');
    expect(wrapper.text()).not.toContain('weakest players');
    expect(wrapper.text()).not.toContain('problem players');
  });

  it('renders common development themes using safe labels', () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: overviewFixture,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-themes"]').text()).toContain('Batting tempo');
    expect(wrapper.get('[data-testid="team-dev-themes"]').text()).toContain(
      'Reset between balls',
    );
    expect(wrapper.get('[data-testid="team-dev-themes"]').text()).not.toContain('batting tempo');
  });

  it('renders drills and checkpoints and omits activation controls', async () => {
    const wrapper = mount(PlayerDevelopmentTeamOverviewCard, {
      props: {
        loading: false,
        error: null,
        overview: overviewFixture,
      },
    });

    expect(wrapper.get('[data-testid="team-dev-drills"]').text()).toContain('Drill Assignment Overview');
    expect(wrapper.get('[data-testid="team-dev-checkpoints"]').text()).toContain('Upcoming Checkpoints');
    expect(wrapper.text()).toContain('Ava Support');
    expect(wrapper.text()).toContain('Review overdue');
    expect(wrapper.text()).not.toContain('Activate plan');
    expect(wrapper.text()).not.toContain('Approve plan');

    await wrapper.findAll('button')[0]?.trigger('click');
    expect(push).toHaveBeenCalled();
  });
});
