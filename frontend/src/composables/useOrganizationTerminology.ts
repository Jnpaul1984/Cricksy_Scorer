import type { FreeOrganizationType } from '@/types/schoolAdmin';

export interface OrganizationTerminology {
  kindLabel: 'School' | 'Club';
  kindLabelLower: 'school' | 'club';
  kindLabelPlural: 'Schools' | 'Clubs';
  kindLabelPluralLower: 'schools' | 'clubs';
  freePlanLabel: 'School Free' | 'Club Free';
  ownerLabel: 'School Owner' | 'Club Owner';
  directoryLabel: 'Your Schools' | 'Your Clubs';
}

const TERMINOLOGY: Record<FreeOrganizationType, OrganizationTerminology> = {
  school: {
    kindLabel: 'School',
    kindLabelLower: 'school',
    kindLabelPlural: 'Schools',
    kindLabelPluralLower: 'schools',
    freePlanLabel: 'School Free',
    ownerLabel: 'School Owner',
    directoryLabel: 'Your Schools',
  },
  club: {
    kindLabel: 'Club',
    kindLabelLower: 'club',
    kindLabelPlural: 'Clubs',
    kindLabelPluralLower: 'clubs',
    freePlanLabel: 'Club Free',
    ownerLabel: 'Club Owner',
    directoryLabel: 'Your Clubs',
  },
};

export function organizationTerminology(
  organizationType: FreeOrganizationType,
): OrganizationTerminology {
  return TERMINOLOGY[organizationType];
}

export function organizationBasePath(organizationType: FreeOrganizationType): string {
  return organizationType === 'club' ? '/clubs' : '/schools';
}
