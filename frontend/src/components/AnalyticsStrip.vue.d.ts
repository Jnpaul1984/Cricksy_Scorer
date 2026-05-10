type Batter = {
    id: string;
    name: string;
    runs: number;
    balls: number;
};
export type Snapshot = {
    score: {
        runs: number;
        wickets: number;
        overs: number;
    };
    batsmen: {
        striker: Batter;
        non_striker: Batter;
    };
};
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;
