<!-- frontend/src/views/DesignSystemShowcaseView.vue -->
<template>
  <div class="ds-page">
    <BaseCard as="section" padding="lg" class="ds-showcase">
      <header class="ds-header">
        <h1>Cricksy Design System V1</h1>
        <p class="ds-subtitle">Internal playground for checking components and tokens.</p>
      </header>

      <!-- Buttons Section -->
      <section class="ds-section">
        <h2>Buttons</h2>

        <h3>Variants</h3>
        <div class="ds-row">
          <BaseButton variant="primary">Primary</BaseButton>
          <BaseButton variant="secondary">Secondary</BaseButton>
          <BaseButton variant="ghost">Ghost</BaseButton>
          <BaseButton variant="danger">Danger</BaseButton>
        </div>

        <h3>Sizes</h3>
        <div class="ds-row ds-row--align-end">
          <BaseButton variant="primary" size="sm">Small</BaseButton>
          <BaseButton variant="primary" size="md">Medium</BaseButton>
          <BaseButton variant="primary" size="lg">Large</BaseButton>
        </div>

        <h3>States</h3>
        <div class="ds-row">
          <BaseButton variant="primary" loading>Loading...</BaseButton>
          <BaseButton variant="secondary" disabled>Disabled</BaseButton>
          <BaseButton variant="primary" full-width>Full Width</BaseButton>
        </div>
      </section>

      <!-- Badges Section -->
      <section class="ds-section">
        <h2>Badges</h2>

        <h3>Variants</h3>
        <div class="ds-row">
          <BaseBadge variant="neutral">Neutral</BaseBadge>
          <BaseBadge variant="primary">Primary</BaseBadge>
          <BaseBadge variant="success">Success</BaseBadge>
          <BaseBadge variant="warning">Warning</BaseBadge>
          <BaseBadge variant="danger">Danger</BaseBadge>
        </div>

        <h3>Uppercase Off</h3>
        <div class="ds-row">
          <BaseBadge variant="primary" :uppercase="false">Mixed Case</BaseBadge>
          <BaseBadge variant="success" :uppercase="false">On Strike</BaseBadge>
        </div>

        <h3>Condensed</h3>
        <div class="ds-row">
          <BaseBadge variant="primary" condensed>●</BaseBadge>
          <BaseBadge variant="success" condensed>4</BaseBadge>
          <BaseBadge variant="danger" condensed>W</BaseBadge>
        </div>
      </section>

      <!-- Inputs Section -->
      <section class="ds-section">
        <h2>Inputs</h2>

        <div class="ds-grid">
          <BaseInput
            v-model="demoInput"
            label="Player Name"
            placeholder="Enter player name"
            help-text="This is helper text for the input."
          />

          <BaseInput
            v-model="demoInputError"
            label="Email Address"
            placeholder="you@example.com"
            :error="showInputError ? 'Please enter a valid email address.' : undefined"
          />

          <BaseInput
            model-value="Readonly value"
            label="Disabled Input"
            disabled
          />
        </div>

        <div class="ds-row" style="margin-top: var(--space-md)">
          <BaseButton
            variant="secondary"
            size="sm"
            @click="showInputError = !showInputError"
          >
            Toggle Error State
          </BaseButton>
        </div>
      </section>

      <!-- Cards Section -->
      <section class="ds-section">
        <h2>Cards &amp; Layout</h2>

        <div class="ds-grid ds-grid--cards">
          <BaseCard padding="md">
            <h4>Simple Card</h4>
            <p>Basic content card with medium padding.</p>
          </BaseCard>

          <BaseCard padding="md" interactive>
            <h4>Interactive Card</h4>
            <p>Hover over me for effect.</p>
          </BaseCard>

          <BaseCard padding="sm" class="ds-stat-card">
            <div class="ds-stat-value">142</div>
            <div class="ds-stat-label">Total Runs</div>
          </BaseCard>

          <BaseCard padding="sm" class="ds-stat-card">
            <div class="ds-stat-value">7.2</div>
            <div class="ds-stat-label">Economy</div>
          </BaseCard>
        </div>
      </section>

      <!-- Scoreboard & Overlay Section -->
      <section class="ds-section">
        <h2>Scoreboard &amp; Overlay</h2>

        <BaseCard padding="md" class="ds-scoreboard-placeholder">
          <p class="ds-placeholder-text">
            <strong>ScoreboardWidget</strong> requires a live game ID to render.
            <br />
            Start a match to see the widget in action.
          </p>
        </BaseCard>

        <h3>Event Overlay Preview</h3>
        <div class="ds-overlay-demo">
          <div class="ds-overlay-container">
            <EventOverlay
              :event="demoEvent"
              :visible="demoOverlayVisible"
            />
            <div v-if="!demoOverlayVisible" class="ds-overlay-placeholder">
              Click a button to preview overlay
            </div>
          </div>

          <div class="ds-row">
            <BaseButton size="sm" variant="primary" @click="showOverlay('FOUR')">FOUR</BaseButton>
            <BaseButton size="sm" variant="primary" @click="showOverlay('SIX')">SIX</BaseButton>
            <BaseButton size="sm" variant="danger" @click="showOverlay('WICKET')">WICKET</BaseButton>
            <BaseButton size="sm" variant="secondary" @click="showOverlay('FIFTY')">50</BaseButton>
            <BaseButton size="sm" variant="secondary" @click="showOverlay('HUNDRED')">100</BaseButton>
          </div>
        </div>
      </section>

      <!-- Color Tokens Reference -->
      <section class="ds-section">
        <h2>Color Tokens</h2>
        <div class="ds-color-grid">
          <div class="ds-color-swatch" style="background: var(--color-primary)">
            <span>--color-primary</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-success)">
            <span>--color-success</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-warning)">
            <span>--color-warning</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-danger)">
            <span>--color-danger</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-accent)">
            <span>--color-accent</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-surface)">
            <span>--color-surface</span>
          </div>
          <div class="ds-color-swatch" style="background: var(--color-surface-alt)">
            <span>--color-surface-alt</span>
          </div>
        </div>
      </section>
    </BaseCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { BaseButton, BaseCard, BaseBadge, BaseInput } from '@/components'
import EventOverlay from '@/components/EventOverlay.vue'
import type { EventType } from '@/composables/useHighlights'

// Input demos
const demoInput = ref('')
const demoInputError = ref('')
const showInputError = ref(false)

// Overlay demo
const demoEvent = ref<EventType | null>(null)
const demoOverlayVisible = ref(false)

function showOverlay(event: EventType) {
  demoEvent.value = event
  demoOverlayVisible.value = true

  // Auto-hide after 2 seconds
  setTimeout(() => {
    demoOverlayVisible.value = false
  }, 2000)
}
</script>

<style scoped>
.ds-page {
  min-height: 100vh;
  padding: var(--space-lg);
  background: var(--color-background, var(--color-surface));
}

.ds-showcase {
  max-width: 900px;
  margin: 0 auto;
}

.ds-header {
  margin-bottom: var(--space-xl);
  text-align: center;
}

.ds-header h1 {
  margin: 0 0 var(--space-sm);
  font-size: var(--text-2xl);
}

.ds-subtitle {
  color: var(--color-muted);
  margin: 0;
}

.ds-section {
  margin-bottom: var(--space-xl);
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
}

.ds-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.ds-section h2 {
  font-size: var(--text-xl);
  margin: 0 0 var(--space-md);
}

.ds-section h3 {
  font-size: var(--text-md);
  color: var(--color-muted);
  margin: var(--space-md) 0 var(--space-sm);
}

.ds-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  align-items: center;
}

.ds-row--align-end {
  align-items: flex-end;
}

.ds-grid {
  display: grid;
  gap: var(--space-md);
}

.ds-grid--cards {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.ds-stat-card {
  text-align: center;
}

.ds-stat-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

.ds-stat-label {
  font-size: var(--text-sm);
  color: var(--color-muted);
}

.ds-scoreboard-demo {
  margin-bottom: var(--space-lg);
}

.ds-scoreboard-placeholder {
  text-align: center;
  margin-bottom: var(--space-lg);
}

.ds-placeholder-text {
  color: var(--color-muted);
  margin: 0;
}

.ds-overlay-demo {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.ds-overlay-container {
  position: relative;
  height: 200px;
  background: var(--color-surface-alt);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.ds-overlay-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.ds-color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-sm);
}

.ds-color-swatch {
  height: 80px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: flex-end;
  padding: var(--space-sm);
  box-shadow: var(--shadow-soft);
}

.ds-color-swatch span {
  font-size: var(--text-xs);
  background: var(--color-surface);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  color: var(--color-on-surface);
}
</style>
