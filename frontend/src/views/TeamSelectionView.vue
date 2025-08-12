<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'

type XI = { team_a_xi: string[]; team_b_xi: string[] }
const KEY = (id: string) => `cricksy.xi.${id}`

const route = useRoute()
const router = useRouter()
const game = useGameStore()

const gameId = computed(() => (route.params.gameId as string) || '')
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref<string | null>(null)

const teamA = computed(() => game.currentGame?.team_a)
const teamB = computed(() => game.currentGame?.team_b)

const selectedA = ref<Set<string>>(new Set())
const selectedB = ref<Set<string>>(new Set())

const canContinue = computed(() => selectedA.value.size === 11 && selectedB.value.size === 11)

function loadSavedXI() {
  try {
    const raw = localStorage.getItem(KEY(gameId.value))
    if (!raw) return
    const obj = JSON.parse(raw) as XI
    if (Array.isArray(obj.team_a_xi)) selectedA.value = new Set(obj.team_a_xi)
    if (Array.isArray(obj.team_b_xi)) selectedB.value = new Set(obj.team_b_xi)
  } catch {}
}

function prefillIfEmpty() {
  if (selectedA.value.size === 0 && teamA.value?.players?.length) {
    teamA.value.players.slice(0, 11).forEach(p => selectedA.value.add(p.id))
  }
  if (selectedB.value.size === 0 && teamB.value?.players?.length) {
    teamB.value.players.slice(0, 11).forEach(p => selectedB.value.add(p.id))
  }
}

function toggleA(id: string) {
  if (selectedA.value.has(id)) {
    selectedA.value.delete(id)
  } else {
    if (selectedA.value.size >= 11) return
    selectedA.value.add(id)
  }
  selectedA.value = new Set(selectedA.value)
}
function toggleB(id: string) {
  if (selectedB.value.has(id)) {
    selectedB.value.delete(id)
  } else {
    if (selectedB.value.size >= 11) return
    selectedB.value.add(id)
  }
  selectedB.value = new Set(selectedB.value)
}

async function persistXIIfSupported(xi: XI) {
  // Optional best-effort persist (ignore if your backend doesn’t support it)
  try {
    const base = (import.meta as any).env.VITE_API_BASE_URL?.replace(/\/+$/, '')
    if (!base) return
    const res = await fetch(`${base}/games/${encodeURIComponent(gameId.value)}/playing-xi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(xi),
    })
    if (!res.ok) {
      // Allow 404/405/501 etc. to pass silently; the step is optional server-side
      return
    }
  } catch {
    // network issues? fine, we still move on because XI is stored locally
  }
}

async function continueToScoring() {
  if (!canContinue.value || saving.value) return
  saving.value = true
  errorMsg.value = null
  try {
    const xi: XI = {
      team_a_xi: Array.from(selectedA.value),
      team_b_xi: Array.from(selectedB.value),
    }
    localStorage.setItem(KEY(gameId.value), JSON.stringify(xi))
    await persistXIIfSupported(xi)
    await router.push({ name: 'game', params: { gameId: gameId.value } })
  } catch (e: any) {
    errorMsg.value = e?.message || 'Failed to continue'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!gameId.value) return router.replace('/')
  try {
    if (!game.currentGame || gameId.value !== game.currentGame.id) {
      await game.loadGame(gameId.value)
    }
    loadSavedXI()
    prefillIfEmpty()
  } catch (e: any) {
    errorMsg.value = e?.message || 'Failed to load match'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="wrap">
    <div class="header">
      <RouterLink to="/" class="back">← Back</RouterLink>
      <h2>Select Playing XI</h2>
      <div class="spacer"></div>
    </div>

    <div v-if="loading" class="loading">Loading match…</div>
    <div v-else-if="!game.currentGame" class="error">No match found.</div>
    <div v-else class="grid">
      <section class="team">
        <h3>{{ teamA?.name || 'Team A' }}</h3>
        <p class="hint">Pick 11 players ({{ selectedA.size }}/11)</p>
        <ul>
          <li
            v-for="p in teamA?.players || []"
            :key="p.id"
            :class="['row', { picked: selectedA.has(p.id), full: selectedA.size >= 11 && !selectedA.has(p.id) }]"
            @click="toggleA(p.id)"
          >
            <input type="checkbox" :checked="selectedA.has(p.id)" @change.prevent />
            <span>{{ p.name }}</span>
          </li>
        </ul>
      </section>

      <section class="team">
        <h3>{{ teamB?.name || 'Team B' }}</h3>
        <p class="hint">Pick 11 players ({{ selectedB.size }}/11)</p>
        <ul>
          <li
            v-for="p in teamB?.players || []"
            :key="p.id"
            :class="['row', { picked: selectedB.has(p.id), full: selectedB.size >= 11 && !selectedB.has(p.id) }]"
            @click="toggleB(p.id)"
          >
            <input type="checkbox" :checked="selectedB.has(p.id)" @change.prevent />
            <span>{{ p.name }}</span>
          </li>
        </ul>
      </section>
    </div>

    <div v-if="errorMsg" class="error">❌ {{ errorMsg }}</div>

    <div class="actions" v-if="game.currentGame">
      <button class="secondary" @click="$router.replace('/')">Cancel</button>
      <button class="primary" :disabled="!canContinue || saving" @click="continueToScoring">
        {{ saving ? 'Saving…' : 'Save & Continue' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.wrap{min-height:100vh;padding:1.25rem;background:linear-gradient(135deg,#0f1115,#151926 35%,#1c2340);color:#fff}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.back{color:#c9d1e6;text-decoration:none}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:1100px;margin:0 auto}
.team{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:1rem}
.team h3{margin:0 0 .25rem}
.hint{opacity:.85;margin:.1rem 0 .8rem}
ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr;gap:.35rem;max-height:60vh;overflow:auto}
.row{display:flex;align-items:center;gap:.6rem;padding:.55rem .6rem;border-radius:10px;background:rgba(255,255,255,.05);cursor:pointer}
.row.full{opacity:.6;cursor:not-allowed}
.row.picked{background:rgba(46,204,113,.16);border:1px solid rgba(46,204,113,.35)}
.loading,.error{text-align:center;opacity:.9;margin:2rem 0}
.actions{display:flex;gap:.75rem;justify-content:flex-end;max-width:1100px;margin:1rem auto 0}
.secondary{background:transparent;border:1px solid rgba(255,255,255,.3);color:#fff;padding:.6rem 1rem;border-radius:10px;cursor:pointer}
.primary{background:linear-gradient(135deg,#f44336,#b71c1c);border:none;color:#fff;padding:.7rem 1.2rem;border-radius:999px;cursor:pointer}
.primary:disabled{opacity:.6;cursor:not-allowed}
@media (max-width:900px){.grid{grid-template-columns:1fr}}
</style>
