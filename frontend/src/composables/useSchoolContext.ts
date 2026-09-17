import type { ComputedRef, InjectionKey, Ref } from 'vue';
import { inject } from 'vue';

import type { SchoolEntitlement, SchoolMembership, SchoolOrganization } from '@/types/schoolAdmin';

export interface SchoolContext {
  organizationId: ComputedRef<string>;
  organization: Ref<SchoolOrganization | null>;
  membership: Ref<SchoolMembership | null>;
  entitlement: Ref<SchoolEntitlement | null>;
  canManageTeams: ComputedRef<boolean>;
  canManageRosterMetadata: ComputedRef<boolean>;
  canManageRosterLifecycle: ComputedRef<boolean>;
  canManageTeamRoster: ComputedRef<boolean>;
  canImport: ComputedRef<boolean>;
}

export const schoolContextKey: InjectionKey<SchoolContext> = Symbol('school-context');

export function useSchoolContext(): SchoolContext {
  const context = inject(schoolContextKey);
  if (!context) throw new Error('School context is unavailable');
  return context;
}
