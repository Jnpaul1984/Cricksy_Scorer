export type DLSKind = 'odi' | 't20';
export declare function fetchRevisedTarget(gameId: string, kind?: DLSKind): Promise<{
    R1_total: number;
    R2_total: number;
    S1: number;
    target: number;
}>;
export declare function fetchPar(gameId: string, kind?: DLSKind): Promise<{
    R1_total: number;
    R2_used: number;
    S1: number;
    par: number;
    ahead_by: number;
}>;
