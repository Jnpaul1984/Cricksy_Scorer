export interface Player {
    id: string;
    name: string;
}
export interface Coach {
    id: string;
    name: string;
}
export interface Team {
    id?: string;
    name: string;
    home_ground?: string;
    season?: string;
    coach_id?: string;
    coach_name?: string;
    players: Player[];
    competitions?: {
        id: string;
        name: string;
    }[];
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;
