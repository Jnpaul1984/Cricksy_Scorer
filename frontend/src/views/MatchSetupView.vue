<script setup lang="ts">
import { reactive, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'
import { getErrorMessage } from '@/utils/api'
import type { GameState } from '@/types'
import PlayersEditor from '@/components/PlayersEditor.vue'

const router = useRouter()
const game = useGameStore()
const creating = ref(false)
const errorMsg = ref<string | null>(null)

type Form = {
  team_a_name: string
  team_b_name: string
  match_type: 'limited' | 'multi_day' | 'custom'
  overs_limit: number | null
  days_limit: number | null
  overs_per_day: number | null
  dls_enabled: boolean
  toss_winner_team: string
  decision: 'bat' | 'bowl'
}

const form = reactive<Form>({
  team_a_name: '',
  team_b_name: '',
  match_type: 'limited',
  overs_limit: 25,
  days_limit: null,
  overs_per_day: null,
  dls_enabled: false,
  toss_winner_team: '',
  decision: 'bat',
})

// ✅ arrays controlled by PlayersEditor
const playersA = ref<string[]>([])
const playersB = ref<string[]>([])

const canSubmit = computed(() => {
  const a = playersA.value.length >= 2
  const b = playersB.value.length >= 2
  return !!(form.team_a_name && form.team_b_name && a && b && form.toss_winner_team)
})

async function onSubmit() {
  if (!canSubmit.value || creating.value) return
  creating.value = true
  errorMsg.value = null
  try {
    const payload = {
      team_a_name: form.team_a_name,
      team_b_name: form.team_b_name,
      players_a: playersA.value,
      players_b: playersB.value,
      match_type: form.match_type,
      overs_limit: form.match_type === 'limited' ? form.overs_limit : null,
      days_limit: form.match_type === 'multi_day' ? form.days_limit : null,
      overs_per_day: form.match_type === 'multi_day' ? form.overs_per_day : null,
      dls_enabled: form.dls_enabled,
      interruptions: [],
      toss_winner_team: form.toss_winner_team,
      decision: form.decision,
    } as const

    const created = (await game.createNewGame(payload as any)) as GameState
    await router.push({ name: 'team-select', params: { gameId: created.id } })
  } catch (e) {
    errorMsg.value = getErrorMessage(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="setup">
    <div class="card">
      <h2>Create Match</h2>

      <form class="form" @submit.prevent="onSubmit">
        <div class="row two">
          <div>
            <label>Team A Name</label>
            <input v-model="form.team_a_name" placeholder="e.g., Bagatelle" />
          </div>
          <div>
            <label>Team B Name</label>
            <input v-model="form.team_b_name" placeholder="e.g., Bridgetown" />
          </div>
        </div>

        <!-- 🎯 New players editors -->
        <div class="row">
          <PlayersEditor
            v-model="playersA"
            :label="'Players – Team A'"
            :teamName="form.team_a_name"
            :max="16"
            :min="2"
          />
        </div>

        <div class="row">
          <PlayersEditor
            v-model="playersB"
            :label="'Players – Team B'"
            :teamName="form.team_b_name"
            :max="16"
            :min="2"
          />
        </div>

        <div class="row two">
          <div>
            <label>Match Type</label>
            <select v-model="form.match_type">
              <option value="limited">Limited Overs</option>
              <option value="multi_day">Multi-day</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div v-if="form.match_type === 'limited'">
            <label>Overs (per innings)</label>
            <input type="number" min="1" max="120" v-model.number="form.overs_limit" />
          </div>
          <template v-else-if="form.match_type === 'multi_day'">
            <div>
              <label>Days</label>
              <input type="number" min="1" max="7" v-model.number="form.days_limit" />
            </div>
            <div>
              <label>Overs per Day</label>
              <input type="number" min="1" max="120" v-model.number="form.overs_per_day" />
            </div>
          </template>
        </div>

        <div class="row two">
          <div>
            <label>DLS Enabled</label>
            <select v-model="form.dls_enabled">
              <option :value="false">No</option>
              <option :value="true">Yes</option>
            </select>
          </div>
          <div>
            <label>Toss Winner</label>
            <select v-model="form.toss_winner_team">
              <option value="">— select —</option>
              <option :value="form.team_a_name" v-if="form.team_a_name">{{ form.team_a_name }}</option>
              <option :value="form.team_b_name" v-if="form.team_b_name">{{ form.team_b_name }}</option>
            </select>
          </div>
        </div>

        <div class="row">
          <label>Decision</label>
          <div class="toggle">
            <label><input type="radio" value="bat" v-model="form.decision" /> Bat</label>
            <label><input type="radio" value="bowl" v-model="form.decision" /> Bowl</label>
          </div>
        </div>

        <div class="actions">
          <button class="primary" type="submit" :disabled="!canSubmit || creating">
            {{ creating ? 'Creating…' : 'Create New Match' }}
          </button>
        </div>

        <div v-if="errorMsg" class="error">
          ❌ {{ errorMsg }}
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.setup{min-height:100vh;padding:2rem;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}
.card{max-width:900px;margin:0 auto;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:18px;padding:1.25rem}
h2{color:#fff;margin:0 0 1rem}
.form{display:block}
.row{display:flex;flex-direction:column;gap:.5rem;margin:.9rem 0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
label{color:#fff;opacity:.9}
input,select{padding:.7rem;border-radius:10px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.1);color:#fff}
.toggle{display:flex;gap:1rem;color:#fff}
.actions{display:flex;justify-content:flex-end;margin-top:1rem}
.primary{background:linear-gradient(135deg,#f44336,#b71c1c);color:#fff;border:none;padding:.9rem 1.4rem;border-radius:28px;cursor:pointer;font-weight:700}
.primary:disabled{opacity:.6;cursor:not-allowed}
.error{margin-top:.75rem;color:#ffb3b3}
@media(max-width:800px){.two{grid-template-columns:1fr}}
</style>
