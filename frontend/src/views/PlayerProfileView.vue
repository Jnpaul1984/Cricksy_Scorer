<template>
  <div class="player-profile-view">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner" aria-busy="true"></div>
        <p>Loading player profile…</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-container">
        <BaseCard class="error-card">
          <div class="error-icon">⚠️</div>
          <h2>Unable to Load Profile</h2>
          <p>{{ error }}</p>
          <BaseButton variant="primary" @click="loadProfile">Try Again</BaseButton>
        </BaseCard>
      </div>

      <!-- Profile Content -->
      <div v-else-if="profile" class="profile-content">
        <!-- Player Header -->
        <BaseCard as="header" class="player-header">
          <div class="player-avatar">{{ playerInitials }}</div>
          <div class="player-info">
            <div class="player-name-row">
              <h1>{{ profile.player_name }}</h1>
              <BaseBadge :variant="roleBadgeVariant">{{ playerRole }}</BaseBadge>
              <BaseButton
                :variant="isFavorite ? 'primary' : 'ghost'"
                size="sm"
                class="follow-btn"
                :class="{ following: isFavorite }"
                :loading="isTogglingFavorite"
                :aria-label="isFavorite ? 'Unfollow this player' : 'Follow this player'"
                @click="toggleFavorite"
              >
                <span v-if="isFavorite">★ Following</span>
                <span v-else>☆ Follow</span>
              </BaseButton>
            </div>
            <div v-if="favoriteError" class="favorite-error">{{ favoriteError }}</div>
            <div class="player-meta">
              <span class="meta-item">🏏 {{ profile.total_matches }} matches</span>
              <span class="meta-item subdued">ID: {{ profile.player_id.slice(0, 8) }}…</span>
            </div>
          </div>
        </BaseCard>

        <!-- Tab Navigation -->
        <BaseCard as="nav" padding="sm" class="tabs-nav">
          <BaseButton
            :variant="activeTab === 'overview' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="overview"
            @click="activeTab = 'overview'"
          >
            Overview
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'batting' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="batting"
            @click="activeTab = 'batting'"
          >
            Batting
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'bowling' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="bowling"
            @click="activeTab = 'bowling'"
          >
            Bowling
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'form' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="form"
            @click="activeTab = 'form'"
          >
            Form
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'season' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="season"
            @click="activeTab = 'season'"
          >
            Season
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'profile' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="profile"
            @click="activeTab = 'profile'"
          >
            Profile
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'notebook' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="notebook"
            @click="activeTab = 'notebook'"
          >
            Notebook
          </BaseButton>
          <BaseButton
            :variant="activeTab === 'mental' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="mental"
            @click="activeTab = 'mental'"
          >
            Mental
          </BaseButton>
          <!-- Development tab: coach-facing only -->
          <BaseButton
            v-if="authStore.canCoach"
            :variant="activeTab === 'development' ? 'primary' : 'ghost'"
            class="tab-btn"
            data-tab="development"
            @click="onDevelopmentTabClick"
          >
            Development
          </BaseButton>
        </BaseCard>

        <!-- Tab Content -->
        <BaseCard class="tab-content">
          <!-- Overview Tab -->
          <div v-if="activeTab === 'overview'" class="tab-panel">
            <!-- Key Stats Grid -->
            <div class="overview-stats-grid">
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_matches }}</div>
                <div class="stat-label">Matches</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_runs_scored.toLocaleString() }}</div>
                <div class="stat-label">Runs</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_wickets }}</div>
                <div class="stat-label">Wickets</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.strike_rate) }}</div>
                <div class="stat-label">Strike Rate</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.batting_average) }}</div>
                <div class="stat-label">Batting Avg</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.economy_rate) }}</div>
                <div class="stat-label">Economy</div>
              </div>
            </div>

            <!-- Fielding Summary -->
            <div class="fielding-summary">
              <h3>🧤 Fielding</h3>
              <div class="fielding-stats">
                <span><strong>{{ profile.catches }}</strong> catches</span>
                <span><strong>{{ profile.stumpings }}</strong> stumpings</span>
                <span><strong>{{ profile.run_outs }}</strong> run outs</span>
              </div>
            </div>

            <!-- Achievements Section -->
            <section v-if="profile.achievements && profile.achievements.length > 0" class="achievements-section">
              <h3>🏆 Achievements</h3>
              <div class="achievements-list">
                <span
                  v-for="achievement in profile.achievements"
                  :key="achievement.id"
                  class="achievement-pill"
                  :title="achievement.description"
                >
                  {{ achievement.badge_icon || '🏅' }} {{ achievement.title }}
                </span>
              </div>
            </section>
            <p v-else class="no-achievements">No achievements yet. Keep playing to earn badges!</p>
          </div>

          <!-- Batting Tab -->
          <div v-else-if="activeTab === 'batting'" class="tab-panel">
            <h3>🏏 Batting Statistics</h3>
            <dl class="stats-list">
              <div class="stats-row">
                <dt>Innings</dt>
                <dd>{{ profile.total_innings_batted }}</dd>
              </div>
              <div class="stats-row">
                <dt>Runs</dt>
                <dd>{{ profile.total_runs_scored.toLocaleString() }}</dd>
              </div>
              <div class="stats-row">
                <dt>Average</dt>
                <dd>{{ formatStat(profile.batting_average) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Strike Rate</dt>
                <dd>{{ formatStat(profile.strike_rate) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Highest Score</dt>
                <dd>{{ profile.highest_score }}</dd>
              </div>
              <div class="stats-row">
                <dt>Centuries (100s)</dt>
                <dd>{{ profile.centuries }}</dd>
              </div>
              <div class="stats-row">
                <dt>Half-Centuries (50s)</dt>
                <dd>{{ profile.half_centuries }}</dd>
              </div>
              <div class="stats-row">
                <dt>Fours</dt>
                <dd>{{ profile.total_fours }}</dd>
              </div>
              <div class="stats-row">
                <dt>Sixes</dt>
                <dd>{{ profile.total_sixes }}</dd>
              </div>
              <div class="stats-row">
                <dt>Balls Faced</dt>
                <dd>{{ profile.total_balls_faced.toLocaleString() }}</dd>
              </div>
              <div class="stats-row">
                <dt>Times Out</dt>
                <dd>{{ profile.times_out }}</dd>
              </div>
            </dl>
          </div>

          <!-- Bowling Tab -->
          <div v-else-if="activeTab === 'bowling'" class="tab-panel">
            <h3>⚾ Bowling Statistics</h3>
            <dl class="stats-list">
              <div class="stats-row">
                <dt>Innings</dt>
                <dd>{{ profile.total_innings_bowled }}</dd>
              </div>
              <div class="stats-row">
                <dt>Overs</dt>
                <dd>{{ formatStat(profile.total_overs_bowled, 1) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Wickets</dt>
                <dd>{{ profile.total_wickets }}</dd>
              </div>
              <div class="stats-row">
                <dt>Average</dt>
                <dd>{{ formatStat(profile.bowling_average) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Economy</dt>
                <dd>{{ formatStat(profile.economy_rate) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Best Figures</dt>
                <dd>{{ profile.best_bowling_figures || '—' }}</dd>
              </div>
              <div class="stats-row">
                <dt>5-Wicket Hauls</dt>
                <dd>{{ profile.five_wicket_hauls }}</dd>
              </div>
              <div class="stats-row">
                <dt>Maidens</dt>
                <dd>{{ profile.maidens }}</dd>
              </div>
              <div class="stats-row">
                <dt>Runs Conceded</dt>
                <dd>{{ profile.total_runs_conceded.toLocaleString() }}</dd>
              </div>
            </dl>
          </div>

          <!-- Form Tab -->
          <div v-else-if="activeTab === 'form'" class="tab-panel">
            <FormTrackerWidget :profile="profile" />
          </div>

          <!-- Season Tab -->
          <div v-else-if="activeTab === 'season'" class="tab-panel">
            <SeasonGraphsWidget :profile="profile" />
          </div>

          <!-- Profile Strengths/Weaknesses Tab -->
          <div v-else-if="activeTab === 'profile'" class="tab-panel">
            <StrengthWeaknessWidget
              :profile="profile"
              :strengths="aiStrengths"
              :weaknesses="aiWeaknesses"
            />
          </div>

          <!-- Notebook Tab -->
          <div v-else-if="activeTab === 'notebook'" class="tab-panel">
            <CoachNotebookWidget :profile="profile" />
          </div>

          <!-- Mental Profile Tab -->
          <div v-else-if="activeTab === 'mental'" class="tab-panel">
            <MentalProfilePanel :player-id="profile.player_id" :player-name="profile.player_name" />
          </div>

          <!-- Development Tab (coach-facing only) -->
          <div v-else-if="activeTab === 'development'" class="tab-panel" data-testid="development-tab-panel">
            <div class="dev-tab-header">
              <h3>📋 Development Plans</h3>
              <div class="dev-tab-badges">
                <BaseBadge variant="warning">Draft only</BaseBadge>
                <BaseBadge variant="primary">Coach review required</BaseBadge>
              </div>
              <p class="dev-tab-advisory">
                These are advisory draft plans generated from available player data.
                They require coach review and must not be treated as official assessments.
              </p>
            </div>

            <!-- Loading state -->
            <div v-if="devPlansLoading" class="dev-loading" data-testid="dev-plans-loading">
              <p>Loading development plans…</p>
            </div>

            <!-- Error state -->
            <div v-else-if="devPlansError" class="dev-error" data-testid="dev-plans-error">
              <p>{{ devPlansError }}</p>
            </div>

            <!-- Plans list -->
            <div v-else>
              <!-- Insufficient data state -->
              <div
                v-if="devInsufficientData"
                class="dev-insufficient"
                data-testid="dev-insufficient-data"
              >
                <p>
                  <strong>Insufficient data to generate a development plan.</strong>
                </p>
                <p>
                  To generate a draft plan, the player needs recent match/form data,
                  coach notes, coaching sessions, or video evidence.
                </p>
              </div>

              <!-- Empty state -->
              <div
                v-else-if="devPlans.length === 0 && !devGenerating"
                class="dev-empty"
                data-testid="dev-plans-empty"
              >
                <p>No development plans exist for this player yet.</p>
              </div>

              <!-- Plans -->
              <div v-if="devPlans.length > 0" class="dev-plans-list">
                <PlayerDevelopmentPlanCard
                  v-for="bundle in devPlans"
                  :key="bundle.plan.id"
                  :bundle="bundle"
                  class="dev-plan-item"
                />
              </div>

              <!-- Generate draft plan action -->
              <div class="dev-generate-section" data-testid="dev-generate-section">
                <BaseButton
                  variant="primary"
                  size="sm"
                  :disabled="devGenerating"
                  data-testid="dev-generate-btn"
                  @click="generateDraftPlan"
                >
                  <span v-if="devGenerating">Generating draft plan…</span>
                  <span v-else>Generate draft development plan</span>
                </BaseButton>
                <p class="dev-generate-note">
                  Plan will be generated from available player data only.
                  No fake recommendations are produced.
                </p>
              </div>
            </div>
          </div>
        </BaseCard>

        <!-- AI Insights Section -->
        <section class="ai-insights-section">
          <BaseCard padding="lg" class="ai-insights-card">
            <header class="ai-insights-header">
              <h2 class="ai-insights-title">🤖 AI Insights</h2>
              <div class="ai-insights-actions">
                <BaseBadge
                  v-if="aiRecentForm?.label"
                  variant="neutral"
                  class="trend-badge"
                >
                  {{ aiRecentForm.label }}
                </BaseBadge>
                <BaseBadge
                  v-if="aiInsightsStatusLabel"
                  variant="neutral"
                  class="trend-badge"
                >
                  {{ aiInsightsStatusLabel }}
                </BaseBadge>
                <BaseButton
                  size="sm"
                  variant="ghost"
                  :disabled="aiInsightsLoading"
                  @click="loadAIInsights(true)"
                >
                  <span v-if="aiInsightsLoading">Refreshing…</span>
                  <span v-else>↻ Refresh</span>
                </BaseButton>
              </div>
            </header>
            <PlayerDevelopmentInsightCard
              :player-name="profile?.player_name ?? 'Player'"
              :player-role="playerRole"
              :insights="aiInsights"
              :loading="aiInsightsLoading"
              :error="aiInsightsError"
            />
            <div v-if="aiInsightsFallback" class="player-ai-fallback">
              <p>AI insight unavailable. Showing deterministic player summary.</p>
              <p>{{ aiInsightsFallback.summary }}</p>
              <ul>
                <li v-for="(item, idx) in aiInsightsFallback.bullets" :key="`player-fallback-${idx}`">
                  {{ item }}
                </li>
              </ul>
            </div>
            <p v-else-if="aiInsightsInsufficientData" class="player-ai-fallback">
              Insufficient player data for AI or deterministic summary.
            </p>
          </BaseCard>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import { BaseButton, BaseCard, BaseBadge } from '@/components'
import CoachNotebookWidget from '@/components/CoachNotebookWidget.vue'
import FormTrackerWidget from '@/components/FormTrackerWidget.vue'
import MentalProfilePanel from '@/components/MentalProfilePanel.vue'
import PlayerDevelopmentInsightCard from '@/components/PlayerDevelopmentInsightCard.vue'
import PlayerDevelopmentPlanCard from '@/components/PlayerDevelopmentPlanCard.vue'
import SeasonGraphsWidget from '@/components/SeasonGraphsWidget.vue'
import StrengthWeaknessWidget from '@/components/StrengthWeaknessWidget.vue'
import { readAiInsightCache, writeAiInsightCache } from '@/services/aiInsightCache'
import { apiService, getErrorMessage, getPlayerAIInsights } from '@/services/api'
import type { FanFavoriteRead, PlayerAIInsights } from '@/services/api'
import { getPlayerProfile } from '@/services/playerApi'
import {
  generateDraftPlayerDevelopmentPlan,
  listPlayerDevelopmentPlans,
  PlayerDevelopmentApiError,
} from '@/services/playerDevelopmentApi'
import type { PlayerDevelopmentPlanDraftBundle } from '@/services/playerDevelopmentApi'
import { useAuthStore } from '@/stores/authStore'
import type { PlayerProfile } from '@/types/player'

type TabName = 'overview' | 'batting' | 'bowling' | 'form' | 'season' | 'profile' | 'notebook' | 'mental' | 'development'

const route = useRoute()
const authStore = useAuthStore()
const loading = ref(true)
const error = ref<string | null>(null)
const profile = ref<PlayerProfile | null>(null)
const activeTab = ref<TabName>('overview')

// Fan favorites state
const isFavorite = ref(false)
const favoriteId = ref<string | null>(null)
const isTogglingFavorite = ref(false)
const favoriteError = ref<string | null>(null)

// AI Insights state
const aiInsightsLoading = ref(false)
const aiInsightsError = ref<string | null>(null)
const aiInsights = ref<PlayerAIInsights | null>(null)
const aiInsightsFallback = ref<{ summary: string; bullets: string[] } | null>(null)
const aiInsightsInsufficientData = ref(false)
const aiInsightsCacheStatus = ref<'none' | 'live' | 'cached' | 'stale' | 'fallback' | 'insufficient'>('none')

// Development plans state (Phase 9D — coach-facing only)
const devPlansLoading = ref(false)
const devPlansError = ref<string | null>(null)
const devPlans = ref<PlayerDevelopmentPlanDraftBundle[]>([])
const devGenerating = ref(false)
const devInsufficientData = ref(false)

// Derive player role from stats
const playerRole = computed<string>(() => {
  if (!profile.value) return 'Player'
  const { total_wickets, total_runs_scored } = profile.value
  if (total_wickets > 10 && total_runs_scored > 200) return 'All-rounder'
  if (total_wickets >= 10) return 'Bowler'
  if (total_runs_scored >= 200) return 'Batter'
  return 'Player'
})

// Role badge variant for BaseBadge component
const roleBadgeVariant = computed<'success' | 'warning' | 'primary' | 'neutral'>(() => {
  switch (playerRole.value) {
    case 'All-rounder': return 'success'
    case 'Bowler': return 'warning'
    case 'Batter': return 'primary'
    default: return 'neutral'
  }
})

// Player initials for avatar
const playerInitials = computed<string>(() => {
  if (!profile.value) return '?'
  const parts = profile.value.player_name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return parts[0].slice(0, 2).toUpperCase()
})

// Format numeric stats with fallback
const formatStat = (value: number | null | undefined, decimals = 2): string => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return value.toFixed(decimals)
}

// AI Insights computed helpers
const aiRecentForm = computed(() => aiInsights.value?.recent_form ?? null)
const aiStrengths = computed<string[]>(() => aiInsights.value?.strengths ?? [])
const aiWeaknesses = computed<string[]>(() => aiInsights.value?.weaknesses ?? [])
const aiInsightsStatusLabel = computed(() => {
  if (aiInsightsCacheStatus.value === 'cached') return 'Cached insight'
  if (aiInsightsCacheStatus.value === 'stale') return 'Stale cache'
  if (aiInsightsCacheStatus.value === 'fallback') return 'Deterministic fallback'
  if (aiInsightsCacheStatus.value === 'insufficient') return 'Insufficient data'
  return null
})

const loadProfile = async () => {
  loading.value = true
  error.value = null

  try {
    const playerId = route.params.playerId as string
    if (!playerId) {
      throw new Error('No player ID provided')
    }
    profile.value = await getPlayerProfile(playerId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load player profile'
  } finally {
    loading.value = false
  }
}

// Load current user's favorites and check if this player is followed
const loadFavorites = async () => {
  if (!profile.value) return

  try {
    const favorites: FanFavoriteRead[] = await apiService.getFanFavorites()
    const match = favorites.find(
      (f) => f.favorite_type === 'player' && f.player_profile_id === profile.value?.player_id
    )
    if (match) {
      isFavorite.value = true
      favoriteId.value = match.id
    } else {
      isFavorite.value = false
      favoriteId.value = null
    }
  } catch (err) {
    // Silently fail - user may not be logged in
    console.warn('Failed to load favorites:', getErrorMessage(err))
  }
}

// Toggle follow/unfollow for current player
const toggleFavorite = async () => {
  if (!profile.value || isTogglingFavorite.value) return

  isTogglingFavorite.value = true
  favoriteError.value = null

  try {
    if (isFavorite.value && favoriteId.value) {
      // Unfollow
      await apiService.deleteFanFavorite(favoriteId.value)
      isFavorite.value = false
      favoriteId.value = null
    } else {
      // Follow
      const newFavorite = await apiService.createFanFavorite({
        favorite_type: 'player',
        player_profile_id: profile.value.player_id,
      })
      isFavorite.value = true
      favoriteId.value = newFavorite.id
    }
  } catch (err) {
    favoriteError.value = getErrorMessage(err)
    console.error('Failed to toggle favorite:', err)
  } finally {
    isTogglingFavorite.value = false
  }
}

// Load AI insights for current player
const AI_PLAYER_STALE_AFTER_MS = 5 * 60 * 1000

const buildPlayerDeterministicFallback = () => {
  if (!profile.value) return null
  const p = profile.value
  if (p.total_matches <= 0) {
    return null
  }
  const bullets = [
    `${p.total_runs_scored} runs across ${p.total_innings_batted} batting innings`,
    `${p.total_wickets} wickets across ${p.total_innings_bowled} bowling innings`,
    `Strike rate ${formatStat(p.strike_rate)} · Economy ${formatStat(p.economy_rate)}`,
  ]
  return {
    summary: `${p.player_name} has deterministic profile trends available while AI insight is unavailable.`,
    bullets,
  }
}

const loadAIInsights = async (forceRefresh = false) => {
  const playerId = route.params.playerId as string
  if (!playerId) return

  const contextHash = `player:${playerId}:${profile.value?.updated_at ?? 'unknown'}`
  if (!forceRefresh) {
    const cached = readAiInsightCache<PlayerAIInsights>({
      scope: 'player-insights',
      key: playerId,
      contextHash,
      staleAfterMs: AI_PLAYER_STALE_AFTER_MS,
    })
    if (cached.entry) {
      aiInsights.value = cached.entry.value
      aiInsightsError.value = null
      aiInsightsFallback.value = null
      aiInsightsInsufficientData.value = false
      aiInsightsCacheStatus.value = cached.status === 'stale' ? 'stale' : 'cached'
      return
    }
  }

  aiInsightsLoading.value = true
  aiInsightsError.value = null
  aiInsightsFallback.value = null
  aiInsightsInsufficientData.value = false

  try {
    const insight = await getPlayerAIInsights(playerId)
    aiInsights.value = insight
    aiInsightsCacheStatus.value = 'live'
    writeAiInsightCache({
      scope: 'player-insights',
      key: playerId,
      contextHash,
      value: insight,
    })
  } catch (err) {
    console.warn('Failed to load AI insights:', err)
    const fallback = buildPlayerDeterministicFallback()
    if (fallback) {
      aiInsights.value = null
      aiInsightsFallback.value = fallback
      aiInsightsInsufficientData.value = false
      aiInsightsCacheStatus.value = 'fallback'
      aiInsightsError.value = null
    } else {
      aiInsights.value = null
      aiInsightsFallback.value = null
      aiInsightsInsufficientData.value = true
      aiInsightsCacheStatus.value = 'insufficient'
      aiInsightsError.value = null
    }
  } finally {
    aiInsightsLoading.value = false
  }
}

onMounted(async () => {
  await loadProfile()
  await loadFavorites()
  await loadAIInsights()
})

// -----------------------------------------------------------------------
// Phase 9D — Player Development (coach-facing only)
// -----------------------------------------------------------------------

const loadDevPlans = async () => {
  const playerId = route.params.playerId as string
  if (!playerId || !authStore.canCoach) return

  devPlansLoading.value = true
  devPlansError.value = null
  devInsufficientData.value = false

  try {
    devPlans.value = await listPlayerDevelopmentPlans(playerId)
  } catch (err) {
    if (err instanceof PlayerDevelopmentApiError && err.isUnauthorized()) {
      devPlansError.value = 'You do not have permission to view development plans for this player.'
    } else if (err instanceof PlayerDevelopmentApiError && err.isNotFound()) {
      // Player not found — show empty
      devPlans.value = []
    } else {
      devPlansError.value = err instanceof Error ? err.message : 'Failed to load development plans.'
    }
  } finally {
    devPlansLoading.value = false
  }
}

const generateDraftPlan = async () => {
  const playerId = route.params.playerId as string
  if (!playerId || devGenerating.value) return

  devGenerating.value = true
  devPlansError.value = null
  devInsufficientData.value = false

  try {
    const result = await generateDraftPlayerDevelopmentPlan(playerId)
    if (result.status === 'insufficient_data') {
      devInsufficientData.value = true
    } else if (result.plan) {
      // Reload the full list to pick up the new plan
      await loadDevPlans()
    }
  } catch (err) {
    if (err instanceof PlayerDevelopmentApiError && err.isUnauthorized()) {
      devPlansError.value = 'You do not have permission to generate a development plan for this player.'
    } else {
      devPlansError.value = err instanceof Error ? err.message : 'Failed to generate development plan.'
    }
  } finally {
    devGenerating.value = false
  }
}

const onDevelopmentTabClick = async () => {
  activeTab.value = 'development'
  // Load plans the first time the tab is opened (if not already loaded)
  if (devPlans.value.length === 0 && !devPlansLoading.value && !devPlansError.value) {
    await loadDevPlans()
  }
}
</script>

<style scoped>
/* =====================================================
   PLAYER PROFILE VIEW - Using Design System Tokens
   ===================================================== */

.player-profile-view {
  padding: var(--space-5) 0;
  min-height: 100vh;
  background: var(--color-bg);
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) 0;
  gap: var(--space-4);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-pill);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-container {
  display: flex;
  justify-content: center;
  padding: var(--space-8) 0;
}

.error-card {
  text-align: center;
  max-width: 400px;
}

.error-icon {
  font-size: var(--text-4xl);
  margin-bottom: var(--space-4);
}

.error-card h2 {
  margin: 0 0 var(--space-2);
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.error-card p {
  color: var(--color-text-muted);
  margin-bottom: var(--space-5);
}

/* Player Header */
.player-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.player-avatar {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-pill);
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  flex-shrink: 0;
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.player-name-row h1 {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  line-height: var(--h2-leading);
  color: var(--color-text);
}

/* Follow Button */
.follow-btn.following:hover:not(:disabled) {
  background: var(--color-error);
  border-color: var(--color-error);
}

.favorite-error {
  color: var(--color-error);
  font-size: var(--text-xs);
  margin-top: var(--space-1);
}

.player-meta {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.meta-item.subdued {
  opacity: 0.7;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

/* Tab Navigation */
.tabs-nav {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.tab-btn {
  flex: 1;
}

.tab-panel h3 {
  margin: 0 0 var(--space-4);
  font-size: var(--h4-size);
  font-weight: var(--h4-weight);
  color: var(--color-text);
}

/* Overview Stats Grid */
.overview-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  text-align: center;
  padding: var(--space-4) var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  transition: transform var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card .stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  line-height: var(--leading-tight);
}

.stat-card .stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: var(--space-1);
}

/* Fielding Summary */
.fielding-summary {
  padding: var(--space-4);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-5);
}

.fielding-summary h3 {
  margin: 0 0 var(--space-3) !important;
  font-size: var(--text-base) !important;
}

.fielding-stats {
  display: flex;
  gap: var(--space-5);
  flex-wrap: wrap;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.fielding-stats strong {
  color: var(--color-text);
}

/* Achievements */
.achievements-section h3 {
  margin-bottom: var(--space-3) !important;
}

.achievements-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.achievement-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: linear-gradient(135deg, var(--color-accent), var(--color-warning));
  color: var(--color-text-inverse);
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: default;
  transition: transform var(--transition-fast);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.achievement-pill:hover {
  transform: scale(1.05);
}

.no-achievements {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-6) 0;
  font-style: italic;
}

/* Stats List (Batting/Bowling tabs) */
.stats-list {
  margin: 0;
  padding: 0;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}

.stats-row:last-child {
  border-bottom: none;
}

.stats-row dt {
  color: var(--color-text-muted);
  font-weight: var(--font-normal);
}

.stats-row dd {
  margin: 0;
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

/* Responsive */
@media (max-width: 600px) {
  .player-header {
    flex-direction: column;
    text-align: center;
  }

  .player-name-row {
    justify-content: center;
  }

  .player-meta {
    justify-content: center;
    flex-wrap: wrap;
  }

  .overview-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-card .stat-value {
    font-size: var(--text-xl);
  }

  .tabs-nav {
    flex-wrap: wrap;
  }

  .tabs-nav .tab-btn {
    flex: none;
    min-width: calc(33% - var(--space-2));
  }
}

/* AI Insights Section */
.ai-insights-section {
  margin-top: var(--space-6);
}

.ai-insights-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.ai-insights-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.ai-insights-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  margin: 0;
}

.ai-insights-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.trend-badge {
  text-transform: capitalize;
}

.ai-insights-loading .skeleton-line {
  height: 12px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-alt, var(--color-border));
  animation: pulse 1.2s ease-in-out infinite;
  margin-bottom: var(--space-2);
}

.ai-insights-loading .skeleton-line:nth-child(1) { width: 90%; }
.ai-insights-loading .skeleton-line:nth-child(2) { width: 75%; }
.ai-insights-loading .skeleton-line:nth-child(3) { width: 60%; }
.ai-insights-loading .skeleton-line:nth-child(4) { width: 45%; }
.ai-insights-loading .skeleton-line.short { width: 40%; }

.ai-insights-error {
  font-size: var(--text-xs);
  color: var(--color-error, var(--color-danger, #dc2626));
}

.ai-insights-empty {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.ai-insights-grid {
  display: grid;
  gap: var(--space-4);
}

@media (min-width: 768px) {
  .ai-insights-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.ai-insights-grid section h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-2);
  color: var(--color-text);
}

.ai-insights-grid section p,
.ai-insights-grid section li {
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: var(--leading-relaxed);
}

.ai-insights-grid section ul {
  margin: 0;
  padding-left: var(--space-4);
}

.ai-insights-grid section li {
  margin-bottom: var(--space-1);
}

.ai-insights-strengths ul li {
  list-style-type: "✓ ";
}

.ai-insights-weaknesses ul li {
  list-style-type: "⚠ ";
}

.ai-insights-form strong {
  color: var(--color-primary);
}

.form-chart {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
}

.form-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  margin: 0;
}

.ai-insights-role-tags {
  grid-column: 1 / -1;
}

.ai-insights-recommendations {
  grid-column: 1 / -1;
}

.ai-insights-recommendations ul li {
  list-style-type: "💡 ";
}

.ai-insights-tags {
  grid-column: 1 / -1;
}

.ai-insights-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.ai-tag {
  text-transform: capitalize;
}

.player-ai-fallback {
  color: var(--color-text-muted);
}

.player-ai-fallback ul {
  margin: var(--space-2) 0 0;
  padding-left: 1rem;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

@media (max-width: 768px) {
  .ai-insights-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }

  .ai-insights-actions {
    width: 100%;
    justify-content: space-between;
  }
}

/* -----------------------------------------------------------------------
   Phase 9D — Development Tab (coach-facing)
   ----------------------------------------------------------------------- */

.dev-tab-header {
  margin-bottom: var(--space-4);
}

.dev-tab-header h3 {
  margin: 0 0 var(--space-2);
}

.dev-tab-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.dev-tab-advisory {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-muted, var(--color-muted));
  margin: 0;
}

.dev-loading,
.dev-error,
.dev-insufficient,
.dev-empty {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
  margin-bottom: var(--space-4);
}

.dev-error {
  color: var(--color-error);
}

.dev-insufficient strong {
  display: block;
  margin-bottom: var(--space-2);
}

.dev-plans-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.dev-generate-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-4);
  background: var(--color-surface-alt);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.dev-generate-note {
  margin: 0;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-muted, var(--color-muted));
}
</style>
