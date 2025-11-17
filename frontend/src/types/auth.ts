export type UserRole =
  | 'free'
  | 'player_pro'
  | 'coach_pro'
  | 'analyst_pro'
  | 'org_pro'
  | 'superuser';

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  full_name?: string | null;
  is_active?: boolean;
  [key: string]: unknown;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}
