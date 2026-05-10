type Member = {
    sid: string;
    role: string;
    name: string;
};
export declare function useRealtime(): {
    socket: Socket;
    connected: any;
    join: (gameId: string, role?: "SCORER" | "COMMENTATOR" | "ANALYST" | "VIEWER", name?: string) => void;
    leave: (gameId: string) => void;
    on: <T = any>(event: string, handler: (p: T) => void) => void;
    off: (event: string, handler?: (...args: any[]) => void) => void;
    getMembers: (gameId: string) => Member[];
};
export {};
