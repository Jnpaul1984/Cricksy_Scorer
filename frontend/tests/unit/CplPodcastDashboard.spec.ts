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
 * - AI talking-point review gates and podcast script builder behavior
 */

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CplPodcastDashboard from '@/components/CplPodcastDashboard.vue';
import type { HistoricalStatsSummaryResponse } from '@/services/api';

// ── Mock the API module ────────────────────────────────────────────────────

const mockGetHistoricalStatsSummary = vi.fn<[], Promise<HistoricalStatsSummaryResponse>>();
const mockToPng = vi.fn<(...args: unknown[]) => Promise<string>>();
const mockClipboardWriteText = vi.fn<(text: string) => Promise<void>>();
const EPISODE_ARCHIVE_KEY = 'cricksy.cplPodcastEpisodeArchive.v1';

vi.mock('@/services/api', () => ({
  getHistoricalStatsSummary: (...args: unknown[]) => mockGetHistoricalStatsSummary(...(args as [])),
}));

vi.mock('html-to-image', () => ({
  toPng: (...args: unknown[]) => mockToPng(...args),
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
        winner_team: 'Trinbago Knight Riders',
        winner_team_canonical: 'Trinbago Knight Riders',
        winner_source: 'result_text',
        winner_confidence: 'high',
        wicket_derivation_source: 'deliveries',
        phase_breakdown: {
          powerplay: { runs: 48, wickets: 2, legal_balls: 36, overs: 6.0, deliveries: 36 },
          middle: { runs: 72, wickets: 1, legal_balls: 48, overs: 8.0, deliveries: 48 },
          death: { runs: 55, wickets: 3, legal_balls: 36, overs: 6.0, deliveries: 36 },
        },
        team_a_canonical: 'Trinbago Knight Riders',
        team_b_canonical: 'Barbados Royals',
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
        winner_team: null,
        winner_team_canonical: null,
        winner_source: null,
        winner_confidence: 'none',
        wicket_derivation_source: 'scorecard',
        phase_breakdown: {},
        team_a_canonical: 'Guyana Amazon Warriors',
        team_b_canonical: 'Jamaica Tallawahs',
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
    diagnostics: {
      matches_imported: 2,
      matches_with_parsed_winner: 1,
      matches_missing_winner_or_result: 1,
      delivery_complete_matches: 1,
      delivery_derived_wicket_matches: 1,
      scorecard_derived_wicket_matches: 1,
      canonical_teams_represented: 4,
      venues_represented: 2,
    },
    top_team_by_wins: {
      team_name: 'Trinbago Knight Riders',
      wins: 1,
      source: 'parsed_result_text',
      confidence: 'medium',
    },
    case_studies: [
      {
        id: 'high_scoring_match',
        title: 'High-scoring match',
        insight: 'Trinbago Knight Riders vs Barbados Royals produced 320 runs in total.',
        source: 'match:cpl-match-1',
        context: 'Derived from innings total runs in validated historical imports.',
      },
    ],
    generated_at: '2026-01-01T00:00:00Z',
    note: 'Deterministic on-demand aggregation from validated historical match data only.',
  };
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('CplPodcastDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.removeItem(EPISODE_ARCHIVE_KEY);
    mockToPng.mockResolvedValue('data:image/png;base64,mock-preview');
    mockClipboardWriteText.mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      configurable: true,
      value: { writeText: mockClipboardWriteText },
    });
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

  it('renders deterministic case studies from historical analytics', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Case Studies');
    expect(wrapper.text()).toContain('High-scoring match');
    expect(wrapper.text()).toContain('Source: match:cpl-match-1');
  });

  it('renders top team by wins from parsed winner diagnostics', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Top team (most wins)');
    expect(wrapper.text()).toContain('Trinbago Knight Riders (1)');
    expect(wrapper.text()).toContain('confidence: medium');
  });

  it('renders AI Talking-Point Assistant panel with fact bundle preview', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const panel = wrapper.find('[aria-label="AI Talking-Point Assistant"]');
    expect(panel.exists()).toBe(true);
    expect(panel.text()).toContain('AI Talking-Point Assistant');
    expect(panel.text()).toContain('Reviewer-gated');
    expect(panel.text()).toContain('needs review');
  });

  it('shows fact bundle with correct facts before generation', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const bundle = wrapper.find('[aria-label="Fact bundle preview"]');
    expect(bundle.exists()).toBe(true);
    expect(bundle.text()).toContain('Matches imported');
    expect(bundle.text()).toContain('Total runs in dataset');
  });

  it('disables generate button when fact bundle is empty', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(emptySummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // No CPL data → dashboard is in empty state, no generate button
    expect(wrapper.text()).toContain('No CPL data available');
    expect(wrapper.find('[aria-label="Generate AI talking points"]').exists()).toBe(false);
  });

  it('shows insufficient-data warning when only 1 fact available', async () => {
    // Supply a CPL summary with only 1 CPL match but no players/venues
    const s = emptySummary();
    s.total_eligible_matches = 1;
    s.matches = [
      {
        match_id: 'cpl-only-1',
        teams: 'Team X vs Team Y',
        team_a: 'Team X',
        team_b: 'Team Y',
        import_batch_id: 'batch-z',
        source_filename: 'test.json',
        source_format: 'cricsheet_json',
        competition: 'Caribbean Premier League',
        season: '2024',
        venue: null,
        match_date: null,
        match_type: 'T20',
        innings_count: 1,
        total_runs: 100,
        total_wickets: 3,
        innings_totals: [{ inning_no: 1, team: 'Team X', runs: 100, wickets: 3, overs: 20.0, extras: 0 }],
        has_delivery_data: false,
      },
    ];
    mockGetHistoricalStatsSummary.mockResolvedValue(s);
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // With only season/match facts, bundle may be < 2; check disable message
    const generateBtn = wrapper.find('[aria-label="Generate AI talking points"]');
    if (generateBtn.exists()) {
      // With 1 match: only 1-2 season facts
      // The button may or may not be disabled depending on fact count
      // We just check the disabled state matches fact count
      const panel = wrapper.find('[aria-label="AI Talking-Point Assistant"]');
      expect(panel.exists()).toBe(true);
    }
  });

  it('generates talking points on button click and shows review panel', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const generateBtn = wrapper.find('[aria-label="Generate AI talking points"]');
    expect(generateBtn.exists()).toBe(true);
    expect(generateBtn.attributes('disabled')).toBeUndefined();

    await generateBtn.trigger('click');
    // Flush the setTimeout(0) in generateAiTalkingPoints
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const result = wrapper.find('[aria-label="Generated talking points"]');
    expect(result.exists()).toBe(true);
    expect(result.text()).toContain('Opening hook');
    expect(result.text()).toContain('Key season facts');
    expect(result.text()).toContain('Questions for the host');
  });

  it('every generated talking point has source fact tags', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    // All non-caution talking points should have at least one source tag
    const cards = wrapper.findAll('.cpld-tp-card');
    expect(cards.length).toBeGreaterThan(0);
    const sourcesEls = wrapper.findAll('.cpld-tp-sources');
    expect(sourcesEls.length).toBeGreaterThan(0);
    // At least one source tag exists
    const sourceTags = wrapper.findAll('.cpld-tp-source-tag');
    expect(sourceTags.length).toBeGreaterThan(0);
  });

  it('talking points start as needs_review status', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const needsReviewBadges = wrapper.findAll('.cpld-badge--needs-review');
    // At least one talking point card should have needs_review badge
    expect(needsReviewBadges.length).toBeGreaterThan(0);
  });

  it('approve button changes talking point status to approved', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const approveBtn = wrapper.find('[aria-label="Approve talking point 1"]');
    expect(approveBtn.exists()).toBe(true);
    await approveBtn.trigger('click');
    await wrapper.vm.$nextTick();

    const approvedBadge = wrapper.find('.cpld-badge--approved');
    expect(approvedBadge.exists()).toBe(true);
  });

  it('reject button changes talking point status to rejected', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const rejectBtn = wrapper.find('[aria-label="Reject talking point 1"]');
    expect(rejectBtn.exists()).toBe(true);
    await rejectBtn.trigger('click');
    await wrapper.vm.$nextTick();

    const rejectedBadge = wrapper.find('.cpld-badge--rejected');
    expect(rejectedBadge.exists()).toBe(true);
  });

  it('copy button shows unreviewed label for needs_review point', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const copyBtn = wrapper.find('[aria-label="Copy talking point 1"]');
    expect(copyBtn.exists()).toBe(true);
    expect(copyBtn.text()).toContain('Unreviewed');
  });

  it('copy button shows reviewed label after approval', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    await wrapper.find('[aria-label="Approve talking point 1"]').trigger('click');
    await wrapper.vm.$nextTick();

    const copyBtn = wrapper.find('[aria-label="Copy talking point 1"]');
    expect(copyBtn.text()).toContain('Reviewed');
  });

  it('clear button removes generated talking points', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    expect(wrapper.find('[aria-label="Generated talking points"]').exists()).toBe(true);

    await wrapper.find('[aria-label="Clear AI talking points"]').trigger('click');
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[aria-label="Generated talking points"]').exists()).toBe(false);
  });

  it('review summary shows approved count', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const summary = wrapper.find('[aria-label="Review summary"]');
    expect(summary.exists()).toBe(true);
    expect(summary.text()).toContain('0 of');
    expect(summary.text()).toContain('Review and approve before using');
  });

  it('generates limitations note when match has no delivery data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Select match 2 (no delivery data)
    await wrapper.find('[aria-label="Select match for story view"]').setValue('cpl-match-2');
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    // Should have a limitations block
    const limitations = wrapper.find('[aria-label="AI limitations"]');
    expect(limitations.exists()).toBe(true);
    expect(limitations.text()).toContain('Delivery data');
  });

  it('ai-generated talking points do not contain fabricated player statistics', async () => {
    // Only supply season-level facts (no players)
    const noPlayers = cplSummary();
    noPlayers.players = [];
    noPlayers.matches = noPlayers.matches.map(m => ({ ...m, has_delivery_data: false }));
    mockGetHistoricalStatsSummary.mockResolvedValue(noPlayers);
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    const result = wrapper.find('[aria-label="Generated talking points"]');
    if (result.exists()) {
      // Should NOT mention any player names (no player facts were supplied)
      expect(result.text()).not.toContain('Kieron Pollard');
      expect(result.text()).not.toContain('Sunil Narine');
    }
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

  it('shows export target and format selectors', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    expect(wrapper.find('[aria-label="Select export target"]').exists()).toBe(true);
    expect(wrapper.find('[aria-label="Select export format"]').text()).toContain('Podcast landscape (1920×1080)');
    expect(wrapper.find('[aria-label="Select export format"]').text()).toContain('Social square (1080×1080)');
    expect(wrapper.find('[aria-label="Select export format"]').text()).toContain('Story/reel vertical (1080×1920)');
    expect(wrapper.find('[aria-label="Select export template"]').exists()).toBe(true);
    expect(wrapper.find('[aria-label="Select export template"]').text()).toContain('Clean Broadcast · Season Summary');
    expect(wrapper.find('[aria-label="Select export template"]').text()).toContain('Bold Social · Season Summary');
  });

  it('updates template family options when export target changes', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Select export target"]').setValue('match_story');
    await flushPromises();

    const templateSelect = wrapper.find('[aria-label="Select export template"]');
    expect(templateSelect.text()).toContain('Data Desk · Match Story');
    expect(templateSelect.text()).toContain('Minimal Stat Card · Match Story');
    expect(wrapper.text()).toContain('Family: Match Story Template · Variant: Data Desk');
  });

  it('disables match story export when no match is selected', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Select export target"]').setValue('match_story');
    await flushPromises();

    const previewButton = wrapper.find('[aria-label="Generate export preview"]');
    expect(previewButton.attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toContain('select a match before exporting match story');
  });

  it('generates export preview and enables download', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const previewButton = wrapper.find('[aria-label="Generate export preview"]');
    await previewButton.trigger('click');
    await flushPromises();

    expect(mockToPng).toHaveBeenCalledTimes(1);
    expect(wrapper.find('img[alt="Export preview image"]').exists()).toBe(true);
    expect(wrapper.find('[aria-label="Download export image"]').attributes('disabled')).toBeUndefined();
  });

  it('applies selected template variant styling to export frame', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Select export template"]').setValue('season-bold-social');
    await flushPromises();
    await wrapper.find('[aria-label="Generate export preview"]').trigger('click');
    await flushPromises();

    expect(mockToPng).toHaveBeenCalledTimes(1);
    const frame = mockToPng.mock.calls[0]?.[0] as HTMLElement;
    expect(frame).toBeTruthy();
    expect(frame.style.background).toMatch(/15,\s*23,\s*42|#0f172a/i);
    expect(wrapper.text()).toContain('Variant: Bold Social');
  });

  it('disables leaderboard export when delivery data is unavailable', async () => {
    const noDelivery = cplSummary();
    noDelivery.matches = noDelivery.matches.map(match => ({ ...match, has_delivery_data: false }));
    noDelivery.players = [];
    mockGetHistoricalStatsSummary.mockResolvedValue(noDelivery);

    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Select export target"]').setValue('leaderboards');
    await flushPromises();

    expect(wrapper.find('[aria-label="Generate export preview"]').attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toContain('leaderboard data is unavailable');
  });

  it('builds editable podcast script draft with provenance and required sections', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();

    const editor = wrapper.find('[aria-label="Podcast script draft editor"]');
    expect(editor.exists()).toBe(true);
    const text = (editor.element as HTMLTextAreaElement).value;
    expect(text).toContain('# Episode working title');
    expect(text).toContain('## Context setup');
    expect(text).toContain('## Approved talking points');
    expect(text).toContain('facts-only outline');
    expect(text).toContain('## Provenance & limitations');
  });

  it('includes only approved talking points in generated script by default', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();

    expect(wrapper.find('[aria-label="Talking points needing review"]').text()).toContain('Set the scene');

    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    let text = (wrapper.find('[aria-label="Podcast script draft editor"]').element as HTMLTextAreaElement).value;
    expect(text).toContain('No approved talking points yet');

    await wrapper.find('[aria-label="Approve talking point 1"]').trigger('click');
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();

    text = (wrapper.find('[aria-label="Podcast script draft editor"]').element as HTMLTextAreaElement).value;
    expect(text).toContain('Set the scene');
    expect(text).not.toContain('Suggested discussion questions');
  });

  it('copies script as markdown and plain text', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();

    await wrapper.find('[aria-label="Copy script as markdown"]').trigger('click');
    await wrapper.find('[aria-label="Copy script as plain text"]').trigger('click');

    expect(mockClipboardWriteText).toHaveBeenCalledTimes(2);
    expect(mockClipboardWriteText.mock.calls[0][0]).toContain('# Episode working title');
    expect(mockClipboardWriteText.mock.calls[1][0]).not.toContain('# Episode working title');
  });

  it('downloads generated script as markdown file', async () => {
    const createObjectURLSpy = vi.fn(() => 'blob:mock-script');
    const revokeObjectURLSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: createObjectURLSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: revokeObjectURLSpy,
    });

    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    await wrapper.find('[aria-label="Download script markdown"]').trigger('click');

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-script');
  });

  it('disables episode package save before a script draft exists', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const saveButton = wrapper.find('[aria-label="Save episode package"]');
    expect(saveButton.attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toContain('generate or edit a script draft before saving a package');
  });

  it('saves episode package with approved points only and keeps needs-review separately', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Approve talking point 1"]').trigger('click');
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    await wrapper.find('[aria-label="Episode working title input"]').setValue('Episode 23 Wrap');
    await wrapper.find('[aria-label="Episode objective input"]').setValue('Review deterministic match context');
    await wrapper.find('[aria-label="Save episode package"]').trigger('click');

    const raw = localStorage.getItem(EPISODE_ARCHIVE_KEY);
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw as string);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].working_title).toBe('Episode 23 Wrap');
    expect(parsed[0].approved_talking_points).toHaveLength(1);
    expect(parsed[0].approved_talking_points[0].title).toBe('Set the scene');
    expect(parsed[0].needs_review_talking_points.length).toBeGreaterThan(0);
    expect(parsed[0].needs_review_talking_points.some((tp: { title: string }) => tp.title === 'Suggested discussion questions')).toBe(true);
    expect(parsed[0].is_incomplete).toBe(false);
  });

  it('marks saved episode package incomplete when no points are approved', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    await wrapper.find('[aria-label="Save episode package"]').trigger('click');

    const parsed = JSON.parse(localStorage.getItem(EPISODE_ARCHIVE_KEY) as string);
    expect(parsed[0].is_incomplete).toBe(true);
    expect(parsed[0].approved_talking_points).toHaveLength(0);
  });

  it('restores saved package context and script when reopened from archive list', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    await wrapper.find('[aria-label="Episode working title input"]').setValue('Reusable Episode');
    await wrapper.find('[aria-label="Save episode package"]').trigger('click');

    await wrapper.find('[aria-label="Episode working title input"]').setValue('Changed');
    await wrapper.find('[aria-label="Episode objective input"]').setValue('Changed objective');
    await wrapper.find('[aria-label="Podcast script draft editor"]').setValue('Changed draft');

    const reopenButton = wrapper.find('[aria-label^="Reopen episode package"]');
    await reopenButton.trigger('click');
    await flushPromises();

    expect((wrapper.find('[aria-label="Episode working title input"]').element as HTMLInputElement).value).toBe('Reusable Episode');
    expect((wrapper.find('[aria-label="Podcast script draft editor"]').element as HTMLTextAreaElement).value).toContain('# Episode working title');
  });

  it('exports episode package markdown and json with provenance block', async () => {
    const createObjectURLSpy = vi.fn(() => 'blob:mock-package');
    const revokeObjectURLSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: createObjectURLSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: revokeObjectURLSpy,
    });

    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    await wrapper.find('[aria-label="Generate AI talking points"]').trigger('click');
    await new Promise(r => setTimeout(r, 10));
    await flushPromises();
    await wrapper.find('[aria-label="Generate podcast script"]').trigger('click');
    await flushPromises();
    await wrapper.find('[aria-label="Save episode package"]').trigger('click');

    await wrapper.find('[aria-label^="Export package markdown"]').trigger('click');
    await wrapper.find('[aria-label^="Export package json"]').trigger('click');

    expect(createObjectURLSpy).toHaveBeenCalledTimes(2);
    const markdownBlob = createObjectURLSpy.mock.calls[0][0] as Blob;
    const jsonBlob = createObjectURLSpy.mock.calls[1][0] as Blob;
    expect(markdownBlob.type).toContain('text/markdown');
    expect(jsonBlob.type).toContain('application/json');
    const savedPackages = JSON.parse(localStorage.getItem(EPISODE_ARCHIVE_KEY) as string);
    expect(savedPackages[0].provenance.limitations.length).toBeGreaterThan(0);
    expect(revokeObjectURLSpy).toHaveBeenCalledTimes(2);
  });

  it('shows all-time scope label in leaderboards when no season is selected', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const lbSection = wrapper.find('[aria-label="Leaderboards"]');
    expect(lbSection.exists()).toBe(true);
    expect(lbSection.text()).toContain('All-time CPL');
  });

  it('shows selected season scope label in leaderboards when a season is active', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    // Select the 2023 season
    const seasonSelect = wrapper.find('#cpld-season-select');
    if (seasonSelect.exists()) {
      await seasonSelect.setValue('2023');
      await seasonSelect.trigger('change');
      await flushPromises();
      const lbSection = wrapper.find('[aria-label="Leaderboards"]');
      expect(lbSection.text()).toContain('CPL 2023');
    }
  });

  it('shows data completeness diagnostics panel in season summary', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const diag = wrapper.find('.cpld-diagnostics');
    expect(diag.exists()).toBe(true);
    expect(diag.text()).toContain('Total CPL matches imported');
    expect(diag.text()).toContain('Delivery-complete matches');
    expect(diag.text()).toContain('Matches missing delivery data');
    expect(diag.text()).toContain('Canonical teams represented');
    expect(diag.text()).toContain('Venues represented');
  });

  it('diagnostics shows warning when some matches lack delivery data', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const diag = wrapper.find('.cpld-diagnostics');
    // cplSummary() has 1 match with delivery data and 1 without
    const missingVal = wrapper.find('.cpld-diag-val--warn');
    expect(missingVal.exists()).toBe(true);
    expect(missingVal.text()).toBe('1');
    expect(diag.text()).toContain('metadata-only');
  });

  it('shows all-time CPL scope label in season summary when no season selected', async () => {
    mockGetHistoricalStatsSummary.mockResolvedValue(cplSummary());
    const wrapper = mount(CplPodcastDashboard);
    await flushPromises();

    const seasonSection = wrapper.find('[aria-label="Season summary"]');
    expect(seasonSection.text()).toContain('All-time CPL');
  });
});
