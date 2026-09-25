import { apiRequest } from '@/services/api';
import type {
  OrganizationCalendar,
  OrganizationAvailabilityFilter,
  OrganizationAvailabilityState,
  OrganizationAvailabilitySummary,
  OrganizationAvailabilityTarget,
  OrganizationAvailabilityTargetType,
  OrganizationEvent,
  OrganizationEventInput,
  PlayerImportPreview,
  PlayerImportResolution,
  PlayerImportResult,
  SchoolEntitlement,
  SchoolCompetition,
  SchoolCompetitionTeam,
  SchoolFixture,
  SchoolFixtureSummary,
  SchoolMembership,
  SchoolMatchCreate,
  SchoolMatchCreateResult,
  SchoolOrganization,
  SchoolCreateInput,
  SchoolRosterPlayer,
  SchoolMatchResult,
  SchoolPlayerStatistics,
  SchoolPublicationState,
  SchoolStandings,
  SchoolTeam,
  SchoolTeamInput,
  SchoolTeamRosterPlayer,
  SchoolTeamStatistics,
  PublicSchoolScorecard,
  FreeOrganizationType,
  OrganizationPlayerAvailability,
} from '@/types/schoolAdmin';

const orgPath = (organizationId: string, suffix = '') =>
  `/api/organizations/${encodeURIComponent(organizationId)}${suffix}`;

export const listOrganizations = async (organizationType?: FreeOrganizationType) => {
  const organizations = await apiRequest<SchoolOrganization[]>('/api/organizations');
  return organizationType
    ? organizations.filter((organization) => organization.organization_type === organizationType)
    : organizations;
};
export const listSchools = () => listOrganizations('school');
export const listClubs = () => listOrganizations('club');
export const createOrganization = (payload: SchoolCreateInput & { organization_type: FreeOrganizationType }) =>
  apiRequest<SchoolOrganization>('/api/organizations', {
    method: 'POST',
    body: JSON.stringify({ name: payload.name, organization_type: payload.organization_type }),
  });
export const createSchool = (payload: SchoolCreateInput) =>
  createOrganization({ name: payload.name, organization_type: 'school' });
export const createClub = (payload: SchoolCreateInput) =>
  createOrganization({ name: payload.name, organization_type: 'club' });
export const getSchool = (organizationId: string) =>
  apiRequest<SchoolOrganization>(orgPath(organizationId));
export const getMySchoolMembership = (organizationId: string) =>
  apiRequest<SchoolMembership>(orgPath(organizationId, '/me'));
export const getSchoolEntitlement = (organizationId: string) =>
  apiRequest<SchoolEntitlement>(orgPath(organizationId, '/entitlements'));

export const listOrganizationEvents = (
  organizationId: string,
  options: {
    upcoming?: boolean;
    includeCancelled?: boolean;
    teamId?: string;
    limit?: number;
    offset?: number;
  } = {},
) => {
  const params = new URLSearchParams();
  if (options.upcoming !== undefined) params.set('upcoming', String(options.upcoming));
  if (options.includeCancelled !== undefined) {
    params.set('include_cancelled', String(options.includeCancelled));
  }
  if (options.teamId) params.set('team_id', options.teamId);
  if (options.limit !== undefined) params.set('limit', String(options.limit));
  if (options.offset !== undefined) params.set('offset', String(options.offset));
  const query = params.toString();
  return apiRequest<{ items: OrganizationEvent[]; total: number; limit: number; offset: number }>(
    orgPath(organizationId, `/events${query ? `?${query}` : ''}`),
  );
};
export const createOrganizationEvent = (organizationId: string, payload: OrganizationEventInput) =>
  apiRequest<OrganizationEvent>(orgPath(organizationId, '/events'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
export const updateOrganizationEvent = (
  organizationId: string,
  eventId: string,
  payload: Partial<OrganizationEventInput>,
) =>
  apiRequest<OrganizationEvent>(orgPath(organizationId, `/events/${encodeURIComponent(eventId)}`), {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
export const cancelOrganizationEvent = (organizationId: string, eventId: string) =>
  apiRequest<OrganizationEvent>(
    orgPath(organizationId, `/events/${encodeURIComponent(eventId)}/cancel`),
    { method: 'POST' },
  );
export const getOrganizationCalendar = (
  organizationId: string,
  options: { upcoming?: boolean; includeCancelled?: boolean; teamId?: string; limit?: number } = {},
) => {
  const params = new URLSearchParams();
  if (options.upcoming !== undefined) params.set('upcoming', String(options.upcoming));
  if (options.includeCancelled !== undefined) {
    params.set('include_cancelled', String(options.includeCancelled));
  }
  if (options.teamId) params.set('team_id', options.teamId);
  if (options.limit !== undefined) params.set('limit', String(options.limit));
  const query = params.toString();
  return apiRequest<OrganizationCalendar>(
    orgPath(organizationId, `/calendar${query ? `?${query}` : ''}`),
  );
};

export const getOrganizationAvailability = (
  organizationId: string,
  targetType: OrganizationAvailabilityTargetType,
  targetId: string,
  options: {
    state?: OrganizationAvailabilityFilter;
    teamId?: string;
    limit?: number;
    offset?: number;
  } = {},
) => {
  const params = new URLSearchParams();
  if (options.state) params.set('state', options.state);
  if (options.teamId) params.set('team_id', options.teamId);
  if (options.limit !== undefined) params.set('limit', String(options.limit));
  if (options.offset !== undefined) params.set('offset', String(options.offset));
  const query = params.toString();
  return apiRequest<OrganizationAvailabilitySummary>(
    orgPath(
      organizationId,
      `/availability/${targetType}/${encodeURIComponent(targetId)}${query ? `?${query}` : ''}`,
    ),
  );
};

export const updateOrganizationAvailabilityDeadline = (
  organizationId: string,
  targetType: OrganizationAvailabilityTargetType,
  targetId: string,
  responseDeadline: string | null,
) =>
  apiRequest<OrganizationAvailabilityTarget>(
    orgPath(organizationId, `/availability/${targetType}/${encodeURIComponent(targetId)}`),
    {
      method: 'PATCH',
      body: JSON.stringify({ response_deadline: responseDeadline }),
    },
  );

export const recordOrganizationPlayerAvailability = (
  organizationId: string,
  targetType: OrganizationAvailabilityTargetType,
  targetId: string,
  rosterMembershipId: string,
  state: OrganizationAvailabilityState,
) =>
  apiRequest<OrganizationPlayerAvailability>(
    orgPath(
      organizationId,
      `/availability/${targetType}/${encodeURIComponent(targetId)}/players/${encodeURIComponent(rosterMembershipId)}`,
    ),
    { method: 'PUT', body: JSON.stringify({ state }) },
  );

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

export const createSchoolMatch = (organizationId: string, payload: SchoolMatchCreate) =>
  apiRequest<SchoolMatchCreateResult>(orgPath(organizationId, '/matches'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const listSchoolPlayerStatistics = (organizationId: string) =>
  apiRequest<SchoolPlayerStatistics[]>(orgPath(organizationId, '/statistics/players'));
export const getSchoolPlayerStatistics = (organizationId: string, playerProfileId: string) =>
  apiRequest<SchoolPlayerStatistics>(
    orgPath(organizationId, `/statistics/players/${encodeURIComponent(playerProfileId)}`),
  );
export const listSchoolTeamStatistics = (organizationId: string) =>
  apiRequest<SchoolTeamStatistics[]>(orgPath(organizationId, '/statistics/teams'));
export const getSchoolTeamStatistics = (organizationId: string, teamId: string) =>
  apiRequest<SchoolTeamStatistics>(
    orgPath(organizationId, `/statistics/teams/${encodeURIComponent(teamId)}`),
  );
export const listSchoolResults = (organizationId: string) =>
  apiRequest<SchoolMatchResult[]>(orgPath(organizationId, '/results'));
export const listSchoolFixtures = (organizationId: string) =>
  apiRequest<SchoolFixtureSummary[]>(orgPath(organizationId, '/fixtures'));

export const listSchoolCompetitions = (organizationId: string) =>
  apiRequest<SchoolCompetition[]>(orgPath(organizationId, '/competitions'));
export const createSchoolCompetition = (
  organizationId: string,
  payload: Pick<SchoolCompetition, 'name' | 'tournament_type' | 'status'> &
    Partial<Pick<SchoolCompetition, 'description' | 'start_date' | 'end_date'>>,
) =>
  apiRequest<SchoolCompetition>(orgPath(organizationId, '/competitions'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
export const updateSchoolCompetition = (
  organizationId: string,
  competitionId: string,
  payload: Partial<
    Pick<
      SchoolCompetition,
      'name' | 'description' | 'tournament_type' | 'start_date' | 'end_date' | 'status'
    >
  >,
) =>
  apiRequest<SchoolCompetition>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}`),
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
export const deleteSchoolCompetition = (organizationId: string, competitionId: string) =>
  apiRequest<void>(orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}`), {
    method: 'DELETE',
  });
export const listSchoolCompetitionTeams = (organizationId: string, competitionId: string) =>
  apiRequest<SchoolCompetitionTeam[]>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}/teams`),
  );
export const addSchoolCompetitionTeam = (
  organizationId: string,
  competitionId: string,
  teamId: string,
) =>
  apiRequest<SchoolCompetitionTeam>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}/teams`),
    { method: 'POST', body: JSON.stringify({ team_id: teamId }) },
  );
export const removeSchoolCompetitionTeam = (
  organizationId: string,
  competitionId: string,
  entrantId: number,
) =>
  apiRequest<void>(
    orgPath(
      organizationId,
      `/competitions/${encodeURIComponent(competitionId)}/teams/${entrantId}`,
    ),
    { method: 'DELETE' },
  );
export const listSchoolCompetitionFixtures = (organizationId: string, competitionId: string) =>
  apiRequest<SchoolFixture[]>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}/fixtures`),
  );
export const createSchoolFixture = (
  organizationId: string,
  competitionId: string,
  payload: {
    team_a_id: string;
    team_b_id: string;
    match_number?: number | null;
    venue?: string | null;
    scheduled_date?: string | null;
    status?: SchoolFixture['status'];
  },
) =>
  apiRequest<SchoolFixture>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}/fixtures`),
    { method: 'POST', body: JSON.stringify(payload) },
  );
export const updateSchoolFixture = (
  organizationId: string,
  competitionId: string,
  fixtureId: string,
  payload: Partial<Pick<SchoolFixture, 'match_number' | 'venue' | 'scheduled_date' | 'status'>>,
) =>
  apiRequest<SchoolFixture>(
    orgPath(
      organizationId,
      `/competitions/${encodeURIComponent(competitionId)}/fixtures/${encodeURIComponent(fixtureId)}`,
    ),
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
export const deleteSchoolFixture = (
  organizationId: string,
  competitionId: string,
  fixtureId: string,
) =>
  apiRequest<void>(
    orgPath(
      organizationId,
      `/competitions/${encodeURIComponent(competitionId)}/fixtures/${encodeURIComponent(fixtureId)}`,
    ),
    { method: 'DELETE' },
  );
export const linkSchoolFixtureGame = (
  organizationId: string,
  competitionId: string,
  fixtureId: string,
  gameId: string,
) =>
  apiRequest<SchoolFixture>(
    orgPath(
      organizationId,
      `/competitions/${encodeURIComponent(competitionId)}/fixtures/${encodeURIComponent(fixtureId)}/game`,
    ),
    { method: 'PUT', body: JSON.stringify({ game_id: gameId }) },
  );
export const getSchoolStandings = (organizationId: string, competitionId: string) =>
  apiRequest<SchoolStandings>(
    orgPath(organizationId, `/competitions/${encodeURIComponent(competitionId)}/standings`),
  );
export const updateSchoolMatchPublication = (
  organizationId: string,
  gameId: string,
  publicationState: SchoolPublicationState,
) =>
  apiRequest<{ game_id: string; organization_id: string; publication_state: SchoolPublicationState }>(
    orgPath(organizationId, `/matches/${encodeURIComponent(gameId)}/publication`),
    { method: 'PATCH', body: JSON.stringify({ publication_state: publicationState }) },
  );
export const getPublicSchoolScorecard = (gameId: string) =>
  apiRequest<PublicSchoolScorecard>(`/public/school-scorecards/${encodeURIComponent(gameId)}`);

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
