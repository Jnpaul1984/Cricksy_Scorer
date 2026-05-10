export interface BestBowlerSuggestion {
    bowler_id: string;
    bowler_name: string;
    reason: string;
    effectiveness_vs_batter: number;
    expected_economy: number;
    confidence: number;
}
export interface WeaknessAnalysis {
    primary_weakness: string;
    weakness_score: number;
    secondary_weakness?: string | null;
    recommended_line: string;
    recommended_length: string;
    recommended_speed?: number | null;
    confidence: number;
}
export interface FieldingZone {
    position: string;
    priority: number;
    coverage_reason: string;
}
export interface FieldingSetup {
    bowler_id: string;
    batter_id: string;
    primary_zone: string;
    recommended_positions: FieldingZone[];
    confidence: number;
    reasoning: string;
}
export interface TacticalSuggestions {
    game_id: string;
    timestamp?: string;
    suggestions?: {
        best_bowler?: BestBowlerSuggestion;
        weakness_analysis?: WeaknessAnalysis;
        fielding_setup?: FieldingSetup;
    };
    best_bowler?: BestBowlerSuggestion;
    weakness?: WeaknessAnalysis;
    fielding?: FieldingSetup;
}
export declare const useTacticalSuggestions: () => {
    suggestions: any;
    loading: any;
    error: any;
    fetchSuggestions: (gameId: string) => Promise<void>;
    fetchBestBowler: (gameId: string) => Promise<void>;
    fetchWeaknessAnalysis: (gameId: string) => Promise<void>;
    fetchFieldingSetup: (gameId: string) => Promise<void>;
    clearSuggestions: () => void;
};
