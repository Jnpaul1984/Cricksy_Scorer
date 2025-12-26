<template>
  <div class="landing">
    <!-- HERO SECTION -->
    <section class="hero">
      <div class="hero-content">
        <h1>The AI-Powered Cricket Analytics Platform</h1>
        <p class="subtitle">
          Smarter scoring, deeper insights, and automated performance analytics —
          built for coaches, analysts, teams, and tournaments.
        </p>

        <div class="hero-actions">
          <BaseButton
            variant="primary"
            size="lg"
            @click="$router.push({ path: '/auth/register', query: { plan: 'free' } })"
          >
            Get started free
          </BaseButton>

          <BaseButton
            variant="ghost"
            size="lg"
            @click="$router.push({ name: 'PricingPage' })"
          >
            View pricing
          </BaseButton>
        </div>
      </div>

      <div class="hero-visual">
        <BaseCard padding="lg" class="hero-demo">
          <ScoreboardWidget game-id="demo" :can-control="false" />
        </BaseCard>
      </div>
    </section>

    <!-- TRUST SECTION -->
    <section class="trust">
      <p class="trust-title">Trusted by Coaches, Schools, and Tournaments</p>
      <div class="trust-logos">
        <BaseBadge variant="neutral">Barbados Schools</BaseBadge>
        <BaseBadge variant="neutral">Youth Academies</BaseBadge>
        <BaseBadge variant="neutral">Club Cricket</BaseBadge>
        <BaseBadge variant="neutral">Caribbean T20</BaseBadge>
      </div>
    </section>

    <!-- FEATURES GRID -->
    <section class="features-grid">
      <BaseCard class="feature">
        <h3>AI Match Insights</h3>
        <p>
          Understand momentum shifts, player impact, and critical turning points automatically.
        </p>
      </BaseCard>

      <BaseCard class="feature">
        <h3>Smart Scoring Console</h3>
        <p>
          Lightning-fast scoring with automated strike rotation, DLS logic, and mistake prevention.
        </p>
      </BaseCard>

      <BaseCard class="feature">
        <h3>Team & Player Dashboards</h3>
        <p>
          Track development, identify patterns, and prepare smarter for every match.
        </p>
      </BaseCard>

      <BaseCard class="feature">
        <h3>Tournament Engine</h3>
        <p>
          Manage events, generate leaderboards, and follow every match in real time.
        </p>
      </BaseCard>
    </section>

    <!-- PRICING PREVIEW -->
    <section class="pricing-preview">
      <h2>Plans for every level</h2>
      <div class="pricing-preview-grid">
        <BaseCard class="pricing-tile">
          <div class="pricing-tile-header">
            <h3>Cricksy Free</h3>
            <BaseBadge variant="neutral">Best for scorers & fans</BaseBadge>
          </div>
          <p class="pricing-tile-copy">Score matches and follow games with basic stats.</p>
          <p class="pricing-tile-price">$0 / month</p>
          <BaseButton
            variant="ghost"
            size="sm"
            @click="$router.push({ path: '/auth/register', query: { plan: 'free' } })"
          >
            Start free
          </BaseButton>
        </BaseCard>

        <BaseCard class="pricing-tile">
          <div class="pricing-tile-header">
            <h3>Player Pro</h3>
            <BaseBadge variant="primary">For serious players</BaseBadge>
          </div>
          <p class="pricing-tile-copy">Career dashboard, form tracker, AI summaries.</p>
          <p class="pricing-tile-price">From $2.99 / month</p>
          <BaseButton
            variant="ghost"
            size="sm"
            @click="$router.push({ name: 'PricingPage' })"
          >
            View pricing
          </BaseButton>
        </BaseCard>

        <BaseCard class="pricing-tile">
          <div class="pricing-tile-header">
            <h3>Org Pro</h3>
            <BaseBadge variant="success">For schools & clubs</BaseBadge>
          </div>
          <p class="pricing-tile-copy">Teams, coaches, dashboards and sponsor overlays.</p>
          <p class="pricing-tile-price">Starting at $99 / month</p>
          <BaseButton
            variant="ghost"
            size="sm"
            @click="$router.push({ name: 'PricingPage', query: { plan: 'org-starter' } })"
          >
            Contact sales
          </BaseButton>
        </BaseCard>
      </div>
    </section>

    <!-- LIVE DEMO -->
    <section class="live-demo">
      <BaseCard padding="lg" class="demo-card">
        <h2>See Cricksy in Action</h2>
        <p class="subtitle">Real-time scoring and analytics in one platform.</p>
        <ScoreboardWidget game-id="demo" :can-control="false" class="live-demo-widget" />
      </BaseCard>
    </section>

    <!-- WHY SECTION -->
    <section class="why">
      <h2>Why Cricksy?</h2>
      <div class="why-grid">
        <BaseCard>
          <h3>Designed for Coaches</h3>
          <p>Insights that actually help training, selection, and game strategy.</p>
        </BaseCard>

        <BaseCard>
          <h3>Analytics for Everyone</h3>
          <p>From youth teams to clubs and tournaments — powerful tools made simple.</p>
        </BaseCard>

        <BaseCard>
          <h3>AI-Powered Intelligence</h3>
          <p>Automatic breakdowns of overs, phases, and turning points.</p>
        </BaseCard>

        <BaseCard>
          <h3>Fast. Accurate. Modern.</h3>
          <p>A scoring system built for the next generation of cricket analytics.</p>
        </BaseCard>
      </div>
    </section>

    <!-- FINAL CTA -->
    <section class="final-cta">
      <BaseCard padding="lg" class="final-card">
        <h2>Start Scoring Smarter</h2>
        <p class="subtitle">Try Cricksy free — upgrade anytime.</p>

        <BaseButton variant="primary" size="lg" @click="$router.push('/auth/register')">
          Get Started Free
        </BaseButton>
      </BaseCard>
    </section>
  </div>
</template>

<script setup lang="ts">
import { BaseCard, BaseButton, BaseBadge } from '@/components'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
</script>

<style scoped>
.landing {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
  padding-bottom: var(--space-10);
}

/* HERO */
.hero {
  display: grid;
  gap: var(--space-8);
  grid-template-columns: 1fr;
  align-items: center;
  padding-top: var(--space-10);
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1fr 1fr;
  }
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.hero-content h1 {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  line-height: 1.1;
  color: var(--color-text);
}

.hero-actions {
  display: flex;
  gap: var(--space-4);
}

.hero-visual .hero-demo {
  width: 100%;
  height: auto;
}

/* TRUST */
.trust {
  text-align: center;
}

.trust-title {
  color: var(--color-text-muted);
  margin-bottom: var(--space-4);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.trust-logos {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}

/* FEATURES */
.features-grid {
  display: grid;
  gap: var(--space-6);
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.feature h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
  color: var(--color-text);
}

.feature p {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

/* PRICING PREVIEW */
.pricing-preview {
  padding-block: var(--space-10);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.pricing-preview h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  text-align: center;
}

.pricing-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}

.pricing-tile {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.pricing-tile-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.pricing-tile-header h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  margin: 0;
}

.pricing-tile-copy {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.pricing-tile-price {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text);
  margin: 0;
}

/* LIVE DEMO */
.live-demo .demo-card {
  text-align: center;
}

.live-demo h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-2);
}

.live-demo-widget {
  margin-top: var(--space-4);
}

/* WHY */
.why h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  text-align: center;
  margin-bottom: var(--space-6);
}

.why-grid {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.why-grid h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
  color: var(--color-text);
}

.why-grid p {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

/* FINAL CTA */
.final-cta {
  display: flex;
  justify-content: center;
}

.final-card {
  text-align: center;
  max-width: 480px;
  width: 100%;
}

.final-card h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-2);
}

/* SUBTITLE (shared) */
.subtitle {
  color: var(--color-text-muted);
  font-size: var(--text-lg);
  line-height: 1.5;
}

.final-card .subtitle {
  margin-bottom: var(--space-5);
}
</style>
