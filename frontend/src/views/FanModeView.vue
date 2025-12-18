<script setup lang="ts">
import { reactive, computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiService, getErrorMessage } from '@/services/api'
import FanFeedWidget from '@/components/FanFeedWidget.vue'
import FanStatsWidget from '@/components/FanStatsWidget.vue'

type TabName = 'feed' | 'stats' | 'create'

type MatchFormat = 'T20' | 'T10' | 'custom'

interface FanMatchForm {
  match_name: string
  format: MatchFormat
  custom_overs: number | null
  team_a_name: string
  team_b_name: string
}

const router = useRouter()
const creating = ref(false)
const errorMsg = ref<string | null>(null)
const activeTab = ref<TabName>('feed')

const form = reactive<FanMatchForm>({
  match_name: '',
  format: 'T20',
  custom_overs: 10,
  team_a_name: '',
  team_b_name: '',
})

const oversLimit = computed(() => {
  switch (form.format) {
    case 'T20': return 20
    case 'T10': return 10
    case 'custom': return form.custom_overs ?? 20
    default: return 20
  }
})

const displayMatchName = computed(() =>
  form.match_name.trim() || 'My Backyard Match'
)

const canSubmit = computed(() =>
  form.team_a_name.trim() !== '' &&
  form.team_b_name.trim() !== '' &&
  !creating.value
)

async function onSubmit() {
  if (!canSubmit.value) return
  creating.value = true
  errorMsg.value = null

  try {
    const result = await apiService.createFanMatch({
      home_team_name: form.team_a_name.trim(),
      away_team_name: form.team_b_name.trim(),
      match_type: form.format === 'custom' ? `${oversLimit.value}-over` : form.format,
      overs_limit: oversLimit.value,
    })

    // Redirect to scoring view
    await router.push({ name: 'GameScoringView', params: { gameId: result.id } })
  } catch (e) {
    errorMsg.value = getErrorMessage(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="fan-mode-view">
    <!-- Tab Navigation -->
    <div class="tab-nav">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'feed' }"
        @click="activeTab = 'feed'"
      >
        🔥 Feed
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'stats' }"
        @click="activeTab = 'stats'"
      >
        📊 Stats
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'create' }"
        @click="activeTab = 'create'"
      >
        ➕ Start Match
      </button>
    </div>

    <!-- Feed Tab -->
    <div v-if="activeTab === 'feed'" class="tab-panel">
      <FanFeedWidget />
    </div>

    <!-- Stats Tab -->
    <div v-else-if="activeTab === 'stats'" class="tab-panel">
      <FanStatsWidget />
    </div>

    <!-- Create Match Tab -->
    <div v-else-if="activeTab === 'create'" class="tab-panel">
      <div class="card">
        <div class="header">
          <h1>🏏 Start a Match</h1>
          <p class="subtitle">Score your own backyard cricket match</p>
        </div>

        <form class="form" @submit.prevent="onSubmit">
        <!-- Match Name (optional) -->
        <div class="field">
          <label for="match-name">Match Name <span class="optional">(optional)</span></label>
          <input
            id="match-name"
            v-model="form.match_name"
            type="text"
            :placeholder="displayMatchName"
            data-testid="input-match-name"
          />
        </div>

        <!-- Format Selection -->
        <div class="field">
          <label>Format</label>
          <div class="format-options">
            <button
              type="button"
              class="format-btn"
              :class="{ active: form.format === 'T20' }"
              data-testid="btn-format-t20"
              @click="form.format = 'T20'"
            >
              T20
            </button>
            <button
              type="button"
              class="format-btn"
              :class="{ active: form.format === 'T10' }"
              data-testid="btn-format-t10"
              @click="form.format = 'T10'"
            >
              10 Overs
            </button>
            <button
              type="button"
              class="format-btn"
              :class="{ active: form.format === 'custom' }"
              data-testid="btn-format-custom"
              @click="form.format = 'custom'"
            >
              Custom
            </button>
          </div>
        </div>

        <!-- Custom Overs (only if custom selected) -->
        <div v-if="form.format === 'custom'" class="field">
          <label for="custom-overs">Overs per Innings</label>
          <input
            id="custom-overs"
            v-model.number="form.custom_overs"
            type="number"
            min="1"
            max="50"
            placeholder="e.g., 5"
            data-testid="input-custom-overs"
          />
        </div>

        <!-- Team Names -->
        <div class="field-row">
          <div class="field">
            <label for="team-a">Team A</label>
            <input
              id="team-a"
              v-model="form.team_a_name"
              type="text"
              placeholder="e.g., Backyard Legends"
              required
              data-testid="input-team-a"
            />
          </div>
          <div class="vs">vs</div>
          <div class="field">
            <label for="team-b">Team B</label>
            <input
              id="team-b"
              v-model="form.team_b_name"
              type="text"
              placeholder="e.g., Street Stars"
              required
              data-testid="input-team-b"
            />
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="errorMsg" class="error">
          ❌ {{ errorMsg }}
        </div>

        <!-- Submit -->
        <div class="actions">
          <button
            type="submit"
            class="start-btn"
            :disabled="!canSubmit"
            data-testid="btn-start-match"
          >
            <span v-if="creating" class="spinner"></span>
            {{ creating ? 'Starting...' : '🏏 Start Match' }}
          </button>
        </div>
        </form>

        <div class="footer">
          <router-link to="/setup" class="back-link">
            ← Back to full match setup
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fan-mode-view {
  min-height: 100vh;
  padding: 1.5rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

/* Tab Navigation */
.tab-nav {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0 1rem;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: #fff;
}

/* Tab Panel */
.tab-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 200px);
}

.card {
  width: 100%;
  max-width: 480px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 2rem;
  backdrop-filter: blur(10px);
}

.header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.header h1 {
  color: #fff;
  font-size: 1.75rem;
  margin: 0 0 0.5rem;
}

.subtitle {
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  font-size: 0.95rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  font-weight: 500;
}

.optional {
  color: rgba(255, 255, 255, 0.5);
  font-weight: 400;
}

.field input {
  padding: 0.75rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 1rem;
  transition: border-color 0.2s, background 0.2s;
}

.field input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.field input:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.15);
}

.format-options {
  display: flex;
  gap: 0.5rem;
}

.format-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.format-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.35);
}

.format-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: #fff;
}

.field-row {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
}

.field-row .field {
  flex: 1;
}

.vs {
  color: rgba(255, 255, 255, 0.5);
  font-weight: 600;
  padding-bottom: 0.85rem;
}

.error {
  background: rgba(255, 100, 100, 0.15);
  border: 1px solid rgba(255, 100, 100, 0.3);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: #ff8080;
  font-size: 0.9rem;
}

.actions {
  margin-top: 0.5rem;
}

.start-btn {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
  color: #fff;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.footer {
  margin-top: 1.5rem;
  text-align: center;
}

.back-link {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
  text-decoration: none;
  transition: color 0.2s;
}

.back-link:hover {
  color: rgba(255, 255, 255, 0.9);
}

@media (max-width: 480px) {
  .fan-mode {
    padding: 1rem;
  }

  .card {
    padding: 1.5rem;
  }

  .field-row {
    flex-direction: column;
    align-items: stretch;
  }

  .vs {
    text-align: center;
    padding: 0.25rem 0;
  }

  .format-options {
    flex-direction: column;
  }
}
</style>
