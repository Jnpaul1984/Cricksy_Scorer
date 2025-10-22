<!-- frontend/src/components/EventOverlay.vue -->
<template>
  <transition name="overlay-pop">
    <div
      v-if="visible && event"
      class="event-overlay"
      role="status"
      aria-live="assertive"
    >
      <div class="badge" :data-kind="event">
        <span v-if="event === 'FOUR'">FOUR!</span>
        <span v-else-if="event === 'SIX'">SIX!</span>
        <span v-else-if="event === 'WICKET'">WICKET!</span>
        <span v-else-if="event === 'DUCK'">🦆 DUCK!</span>
        <span v-else-if="event === 'FIFTY'">50</span>
        <span v-else-if="event === 'HUNDRED'">100</span>
      </div>

      <!-- simple confetti-ish bits (for positive events) -->
      <div v-if="confettiOn" class="confetti">
        <i v-for="n in 24" :key="n" />
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EventType } from "@/composables/useHighlights";

const props = defineProps<{
  event: EventType | null;
  visible: boolean;
  duration?: number; // ms
}>();

// Confetti only for celebratory events
const confettiOn = computed(
  () => props.event === "FOUR" || props.event === "SIX" || props.event === "FIFTY" || props.event === "HUNDRED"
);
</script>

<style scoped>
.event-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  pointer-events: none;
  z-index: 60;
}

.badge {
  font-weight: 800;
  font-size: clamp(2.5rem, 6vw, 5rem);
  line-height: 1;
  padding: 0.5em 0.8em;
  border-radius: 1rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  transform: translateZ(0);
  animation: pulse 0.6s ease-out, floatUp var(--dur, 1.8s) ease-out;
  --dur: 1.8s;
  color: white;
}

/* Color themes per event */
.badge[data-kind="FOUR"],
.badge[data-kind="FIFTY"] { background: linear-gradient(135deg, #00b894, #00cec9); }

.badge[data-kind="SIX"],
.badge[data-kind="HUNDRED"] { background: linear-gradient(135deg, #0984e3, #6c5ce7); }

.badge[data-kind="WICKET"] { background: linear-gradient(135deg, #d63031, #e17055); }
.badge[data-kind="DUCK"]   { background: linear-gradient(135deg, #2d3436, #636e72); }

/* Transition wrapper */
.overlay-pop-enter-active,
.overlay-pop-leave-active { transition: opacity 220ms ease; }
.overlay-pop-enter-from,
.overlay-pop-leave-to { opacity: 0; }

/* Confetti sprinkles */
.confetti {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.confetti i {
  --x: calc((var(--i) - 12) * 3%);
  --delay: calc((var(--i) * 40ms));
  position: absolute;
  top: -10%;
  left: 50%;
  width: 10px;
  height: 16px;
  background: hsl(calc(var(--i) * 15), 80%, 55%);
  transform: translateX(var(--x)) rotate(0deg);
  opacity: 0.95;
  animation: fall var(--dur, 1.8s) linear var(--delay) forwards;
}
.confetti i:nth-child(n)  { --i: 1; }
.confetti i:nth-child(2)  { --i: 2; }
.confetti i:nth-child(3)  { --i: 3; }
.confetti i:nth-child(4)  { --i: 4; }
.confetti i:nth-child(5)  { --i: 5; }
.confetti i:nth-child(6)  { --i: 6; }
.confetti i:nth-child(7)  { --i: 7; }
.confetti i:nth-child(8)  { --i: 8; }
.confetti i:nth-child(9)  { --i: 9; }
.confetti i:nth-child(10) { --i: 10; }
.confetti i:nth-child(11) { --i: 11; }
.confetti i:nth-child(12) { --i: 12; }
.confetti i:nth-child(13) { --i: 13; }
.confetti i:nth-child(14) { --i: 14; }
.confetti i:nth-child(15) { --i: 15; }
.confetti i:nth-child(16) { --i: 16; }
.confetti i:nth-child(17) { --i: 17; }
.confetti i:nth-child(18) { --i: 18; }
.confetti i:nth-child(19) { --i: 19; }
.confetti i:nth-child(20) { --i: 20; }
.confetti i:nth-child(21) { --i: 21; }
.confetti i:nth-child(22) { --i: 22; }
.confetti i:nth-child(23) { --i: 23; }
.confetti i:nth-child(24) { --i: 24; }

@keyframes fall {
  0%   { transform: translate(-50%, -10%) rotate(0deg); opacity: 0; }
  10%  { opacity: 1; }
  100% { transform: translate(-50%, 110%) rotate(360deg); opacity: 0; }
}

@keyframes pulse {
  0% { transform: scale(0.7); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes floatUp {
  0% { transform: translateY(12px); }
  100% { transform: translateY(-8px); }
}
</style>
