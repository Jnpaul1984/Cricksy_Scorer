<template>
  <BaseCard as="section" padding="md" class="team-dev-card">
    <div class="section-header">
      <h2>Team Development Overview</h2>
      <div class="team-dev-badges">
        <BaseBadge variant="warning">Draft only</BaseBadge>
        <BaseBadge variant="primary">Coach review required</BaseBadge>
      </div>
    </div>

    <p class="team-dev-advisory">
      This dashboard summarizes real Phase 9 development records for players in your permitted
      coach or organization scope. Draft plans remain advisory until a coach reviews them.
    </p>

    <div v-if="loading" class="team-dev-state" data-testid="team-dev-loading">
      Loading team development overview…
    </div>

    <div v-else-if="error" class="team-dev-state team-dev-error" data-testid="team-dev-error">
      {{ error }}
    </div>

    <div
      v-else-if="!overview || overview.total_assigned_players === 0"
      class="team-dev-state"
      data-testid="team-dev-empty"
    >
      <p>No players are currently assigned in this development scope.</p>
      <p>Once assignments are in place, team development coverage will appear here.</p>
    </div>

    <div v-else class="team-dev-content" data-testid="team-dev-content">
      <section class="summary-section">
        <h3>Development Coverage Summary</h3>
        <div class="summary-grid">
          <article class="summary-tile">
            <span class="summary-value">{{ overview.total_assigned_players }}</span>
            <span class="summary-label">Assigned players</span>
          </article>
          <article class="summary-tile">
            <span class="summary-value">{{ overview.players_with_draft_plans }}</span>
            <span class="summary-label">Players with draft plans</span>
          </article>
          <article class="summary-tile">
            <span class="summary-value">{{ overview.players_without_plans }}</span>
            <span class="summary-label">Players without draft plans yet</span>
          </article>
          <article class="summary-tile">
            <span class="summary-value">{{ overview.plans_requiring_review }}</span>
            <span class="summary-label">Plans requiring coach review</span>
          </article>
        </div>
        <div class="coverage-tags">
          <BaseBadge variant="neutral">{{ overview.players_with_goals }} players with goals</BaseBadge>
          <BaseBadge variant="neutral">{{ overview.players_with_drills }} players with drills</BaseBadge>
          <BaseBadge variant="neutral"
            >{{ overview.players_with_checkpoints }} players with checkpoints</BaseBadge
          >
        </div>
      </section>

      <section
        v-if="overview.players_with_draft_plans === 0"
        class="team-dev-state team-dev-no-plans"
        data-testid="team-dev-no-plans"
      >
        <p>No draft plans are available yet for this group.</p>
        <p>Assigned players will appear here as soon as draft development plans are created.</p>
      </section>

      <div v-else class="team-dev-grid">
        <section class="panel" data-testid="team-dev-attention">
          <div class="panel-header">
            <h3>Needs Coach Attention</h3>
            <BaseBadge variant="warning">{{ attentionCount }}</BaseBadge>
          </div>
          <p class="panel-copy">
            Use this queue to support players who still need draft coverage, stronger evidence, or
            an upcoming review touchpoint.
          </p>

          <div v-if="overview.players_without_plan_details.length > 0" class="attention-group">
            <h4>Players without draft plans yet</h4>
            <ul>
              <li v-for="player in overview.players_without_plan_details" :key="player.player_profile_id">
                <span>{{ player.player_name }}</span>
                <BaseButton
                  variant="ghost"
                  size="sm"
                  @click="goToPlayer(player.player_profile_id)"
                >
                  View player
                </BaseButton>
              </li>
            </ul>
          </div>

          <div
            v-if="overview.evidence_coverage_summary.players_needing_more_evidence_details.length > 0"
            class="attention-group"
          >
            <h4>More evidence needed</h4>
            <ul>
              <li
                v-for="player in overview.evidence_coverage_summary.players_needing_more_evidence_details"
                :key="player.player_profile_id"
              >
                <div>
                  <strong>{{ player.player_name }}</strong>
                  <p>{{ player.advisory_note }}</p>
                </div>
                <BaseButton
                  variant="ghost"
                  size="sm"
                  @click="goToPlayer(player.player_profile_id)"
                >
                  Review player
                </BaseButton>
              </li>
            </ul>
          </div>

          <div v-if="checkpointAttentionItems.length > 0" class="attention-group">
            <h4>Checkpoint follow-ups</h4>
            <ul>
              <li v-for="checkpoint in checkpointAttentionItems" :key="checkpoint.checkpoint_id">
                <div>
                  <strong>{{ checkpoint.player_name }}</strong>
                  <p>{{ checkpoint.advisory_label }} · {{ formatDate(checkpoint.checkpoint_date) }}</p>
                </div>
                <BaseButton
                  variant="ghost"
                  size="sm"
                  @click="goToPlayer(checkpoint.player_profile_id)"
                >
                  Open player
                </BaseButton>
              </li>
            </ul>
          </div>

          <p
            v-if="attentionCount === 0"
            class="panel-empty"
          >
            No immediate development support items are waiting right now.
          </p>
        </section>

        <section class="panel" data-testid="team-dev-themes">
          <div class="panel-header">
            <h3>Common Development Themes</h3>
            <BaseBadge variant="neutral">{{ overview.common_development_areas.length }}</BaseBadge>
          </div>
          <p class="panel-copy">
            Safe coaching labels help you spot shared growth focuses across the group.
          </p>
          <ul v-if="overview.common_development_areas.length > 0" class="theme-list">
            <li v-for="theme in overview.common_development_areas" :key="`${theme.category}-${theme.safe_display_label}`">
              <div>
                <strong>{{ theme.safe_display_label }}</strong>
                <p>{{ humanize(theme.category) }}</p>
              </div>
              <BaseBadge variant="primary">{{ theme.player_count }} players</BaseBadge>
            </li>
          </ul>
          <p v-else class="panel-empty">
            Development themes will appear once draft plans add safe coaching labels.
          </p>
        </section>

        <section class="panel" data-testid="team-dev-drills">
          <div class="panel-header">
            <h3>Drill Assignment Overview</h3>
            <BaseBadge variant="neutral">{{ overview.drill_assignment_summary.total_assignments }}</BaseBadge>
          </div>
          <p class="panel-copy">
            Review current drill coverage by assignment status and drill category.
          </p>
          <div class="split-columns">
            <div>
              <h4>By status</h4>
              <ul v-if="overview.drill_assignment_summary.by_status.length > 0" class="compact-list">
                <li v-for="item in overview.drill_assignment_summary.by_status" :key="item.status">
                  <span>{{ humanize(item.status) }}</span>
                  <strong>{{ item.count }}</strong>
                </li>
              </ul>
              <p v-else class="panel-empty">No drill assignments are available yet.</p>
            </div>
            <div>
              <h4>By category</h4>
              <ul v-if="overview.drill_assignment_summary.by_category.length > 0" class="compact-list">
                <li v-for="item in overview.drill_assignment_summary.by_category" :key="item.category">
                  <span>{{ humanize(item.category) }}</span>
                  <strong>{{ item.count }}</strong>
                </li>
              </ul>
              <p v-else class="panel-empty">No drill categories are available yet.</p>
            </div>
          </div>
        </section>

        <section class="panel panel-full" data-testid="team-dev-checkpoints">
          <div class="panel-header">
            <h3>Upcoming Checkpoints</h3>
            <BaseBadge variant="neutral">{{ overview.upcoming_checkpoints.length }}</BaseBadge>
          </div>
          <p class="panel-copy">
            Keep upcoming reviews constructive and grounded in the evidence attached to each draft
            plan.
          </p>
          <ul v-if="overview.upcoming_checkpoints.length > 0" class="checkpoint-list">
            <li v-for="checkpoint in overview.upcoming_checkpoints" :key="checkpoint.checkpoint_id">
              <div>
                <strong>{{ checkpoint.player_name }}</strong>
                <p>
                  {{ formatDate(checkpoint.checkpoint_date) }} ·
                  {{ humanize(checkpoint.progress_status) }} ·
                  {{ checkpoint.advisory_label }}
                </p>
              </div>
              <BaseButton variant="ghost" size="sm" @click="goToPlayer(checkpoint.player_profile_id)">
                Open player
              </BaseButton>
            </li>
          </ul>
          <p v-else class="panel-empty">
            No checkpoints are scheduled yet for the visible draft plans.
          </p>
        </section>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';

import { BaseBadge, BaseButton, BaseCard } from '@/components';
import type {
  PlayerDevelopmentTeamOverview,
} from '@/services/playerDevelopmentApi';

const props = defineProps<{
  loading: boolean;
  error: string | null;
  overview: PlayerDevelopmentTeamOverview | null;
}>();

const router = useRouter();

const checkpointAttentionItems = computed(() =>
  (props.overview?.upcoming_checkpoints ?? []).filter((checkpoint) => checkpoint.is_overdue),
);

const attentionCount = computed(
  () =>
    (props.overview?.players_without_plan_details.length ?? 0) +
    (props.overview?.evidence_coverage_summary.players_needing_more_evidence_details.length ?? 0) +
    checkpointAttentionItems.value.length,
);

function goToPlayer(playerId: string) {
  router.push({ name: 'PlayerProfile', params: { playerId } });
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function humanize(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
</script>

<style scoped>
.team-dev-card {
  border: 1px solid var(--color-border);
}

.section-header,
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.section-header h2,
.panel-header h3 {
  margin: 0;
}

.team-dev-badges,
.coverage-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.team-dev-advisory,
.panel-copy,
.panel-empty,
.team-dev-state p,
.attention-group p,
.theme-list p,
.checkpoint-list p {
  color: var(--color-muted);
}

.team-dev-state {
  padding: var(--space-md);
  font-size: var(--text-sm);
}

.team-dev-error {
  color: var(--color-error, #b3261e);
}

.summary-section,
.panel {
  margin-top: var(--space-lg);
}

.summary-grid,
.team-dev-grid {
  display: grid;
  gap: var(--space-md);
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin: var(--space-md) 0;
}

.summary-tile,
.panel {
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.summary-value {
  display: block;
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

.summary-label {
  font-size: var(--text-sm);
}

.team-dev-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.panel-full {
  grid-column: 1 / -1;
}

.attention-group,
.split-columns {
  margin-top: var(--space-md);
}

.attention-group h4,
.split-columns h4 {
  margin: 0 0 var(--space-xs);
}

.attention-group ul,
.theme-list,
.compact-list,
.checkpoint-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.attention-group li,
.theme-list li,
.compact-list li,
.checkpoint-list li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-border);
}

.attention-group li:last-child,
.theme-list li:last-child,
.compact-list li:last-child,
.checkpoint-list li:last-child {
  border-bottom: none;
}

.split-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-md);
}

@media (max-width: 640px) {
  .section-header,
  .panel-header,
  .attention-group li,
  .theme-list li,
  .compact-list li,
  .checkpoint-list li {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
