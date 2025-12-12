<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <BaseCard class="beta-modal" padding="lg">
          <h2 class="modal-title">Cricksy Beta Checklist</h2>
          <p class="modal-intro">
            Welcome to the Cricksy beta! Use this checklist to track your testing progress. For full details, see the Beta Tester Guide.
          </p>

          <div class="checklist-section">
            <h3><BaseBadge variant="primary">Match Setup & Scoring</BaseBadge></h3>
            <div v-for="(item, i) in matchChecklist" :key="'match-' + i" class="checklist-item">
              <input type="checkbox" v-model="checked.match[i]" :id="'match-' + i" />
              <label :for="'match-' + i">{{ item }}</label>
            </div>
          </div>

          <div class="checklist-section">
            <h3><BaseBadge variant="success">Viewer & Sharing</BaseBadge></h3>
            <div v-for="(item, i) in viewerChecklist" :key="'viewer-' + i" class="checklist-item">
              <input type="checkbox" v-model="checked.viewer[i]" :id="'viewer-' + i" />
              <label :for="'viewer-' + i">{{ item }}</label>
            </div>
          </div>

          <div class="checklist-section">
            <h3><BaseBadge variant="warning">Player Profiles & AI Insights</BaseBadge></h3>
            <div v-for="(item, i) in profileChecklist" :key="'profile-' + i" class="checklist-item">
              <input type="checkbox" v-model="checked.profile[i]" :id="'profile-' + i" />
              <label :for="'profile-' + i">{{ item }}</label>
            </div>
          </div>

          <div v-if="showDashboards" class="checklist-section">
            <h3><BaseBadge variant="neutral">Analyst / Org Dashboards</BaseBadge></h3>
            <div v-for="(item, i) in dashboardChecklist" :key="'dash-' + i" class="checklist-item">
              <input type="checkbox" v-model="checked.dash[i]" :id="'dash-' + i" />
              <label :for="'dash-' + i">{{ item }}</label>
            </div>
          </div>

          <div class="modal-footer">
            <BaseButton variant="secondary" @click="close">Close</BaseButton>
            <BaseButton as="a" :href="guideUrl" target="_blank" variant="primary">Open Full Guide</BaseButton>
          </div>
        </BaseCard>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { BaseCard, BaseButton, BaseBadge } from '@/components'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits(['update:visible'])

const guideUrl = 'https://github.com/Jnpaul1984/Cricksy_Scorer/blob/main/docs/beta/Cricksy_Beta_Tester_Guide.md'

const matchChecklist = [
  'Create a new match',
  'Add teams and players',
  'Score 5–10 overs ball-by-ball',
  'Record wickets and extras',
  'Try retire hurt, bowler change, etc.',
]
const viewerChecklist = [
  'Open the public viewer',
  'Check live score updates',
  'Share a match link and open on another device',
]
const profileChecklist = [
  'Open a player profile',
  'Review stats and graphs',
  'Read AI summaries',
]
const dashboardChecklist = [
  'Open Analyst Workspace or Org Dashboard',
  'Filter matches or teams',
  'Review analytics and charts',
]

const checked = ref({
  match: Array(matchChecklist.length).fill(false),
  viewer: Array(viewerChecklist.length).fill(false),
  profile: Array(profileChecklist.length).fill(false),
  dash: Array(dashboardChecklist.length).fill(false),
})

const showDashboards = computed(() => {
  // This prop should be set by parent based on user profile, or you can inject user store here
  // For now, always show for demo; replace with real logic as needed
  return true
})

watch(() => props.visible, (val) => {
  if (!val) {
    // Reset checklist when closed
    checked.value = {
      match: Array(matchChecklist.length).fill(false),
      viewer: Array(viewerChecklist.length).fill(false),
      profile: Array(profileChecklist.length).fill(false),
      dash: Array(dashboardChecklist.length).fill(false),
    }
  }
})

function close() {
  emit('update:visible', false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.beta-modal {
  max-width: 480px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-title {
  margin-bottom: 0.5em;
}
.modal-intro {
  margin-bottom: 1.5em;
  color: #444;
}
.checklist-section {
  margin-bottom: 1.2em;
}
.checklist-item {
  display: flex;
  align-items: center;
  gap: 0.5em;
  margin-bottom: 0.4em;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75em;
  margin-top: 2em;
}
</style>
