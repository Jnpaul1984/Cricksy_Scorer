import { computed, type ComputedRef, type Ref } from 'vue';

import type { PracticeWorkflowState } from '@/services/schoolAdminApi';
import type { SchoolTeamRosterPlayer } from '@/types/schoolAdmin';

/**
 * Maps the private, organization-authorized workflow response into display-only
 * scorer data. It deliberately has no game store, socket, or public-statistics
 * dependency: labels can only come from the frozen private participant lists.
 */
export function usePrivatePracticeScorerAdapter(
  state: Ref<PracticeWorkflowState | null>,
  teamA: ComputedRef<SchoolTeamRosterPlayer[]>,
  teamB: ComputedRef<SchoolTeamRosterPlayer[]>,
  batting: ComputedRef<SchoolTeamRosterPlayer[]>,
  bowling: ComputedRef<SchoolTeamRosterPlayer[]>,
) {
  const labels = computed(() => new Map([...teamA.value, ...teamB.value].map((player) => [player.player_profile_id, player.player_name])));
  const snapshot = computed(() => state.value?.snapshot ?? {});
  const id = (key: string, fallback: string) => String(snapshot.value[key] ?? fallback ?? '');
  const label = (playerId: string) => labels.value.get(playerId) || 'Unavailable participant';
  const strikerId = computed(() => id('current_striker_id', batting.value[0]?.player_profile_id || ''));
  const nonStrikerId = computed(() => id('current_non_striker_id', batting.value[1]?.player_profile_id || ''));
  const bowlerId = computed(() => id('current_bowler_id', bowling.value[0]?.player_profile_id || ''));

  return {
    strikerId, nonStrikerId, bowlerId,
    strikerName: computed(() => label(strikerId.value)),
    nonStrikerName: computed(() => label(nonStrikerId.value)),
    bowlerName: computed(() => label(bowlerId.value)),
    totalRuns: computed(() => Number(snapshot.value.total_runs ?? 0)),
    totalWickets: computed(() => Number(snapshot.value.total_wickets ?? 0)),
    overs: computed(() => `${Number(snapshot.value.overs_completed ?? 0)}.${Number(snapshot.value.balls_this_over ?? 0)}`),
    target: computed(() => snapshot.value.target == null ? null : Number(snapshot.value.target)),
    inning: computed(() => Number(snapshot.value.current_inning ?? 1)),
  };
}
