<template>
  <main class="help-view">
    <div class="help-container">
      <!-- Header -->
      <header class="help-header">
        <h1>Cricksy Scorer — Help & Guide</h1>
        <p>Learn how to score, share, and broadcast your matches.</p>
      </header>

      <!-- Navigation Tabs -->
      <nav class="help-nav">
        <button
          v-for="tab in tabs"
          :key="tab"
          :class="{ active: activeTab === tab }"
          class="nav-btn"
          @click="activeTab = tab"
        >
          {{ formatTabName(tab) }}
        </button>
      </nav>

      <!-- Content Sections -->
      <div class="help-content">
        <!-- Scoring Section -->
        <section v-show="activeTab === 'scoring'" class="help-section">
          <h2>Ball-by-Ball Scoring</h2>
          <div class="section-content">
            <h3>Basic Runs</h3>
            <p>Click the run buttons (0–6) to record runs off each delivery. Runs accumulate immediately.</p>
            
            <h3>Extras</h3>
            <p><strong>Wides & No-balls:</strong> Click the "W" or "NB" button. These add 1 run automatically and don't count as a legal ball.</p>
            <p><strong>Byes & Leg-byes:</strong> Click "By" or "LB". These are extras but do count as legal balls.</p>

            <h3>Wickets</h3>
            <p>Click the <strong>Wicket</strong> button to dismiss the striker. Select the dismissal type and (optionally) which batsman to dismiss next.</p>

            <h3>Undo Last Ball</h3>
            <p>Click <strong>Undo</strong> to revert the last delivery and restore match state completely.</p>

            <h3>Commentary</h3>
            <p>Add optional commentary for each ball in the text field. This appears in ball-by-ball replays.</p>
          </div>
        </section>

        <!-- Viewer Section -->
        <section v-show="activeTab === 'viewer'" class="help-section">
          <h2>Public Scoreboard Viewer</h2>
          <div class="section-content">
            <h3>Share Live Scores</h3>
            <p>Once a match is underway, anyone can watch the live score on the public viewer.</p>

            <div class="code-example">
              <code>https://cricksy.app/#/view/&lt;game-id&gt;</code>
            </div>

            <h3>Customizing the Viewer</h3>
            <p>Add query parameters to customize title, logo, and theme:</p>
            <div class="code-example">
              <code>/?gameId=abc123&amp;title=School%20Cricket%202025&amp;logo=https://school.edu/logo.png&amp;theme=dark</code>
            </div>

            <h3>Share Link</h3>
            <p>Use the <strong>Share link</strong> button in the viewer header to generate a shareable URL with all customizations preserved.</p>
          </div>
        </section>

        <!-- Projector Mode Section -->
        <section v-show="activeTab === 'projector'" class="help-section">
          <h2>Projector Mode for TV & Large Screens</h2>
          <div class="section-content">
            <h3>What is Projector Mode?</h3>
            <p>Optimized display for large screens, TVs, and projectors. Larger fonts, more padding, and minimal clutter.</p>

            <h3>Using Presets</h3>
            <p>Add a <code>preset</code> parameter to apply pre-tuned settings:</p>
            
            <div class="preset-group">
              <h4>preset=tv1080</h4>
              <p>For 1920×1080 TVs. Scale: 1.15, spacious padding, all sections visible.</p>
              <div class="code-example">
                <code>/?preset=tv1080</code>
              </div>
            </div>

            <div class="preset-group">
              <h4>preset=proj720</h4>
              <p>For 1280×720 projectors. Scale: 1.3, compact padding, hides win probability.</p>
              <div class="code-example">
                <code>/?preset=proj720</code>
              </div>
            </div>

            <div class="preset-group">
              <h4>preset=overlay</h4>
              <p>For OBS overlays. Minimal style, shows only current bowler, compact.</p>
              <div class="code-example">
                <code>/?preset=overlay</code>
              </div>
            </div>

            <h3>Fine-Tune with Individual Params</h3>
            <p>For custom setups, use these parameters:</p>
            <ul>
              <li><code>layout=projector</code> – Enable projector UI mode</li>
              <li><code>scale=1.5</code> – Scale factor (1, 1.1, 1.25, 1.5)</li>
              <li><code>density=spacious</code> – Padding/font: compact, normal, spacious</li>
              <li><code>safeArea=on</code> – Add extra padding for TV edge cropping</li>
              <li><code>show=bowler,lastballs</code> – Show only specific sections</li>
              <li><code>hide=winprob</code> – Hide specific sections</li>
            </ul>

            <h3>Example Custom URL</h3>
            <div class="code-example">
              <code>/?scale=1.2&amp;density=compact&amp;safeArea=on&amp;hide=winprob</code>
            </div>

            <h3>Fullscreen Tip</h3>
            <p>Press <strong>F11</strong> (or Cmd+Control+F on Mac) to enter fullscreen for the cleanest presentation.</p>
          </div>
        </section>

        <!-- OBS & Streaming Section -->
        <section v-show="activeTab === 'obs'" class="help-section">
          <h2>OBS / Streaming Setup</h2>
          <div class="section-content">
            <h3>Add to OBS</h3>
            <ol>
              <li>In OBS, add a <strong>Browser Source</strong></li>
              <li>Copy the embed URL (use the projector preset overlay)</li>
              <li>Set width to your canvas width (e.g., 1920)</li>
              <li>Set height to ~200px (adjust as needed)</li>
              <li><strong>Enable transparency</strong> in source properties if you want rounded corners</li>
            </ol>

            <h3>Embed URL Example</h3>
            <p>Use the <strong>/embed/:gameId</strong> route for minimal styling:</p>
            <div class="code-example">
              <code>https://cricksy.app/#/embed/&lt;game-id&gt;?preset=overlay</code>
            </div>

            <h3>Sizing Guide</h3>
            <ul>
              <li><strong>Canvas 1920×1080:</strong> Scoreboard width 100%, height 220px</li>
              <li><strong>Canvas 1280×720:</strong> Scoreboard width 100%, height 160px</li>
              <li><strong>Smaller canvas:</strong> Adjust height proportionally (height = width ÷ 7)</li>
            </ul>

            <h3>Refresh Rate</h3>
            <p>Live score updates come via WebSocket (typically &lt;1s latency). If WebSocket fails, it falls back to polling every 5 seconds.</p>

            <h3>Tips</h3>
            <ul>
              <li>Use a dark theme for better visibility on bright projectors</li>
              <li>Position the scoreboard at the bottom of your canvas for standard sports broadcast layout</li>
              <li>Test on the actual projector/TV before the match</li>
            </ul>
          </div>
        </section>

        <!-- Roles Section -->
        <section v-show="activeTab === 'roles'" class="help-section">
          <h2>User Roles & Permissions</h2>
          <div class="section-content">
            <div class="role-group">
              <h3>📋 Scorer</h3>
              <p>Records every ball, wicket, and extra. Full match control. Only scorers can record deliveries.</p>
            </div>

            <div class="role-group">
              <h3>🎤 Commentary</h3>
              <p>Adds live commentary without affecting the score. Great for broadcast narration.</p>
            </div>

            <div class="role-group">
              <h3>📊 Analyst</h3>
              <p>Views match data and generates AI insights. Read-only access; cannot score.</p>
            </div>

            <div class="role-group">
              <h3>👁️ Viewer</h3>
              <p>Watches live score updates in real-time. Public link; anyone can access. No authentication required.</p>
            </div>

            <div class="role-group">
              <h3>🏆 Coach / Organization Admin</h3>
              <p>Manages teams, players, and multiple matches. Access to analytics and reports.</p>
            </div>
          </div>
        </section>

        <!-- FAQ Section -->
        <section v-show="activeTab === 'faq'" class="help-section">
          <h2>Frequently Asked Questions</h2>
          <div class="section-content">
            <div class="faq-item">
              <h3>Can I access the viewer on mobile?</h3>
              <p>Yes! The viewer is responsive and works on phones, tablets, and desktops. Scoring works best on larger screens.</p>
            </div>

            <div class="faq-item">
              <h3>How do I share the scoreboard?</h3>
              <p>Click <strong>Share link</strong> in the viewer header. Copy the URL and share via WhatsApp, email, or social media.</p>
            </div>

            <div class="faq-item">
              <h3>Does the projector mode work offline?</h3>
              <p>No; projector mode is live view only. Scorers must have an internet connection to record deliveries.</p>
            </div>

            <div class="faq-item">
              <h3>Can I embed the scoreboard on my website?</h3>
              <p>Yes! Use the <code>/embed/:gameId</code> route and add the iframe to your HTML. See the OBS section for sizing guidance.</p>
            </div>

            <div class="faq-item">
              <h3>What's the latency of live updates?</h3>
              <p>Typically &lt;1 second via WebSocket. If there's a connection issue, updates fall back to polling (5 second intervals).</p>
            </div>

            <div class="faq-item">
              <h3>Can I customize colors or branding?</h3>
              <p>Currently, theme is limited to dark/light. Custom branding (logo, title) is supported via query params.</p>
            </div>

            <div class="faq-item">
              <h3>How do I revert a mistake?</h3>
              <p>Click <strong>Undo Last Ball</strong> to revert the last delivery completely. You can only undo one ball at a time.</p>
            </div>
          </div>
        </section>
      </div>

      <!-- Footer -->
      <footer class="help-footer">
        <p>Need more help? Check the <RouterLink to="/">home page</RouterLink> or contact support.</p>
      </footer>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const tabs = [
  'scoring',
  'viewer',
  'projector',
  'obs',
  'roles',
  'faq',
]

const activeTab = ref('scoring')

function formatTabName(tab: string): string {
  const names: Record<string, string> = {
    scoring: '📋 Scoring',
    viewer: '👁️ Viewer',
    projector: '📺 Projector',
    obs: '🎬 OBS',
    roles: '👥 Roles',
    faq: '❓ FAQ',
  }
  return names[tab] || tab
}
</script>

<style scoped>
.help-view {
  min-height: 100dvh;
  background: linear-gradient(180deg, var(--color-bg) 0%, var(--color-surface) 100%);
  padding: var(--space-6);
}

.help-container {
  max-width: 1000px;
  margin: 0 auto;
}

.help-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.help-header h1 {
  font-size: var(--h1-size);
  font-weight: var(--font-extrabold);
  margin: 0 0 var(--space-2) 0;
  letter-spacing: -0.02em;
}

.help-header p {
  font-size: var(--text-lg);
  color: var(--color-text-muted);
  margin: 0;
}

.help-nav {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.nav-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: var(--font-semibold);
  transition: all 200ms ease;
}

.nav-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.nav-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.help-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.help-section {
  animation: fadeIn 200ms ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.help-section h2 {
  font-size: var(--h2-size);
  font-weight: var(--font-bold);
  margin: 0 0 var(--space-4) 0;
  color: var(--color-primary);
}

.section-content {
  display: grid;
  gap: var(--space-4);
}

.help-section h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: var(--space-3) 0 var(--space-2) 0;
  color: var(--color-text);
}

.help-section p {
  margin: 0 0 var(--space-2) 0;
  line-height: 1.6;
  color: var(--color-text);
}

.help-section ul {
  margin: 0;
  padding-left: var(--space-4);
}

.help-section li {
  margin: var(--space-1) 0;
  line-height: 1.6;
}

.code-example {
  background: var(--color-bg);
  border-left: 3px solid var(--color-primary);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: var(--space-2) 0;
}

.code-example code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  word-break: break-all;
}

.preset-group {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  margin: var(--space-3) 0;
}

.preset-group h4 {
  margin: 0 0 var(--space-2) 0;
  color: var(--color-primary);
  font-weight: var(--font-semibold);
}

.preset-group p {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
}

.role-group {
  background: var(--color-bg);
  border-left: 3px solid var(--color-secondary);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  margin: var(--space-3) 0;
}

.role-group h3 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
}

.role-group p {
  margin: 0;
  font-size: var(--text-sm);
}

.faq-item {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-4);
}

.faq-item:last-child {
  border-bottom: none;
}

.faq-item h3 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  color: var(--color-primary);
}

.faq-item p {
  margin: 0;
}

.help-footer {
  text-align: center;
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.help-footer p {
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .help-view {
    padding: var(--space-4);
  }

  .help-container {
    max-width: 100%;
  }

  .help-header {
    margin-bottom: var(--space-6);
  }

  .help-header h1 {
    font-size: var(--h2-size);
  }

  .help-header p {
    font-size: var(--text-base);
  }

  .help-nav {
    gap: var(--space-1);
  }

  .nav-btn {
    padding: var(--space-1) var(--space-2);
    font-size: var(--text-sm);
  }

  .help-content {
    padding: var(--space-4);
  }

  .code-example {
    padding: var(--space-2);
    font-size: var(--text-xs);
  }
}
</style>
