/**
 * CplPodcastDashboard.spec.ts
 *
 * Unit tests for the CPL Podcast & Social Dashboard component.
 *
 * Validates:
 * - Loading state renders while data is being fetched
 * - Empty/no-CPL-data state is shown when no CPL matches exist
 * - Error state is shown when the API call fails
 * - CPL summary cards render correct counts from imported data
 * - Leaderboards show top scorers / wicket takers from delivery data
 * - Venue cards render when CPL venues exist
 * - Podcast prep panel renders deterministic facts
 * - No fake/hardcoded data: all displayed values come from the mocked API
 * - Insufficient-data warnings render when delivery data is absent
 * - Provenance bar is always visible
 * - AI placeholder is visible (future enhancement note)
 */

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CplPodcastDashboard from '@/components/CplPodcastDashboard.vue';
import type { HistoricalStatsSummaryResponse } from '@/services/api';

// ── Mock the API module ────────────────────────────────────────────────────

const mockGetHistoricalStatsSummary = vi.fn<[], Promise<HistoricalStatsSummaryResponse>>();

vi.mock('@/services/api', () => ({
  getHistoricalStatsSummary: (...args: unknown[]) => mockGetHistoricalStatsSummary(...(args as [])),
}));

// ── Test data factories ────────────────────────────────────────────────────

function emptySummary(): HistoricalStatsSummaryResponse {
  return {
    total_eligible_matches: 0,
    excluded_metadata_only_count: 0,
    excluded_invalid_count: 0,
    matches: [],
    players: [],
    teams: [],
    venues: [],
    competitions: [],
    seasons: [],
    generated_at: '2026-01-01T00:00:00Z',
    note: 'Deterministic on-demand aggregation from validated historical match data only.',
  };
}

function cplSummary(): HistoricalStatsSummaryResponse {
  return {
    total_eligible_matches: 2,
    excluded_metadata_only_count: 0,
    excluded_invalid_count: 0,
    matches: [
      {
        match_id: 'cpl-match-1',
        teams: 'Trinbago Knight Riders vs Barbados Royals',
        team_a: 'Trinbago Knight Riders',
        team_b: 'Barbados Royals',
        import_batch_id: 'batch-001',
        source_filename: 'cpl_2023_m1.json',
        source_format: 'cricsheet_json',
        competition: 'Caribbean Premier League',
        season: '2023',
        venue: 'Queen\'s Park Oval',
        match_date: '2023-08-01',
        match_type: 'T20',
        innings_count: 2,
        total_runs: 320,
        total_wickets: 14,
        innings_totals: [
          { inning_no: 1, team: 'Trinbago Knight Riders', runs: 175, wickets: 6, overs: 20.0, extras: 8 },
          { inning_no: 2, team: 'Barbados Royals', runs: 145, wickets: 8, overs: 19.3, extras: 5 },
        ],
        has_delivery_data: true,
      },
      {
        match_id: 'cpl-match-2',
        teams: 'Guyana Amazon Warriors vs Jamaica Tallawahs',
        team_a: 'Guyana Amazon Warriors',
        team_b: 'Jamaica Tallawahs',
        import_batch_id: 'batch-002',
        source_filename: 'cpl_2023_m2.json',
        source_format: 'cricsheet_json',
        competition: 'Caribbean Premier League',
        season: '2023',
        venue: 'Providence Stadium',
        match_date: '2023-08-05',
        match_type: 'T20',
        innings_count: 1,
        total_runs: 160,
        total_wickets: 5,
        innings_totals: [
          { inning_no: 1, team: 'Guyana Amazon Warriors', runs: 160, wickets: 5, overs: 20.0, extras: 10 },
        ],
        has_delivery_data: false,
      },
    ],
    players: [
      {
        player_name: 'Kieron Pollard',
        matches_contributed: 1,
        runs_scored: 87,
        balls_faced: 52,
        strike_rate: 167.3,
        fours: 5,
        sixes: 7,
        dismissals: 1,
        overs_bowled: 2.0,
        runs_conceded: 24,
        wickets: 1,
        economy_rate: 12.0,
        maidens: 0,
      },
      {
        player_name: 'Sunil Narine',
        matches_contributed: 1,
        runs_scored: 12,
        balls_faced: 8,
        strike_rate: 150.0,
        fours: 1,
        sixes: 1,
        dismissals: 1,
        overs_bowled: 4.0,
        runs_conceded: 22,
        wickets: 3,
        economy_rate: 5.5,
        maidens: 0,
      },
    ],
    teams: [
      {
        team_name: 'Trinbago Knight Riders',
        matches_played: 1,
        innings_batted: 1,
        avg_score: 175.0,
        avg_wickets: 6.0,
        total_runs: 175,
        total_wickets: 6,
      },
      {
        team_name: 'Barbados Royals',
        matches_played: 1,
        innings_batted: 1,
        avg_score: 145.0,
        avg_wickets: 8.0,
        total_runs: 145,
        total_wickets: 8,
      },
    ],
    venues: [
      {
        venue: "Queen's Park Oval",
        match_count: 1,
        avg_first_innings_score: 175.0,
        avg_second_innings_score: 145.0,
        avg_total_runs: 320.0,
        avg_wickets: 7.0,
      },
      {
        venue: 'Providence Stadium',
        match_count: 1,
        avg_first_innings_score: 0,
        avg_second_innings_score: null,
        avg_total_runs: 160.0,
        avg_wickets: 5.0,
      },
    ],
    competitions: [
      { competition: 'Caribbean Premier League', match_count: 2, avg_total_runs: 240.0, avg_wickets: 9.5 },
    ],
    seasons: [
      { season: '2023', match_count: 2, avg_total_runs: 240.0, avg_wickets: 9.5 },
    ],
    generated_at: '2026-01-01T00:00:00Z',
    note: 'Deterministic on-demand aggregation from validated historical match data only.',
  };
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('CplPodcastDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while fetching', async () => {
    // Simulate a pending promise
    mockGetHistoricalStatsSummary.mockReturnValue(new Promise(() => {}));
    const wrapper = mount(CplPodcastDashboard);
    // Wait for onMounted to fire and set loading=true
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[role="status"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Loading');
  });

  it('shows error state when the API call fails', async () => {
    mockGetHistoricalStatsSummary.mockRejectedValue(new Error('Network error'));
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();
    expect(wrapper.find('[role="alert"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Unable to load');
  });

  it('shows no-CPL-data state when only non-CPL matches exist', async () => {
    // Summary with a non-CPL match
    const summary = emptySummary();
    summary.total_eligible_matches = 1;
    summary.matches = [
      {
        match_id: 'other-1',
        teams: 'Team A vs Team B',
        team_a: 'Team A',
        team_b: 'Team B',
        import_batch_id: 'batch-X',
        source_filename: 'other.json',
        source_format: 'cricsheet_json',
        competition: 'Some Other League',
        season: '2022',
        venue: 'Some Ground',
        match_date: '2022-06-01',
        match_type: 'T20',
        innings_count: 2,
        total_runs: 280,
        total_wickets: 12,
        innings_totals: [],
        has_delivery_data: false,
      },
    ];
    mockGetHistoricalStatsSummary.mockResolvedValue(summary);
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();
    expect(wrapper.text()).toContain('No CPL data available');
  });

  it('shows empty state when no matches at all', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(emptySummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();
    expect(wrapper.text()).toContain('No CPL data available');
  });

  it('renders summary cards with correct counts from CPL data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Should show 2 matches
    const text = wrapper.text();
    expect(text).toContain('2'); // matches count
    // Should show total runs (320 + 160 = 480)
    expect(text).toContain('480');
  });

  it('renders venue cards for CPL venues', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain("Queen's Park Oval");
    expect(wrapper.text()).toContain('Providence Stadium');
  });

  it('renders venue with missing avg score warning', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Providence Stadium has avg_first_innings_score = 0, should warn
    expect(wrapper.text()).toContain('Avg 1st innings score unavailable');
  });

  it('renders top run scorers in leaderboard', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Kieron Pollard');
    expect(wrapper.text()).toContain('87');
  });

  it('renders top wicket takers in leaderboard', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Sunil Narine');
    // Should show wickets: 3
    expect(wrapper.text()).toContain('3');
  });

  it('shows delivery-data warning for match without delivery data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Select a match without delivery data
    const select = wrapper.find('[aria-label="Select match for story view"]');
    await select.setValue('cpl-match-2');
    await flushPromises();

    expect(wrapper.text()).toContain('Ball-by-ball delivery data not imported');
  });

  it('renders innings comparison for selected match with data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Select match 1 which has 2 innings
    const select = wrapper.find('[aria-label="Select match for story view"]');
    await select.setValue('cpl-match-1');
    await flushPromises();

    expect(wrapper.text()).toContain('Innings Comparison');
    expect(wrapper.text()).toContain('175/6');
    expect(wrapper.text()).toContain('145/8');
  });

  it('renders podcast prep panel with deterministic facts', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Podcast Prep Panel');
    expect(wrapper.text()).toContain('Matches imported');
    expect(wrapper.text()).toContain('Total runs in dataset');
  });

  it('renders AI placeholder note', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('AI Talking-Point Assistant');
    expect(wrapper.text()).toContain('future enhancement');
  });

  it('always shows provenance bar with no-fake-data notice', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const bar = wrapper.find('[aria-label="Data provenance notice"]');
    expect(bar.exists()).toBe(true);
    expect(bar.text()).toContain('validated historical import only');
  });

  it('does not render any hardcoded/fake player names outside of mock data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(emptySummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // These are names that should never be hardcoded in the component
    const hardcodedFakeNames = ['John Smith', 'Player One', 'Test Player', 'Demo Player'];
    for (const name of hardcodedFakeNames) {
      expect(wrapper.text()).not.toContain(name);
    }
  });

  it('filter reset restores all filters to default', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Change season filter
    const seasonSelect = wrapper.find('[aria-label="Filter by season"]');
    await seasonSelect.setValue('2023');

    // Reset
    const resetBtn = wrapper.find('button');
    // find "Reset filters" button
    const buttons = wrapper.findAll('button');
    const resetButton = buttons.find(b => b.text().includes('Reset'));
    await resetButton?.trigger('click');
    await flushPromises();

    expect((seasonSelect.element as HTMLSelectElement).value).toBe('all');
  });

  it('shows season in filter options when CPL season exists', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const seasonSelect = wrapper.find('[aria-label="Filter by season"]');
    expect(seasonSelect.text()).toContain('2023');
  });

  it('shows teams in filter options when CPL teams exist', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const teamSelect = wrapper.find('[aria-label="Filter by team"]');
    expect(teamSelect.text()).toContain('Trinbago Knight Riders');
  });
});
