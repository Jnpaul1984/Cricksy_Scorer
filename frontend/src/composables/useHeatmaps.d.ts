interface HeatmapPoint {
    zone: string;
    x_coordinate: number;
    y_coordinate: number;
    value: number;
    count: number;
    detail: string;
}
interface HeatmapResponse {
    status: string;
    player_id?: string;
    player_name?: string;
    bowler_id?: string;
    bowler_name?: string;
    heatmap?: {
        heatmap_id: string;
        heatmap_type: string;
        data_points: HeatmapPoint[];
        average_value: number;
        total_events: number;
        metadata: Record<string, any>;
    };
    message?: string;
}
interface MatchupResponse {
    status: string;
    matchup?: {
        batter_id: string;
        batter_name: string;
        bowler_id: string;
        bowler_name: string;
        total_deliveries: number;
        dangerous_areas: string[];
        weak_overlap_areas: string[];
        dismissal_zones: string[];
        recommendation: string;
    };
}
export declare const useHeatmaps: () => {
    isLoading: any;
    fetchScoresHeatmap: (playerId: string) => Promise<HeatmapResponse | null>;
    fetchDismissalHeatmap: (playerId: string) => Promise<HeatmapResponse | null>;
    fetchReleaseZones: (bowlerId: string) => Promise<HeatmapResponse | null>;
    fetchMatchup: (batterId: string, bowlerId: string) => Promise<MatchupResponse | null>;
    fetchGameHeatmapSummary: (gameId: string, teamSide: "a" | "b") => Promise<any | null>;
};
export {};
