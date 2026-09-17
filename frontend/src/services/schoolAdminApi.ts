import { apiRequest } from '@/services/api';
import type {
  PlayerImportPreview,
  PlayerImportResolution,
  PlayerImportResult,
  SchoolEntitlement,
  SchoolMembership,
  SchoolOrganization,
  SchoolRosterPlayer,
  SchoolTeam,
  SchoolTeamInput,
  SchoolTeamRosterPlayer,
} from '@/types/schoolAdmin';

const orgPath = (organizationId: string, suffix = '') =>
  `/api/organizations/${encodeURIComponent(organizationId)}${suffix}`;

export const listSchools = () => apiRequest<SchoolOrganization[]>('/api/organizations');
export const getSchool = (organizationId: string) =>
  apiRequest<SchoolOrganization>(orgPath(organizationId));
export const getMySchoolMembership = (organizationId: string) =>
  apiRequest<SchoolMembership>(orgPath(organizationId, '/me'));
export const getSchoolEntitlement = (organizationId: string) =>
  apiRequest<SchoolEntitlement>(orgPath(organizationId, '/entitlements'));

export const listSchoolTeams = (organizationId: string) =>
  apiRequest<SchoolTeam[]>(orgPath(organizationId, '/teams'));
export const getSchoolTeam = (organizationId: string, teamId: string) =>
  apiRequest<SchoolTeam>(orgPath(organizationId, `/teams/${encodeURIComponent(teamId)}`));
export const createSchoolTeam = (organizationId: string, payload: SchoolTeamInput) =>
  apiRequest<SchoolTeam>(orgPath(organizationId, '/teams'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
export const updateSchoolTeam = (
  organizationId: string,
  teamId: string,
  payload: Partial<SchoolTeamInput>,
) =>
  apiRequest<SchoolTeam>(orgPath(organizationId, `/teams/${encodeURIComponent(teamId)}`), {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
export const archiveSchoolTeam = (organizationId: string, teamId: string) =>
  apiRequest<void>(orgPath(organizationId, `/teams/${encodeURIComponent(teamId)}`), {
    method: 'DELETE',
  });

export const listSchoolPlayers = (
  organizationId: string,
  status: 'active' | 'inactive' | 'all' = 'active',
) => apiRequest<SchoolRosterPlayer[]>(orgPath(organizationId, `/players?status=${status}`));
export const createSchoolPlayer = (
  organizationId: string,
  payload: { player_name: string; student_identifier?: string | null; year_group?: string | null },
) =>
  apiRequest<SchoolRosterPlayer>(orgPath(organizationId, '/players'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
export const updateSchoolPlayer = (
  organizationId: string,
  membershipId: string,
  payload: {
    student_identifier?: string | null;
    year_group?: string | null;
    status?: 'active' | 'inactive';
  },
) =>
  apiRequest<SchoolRosterPlayer>(
    orgPath(organizationId, `/players/${encodeURIComponent(membershipId)}`),
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  );
export const deactivateSchoolPlayer = (organizationId: string, membershipId: string) =>
  apiRequest<void>(orgPath(organizationId, `/players/${encodeURIComponent(membershipId)}`), {
    method: 'DELETE',
  });

export const listTeamRoster = (organizationId: string, teamId: string) =>
  apiRequest<SchoolTeamRosterPlayer[]>(
    orgPath(organizationId, `/teams/${encodeURIComponent(teamId)}/players`),
  );
export const addTeamRosterPlayer = (
  organizationId: string,
  teamId: string,
  schoolPlayerMembershipId: string,
) =>
  apiRequest<SchoolTeamRosterPlayer>(
    orgPath(organizationId, `/teams/${encodeURIComponent(teamId)}/players`),
    {
      method: 'POST',
      body: JSON.stringify({ school_player_membership_id: schoolPlayerMembershipId }),
    },
  );
export const setTeamRosterPlayerStatus = (
  organizationId: string,
  teamId: string,
  teamRosterMembershipId: string,
  status: 'active' | 'inactive',
) =>
  apiRequest<SchoolTeamRosterPlayer>(
    orgPath(
      organizationId,
      `/teams/${encodeURIComponent(teamId)}/players/${encodeURIComponent(teamRosterMembershipId)}`,
    ),
    { method: 'PATCH', body: JSON.stringify({ status }) },
  );
export const deactivateTeamRosterPlayer = (
  organizationId: string,
  teamId: string,
  teamRosterMembershipId: string,
) =>
  apiRequest<void>(
    orgPath(
      organizationId,
      `/teams/${encodeURIComponent(teamId)}/players/${encodeURIComponent(teamRosterMembershipId)}`,
    ),
    { method: 'DELETE' },
  );

export const previewPlayerImport = (
  organizationId: string,
  file: File,
  columnMapping?: Record<string, string>,
) => {
  const form = new FormData();
  form.append('file', file);
  if (columnMapping && Object.keys(columnMapping).length) {
    form.append('column_mapping', JSON.stringify(columnMapping));
  }
  return apiRequest<PlayerImportPreview>(orgPath(organizationId, '/player-imports/preview'), {
    method: 'POST',
    body: form,
  });
};

export const applyPlayerImport = (
  organizationId: string,
  importId: string,
  resolutions: PlayerImportResolution[],
) =>
  apiRequest<PlayerImportResult>(
    orgPath(organizationId, `/player-imports/${encodeURIComponent(importId)}/apply`),
    { method: 'POST', body: JSON.stringify({ resolutions }) },
  );
