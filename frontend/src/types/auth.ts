export type UserRole =
  | 'free'
  | 'player_pro'
  | 'coach_pro'
  | 'analyst_pro'
  | 'org_pro'
  | 'superuser';

export interface SubscriptionInfo {
  plan: string;
  status: string;
  renewal_date: string | null;
  tokens_used: number;
  tokens_limit: number | null;
}

export interface AuthUser {
  id: string;
  email: string;
  name?: string | null;
  role: UserRole;
  is_superuser?: boolean;
  is_active?: boolean;
  org_id?: string | null;
  subscription?: SubscriptionInfo | null;
  created_at?: string | null;
  requires_password_change?: boolean;
  [key: string]: unknown;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}
