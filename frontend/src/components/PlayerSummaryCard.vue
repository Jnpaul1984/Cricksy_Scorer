<template>
  <div class="player-summary-card">
    <div class="card-header">
      <h3>👤 Player Summary</h3>
      <span class="badge">Simplified for Player</span>
    </div>

    <div v-if="!summary" class="empty-state">
      <p>No player summary available.</p>
    </div>

    <div v-else class="summary-content">
      <!-- Focus Area -->
      <section class="focus-area">
        <h4>🎯 What to Focus On</h4>
        <p class="focus-text">{{ summary.focus_area }}</p>
      </section>

      <!-- Key Points -->
      <section class="key-points">
        <h4>📝 Key Points</h4>
        <ul class="points-list">
          <li v-for="(point, idx) in summary.key_points" :key="idx">
            {{ point }}
          </li>
        </ul>
      </section>

      <!-- Encouragement -->
      <section class="encouragement">
        <div class="encouragement-box">
          <span class="icon">💪</span>
          <p>{{ summary.encouragement }}</p>
        </div>
      </section>

      <!-- Next Steps -->
      <section class="next-steps">
        <h4>🚀 Next Steps</h4>
        <p class="steps-text">{{ summary.next_steps }}</p>
      </section>
    </div>

    <div class="card-footer">
      <button @click="$emit('close')" class="btn-close">Close</button>
      <button @click="copyToClipboard" class="btn-copy">📋 Copy Summary</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PlayerSummaryResponse } from '@/services/coachPlusVideoService';

const props = defineProps<{
  summary: PlayerSummaryResponse | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

function copyToClipboard() {
  if (!props.summary) return;

  const text = `
🎯 What to Focus On:
${props.summary.focus_area}

📝 Key Points:
${props.summary.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n')}

💪 ${props.summary.encouragement}

🚀 Next Steps:
${props.summary.next_steps}
  `.trim();

  navigator.clipboard.writeText(text).then(() => {
    alert('Player summary copied to clipboard!');
  });
}
</script>

<style scoped>
.player-summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 2rem;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.badge {
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.empty-state {
  text-align: center;
  padding: 2rem 1rem;
  opacity: 0.8;
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.summary-content section h4 {
  margin: 0 0 0.75rem;
  font-size: 1.1rem;
  font-weight: 600;
  opacity: 0.9;
}

.focus-text,
.steps-text {
  font-size: 1.05rem;
  line-height: 1.6;
  background: rgba(255, 255, 255, 0.1);
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid rgba(255, 255, 255, 0.5);
}

.points-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.points-list li {
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.points-list li::before {
  content: '✓';
  font-weight: 700;
  flex-shrink: 0;
}

.encouragement-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(255, 255, 255, 0.15);
  padding: 1.25rem;
  border-radius: 8px;
  border: 2px dashed rgba(255, 255, 255, 0.3);
}

.encouragement-box .icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.encouragement-box p {
  margin: 0;
  font-size: 1.1rem;
  line-height: 1.6;
  font-style: italic;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.btn-close,
.btn-copy {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, opacity 0.2s;
}

.btn-close {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-copy {
  background: white;
  color: #667eea;
}

.btn-copy:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}
</style>
