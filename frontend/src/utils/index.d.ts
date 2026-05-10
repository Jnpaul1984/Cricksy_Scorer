export * from './api';
export declare const debounce: <T extends (...args: any[]) => any>(func: T, delay: number) => ((...args: Parameters<T>) => void);
export declare const throttle: <T extends (...args: any[]) => any>(func: T, limit: number) => ((...args: Parameters<T>) => void);
export declare const formatOvers: (balls: number) => string;
export declare const formatScore: (runs: number, wickets: number) => string;
export declare const isValidUUID: (uuid: string) => boolean;
export declare const isValidPlayerName: (name: string) => boolean;
export declare const isValidTeamName: (name: string) => boolean;
export declare const formatDate: (date: Date) => string;
export declare const storage: {
    get: <T>(key: string, defaultValue: T) => T;
    set: <T>(key: string, value: T) => void;
    remove: (key: string) => void;
};
export declare const handleApiError: (error: unknown) => string;
export declare const CRICKET_CONSTANTS: {
    readonly BALLS_PER_OVER: 6;
    readonly MAX_OVERS_25: 25;
    readonly MAX_WICKETS: 10;
    readonly MIN_PLAYERS_PER_TEAM: 4;
    readonly MAX_PLAYERS_PER_TEAM: 15;
};
