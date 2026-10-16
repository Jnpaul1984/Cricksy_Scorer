<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  createPracticeMatch, getPracticeMatch, listSchoolTeams, listTeamRoster,
  scorePracticeDelivery, startPracticeInnings, startPracticeMatch, startPracticeOver, undoLastPracticeDelivery,
  type PracticeWorkflowState,
} from '@/services/schoolAdminApi';
import type { SchoolTeam, SchoolTeamRosterPlayer } from '@/types/schoolAdmin';
import { getErrorMessage } from '@/services/api';

const { organizationId, canCreateSchoolMatch, terminology } = useSchoolContext();
const route = useRoute(); const router = useRouter();
const teams = ref<SchoolTeam[]>([]);
const teamAId = ref(''); const teamBId = ref('');
const rosterA = ref<SchoolTeamRosterPlayer[]>([]); const rosterB = ref<SchoolTeamRosterPlayer[]>([]);
const frozenA = ref<SchoolTeamRosterPlayer[]>([]); const frozenB = ref<SchoolTeamRosterPlayer[]>([]);
const selectedA = ref<string[]>([]); const selectedB = ref<string[]>([]);
const firstSide = ref<'team_a' | 'team_b'>('team_a'); const overs = ref(2);
const state = ref<PracticeWorkflowState | null>(null); const gameId = ref('');
const loading = ref(false); const error = ref(''); const notice = ref('');
const nextOverBowlerId = ref('');
let loadGeneration = 0;
let organizationGeneration = 0;

const activeA = computed(() => rosterA.value.filter((p) => p.operationally_available));
const activeB = computed(() => rosterB.value.filter((p) => p.operationally_available));
const sideA = computed(() => frozenA.value.length ? frozenA.value : activeA.value.filter((p) => selectedA.value.includes(p.id)));
const sideB = computed(() => frozenB.value.length ? frozenB.value : activeB.value.filter((p) => selectedB.value.includes(p.id)));
const inning = computed(() => Number(state.value?.snapshot.current_inning ?? 1));
const firstBattingSide = computed(() => state.value?.practice_start_context.first_batting_side ?? firstSide.value);
const batting = computed(() => (inning.value === 1 ? firstBattingSide.value : (firstBattingSide.value === 'team_a' ? 'team_b' : 'team_a')) === 'team_a' ? sideA.value : sideB.value);
const bowling = computed(() => batting.value === sideA.value ? sideB.value : sideA.value);
const canCreate = computed(() => canCreateSchoolMatch.value && teamAId.value && teamBId.value && sideA.value.length >= 2 && sideB.value.length >= 2);
const revision = computed(() => state.value?.revision ?? 0);
const currentStriker = computed(() => String((state.value?.snapshot.current_striker_id as string | null) || batting.value[0]?.player_profile_id || ''));
const currentNonStriker = computed(() => String((state.value?.snapshot.current_non_striker_id as string | null) || batting.value[1]?.player_profile_id || ''));
const currentBowler = computed(() => String((state.value?.snapshot.current_bowler_id as string | null) || bowling.value[0]?.player_profile_id || ''));
const needsNextOver = computed(() => state.value?.status === 'in_progress' && !(state.value?.snapshot.current_bowler_id as string | null));
const secondInningsBatting = computed(() => firstBattingSide.value === 'team_a' ? sideB.value : sideA.value);
const secondInningsBowling = computed(() => firstBattingSide.value === 'team_a' ? sideA.value : sideB.value);

async function loadRoster(side: 'a' | 'b') {
  const id = side === 'a' ? teamAId.value : teamBId.value;
  if (!id) return;
  const generation = organizationGeneration; const requestedOrganizationId = organizationId.value; const requestedTeamId = id;
  const roster = await listTeamRoster(requestedOrganizationId, requestedTeamId);
  if (generation !== organizationGeneration || requestedOrganizationId !== organizationId.value || requestedTeamId !== (side === 'a' ? teamAId.value : teamBId.value)) return;
  if (side === 'a') { rosterA.value = roster; selectedA.value = roster.filter((p) => p.operationally_available).slice(0, 2).map((p) => p.id); }
  else { rosterB.value = roster; selectedB.value = roster.filter((p) => p.operationally_available).slice(0, 2).map((p) => p.id); }
}
function toggle(side: 'a' | 'b', id: string) {
  const selected = side === 'a' ? selectedA : selectedB;
  selected.value = selected.value.includes(id) ? selected.value.filter((value) => value !== id) : [...selected.value, id];
}
async function refetch(conflict = false) {
  if (!gameId.value) return;
  const generation = ++loadGeneration; const requestedGameId = gameId.value; const requestedOrganizationId = organizationId.value;
  const loaded = await getPracticeMatch(requestedOrganizationId, requestedGameId);
  if (generation !== loadGeneration || requestedGameId !== gameId.value || requestedOrganizationId !== organizationId.value) return;
  state.value = loaded;
  frozenA.value = state.value.frozen_sides.team_a.map((player) => ({ id: player.id, player_profile_id: player.id, player_name: player.label || 'Unavailable participant', operationally_available: true } as SchoolTeamRosterPlayer));
  frozenB.value = state.value.frozen_sides.team_b.map((player) => ({ id: player.id, player_profile_id: player.id, player_name: player.label || 'Unavailable participant', operationally_available: true } as SchoolTeamRosterPlayer));
  if (conflict) notice.value = 'This practice match changed in another tab. The latest private state has been loaded.';
}
function clearPrivateWorkflow() { loadGeneration += 1; gameId.value = ''; state.value = null; frozenA.value = []; frozenB.value = []; nextOverBowlerId.value = ''; notice.value = ''; error.value = ''; }
function clearOrganizationState() {
  organizationGeneration += 1; clearPrivateWorkflow(); teams.value = []; teamAId.value = ''; teamBId.value = '';
  rosterA.value = []; rosterB.value = []; selectedA.value = []; selectedB.value = []; loading.value = false;
}
async function loadOrganizationState() {
  clearOrganizationState(); const generation = organizationGeneration; const requestedOrganizationId = organizationId.value;
  if (!canCreateSchoolMatch.value) return;
  try {
    const loadedTeams = await listSchoolTeams(requestedOrganizationId);
    if (generation !== organizationGeneration || requestedOrganizationId !== organizationId.value) return;
    teams.value = loadedTeams;
    const requestedGameId = route.query.gameId;
    if (typeof requestedGameId === 'string' && requestedGameId) { gameId.value = requestedGameId; await refetch(); }
  } catch (reason) { if (generation === organizationGeneration && requestedOrganizationId === organizationId.value) error.value = getErrorMessage(reason); }
}
async function perform(action: () => Promise<PracticeWorkflowState | void>) {
  const generation = organizationGeneration; const requestedOrganizationId = organizationId.value;
  loading.value = true; error.value = ''; notice.value = '';
  try {
    const result = await action();
    if (generation !== organizationGeneration || requestedOrganizationId !== organizationId.value) return;
    if (result) state.value = result;
  }
  catch (reason) {
    if (generation !== organizationGeneration || requestedOrganizationId !== organizationId.value) return;
    if ((reason as { status?: number }).status === 409 && gameId.value) { await refetch(true); }
    else error.value = getErrorMessage(reason);
  } finally { if (generation === organizationGeneration && requestedOrganizationId === organizationId.value) loading.value = false; }
}
async function createAndStart() {
  await perform(async () => {
    const created = await createPracticeMatch(organizationId.value, {
      team_a: { source_squad_id: teamAId.value, participant_membership_ids: selectedA.value },
      team_b: { source_squad_id: teamBId.value, participant_membership_ids: selectedB.value }, overs: overs.value,
    });
    gameId.value = created.game_id;
    await router.replace({ query: { ...route.query, gameId: gameId.value } });
    await startPracticeMatch(organizationId.value, gameId.value, firstSide.value);
    const initial = await getPracticeMatch(organizationId.value, gameId.value);
    return startPracticeInnings(organizationId.value, gameId.value, {
      expected_revision: initial.revision,
      striker_id: batting.value[0].player_profile_id,
      non_striker_id: batting.value[1].player_profile_id,
      opening_bowler_id: bowling.value[0].player_profile_id,
    });
  });
}
function score(runs: number, wicket = false) {
  return perform(() => scorePracticeDelivery(organizationId.value, gameId.value, {
    expected_revision: revision.value, striker_id: currentStriker.value, non_striker_id: currentNonStriker.value,
    bowler_id: currentBowler.value, runs_scored: runs, is_wicket: wicket,
    ...(wicket ? { dismissal_type: 'bowled', dismissed_player_id: currentStriker.value } : {}),
  }));
}
async function undo() { await perform(() => undoLastPracticeDelivery(organizationId.value, gameId.value, revision.value)); }
function startSecondInnings() { return perform(() => startPracticeInnings(organizationId.value, gameId.value, { expected_revision: revision.value, striker_id: secondInningsBatting.value[0].player_profile_id, non_striker_id: secondInningsBatting.value[1].player_profile_id, opening_bowler_id: secondInningsBowling.value[0].player_profile_id })); }
function beginNextOver() { return perform(() => startPracticeOver(organizationId.value, gameId.value, { expected_revision: revision.value, bowler_id: nextOverBowlerId.value || bowling.value[0]?.player_profile_id || '' })); }
onMounted(loadOrganizationState);
watch(organizationId, loadOrganizationState);
watch(() => route.query.gameId, async () => { clearPrivateWorkflow(); const requestedGameId = route.query.gameId; if (!canCreateSchoolMatch.value || typeof requestedGameId !== 'string' || !requestedGameId) return; gameId.value = requestedGameId; try { await refetch(); } catch (reason) { if (gameId.value) error.value = getErrorMessage(reason); } });
</script>

<template>
  <section class="practice" data-testid="practice-match-view">
    <h2>Private practice match</h2><p>Only this {{ terminology.kindLabel }} can access this score. It is never published or broadcast.</p>
    <p v-if="!canCreateSchoolMatch" class="error">Your current role cannot create or score private practice matches.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <template v-if="!gameId && canCreateSchoolMatch">
      <label>Side A team <select v-model="teamAId" data-testid="practice-team-a" @change="loadRoster('a')"><option value="">Choose team</option><option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option></select></label>
      <div v-if="rosterA.length"><strong>Side A players</strong><label v-for="player in activeA" :key="player.id"><input type="checkbox" :checked="selectedA.includes(player.id)" @change="toggle('a', player.id)"> {{ player.player_name }}</label></div>
      <label>Side B team <select v-model="teamBId" data-testid="practice-team-b" @change="loadRoster('b')"><option value="">Choose team</option><option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option></select></label>
      <div v-if="rosterB.length"><strong>Side B players</strong><label v-for="player in activeB" :key="player.id"><input type="checkbox" :checked="selectedB.includes(player.id)" @change="toggle('b', player.id)"> {{ player.player_name }}</label></div>
      <label>Overs <input v-model.number="overs" type="number" min="1" max="120"></label><label>First batting side <select v-model="firstSide"><option value="team_a">Side A</option><option value="team_b">Side B</option></select></label>
      <button :disabled="!canCreate || loading" data-testid="create-practice" @click="createAndStart">Create and start private practice</button>
    </template>
    <section v-else-if="state" class="scoring" data-testid="practice-scoring">
      <p>Private revision {{ revision }} · {{ state.status }} · {{ String(state.snapshot.total_runs ?? 0) }}/{{ String(state.snapshot.total_wickets ?? 0) }}</p>
      <p v-if="state.snapshot.target">Target {{ String(state.snapshot.target) }}</p>
      <button v-for="runs in [0, 1, 4, 6]" :key="runs" :disabled="loading || state.status !== 'in_progress' || needsNextOver" :data-testid="`score-${runs}`" @click="score(runs)">+{{ runs }}</button>
      <button :disabled="loading || state.status !== 'in_progress' || needsNextOver" @click="score(0, true)">Wicket</button><button :disabled="loading" data-testid="undo-ball" @click="undo">Undo last ball</button>
      <div v-if="needsNextOver"><label>Next over bowler <select v-model="nextOverBowlerId" data-testid="next-over-bowler"><option v-for="player in bowling" :key="player.player_profile_id" :value="player.player_profile_id">{{ player.player_name }}</option></select></label><button :disabled="loading" data-testid="start-next-over" @click="beginNextOver">Start next over</button></div>
      <button v-if="state.status === 'innings_break' && inning === 1" :disabled="loading" data-testid="start-second-innings" @click="startSecondInnings">Start second innings</button>
    </section>
  </section>
</template>

<style scoped>
.practice{max-width:54rem;padding:1rem}.practice label{display:block;margin:.7rem 0}.practice select,.practice input{margin-left:.5rem}.practice button{margin:.4rem;padding:.5rem .8rem}.error{color:#b42318}.scoring{margin-top:1rem;padding:1rem;border:1px solid #789;border-radius:.5rem}
</style>
