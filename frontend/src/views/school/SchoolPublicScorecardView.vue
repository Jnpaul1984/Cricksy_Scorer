<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';
import { getErrorMessage } from '@/services/api';
import { getPublicCompetitionScorecard, getPublicSchoolScorecard } from '@/services/schoolAdminApi';
import type { PublicOpaqueSchoolScorecard, PublicSchoolScorecard } from '@/types/schoolAdmin';

const props = defineProps<{ gameId?: string; publicIdentifier?: string; competitionPublicKey?: string; scorecardPublicIdentifier?: string }>();
const scorecard = ref<(PublicSchoolScorecard | PublicOpaqueSchoolScorecard) | null>(null);
const loading = ref(true);
const error = ref('');
const canonicalSharePath = computed(() => (
  props.publicIdentifier && props.competitionPublicKey && props.scorecardPublicIdentifier
    ? `/community/${props.publicIdentifier}/competitions/${props.competitionPublicKey}/scorecards/${props.scorecardPublicIdentifier}`
    : null
));

async function load() {
  loading.value = true; error.value = ''; scorecard.value = null;
  try {
    scorecard.value = props.scorecardPublicIdentifier && props.publicIdentifier && props.competitionPublicKey
      ? await getPublicCompetitionScorecard(props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier)
      : await getPublicSchoolScorecard(props.gameId || '');
  } catch (reason) {
    const status = (reason as { status?: number })?.status;
    error.value =
      status === 404 ? 'This scorecard is not published.' : getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(() => [props.gameId, props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier], load);
</script>

<template>
  <main class="public-scorecard">
    <p v-if="loading" role="status">Loading published scorecard…</p>
    <section v-else-if="error" class="notice error" role="alert">
      <h1>Scorecard unavailable</h1>
      <p>{{ error }}</p>
    </section>
    <template v-else-if="scorecard">
      <header>
        <p class="eyebrow">Published scorecard</p>
        <h1>{{ scorecard.team_a.name }} vs {{ scorecard.team_b.name }}</h1>
        <p>{{ scorecard.status }} · {{ scorecard.publication_state.replace('_', ' ') }}</p>
      </header>
      <section class="score-summary">
        <strong>{{ scorecard.batting_team_name || 'Current innings' }}</strong>
        <span>{{ scorecard.total_runs }}/{{ scorecard.total_wickets }}</span>
        <span>{{ scorecard.overs_completed }}.{{ scorecard.balls_this_over }} overs</span>
      </section>
      <p v-if="scorecard.result" class="result">{{ scorecard.result }}</p>
      <PublicShareLinkButton v-if="canonicalSharePath" :path="canonicalSharePath" label="Copy scorecard link" />
      <div class="tables">
        <section>
          <h2>Batting</h2>
          <table>
            <thead>
              <tr>
                <th>Player</th>
                <th>R</th>
                <th>B</th>
                <th>4s</th>
                <th>6s</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scorecard.batting_scorecard" :key="row.player_name">
                <td>
                  {{ row.player_name }}<small v-if="row.how_out"> {{ row.how_out }}</small>
                </td>
                <td>{{ row.runs ?? '—' }}</td>
                <td>{{ row.balls_faced ?? '—' }}</td>
                <td>{{ row.fours ?? '—' }}</td>
                <td>{{ row.sixes ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
        <section>
          <h2>Bowling</h2>
          <table>
            <thead>
              <tr>
                <th>Player</th>
                <th>O</th>
                <th>R</th>
                <th>W</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scorecard.bowling_scorecard" :key="row.player_name">
                <td>{{ row.player_name }}</td>
                <td>{{ row.overs_bowled ?? '—' }}</td>
                <td>{{ row.runs_conceded ?? '—' }}</td>
                <td>{{ row.wickets_taken ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <p class="privacy-note">
        This public view contains only published cricket information.
        <template v-if="scorecard.organization_type === 'club'">
          Club membership and private player metadata are not displayed.
        </template>
        <template v-else> School membership and student metadata are not displayed. </template>
      </p>
    </template>
  </main>
</template>

<style scoped>
.public-scorecard {
  max-width: 980px;
  margin: 2rem auto;
  padding: 1rem;
  color: #eef2ff;
}
header,
.score-summary,
.tables section,
.notice {
  padding: 1.2rem;
  border: 1px solid #3b4768;
  border-radius: 12px;
  background: #171e30;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.score-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1rem;
  margin: 1rem 0;
  font-size: 1.2rem;
}
.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}
table {
  width: 100%;
}
small {
  display: block;
  color: #aebbd7;
}
.result,
.privacy-note {
  padding: 0.8rem;
  border-left: 4px solid #70d7b0;
  background: #20283d;
}
.error {
  border-color: #d56b6b;
}
</style>
