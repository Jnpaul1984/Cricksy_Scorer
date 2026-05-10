export interface InningsGradeData {
    grade: 'A+' | 'A' | 'B' | 'C' | 'D';
    score_percentage: number;
    par_score: number;
    total_runs: number;
    run_rate: number;
    wickets_lost: number;
    wicket_efficiency: number;
    boundary_count: number;
    boundary_percentage: number;
    dot_ball_ratio: number;
    overs_played: number;
    grade_factors: {
        score_percentage_contribution: string;
        wicket_efficiency_contribution: string;
        strike_rotation_contribution: string;
        boundary_efficiency_contribution: string;
    };
    inning_num?: number;
    game_id?: string;
    batting_team?: string;
    bowling_team?: string;
}
export declare function useInningsGrade(): {
    grade: any;
    loading: any;
    error: any;
    gradeColor: any;
    gradeLabel: any;
    fetchCurrentGrade: (gameId: string, inningNum?: number) => Promise<void>;
    fetchInningGrade: (gameId: string, inningNum: number) => Promise<void>;
    clear: () => void;
};
