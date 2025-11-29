<script setup lang="ts">
import { RouterLink } from 'vue-router'

import logoAvif1024 from '@/assets/optimized/logo-w1024.avif'
import logoWebp1024 from '@/assets/optimized/logo-w1024.webp'
import logoAvif1440 from '@/assets/optimized/logo-w1440.avif'
import logoWebp1440 from '@/assets/optimized/logo-w1440.webp'
import logoAvif480 from '@/assets/optimized/logo-w480.avif'
import logoWebp480 from '@/assets/optimized/logo-w480.webp'
import logoAvif768 from '@/assets/optimized/logo-w768.avif'
import logoWebp768 from '@/assets/optimized/logo-w768.webp'

const logoSources = [
  { width: 480, avif: logoAvif480, webp: logoWebp480 },
  { width: 768, avif: logoAvif768, webp: logoWebp768 },
  { width: 1024, avif: logoAvif1024, webp: logoWebp1024 },
  { width: 1440, avif: logoAvif1440, webp: logoWebp1440 },
] as const

const logoAvifSrcset = logoSources.map((src) => `${src.avif} ${src.width}w`).join(', ')
const logoWebpSrcset = logoSources.map((src) => `${src.webp} ${src.width}w`).join(', ')
const logoFallbackSrc = logoSources.find((src) => src.width === 768)?.webp ?? logoSources[0].webp

const personas = [
  {
    icon: '📋',
    title: 'Scorers',
    description: 'Intuitive ball-by-ball scoring with real-time sync and offline support.',
  },
  {
    icon: '🎯',
    title: 'Coaches',
    description: 'Advanced analytics, player performance tracking, and tactical insights.',
  },
  {
    icon: '📊',
    title: 'Analysts',
    description: 'ML-powered predictions, historical data, and exportable reports.',
  },
  {
    icon: '🏏',
    title: 'Fans',
    description: 'Follow live matches, track favorite players, and view leaderboards.',
  },
]

const steps = [
  {
    step: 1,
    title: 'Create a Match',
    description: 'Set up teams, players, and match format in seconds.',
  },
  {
    step: 2,
    title: 'Score Live',
    description: 'Record every ball with our streamlined scoring interface.',
  },
  {
    step: 3,
    title: 'Share & Analyze',
    description: 'Broadcast live scoreboards and dive into rich analytics.',
  },
]
</script>

<template>
  <div class="landing">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <picture class="hero-logo">
          <source :srcset="logoAvifSrcset" sizes="120px" type="image/avif" />
          <source :srcset="logoWebpSrcset" sizes="120px" type="image/webp" />
          <img
            :src="logoFallbackSrc"
            sizes="120px"
            alt="Cricksy Mascot"
            loading="eager"
            decoding="async"
            width="120"
            height="120"
          />
        </picture>
        <h1 class="hero-title">Cricksy Scorer</h1>
        <p class="hero-tagline">
          The modern cricket scoring platform for clubs, leagues, and fans.
        </p>
        <div class="hero-actions">
          <RouterLink to="/login" class="btn btn-primary">Start Scoring</RouterLink>
          <RouterLink to="/fan" class="btn btn-secondary">View Demo</RouterLink>
        </div>
      </div>
    </section>

    <!-- Value Props Section -->
    <section class="personas">
      <h2 class="section-title">Built for Everyone in Cricket</h2>
      <div class="personas-grid">
        <div v-for="persona in personas" :key="persona.title" class="persona-card">
          <span class="persona-icon">{{ persona.icon }}</span>
          <h3 class="persona-title">{{ persona.title }}</h3>
          <p class="persona-desc">{{ persona.description }}</p>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="how-it-works">
      <h2 class="section-title">How It Works</h2>
      <div class="steps-grid">
        <div v-for="item in steps" :key="item.step" class="step-card">
          <div class="step-number">{{ item.step }}</div>
          <h3 class="step-title">{{ item.title }}</h3>
          <p class="step-desc">{{ item.description }}</p>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="cta">
      <h2 class="cta-title">Ready to elevate your cricket experience?</h2>
      <div class="cta-actions">
        <RouterLink to="/login" class="btn btn-primary">Sign In</RouterLink>
        <RouterLink to="/fan" class="btn btn-ghost">Try Fan Mode</RouterLink>
        <RouterLink to="/pricing" class="btn btn-ghost">View Pricing</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.landing {
  color: var(--color-text);
}

/* Hero Section */
.hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  padding: var(--space-8) var(--space-4);
  text-align: center;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.08), rgba(16, 185, 129, 0.06));
}

.hero-content {
  max-width: 640px;
}

.hero-logo {
  display: inline-block;
  margin-bottom: var(--space-4);
}

.hero-logo img {
  width: 120px;
  height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(34, 211, 238, 0.3));
}

.hero-title {
  font-family: var(--font-heading);
  font-size: var(--text-4xl);
  font-weight: var(--font-extrabold);
  color: var(--color-primary);
  margin: 0 0 var(--space-3);
  line-height: var(--leading-tight);
}

.hero-tagline {
  font-size: var(--text-xl);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6);
  line-height: var(--leading-relaxed);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-3) var(--space-5);
  font-family: var(--font-body);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: var(--color-primary);
  color: #0f172a;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--color-secondary);
  color: #fff;
}

.btn-secondary:hover {
  background: var(--color-secondary-hover);
  transform: translateY(-1px);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border-strong);
}

.btn-ghost:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary);
}

/* Section Titles */
.section-title {
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  text-align: center;
  margin: 0 0 var(--space-6);
  color: var(--color-text);
}

/* Personas Section */
.personas {
  padding: var(--space-10) var(--space-4);
  background: var(--color-surface);
}

.personas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-5);
  max-width: 1000px;
  margin: 0 auto;
}

.persona-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  text-align: center;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.persona-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.persona-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: var(--space-3);
}

.persona-title {
  font-family: var(--font-heading);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-2);
  color: var(--color-primary);
}

.persona-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: var(--leading-relaxed);
}

/* How It Works Section */
.how-it-works {
  padding: var(--space-10) var(--space-4);
  background: var(--color-bg);
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-5);
  max-width: 900px;
  margin: 0 auto;
}

.step-card {
  text-align: center;
  padding: var(--space-5);
}

.step-number {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-heading);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  background: var(--color-primary);
  color: #0f172a;
  border-radius: var(--radius-pill);
  margin-bottom: var(--space-3);
}

.step-title {
  font-family: var(--font-heading);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-2);
  color: var(--color-text);
}

.step-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: var(--leading-relaxed);
}

/* CTA Section */
.cta {
  padding: var(--space-10) var(--space-4);
  text-align: center;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.06), rgba(245, 158, 11, 0.04));
}

.cta-title {
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin: 0 0 var(--space-5);
  color: var(--color-text);
}

.cta-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
}

/* Responsive */
@media (max-width: 640px) {
  .hero {
    min-height: 60vh;
    padding: var(--space-6) var(--space-4);
  }

  .hero-logo img {
    width: 80px;
    height: 80px;
  }

  .hero-title {
    font-size: var(--text-3xl);
  }

  .hero-tagline {
    font-size: var(--text-lg);
  }

  .section-title {
    font-size: var(--text-xl);
  }

  .personas,
  .how-it-works,
  .cta {
    padding: var(--space-8) var(--space-4);
  }
}
</style>
