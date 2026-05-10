export interface ApiResponse<T> {
    data: T;
    status: number;
    success?: boolean;
    error?: string;
}
export interface UseApi {
    get: <T>(path: string) => Promise<ApiResponse<T>>;
    post: <T>(path: string, body: any) => Promise<ApiResponse<T>>;
    put: <T>(path: string, body: any) => Promise<ApiResponse<T>>;
    delete: <T>(path: string) => Promise<ApiResponse<T>>;
}
export declare function useApi(): UseApi;
