import type { ComputedRef, InjectionKey, Ref } from 'vue';
import { inject } from 'vue';

import type { OrganizationTerminology } from '@/composables/useOrganizationTerminology';
import type {
  FreeOrganizationType,
  SchoolEntitlement,
  SchoolMembership,
  SchoolOrganization,
} from '@/types/schoolAdmin';

export interface SchoolContext {
  organizationId: ComputedRef<string>;
  organizationType: ComputedRef<FreeOrganizationType>;
  organizationBasePath: ComputedRef<string>;
  terminology: ComputedRef<OrganizationTerminology>;
  organization: Ref<SchoolOrganization | null>;
  membership: Ref<SchoolMembership | null>;
  entitlement: Ref<SchoolEntitlement | null>;
  canManageTeams: ComputedRef<boolean>;
  canManageRosterMetadata: ComputedRef<boolean>;
  canManageRosterLifecycle: ComputedRef<boolean>;
  canManageTeamRoster: ComputedRef<boolean>;
  canImport: ComputedRef<boolean>;
  canCreateSchoolMatch: ComputedRef<boolean>;
  canViewStatistics: ComputedRef<boolean>;
  canViewFixturesResults: ComputedRef<boolean>;
  canViewCompetitions: ComputedRef<boolean>;
  canManageCompetitions: ComputedRef<boolean>;
  canDeleteCompetitions: ComputedRef<boolean>;
  canLinkFixtures: ComputedRef<boolean>;
  canPublishScorecards: ComputedRef<boolean>;
  canViewEvents: ComputedRef<boolean>;
  canManageEvents: ComputedRef<boolean>;
}

export const schoolContextKey: InjectionKey<SchoolContext> = Symbol('school-context');

export function useSchoolContext(): SchoolContext {
  const context = inject(schoolContextKey);
  if (!context) throw new Error('Organization context is unavailable');
  return context;
}
