<script setup lang="ts">
import { computed, withDefaults, defineProps } from 'vue'
import { RouterLink } from 'vue-router'

import { BaseCard, BaseBadge } from '@/components'
import { isValidUUID } from '@/utils'
import { fmtSR } from '@/utils/cricket'

type BatEntry = {
  player_id: string
  player_name: string
  runs: number | string
  balls_faced: number | string
  fours: number | string
  sixes: number | string
  strike_rate?: number | string
  how_out?: string
  is_out: boolean
}

const props = withDefaults(defineProps<{
  entries: BatEntry[]
  strikerId?: string
  nonStrikerId?: string
}>(), {
  entries: () => [],
  strikerId: undefined,
  nonStrikerId: undefined,
})

/* ---------- helpers ---------- */
const i = (v: unknown) => {
  const n = Number(v)
  return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0
}
const f = (v: unknown) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}
function sr(e: BatEntry) {
  const given = f(e.strike_rate)
  if (given > 0) return given.toFixed(1)
  return fmtSR(i(e.runs), i(e.balls_faced))
}
function status(e: BatEntry) {
  if (e.is_out) return e.how_out ? `Out (${e.how_out})` : 'Out'
  return 'Not out'
}

/* ---------- view-model rows (normalized once) ---------- */
type Row = {
  id: string
  name: string
  runs: number
  balls: number
  fours: number
  sixes: number
  sr: string
  status: string
  isOut: boolean
  isStriker: boolean
  isNonStriker: boolean
}

const rows = computed<Row[]>(() =>
  (props.entries || []).map((e) => ({
    id: e.player_id,
    name: e.player_name,
    runs: i(e.runs),
    balls: i(e.balls_faced),
    fours: i(e.fours),
    sixes: i(e.sixes),
    sr: sr(e),
    status: status(e),
    isOut: !!e.is_out,
    isStriker: props.strikerId === e.player_id,
    isNonStriker: props.nonStrikerId === e.player_id,
  })),
)
</script>

<template>
  <BaseCard as="section" padding="md" class="batting-card" aria-label="Batting card">
    <h3>Batting</h3>

    <table v-if="rows.length">
      <caption class="visually-hidden">Batting scorecard</caption>
      <colgroup>
        <col />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:6ch" />
        <col />
      </colgroup>
      <thead>
        <tr>
          <th scope="col">Player</th>
          <th scope="col" class="num">R</th>
          <th scope="col" class="num">B</th>
          <th scope="col" class="num">4s</th>
          <th scope="col" class="num">6s</th>
          <th scope="col" class="num">SR</th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.id"
          :class="[{ out: r.isOut, striker: r.isStriker, nonStriker: r.isNonStriker }]"
        >
          <td class="name" :title="r.name">
            <BaseBadge v-if="r.isStriker" variant="primary" condensed class="strike-indicator">●</BaseBadge>
            <RouterLink v-if="isValidUUID(r.id)" :to="{ name: 'PlayerProfile', params: { playerId: r.id } }" class="player-link nameText">{{ r.name }}</RouterLink>
            <span v-else class="nameText">{{ r.name }}</span>
          </td>
          <td class="num">{{ r.runs }}</td>
          <td class="num">{{ r.balls }}</td>
          <td class="num">{{ r.fours }}</td>
          <td class="num">{{ r.sixes }}</td>
          <td class="num">{{ r.sr }}</td>
          <td class="status" :title="r.status">{{ r.status }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty">No batting entries yet.</div>
  </BaseCard>
</template>

<style scoped>
/* BaseCard handles background/border/radius/padding */
.batting-card h3 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-extrabold);
}

table {
  width: 100%;
  border-collapse: collapse;
}

caption.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

th, td {
  padding: var(--space-2);
  border-top: 1px dashed var(--color-border-subtle);
}

thead th {
  border-top: 0;
  text-align: left;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-bold);
}

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.name {
  font-weight: var(--font-bold);
  max-width: 0;
}

.nameText {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}

.status {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.empty {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: var(--space-2) 0;
}

/* Strike indicator badge */
.strike-indicator {
  margin-right: var(--space-1);
  vertical-align: middle;
}

/* Row highlights */
tr.striker .name {
  color: var(--color-primary);
}

tr.nonStriker .name {
  color: var(--color-success);
}

tr.out .name {
  opacity: 0.7;
}

/* Player profile link */
.player-link {
  color: inherit;
  text-decoration: none;
}

.player-link:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
}
</style>
