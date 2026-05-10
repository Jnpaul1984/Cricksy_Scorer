import type { AuthUser } from '@/types/auth';
export interface AuthState {
    user: AuthUser | null;
    token: string | null;
    loading: boolean;
}
export declare const useAuthStore: any;
