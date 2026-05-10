export interface DeliveryData {
    id: number;
    over_number: number;
    ball_number: number;
    bowler_id: string;
    striker_id: string;
    runs_off_bat?: number;
    extra_type?: string | null;
    extra_runs?: number;
    runs_scored?: number;
    is_wicket?: boolean;
    dismissal_type?: string | null;
    dismissed_player_id?: string | null;
    commentary?: string | null;
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;
