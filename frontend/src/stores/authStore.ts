import { defineStore } from 'pinia';

import type { AuthUser, UserRole } from '@/types/auth';
import { getCurrentUser, logout as authLogout } from '@/services/auth';
import { getStoredToken, setStoredToken } from '@/services/api';

const SCORING_ROLES: ReadonlyArray<UserRole> = ['coach_pro', 'org_pro', 'superuser'];
const ANALYTICS_ROLES: ReadonlyArray<UserRole> = ['analyst_pro', 'org_pro', 'superuser'];
const TOURNAMENT_ROLES: ReadonlyArray<UserRole> = ['org_pro', 'superuser'];

function isUnauthorizedError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const status = (err as { status?: number }).status;
  return status === 401;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
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
    isCoachPro: (state) => state.user?.role === 'coach_pro',
    isAnalystPro: (state) => state.user?.role === 'analyst_pro',
    isOrgPro: (state) => state.user?.role === 'org_pro',
    isSuperuser: (state) => state.user?.role === 'superuser',
    canScore: (state) => SCORING_ROLES.includes((state.user?.role ?? 'free') as UserRole),
    canAnalyze: (state) => ANALYTICS_ROLES.includes((state.user?.role ?? 'free') as UserRole),
    canManageTournaments: (state) => TOURNAMENT_ROLES.includes((state.user?.role ?? 'free') as UserRole),
    // Legacy helpers used across the app
    isOrg: (state) => state.user?.role === 'org_pro',
    isCoach: (state) => state.user?.role === 'coach_pro',
    isAnalyst: (state) => state.user?.role === 'analyst_pro',
    isPlayer: (state) => state.user?.role === 'player_pro',
    isSuper: (state) => state.user?.role === 'superuser',
  },
  actions: {
    hasAnyRole(roles: UserRole[]): boolean {
      const currentRole = this.user?.role ?? null;
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
