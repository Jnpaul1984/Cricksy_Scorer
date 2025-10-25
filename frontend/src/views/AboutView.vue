<template>
  <div class="about-view">
    <div class="container">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">About Cricksy Scorer</h1>
          <p class="hero-subtitle">
            Professional cricket scoring application designed specifically for schools
          </p>
        </div>
      </section>

      <!-- Features Section -->
      <section class="features-section">
        <h2 class="section-title">Why Choose Cricksy Scorer?</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">🏏</div>
            <h3>School-Focused</h3>
            <p>Designed specifically for 25-over school cricket matches with simplified scoring</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>Real-time Statistics</h3>
            <p>Live batting and bowling scorecards with detailed player statistics</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">📱</div>
            <h3>Mobile Friendly</h3>
            <p>Responsive design works perfectly on tablets and phones for field scoring</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">💾</div>
            <h3>Data Export</h3>
            <p>Export complete game data as JSON files for record keeping and analysis</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <h3>Fast & Reliable</h3>
            <p>Built with modern web technologies for speed and reliability</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <h3>Easy to Use</h3>
            <p>Intuitive interface that anyone can learn quickly</p>
          </div>
        </div>
      </section>

      <!-- Technical Section -->
      <section class="tech-section">
        <h2 class="section-title">Technical Details</h2>
        <div class="tech-content">
          <div class="tech-item">
            <h3>Frontend</h3>
            <p>Vue.js 3 with TypeScript for a modern, type-safe user interface</p>
          </div>

          <div class="tech-item">
            <h3>Backend</h3>
            <p>FastAPI with PostgreSQL for robust data storage and API performance</p>
          </div>

          <div class="tech-item">
            <h3>Deployment</h3>
            <p>Cloud-ready architecture with Docker support for easy deployment</p>
          </div>
        </div>
      </section>

      <!-- Contact Section -->
      <section class="contact-section">
        <h2 class="section-title">Get Started</h2>
        <div class="contact-content">
          <p>Ready to transform your school's cricket scoring?</p>
          <RouterLink to="/" class="cta-button">
            🏏 Start Scoring Now
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.about-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.hero-section {
  text-align: center;
  margin-bottom: 4rem;
}

.hero-content {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 3rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.hero-title {
  font-size: 3rem;
  font-weight: bold;
  color: white;
  margin-bottom: 1rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.9);
  max-width: 600px;
  margin: 0 auto;
}

.section-title {
  font-size: 2rem;
  font-weight: bold;
  color: white;
  text-align: center;
  margin-bottom: 2rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.features-section {
  margin-bottom: 4rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.3rem;
  font-weight: bold;
  color: white;
  margin-bottom: 1rem;
}

.feature-card p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

.tech-section {
  margin-bottom: 4rem;
}

.tech-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.tech-item {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.tech-item h3 {
  font-size: 1.2rem;
  font-weight: bold;
  color: white;
  margin-bottom: 1rem;
}

.tech-item p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

.contact-section {
  text-align: center;
}

.contact-content {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 3rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.contact-content p {
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2rem;
}

.cta-button {
  display: inline-block;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
  color: white;
  padding: 1rem 2rem;
  border-radius: 50px;
  text-decoration: none;
  font-weight: bold;
  font-size: 1.1rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }

  .hero-content,
  .contact-content {
    padding: 2rem;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .container {
    padding: 0 1rem;
  }
}
</style>
