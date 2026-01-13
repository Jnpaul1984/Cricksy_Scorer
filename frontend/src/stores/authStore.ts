import { defineStore } from 'pinia';

import { getStoredToken, setStoredToken } from '@/services/api';
import { getCurrentUser, logout as authLogout } from '@/services/auth';
import type { AuthUser, UserRole, SubscriptionInfo } from '@/types/auth';

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
}

const isSuperuser = (state: AuthState): boolean =>
  state.user?.role === 'superuser' || Boolean(state.user?.is_superuser);

function isUnauthorizedError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const status = (err as { status?: number }).status;
  return status === 401;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: getStoredToken(),
    loading: false,
  }),
  getters: {
    currentUser: (state): AuthUser | null => state.user,
    isLoggedIn: (state) => Boolean(state.user),
    role: (state): UserRole | null => state.user?.role ?? null,
    is: (state) => (role: UserRole) => (state.user?.role ?? null) === role,
    isFreeUser: (state) => !state.user || state.user.role === 'free',
    isPlayerPro: (state) => state.user?.role === 'player_pro',
    isCoachPro: (state) => state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || isSuperuser(state),
    isCoachProPlus: (state) => state.user?.role === 'coach_pro_plus' || state.user?.role === 'org_pro' || isSuperuser(state),
    isAnalystPro: (state) => state.user?.role === 'analyst_pro' || isSuperuser(state),
    isOrgPro: (state) => state.user?.role === 'org_pro' || isSuperuser(state),
    isSuperuser,
    canScore: (state) =>
      isSuperuser(state) || state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || state.user?.role === 'org_pro',
    canAnalyze: (state) =>
      isSuperuser(state) || state.user?.role === 'analyst_pro' || state.user?.role === 'org_pro',
    canManageTournaments: (state) =>
      isSuperuser(state) || state.user?.role === 'org_pro',
    // Legacy helpers used across the app
    isOrg: (state) => state.user?.role === 'org_pro' || isSuperuser(state),
    isCoach: (state) => state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || isSuperuser(state),
    isAnalyst: (state) => state.user?.role === 'analyst_pro' || isSuperuser(state),
    isPlayer: (state) => state.user?.role === 'player_pro',
    isSuper: (state) => isSuperuser(state),
    // New profile-related getters
    userName: (state): string => state.user?.name || state.user?.email?.split('@')[0] || '',
    userEmail: (state): string => state.user?.email || '',
    userId: (state): string => state.user?.id || '',
    createdAt: (state): string | null => state.user?.created_at || null,
    orgId: (state): string | null => state.user?.org_id || null,
    subscription: (state): SubscriptionInfo | null => state.user?.subscription || null,
    planName: (state): string => state.user?.subscription?.plan || state.user?.role || 'free',
    requiresPasswordChange: (state): boolean => state.user?.requires_password_change || false,
  },
  actions: {
    hasAnyRole(roles: UserRole[]): boolean {
      const currentRole = this.user?.role ?? null;
      if (this.isSuperuser) return true;
      if (!currentRole) return false;
      return roles.includes(currentRole);
    },
    requireRole(...roles: UserRole[]): boolean {
      return this.hasAnyRole(roles);
    },
    async loadUser() {
      const storedToken = getStoredToken();
      this.token = storedToken;
      if (!storedToken || this.loading) {
        return;
      }
      this.loading = true;
      try {
        const user = await getCurrentUser();
        if (user) {
          this.user = user;
          return;
        }
        this.user = null;
        this.token = null;
        setStoredToken(null);
      } catch (error) {
        if (isUnauthorizedError(error)) {
          this.user = null;
          this.token = null;
          setStoredToken(null);
          return;
        }
        console.error('Failed to load current user', error);
      } finally {
        this.loading = false;
      }
    },
    async logout() {
      authLogout();
      this.user = null;
      this.token = null;
    },
  },
});
