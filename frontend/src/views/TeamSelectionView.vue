<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'

import { useGameStore } from '@/stores/gameStore'

type XI = {
  keeper_b: string | null;
  captain_a: string | null;
  keeper_a: string | null;
  captain_b: string | null; team_a_xi: string[]; team_b_xi: string[]
}
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
const teamADisplayName = computed(() =>
  teamA.value?.name && teamA.value.name.trim().length ? teamA.value.name : 'Team A'
)
const teamBDisplayName = computed(() =>
  teamB.value?.name && teamB.value.name.trim().length ? teamB.value.name : 'Team B'
)

const selectedA = ref<Set<string>>(new Set())
const selectedB = ref<Set<string>>(new Set())

// NEW: role selections
const captainA = ref<string | null>(null)
const keeperA  = ref<string | null>(null)
const captainB = ref<string | null>(null)
const keeperB  = ref<string | null>(null)

// (optional) require roles to be chosen before continuing
const canContinue = computed(() =>
  selectedA.value.size === 11 &&
  selectedB.value.size === 11 &&
  !!captainA.value && !!keeperA.value &&
  !!captainB.value && !!keeperB.value
)

// Flatten sets to arrays (used for payload and dropdowns)
const xiAList = computed(() => Array.from(selectedA.value))
const xiBList = computed(() => Array.from(selectedB.value))

// teamA/teamB already exist as computed(() => game.currentGame?.team_a / team_b)
function nameFromId(id: string, team: any) {
  const arr = team?.players ?? []
  const found = Array.isArray(arr) ? arr.find((p: any) => p?.id === id) : undefined
  return found?.name ?? id
}

// Basic in-UI guard to keep roles within the XI
function validateRoles(): string | null {
  if (xiAList.value.length !== 11 || xiBList.value.length !== 11) return 'Each XI must be 11 players.'
  const teamAName = teamADisplayName.value
  const teamBName = teamBDisplayName.value
  if (captainA.value && !selectedA.value.has(captainA.value)) return `${teamAName} captain must be in the XI.`
  if (keeperA.value  && !selectedA.value.has(keeperA.value))  return `${teamAName} wicket-keeper must be in the XI.`
  if (captainB.value && !selectedB.value.has(captainB.value)) return `${teamBName} captain must be in the XI.`
  if (keeperB.value  && !selectedB.value.has(keeperB.value))  return `${teamBName} wicket-keeper must be in the XI.`
  return null
}


function loadSavedXI() {
  try {
    const raw = localStorage.getItem(KEY(gameId.value))
    if (!raw) return
    const obj = JSON.parse(raw) as XI
    if (Array.isArray(obj.team_a_xi)) selectedA.value = new Set(obj.team_a_xi)
    if (Array.isArray(obj.team_b_xi)) selectedB.value = new Set(obj.team_b_xi)
    if (obj.captain_a) captainA.value = obj.captain_a
    if (obj.keeper_a)  keeperA.value  = obj.keeper_a
    if (obj.captain_b) captainB.value = obj.captain_b
    if (obj.keeper_b)  keeperB.value  = obj.keeper_b

  } catch {
    // ignore corrupted cached XI data
  }
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

async function persistXIIfSupported() {
  const base = (import.meta as any).env.VITE_API_BASE_URL?.replace(/\/+$/, '')
  if (!base) return

  const payload = {
    team_a: xiAList.value,
    team_b: xiBList.value,
    captain_a: captainA.value,
    keeper_a:  keeperA.value,
    captain_b: captainB.value,
    keeper_b:  keeperB.value,
  }

  const res = await fetch(`${base}/games/${encodeURIComponent(gameId.value)}/playing-xi`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(`Failed to set XI: ${res.status} ${JSON.stringify(body)}`)
  }
}


async function continueToScoring() {
  if (!canContinue.value || saving.value) return
  saving.value = true
  errorMsg.value = null

  try {
    // NEW: validate roles on the client
    const v = validateRoles()
    if (v) throw new Error(v)

    // Save XI locally (your existing code)
    const xi = {
      team_a_xi: xiAList.value,
      team_b_xi: xiBList.value,
      captain_a: captainA.value,
      keeper_a: keeperA.value,
      captain_b: captainB.value,
      keeper_b: keeperB.value,
    }
    localStorage.setItem(KEY(gameId.value), JSON.stringify(xi))

    // NEW: send XI + roles to backend
    await persistXIIfSupported()

    // (Your existing navigation to scoring)
    await game.loadGame(gameId.value) // optional refresh if you want captain/keeper reflected immediately
    router.push({ name: 'GameScoringView', params: { gameId: gameId.value } })
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
        <h3>{{ teamADisplayName }}</h3>
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
    <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
      <div>
        <label class="block text-sm font-medium mb-1">{{ teamADisplayName }} Captain</label>
        <select v-model="captainA" class="w-full border rounded p-2" :disabled="xiAList.length === 0">
          <option :value="null" disabled>Select captain</option>
          <option v-for="pid in xiAList" :key="pid" :value="pid">
            {{ nameFromId(pid, teamA) }}
          </option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">{{ teamADisplayName }} Wicket-keeper</label>
        <select v-model="keeperA" class="w-full border rounded p-2" :disabled="xiAList.length === 0">
          <option :value="null" disabled>Select wicket-keeper</option>
          <option v-for="pid in xiAList" :key="pid" :value="pid">
            {{ nameFromId(pid, teamA) }}
          </option>
        </select>
      </div>
    </div>

      <section class="team">
        <h3>{{ teamBDisplayName }}</h3>
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
    <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
      <div>
        <label class="block text-sm font-medium mb-1">{{ teamBDisplayName }} Captain</label>
        <select v-model="captainB" class="w-full border rounded p-2" :disabled="xiBList.length === 0">
          <option :value="null" disabled>Select captain</option>
          <option v-for="pid in xiBList" :key="pid" :value="pid">
            {{ nameFromId(pid, teamB) }}
          </option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">{{ teamBDisplayName }} Wicket-keeper</label>
        <select v-model="keeperB" class="w-full border rounded p-2" :disabled="xiBList.length === 0">
          <option :value="null" disabled>Select wicket-keeper</option>
          <option v-for="pid in xiBList" :key="pid" :value="pid">
            {{ nameFromId(pid, teamB) }}
          </option>
        </select>
      </div>
    </div>

    </div>

    <div v-if="errorMsg" class="error">❌ {{ errorMsg }}</div>

    <div v-if="game.currentGame" class="actions">
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
