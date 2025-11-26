import { apiRequest, setStoredToken, getStoredToken } from './api';

import type { AuthUser, AuthTokenResponse } from '@/types/auth';

export interface AuthLoginResult {
  token: string;
  user: AuthUser | null;
}

function isUnauthorizedError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const status = (err as { status?: number }).status;
  return status === 401;
}

async function fetchToken(email: string, password: string): Promise<AuthTokenResponse> {
  const params = new URLSearchParams();
  params.set('username', email);
  params.set('password', password);
  return apiRequest<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    body: params,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
}

export async function login(email: string, password: string): Promise<AuthLoginResult> {
  const tokenResponse = await fetchToken(email, password);
  setStoredToken(tokenResponse.access_token);
  const user = await getCurrentUser();
  return { token: tokenResponse.access_token, user };
}

export async function register(email: string, password: string): Promise<AuthLoginResult> {
  await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return login(email, password);
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  if (!getStoredToken()) return null;
  try {
    return await apiRequest<AuthUser>('/auth/me');
  } catch (err) {
    if (isUnauthorizedError(err)) {
      return null;
    }
    throw err;
  }
}

export function logout() {
  setStoredToken(null);
}
