import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest } from '@/services/api';
import {
  addTeamRosterPlayer,
  applyPlayerImport,
  createSchoolMatch,
  listSchoolPlayers,
  previewPlayerImport,
} from '@/services/schoolAdminApi';

vi.mock('@/services/api', () => ({ apiRequest: vi.fn() }));

describe('schoolAdminApi', () => {
  beforeEach(() => vi.resetAllMocks());

  it('scopes roster reads by organization and lifecycle status', async () => {
    vi.mocked(apiRequest).mockResolvedValue([]);
    await listSchoolPlayers('school A/1', 'inactive');
    expect(apiRequest).toHaveBeenCalledWith(
      '/api/organizations/school%20A%2F1/players?status=inactive',
    );
  });

  it('assigns exact School membership IDs and never writes Team.players', async () => {
    vi.mocked(apiRequest).mockResolvedValue({});
    await addTeamRosterPlayer('school-a', 'team-a', 'membership-a');
    const [, options] = vi.mocked(apiRequest).mock.calls[0];
    expect(options?.body).toBe(JSON.stringify({ school_player_membership_id: 'membership-a' }));
    expect(String(options?.body)).not.toContain('Team.players');
    expect(String(options?.body)).not.toContain('player_profile_id');
  });

  it.each(['players.csv', 'players.xlsx'])(
    'sends %s as multipart preview without mutation payload',
    async (filename) => {
      vi.mocked(apiRequest).mockResolvedValue({});
      const file = new File(['player_name\nAsha'], filename);
      await previewPlayerImport('school-a', file, { 'Student Name': 'player_name' });
      const [path, options] = vi.mocked(apiRequest).mock.calls[0];
      expect(path).toBe('/api/organizations/school-a/player-imports/preview');
      expect(options?.method).toBe('POST');
      expect(options?.body).toBeInstanceOf(FormData);
      expect((options?.body as FormData).get('file')).toBe(file);
      expect((options?.body as FormData).get('column_mapping')).toBe(
        '{"Student Name":"player_name"}',
      );
    },
  );

  it('applies only explicit row resolution fields', async () => {
    vi.mocked(apiRequest).mockResolvedValue({});
    const resolutions = [
      {
        source_row_number: 2,
        action: 'use_existing' as const,
        school_player_membership_id: 'allowed-a',
        team_id: 'team-a',
      },
    ];
    await applyPlayerImport('school-a', 'import-a', resolutions);
    const [path, options] = vi.mocked(apiRequest).mock.calls[0];
    expect(path).toBe('/api/organizations/school-a/player-imports/import-a/apply');
    expect(JSON.parse(String(options?.body))).toEqual({ resolutions });
  });

  it('creates a match through the organization-scoped School contract', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ game_id: 'game-a' });
    const payload = {
      team_a: {
        team_id: 'team-a',
        playing_xi_membership_ids: Array.from({ length: 11 }, (_, index) => `a-${index}`),
        captain_membership_id: 'a-0',
        wicketkeeper_membership_id: 'a-1',
      },
      team_b: {
        team_id: 'team-b',
        playing_xi_membership_ids: Array.from({ length: 11 }, (_, index) => `b-${index}`),
        captain_membership_id: 'b-0',
        wicketkeeper_membership_id: 'b-1',
      },
      match_type: 'limited' as const,
      overs_limit: 20,
      days_limit: null,
      overs_per_day: null,
      dls_enabled: false,
      toss_winner_side: 'team_a' as const,
      decision: 'bat' as const,
    };

    await createSchoolMatch('school A/1', payload);

    expect(apiRequest).toHaveBeenCalledWith('/api/organizations/school%20A%2F1/matches', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  });
});
