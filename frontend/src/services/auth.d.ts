import type { AuthUser } from '@/types/auth';
export interface AuthLoginResult {
    token: string;
    user: AuthUser | null;
}
export declare function login(email: string, password: string): Promise<AuthLoginResult>;
export declare function register(email: string, password: string): Promise<AuthLoginResult>;
export declare function getCurrentUser(): Promise<AuthUser | null>;
export declare function logout(): void;
export declare function changePassword(currentPassword: string, newPassword: string): Promise<{
    id: string;
    email: string;
    message: string;
}>;
