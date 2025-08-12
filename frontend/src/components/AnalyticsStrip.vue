<template>
  <div class="analytics-strip" v-if="hasAny">
    <div class="card" v-if="strikerName">
      <div class="label">Striker Dot%</div>
      <div class="value">
        {{ strikerDotPct.toFixed(0) }}<span class="unit">%</span>
      </div>
      <div class="sub">{{ strikerName }} · {{ strikerDots }}/{{ strikerBalls }} dots</div>
    </div>

    <div class="card" v-if="bowlerName && bowlerBalls > 0">
      <div class="label">Bowler Dot%</div>
      <div class="value">
        {{ bowlerDotPct.toFixed(0) }}<span class="unit">%</span>
      </div>
      <div class="sub">{{ bowlerName }} · {{ bowlerDots }}/{{ bowlerBalls }} dots</div>
    </div>

    <div class="card">
      <div class="label">Team RR</div>
      <div class="value">{{ teamRR.toFixed(2) }}</div>
      <div class="sub">{{ runs }}/{{ wickets }} in {{ oversDisplay }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

type Batter = { id?: string; name?: string; runs?: number; balls?: number };
type Teams = { batting?: { name?: string }, bowling?: { name?: string } };
type Bowler = { id?: string; name?: string; balls?: number };
type Snapshot = {
  score: { runs: number; wickets: number; overs: number };
  batsmen: { striker: Batter; non_striker: Batter };
  teams?: Teams;
  bowler?: Bowler | null; // optional; hide bowler card if absent
};

const props = defineProps<{
  snapshot: Snapshot | null;
  strikerDots: number;
  strikerBalls: number;
  bowlerDots: number;
  bowlerBalls: number;
}>();

const runs = computed(() => props.snapshot?.score?.runs ?? 0);
const wickets = computed(() => props.snapshot?.score?.wickets ?? 0);
const oversNumber = computed(() => props.snapshot?.score?.overs ?? 0);

function oversToFloat(overs: number): number {
  // Convert 12.3 -> 12 + 3/6; clamp weird decimals
  const whole = Math.trunc(overs);
  const ballsDec = Math.round((overs - whole) * 10);
  const legalBalls = Math.min(Math.max(ballsDec, 0), 5);
  return whole + legalBalls / 6;
}

const oversFloat = computed(() => oversToFloat(oversNumber.value));
const oversDisplay = computed(() => `${oversNumber.value} ov`);
const teamRR = computed(() => {
  const o = oversFloat.value;
  return o > 0 ? runs.value / o : 0;
});

const strikerName = computed(() => props.snapshot?.batsmen?.striker?.name || "");
const bowlerName = computed(() => props.snapshot?.bowler?.name || "");

const strikerDotPct = computed(() => {
  const b = props.strikerBalls;
  return b > 0 ? (props.strikerDots / b) * 100 : 0;
});

const bowlerDotPct = computed(() => {
  const b = props.bowlerBalls;
  return b > 0 ? (props.bowlerDots / b) * 100 : 0;
});

const hasAny = computed(() => true);
</script>

<style scoped>
.analytics-strip {
  display: grid;
  grid-auto-flow: column;
  gap: 10px;
  margin-top: 8px;
  border-top: 1px solid rgba(255,255,255,.06);
  padding-top: 6px;
}
.card {
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 12px;
  padding: 8px 10px;
  min-width: 120px;
}
.label {
  font-size: 11px;
  color: var(--muted);
  letter-spacing: .02em;
}
.value {
  font-weight: 800;
  font-size: 20px;
  line-height: 1.1;
}
.value .unit { font-size: 12px; font-weight: 700; margin-left: 2px; opacity: .8; }
.sub {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
  white-space: nowrap;
}
@media (max-width: 520px) {
  .analytics-strip { grid-auto-flow: row; }
}
</style>
