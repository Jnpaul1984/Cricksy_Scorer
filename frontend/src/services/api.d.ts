import type { MatchResult } from '@/types';
export type ScoreUpdatePayload = any;
export declare const API_BASE: string;
export declare const TOKEN_STORAGE_KEY = "cricksy_token";
type UnauthorizedHandler = (error: Error) => void;
export declare function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void;
export declare function getStoredToken(): string | null;
export declare function setStoredToken(token: string | null): void;
export declare function getErrorMessage(err: unknown): string;
export type TossDecision = 'bat' | 'bowl';
type ApiRequestOptions = RequestInit & {
    /** If true, do NOT attach the Authorization header even if a token is present. */
    noAuth?: boolean;
};
/** Low-level fetch wrapper that preserves JSON errors from FastAPI. */
declare function request<T>(path: string, init?: ApiRequestOptions): Promise<T>;
export declare function apiRequestPublic<T>(path: string, init?: RequestInit): Promise<T>;
export { request as apiRequest };
export type MatchType = 'limited' | 'multi_day' | 'custom';
export type Decision = 'bat' | 'bowl';
export type ExtraCode = 'nb' | 'wd' | 'b' | 'lb';
export interface CreateGameRequest {
    team_a_name: string;
    team_b_name: string;
    players_a: string[];
    players_b: string[];
    match_type?: MatchType;
    overs_limit?: number | null;
    days_limit?: number | null;
    overs_per_day?: number | null;
    dls_enabled?: boolean;
    interruptions?: Array<Record<string, string | null>>;
    toss_winner_team: string;
    decision: TossDecision;
}
export interface GameMinimal {
    id: string;
    team_a_name: string;
    team_b_name: string;
    match_type: MatchType;
    overs_limit: number | null;
    days_limit: number | null;
    dls_enabled: boolean;
    decision: TossDecision;
    [k: string]: any;
}
export interface ScoreDeliveryRequest {
    striker_id: string;
    non_striker_id: string;
    bowler_id: string;
    runs_off_bat?: number;
    runs_scored?: number;
    extra?: 'wd' | 'nb' | 'b' | 'lb';
    is_wicket: boolean;
    dismissal_type?: string | null;
    dismissed_player_id?: string | null;
    dismissed_player_name?: string | null;
    commentary?: string;
    fielder_id?: string | null;
    shot_angle_deg?: number | null;
    shot_map?: string | null;
}
export interface DeliveryCorrectionRequest {
    runs_scored?: number;
    runs_off_bat?: number;
    extra?: 'wd' | 'nb' | 'b' | 'lb' | null;
    is_wicket?: boolean;
    dismissal_type?: string | null;
    dismissed_player_id?: string | null;
    fielder_id?: string | null;
    shot_map?: string | null;
    shot_angle_deg?: number | null;
    commentary?: string | null;
}
export interface Snapshot {
    id?: string;
    status?: string;
    score?: {
        runs: number;
        wickets: number;
        overs: number | string;
    };
    batsmen: {
        striker: {
            id: string | null;
            name: string;
            runs: number;
            balls: number;
            is_out: boolean;
        };
        non_striker: {
            id: string | null;
            name: string;
            runs: number;
            balls: number;
            is_out: boolean;
        };
    };
    current_bowler: {
        id: string | null;
        name: string | null;
    };
    overs: string;
    total_runs?: number;
    total_wickets?: number;
    overs_completed?: number;
    balls_this_over?: number;
    current_inning?: number;
    batting_team_name?: string;
    bowling_team_name?: string;
    batting_scorecard?: Record<string, any>;
    bowling_scorecard?: Record<string, any>;
    last_delivery?: {
        over_number: number;
        ball_number: number;
        bowler_id: string;
        striker_id: string;
        non_striker_id: string;
        runs_off_bat?: number;
        extra_type?: ExtraCode | null;
        extra_runs?: number;
        runs_scored?: number;
        shot_map?: string | null;
    } | null;
    dls?: {
        method: 'DLS';
        par?: number;
        target?: number;
        ahead_by?: number;
    };
    extras_totals?: {
        wides: number;
        no_balls: number;
        byes: number;
        leg_byes: number;
        penalty: number;
        total: number;
    };
    fall_of_wickets?: Array<{
        score: number;
        wicket: number;
        batter_id: string;
        batter_name: string;
        over: string;
        dismissal_type?: string | null;
        bowler_id?: string | null;
        bowler_name?: string | null;
        fielder_id?: string | null;
        shot_angle_deg?: number | null;
        fielder_name?: string | null;
    }>;
    last_ball_bowler_id?: string | null;
    current_bowler_id?: string | null;
    balls_bowled_total?: number;
    needs_new_innings?: boolean;
    teams?: {
        batting: {
            name: string;
        };
        bowling: {
            name: string;
        };
    };
    players?: {
        batting: Array<{
            id: string;
            name: string;
        }>;
        bowling: Array<{
            id: string;
            name: string;
        }>;
    };
    interruptions?: Interruption[];
    mini_batting_card?: any[];
    mini_bowling_card?: any[];
    needs_new_batter?: boolean;
    needs_new_over?: boolean;
    [k: string]: any;
}
export interface OversLimitBody {
    overs_limit: number;
}
export type TeamSide = 'A' | 'B';
export interface TeamRoleUpdate {
    side: TeamSide;
    captain_id?: string | null;
    wicket_keeper_id?: string | null;
}
export interface ContributorIn {
    user_id: string;
    role: 'SCORER' | 'COMMENTATOR' | 'ANALYST' | 'VIEWER';
    display_name?: string | null;
}
export interface Contributor {
    id: number;
    game_id: string;
    user_id: string;
    role: ContributorIn['role'];
    display_name?: string | null;
}
export interface SponsorCreateBody {
    name: string;
    logo: File;
    click_url?: string | null;
    weight?: number;
    surfaces?: string[];
    start_at?: string | null;
    end_at?: string | null;
}
export interface SponsorRow {
    id: string;
    name: string;
    logoUrl: string;
    clickUrl?: string | null;
    weight: number;
    surfaces: string[];
    is_active?: boolean;
    start_at?: string | null;
    end_at?: string | null;
}
export interface SponsorImpressionIn {
    game_id: string;
    sponsor_id: string | number;
    at?: string | null;
}
export interface SponsorImpressionsOut {
    inserted: number;
    ids: number[];
}
export interface StartOverBody {
    bowler_id: string;
}
export interface ReplaceBatterBody {
    new_batter_id: string;
}
export interface MidOverChangeBody {
    new_bowler_id: string;
    reason?: 'injury' | 'other';
}
export interface OpenersBody {
    striker_id: string;
    non_striker_id: string;
}
export interface NextBatterBody {
    batter_id: string;
}
export interface StartNextInningsBody {
    striker_id?: string | null;
    non_striker_id?: string | null;
    opening_bowler_id?: string | null;
}
export type Interruption = {
    id: string;
    kind: 'weather' | 'injury' | 'light' | string;
    note?: string | null;
    started_at: string;
    ended_at?: string | null;
};
declare function getInterruptions(gameId: string): Promise<Interruption[]>;
/** POST /interruptions/start with best-effort encoding */
declare function openInterruption(gameId: string, kind?: 'weather' | 'injury' | 'light' | 'other' | string, note?: string): Promise<Interruption>;
/** POST /interruptions/stop  omit {"kind": null}. Accepts JSON, falls back to empty body. */
declare function stopInterruption(gameId: string, kind?: 'weather' | 'injury' | 'light' | 'other'): Promise<{
    ok: true;
    interruptions: Interruption[];
}>;
export { getInterruptions, openInterruption, stopInterruption };
export type DLSPreviewOut = {
    team1_score: number;
    team1_resources: number;
    team2_resources: number;
    target: number;
    format_overs: 20 | 50;
    G50: number;
};
export interface DlsRevisedTargetIn {
    kind: 'odi' | 't20';
    innings: 1 | 2;
    max_overs?: number;
}
export interface DlsRevisedTargetOut {
    R1_total: number;
    R2_total: number;
    S1: number;
    target: number;
}
export interface DlsParNowIn {
    kind: 'odi' | 't20';
    innings: 1 | 2;
    max_overs?: number;
}
export interface DlsParNowOut {
    R1_total: number;
    R2_used: number;
    S1: number;
    par: number;
    ahead_by: number;
}
export declare function getDlsPreview(gameId: string, G50?: number): Promise<DLSPreviewOut>;
export declare function postDlsApply(gameId: string, G50?: number): Promise<DLSPreviewOut & {
    applied: boolean;
}>;
export declare function patchReduceOvers(gameId: string, innings: 1 | 2, newOvers: number): Promise<{
    innings: number;
    new_overs: number;
    new_balls_limit: number;
}>;
export interface CaseStudyInningsSummary {
    team: string;
    runs: number;
    wickets: number;
    overs: number;
    run_rate: number;
}
export type CaseStudyPhaseImpact = "positive" | "negative" | "neutral";
export interface CaseStudyPhase {
    id: "powerplay" | "middle" | "death" | "custom";
    label: string;
    start_over: number;
    end_over: number;
    runs: number;
    wickets: number;
    run_rate: number;
    net_swing_vs_par: number;
    impact: CaseStudyPhaseImpact;
    impact_label: string;
}
export interface CaseStudyKeyPlayer {
    id: string;
    name: string;
    team: string;
    role: string;
    batting?: {
        innings: number;
        runs: number;
        balls: number;
        strike_rate: number;
        boundaries: {
            fours: number;
            sixes: number;
        };
    } | null;
    bowling?: {
        overs: number;
        maidens: number;
        runs: number;
        wickets: number;
        economy: number;
    } | null;
    fielding?: {
        catches: number;
        run_outs: number;
        drops: number;
    } | null;
    impact: "high" | "medium" | "low";
    impact_label: string;
    impact_score?: number | null;
}
export interface CaseStudyMatch {
    id: string;
    date: string;
    format: "T20" | "ODI" | "TEST" | "CUSTOM" | string;
    home_team?: string | null;
    away_team?: string | null;
    teams_label: string;
    venue?: string | null;
    result: string;
    overs_per_side?: number | null;
    innings: CaseStudyInningsSummary[];
}
export interface CaseStudyMomentumSummary {
    title: string;
    subtitle: string;
    winning_side?: string | null;
    swing_metric?: {
        runs_above_par?: number | null;
        win_probability_shift?: number | null;
    } | null;
}
export interface CaseStudyKeyPhase {
    title: string;
    detail: string;
    overs_range?: {
        start_over: number;
        end_over: number;
    } | null;
    reason_codes?: string[];
}
export interface CaseStudyDismissalPatterns {
    summary?: string | null;
    by_bowler_type?: {
        type: string;
        wickets: number;
    }[];
    by_shot_type?: {
        shot: string;
        wickets: number;
    }[];
    by_zone?: {
        zone: string;
        wickets: number;
    }[];
}
export interface CaseStudyAIBlock {
    match_summary: string;
    generated_at?: string | null;
    model_version?: string | null;
    tokens_used?: number | null;
}
export interface MatchCaseStudyResponse {
    match: CaseStudyMatch;
    momentum_summary: CaseStudyMomentumSummary;
    key_phase: CaseStudyKeyPhase;
    phases: CaseStudyPhase[];
    key_players: CaseStudyKeyPlayer[];
    dismissal_patterns?: CaseStudyDismissalPatterns | null;
    ai?: CaseStudyAIBlock | null;
}
export declare function getMatchCaseStudy(matchId: string): Promise<MatchCaseStudyResponse>;
export interface MatchAiSummaryTeam {
    team_id: string;
    team_name: string;
    result: 'won' | 'lost' | 'tied' | 'no_result';
    total_runs: number;
    wickets_lost: number;
    overs_faced: number;
    key_stats: string[];
}
export interface DecisivePhaseSummary {
    phase_id: string;
    innings: number;
    label: string;
    over_range: [number, number];
    impact_score: number;
    narrative: string;
}
export interface MomentumShiftSummary {
    shift_id: string;
    innings: number;
    over: number;
    description: string;
    impact_delta: number;
    team_benefiting_id: string;
}
export interface PlayerHighlightSummary {
    player_id: string;
    player_name: string;
    team_id: string;
    role: string;
    highlight_type: string;
    summary: string;
}
export interface MatchAiSummary {
    match_id: string;
    format: string;
    teams: MatchAiSummaryTeam[];
    key_themes: string[];
    decisive_phases: DecisivePhaseSummary[];
    momentum_shifts: MomentumShiftSummary[];
    player_highlights: PlayerHighlightSummary[];
    overall_summary: string;
    created_at: string;
    headline?: string;
    narrative?: string;
    tactical_themes?: string[];
    tags?: string[];
    generated_at?: string;
}
export declare function getMatchAiSummary(matchId: string): Promise<MatchAiSummary>;
export interface AnalystMatchListItem {
    id: string;
    date: string;
    format: string;
    teams: string;
    result: string;
    run_rate: number;
    phase_swing: string;
}
export interface AnalystMatchListResponse {
    items: AnalystMatchListItem[];
    total: number;
}
export declare function getAnalystMatches(): Promise<AnalystMatchListResponse>;
export interface MatchCommentaryItem {
    over: number | null;
    ball_index: number | null;
    event_tags: string[];
    text: string;
    tone: 'neutral' | 'hype' | 'critical';
    created_at: string;
}
export interface MatchAiCommentaryResponse {
    match_id: string;
    commentary: MatchCommentaryItem[];
}
export declare function fetchMatchAiCommentary(matchId: string): Promise<MatchAiCommentaryResponse>;
export interface AICommentaryRequest {
    match_id: string;
    over: number;
    ball: number;
    runs: number;
    wicket: boolean;
    batter: string;
    bowler: string;
    context?: Record<string, unknown>;
}
export interface AICommentaryResponse {
    commentary: string;
}
export declare function generateAICommentary(payload: AICommentaryRequest): Promise<AICommentaryResponse>;
export interface PlayerAIRecentForm {
    label: string;
    trend: number[];
}
export interface PlayerAIInsights {
    player_id: string;
    summary: string;
    strengths: string[];
    weaknesses: string[];
    recent_form: PlayerAIRecentForm;
    role_tags: string[];
    recommendations: string[];
}
export declare function getPlayerAIInsights(playerId: string): Promise<PlayerAIInsights>;
export interface FanMatchCreate {
    home_team_name: string;
    away_team_name: string;
    match_type?: string;
    overs_limit?: number | null;
}
export interface FanMatchRead {
    id: string;
    home_team_name: string;
    away_team_name: string;
    match_type: string;
    overs_limit: number | null;
    is_fan_match: boolean;
}
export type FanFavoriteType = 'player' | 'team';
export interface FanFavoriteCreate {
    favorite_type: FanFavoriteType;
    player_profile_id?: string | null;
    team_id?: string | null;
}
export interface FanFavoriteRead {
    id: string;
    favorite_type: FanFavoriteType;
    player_profile_id: string | null;
    team_id: string | null;
    created_at: string;
    player_name?: string | null;
    team_name?: string | null;
}
export declare const apiService: {
    createGame: (body: CreateGameRequest) => Promise<GameMinimal>;
    getGame: (gameId: string) => Promise<GameMinimal>;
    getSnapshot: (gameId: string) => Promise<Snapshot>;
    getResults(gameId: string): Promise<MatchResult | null>;
    searchGames: (team_a?: string, team_b?: string) => Promise<{
        id: string;
        team_a_name: string;
        team_b_name: string;
        status?: string;
    }[]>;
    createFanMatch: (body: FanMatchCreate) => Promise<FanMatchRead>;
    listFanMatches: (limit?: number, offset?: number) => Promise<FanMatchRead[]>;
    getFanMatch: (matchId: string) => Promise<FanMatchRead>;
    getFanFavorites: () => Promise<FanFavoriteRead[]>;
    createFanFavorite: (payload: FanFavoriteCreate) => Promise<FanFavoriteRead>;
    deleteFanFavorite: (favoriteId: string) => Promise<void>;
    scoreDelivery: (gameId: string, body: ScoreDeliveryRequest) => Promise<Snapshot>;
    correctDelivery: (gameId: string, deliveryId: number, body: DeliveryCorrectionRequest) => Promise<Snapshot>;
    undoLast: (gameId: string) => Promise<Snapshot>;
    setOversLimit: (gameId: string, body: OversLimitBody | number) => Promise<{
        id: string;
        overs_limit: number;
    }>;
    dlsRevisedTarget: (gameId: string, body: DlsRevisedTargetIn) => Promise<DlsRevisedTargetOut>;
    dlsParNow: (gameId: string, body: DlsParNowIn) => Promise<DlsParNowOut>;
    setTeamRoles: (gameId: string, body: TeamRoleUpdate) => Promise<{
        ok: true;
        team_roles: any;
    }>;
    startOver: (gameId: string, bowler_id: string) => Promise<{
        ok: true;
        current_bowler_id: string;
    }>;
    changeBowlerMidOver: (gameId: string, new_bowler_id: string, reason?: "injury" | "other") => Promise<Snapshot>;
    replaceBatter: (gameId: string, new_batter_id: string) => Promise<Snapshot>;
    setNextBatter: (gameId: string, batter_id: string) => Promise<{
        ok: true;
        current_striker_id: string;
    }>;
    deliveries: (gameId: string, params?: {
        innings?: number;
        limit?: number;
        order?: "asc" | "desc";
    }) => Promise<{
        game_id: string;
        count: number;
        deliveries: any[];
    }>;
    recentDeliveries: (gameId: string, limit?: number) => Promise<{
        game_id: string;
        count: number;
        deliveries: any[];
    }>;
    setOpeners: (gameId: string, body: OpenersBody) => Promise<Snapshot>;
    getInterruptions: typeof getInterruptions;
    openInterruption: typeof openInterruption;
    stopInterruption: typeof stopInterruption;
    addContributor: (gameId: string, body: ContributorIn) => Promise<Contributor>;
    listContributors: (gameId: string) => Promise<Contributor[]>;
    removeContributor: (gameId: string, contribId: number) => Promise<{
        ok: true;
    }>;
    uploadSponsor: (body: SponsorCreateBody) => Promise<any>;
    /** List all sponsors (active + inactive) */
    getSponsors: () => Promise<SponsorRow[]>;
    /** Get a single sponsor by ID */
    getSponsor: (sponsorId: string) => Promise<SponsorRow>;
    /** Update an existing sponsor (partial update) */
    updateSponsor: (sponsorId: string, body: {
        name?: string;
        logo_url?: string;
        click_url?: string | null;
        weight?: number;
        is_active?: boolean;
        start_at?: string | null;
        end_at?: string | null;
    }) => Promise<SponsorRow>;
    /** Delete a sponsor */
    deleteSponsor: (sponsorId: string) => Promise<{
        status: string;
    }>;
    getGameSponsors: (gameId: string) => Promise<SponsorRow[]>;
    logSponsorImpressions: (payload: SponsorImpressionIn | SponsorImpressionIn[]) => Promise<SponsorImpressionsOut>;
    healthz: () => Promise<{
        status: "ok";
    }>;
    createBetaUser: (payload: {
        email: string;
        role: string;
        plan: string;
        org_id?: string | null;
        beta_tag?: string | null;
        password?: string | null;
    }) => Promise<{
        id: string;
        email: string;
        role: string;
        plan: string;
        org_id: string | null;
        beta_tag: string | null;
        temp_password: string;
    }>;
    listBetaUsers: () => Promise<{
        id: string;
        email: string;
        role: string;
        is_active: boolean;
        created_at: string | null;
        beta_tag: string | null;
        org_id: string | null;
    }[]>;
    resetUserPassword: (userId: string, password?: string | null) => Promise<{
        id: string;
        email: string;
        temp_password: string;
    }>;
    deactivateUser: (userId: string) => Promise<{
        id: string;
        email: string;
        is_active: boolean;
    }>;
    reactivateUser: (userId: string) => Promise<{
        id: string;
        email: string;
        is_active: boolean;
    }>;
    startNextInnings: (gameId: string, body: StartNextInningsBody) => Promise<Snapshot>;
    createTournament: (body: {
        name: string;
        description?: string | null;
        tournament_type?: string;
        start_date?: string | null;
        end_date?: string | null;
    }) => Promise<any>;
    getTournaments: (skip?: number, limit?: number) => Promise<any[]>;
    getTournament: (tournamentId: string) => Promise<any>;
    updateTournament: (tournamentId: string, body: {
        name?: string;
        description?: string | null;
        tournament_type?: string;
        start_date?: string | null;
        end_date?: string | null;
        status?: string;
    }) => Promise<any>;
    deleteTournament: (tournamentId: string) => Promise<{
        status: string;
    }>;
    addTeamToTournament: (tournamentId: string, body: {
        team_name: string;
        team_data?: any;
    }) => Promise<any>;
    getTournamentTeams: (tournamentId: string) => Promise<any[]>;
    getPointsTable: (tournamentId: string) => Promise<any[]>;
    createFixture: (body: {
        tournament_id: string;
        match_number?: number | null;
        team_a_name: string;
        team_b_name: string;
        venue?: string | null;
        scheduled_date?: string | null;
    }) => Promise<any>;
    getFixture: (fixtureId: string) => Promise<any>;
    getTournamentFixtures: (tournamentId: string) => Promise<any[]>;
    updateFixture: (fixtureId: string, body: {
        match_number?: number | null;
        team_a_name?: string;
        team_b_name?: string;
        venue?: string | null;
        scheduled_date?: string | null;
        status?: string;
        result?: string | null;
        game_id?: string | null;
    }) => Promise<any>;
    deleteFixture: (fixtureId: string) => Promise<{
        status: string;
    }>;
};
export default apiService;
