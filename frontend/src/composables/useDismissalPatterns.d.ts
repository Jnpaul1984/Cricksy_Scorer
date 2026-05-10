interface DismissalPattern {
    pattern_name: string;
    pattern_type: string;
    dismissal_count: number;
    dismissal_percentage: number;
    severity: string;
    context: string;
    recommendation: string;
    confidence?: number;
}
interface CriticalSituation {
    situation_type: string;
    dismissal_count: number;
    risk_level: string;
    scenario_description: string;
}
interface PlayerAnalysis {
    player_id: string;
    player_name: string;
    analysis: {
        total_dismissals: number;
        dismissals_by_type: Record<string, number>;
        dismissals_by_phase: Record<string, number>;
        dismissals_by_delivery: Record<string, number>;
        overall_vulnerability_score: number;
        primary_vulnerability: string;
        secondary_vulnerabilities: string[];
        top_patterns: DismissalPattern[];
        critical_situations: CriticalSituation[];
        improvement_areas: string[];
    };
}
interface TeamAnalysis {
    status: string;
    game_id: string;
    team_side: string;
    team_analysis: {
        total_team_dismissals: number;
        vulnerable_players: Array<{
            player_name: string;
            vulnerability_score: number;
        }>;
        phase_vulnerability: Record<string, number>;
        team_recommendations: string[];
    };
    player_details: Array<{
        player_name: string;
        total_dismissals: number;
        vulnerability_score: number;
        primary_vulnerability: string;
        top_patterns: DismissalPattern[];
    }>;
}
interface VulnerabilityScore {
    status: string;
    player_id: string;
    player_name: string;
    vulnerability_score: number;
    risk_level: string;
    primary_vulnerability: string;
    total_dismissals: number;
}
interface DismissalTrend {
    status: string;
    player_id: string;
    player_name: string;
    trend: {
        period: string;
        dismissal_count: number;
        average_runs_at_dismissal: number;
        average_deliveries_faced: number;
        trend_direction: string;
    };
}
export declare function useDismissalPatterns(): {
    loading: any;
    error: any;
    fetchPlayerAnalysis: (playerId: string) => Promise<PlayerAnalysis | null>;
    fetchTeamAnalysis: (gameId: string, teamSide: "a" | "b") => Promise<TeamAnalysis | null>;
    fetchVulnerabilityScore: (playerId: string) => Promise<VulnerabilityScore | null>;
    fetchDismissalTrend: (playerId: string, period?: "last_5" | "last_10" | "last_20") => Promise<DismissalTrend | null>;
    getRiskColor: (riskLevel: string) => string;
    formatDismissalType: (dismissalType: string) => string;
    getSeverityIcon: (severity: string) => string;
    getRiskLevelText: (score: number) => string;
};
export {};
