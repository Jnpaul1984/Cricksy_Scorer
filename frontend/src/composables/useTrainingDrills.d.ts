interface TrainingDrill {
    drill_id: string;
    name: string;
    description: string;
    category: string;
    severity: string;
    reason?: string;
    reps_or_count: number;
    duration_minutes: number;
    focus_area: string;
    difficulty: number;
    recommended_frequency?: string;
    expected_improvement?: string;
}
interface DrillPlan {
    player_id: string;
    player_name?: string;
    drills: TrainingDrill[];
    high_priority_count?: number;
    medium_priority_count?: number;
    low_priority_count?: number;
    total_weekly_hours?: number;
    focus_areas?: string[];
}
interface DrillCategory {
    category: string;
    templates: Array<{
        name: string;
        description: string;
        duration_minutes: number;
        reps_or_count: number;
        focus_area: string;
        difficulty: number;
    }>;
}
export declare function useTrainingDrills(): {
    loading: any;
    error: any;
    fetchPlayerDrills: (playerId: string) => Promise<{
        drill_plan: DrillPlan;
    } | null>;
    fetchTeamDrills: (gameId: string, teamSide: "a" | "b") => Promise<{
        team_drills: Array<{
            player_name: string;
            drill_plan: DrillPlan;
        }>;
    } | null>;
    fetchDrillCategories: () => Promise<{
        categories: DrillCategory[];
    } | null>;
    getSeverityColor: (severity: string) => string;
    getDifficultyColor: (difficulty: number) => string;
    formatDuration: (minutes: number) => string;
    formatFrequency: (frequency: string) => string;
};
export {};
