import { defineStore } from 'pinia';

import type { AuthUser } from '@/types/auth';
import { getCurrentUser, logout as authLogout } from '@/services/auth';
import { getStoredToken, setStoredToken } from '@/services/api';

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
    isLoggedIn: (state) => Boolean(state.user),
    role: (state) => state.user?.role ?? 'free',
    isOrg(): boolean {
      return this.role === 'org_pro';
    },
    isCoach(): boolean {
      return this.role === 'coach_pro';
    },
    isAnalyst(): boolean {
      return this.role === 'analyst_pro';
    },
    isPlayer(): boolean {
      return this.role === 'player_pro';
    },
    isSuper(): boolean {
      return this.role === 'superuser';
    },
  },
  actions: {
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
