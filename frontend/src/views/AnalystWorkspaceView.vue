<script setup lang="ts">
/**
 * AnalystWorkspaceView.vue
 * Analyst-focused workspace for match analysis, team performance, and data exports.
 * Layout-only V1 – data fetching to be wired in future sprints.
 */

// TODO: Wire real data in Week X
// - Fetch matches from matches API
// - Fetch team performance metrics from analytics service
// - Implement custom query builder and export functionality
</script>

<template>
  <div class="analyst-workspace">
    <header class="page-header">
      <h1 class="page-title">Analyst Workspace</h1>
      <p class="page-subtitle">Deep dive into match data, team performance, and generate custom reports.</p>
    </header>

    <div class="workspace-layout">
      <!-- Left Panel: Matches List -->
      <aside class="matches-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="panel-icon">🏏</span>
            Matches
          </h2>
          <input
            type="search"
            class="search-input"
            placeholder="Search matches..."
          />
        </div>
        <div class="panel-content">
          <!-- TODO: Wire real data in Week X -->
          <ul class="match-list">
            <li class="match-item active placeholder">
              <div class="match-teams">Team A vs Team B</div>
              <div class="match-meta">
                <span class="match-date">Nov 25, 2025</span>
                <span class="match-status status-completed">Completed</span>
              </div>
            </li>
            <li class="match-item placeholder">
              <div class="match-teams">City XI vs County CC</div>
              <div class="match-meta">
                <span class="match-date">Nov 22, 2025</span>
                <span class="match-status status-completed">Completed</span>
              </div>
            </li>
            <li class="match-item placeholder">
              <div class="match-teams">Lions vs Tigers</div>
              <div class="match-meta">
                <span class="match-date">Nov 18, 2025</span>
                <span class="match-status status-completed">Completed</span>
              </div>
            </li>
            <li class="match-item placeholder">
              <div class="match-teams">Eagles vs Hawks</div>
              <div class="match-meta">
                <span class="match-date">Nov 15, 2025</span>
                <span class="match-status status-completed">Completed</span>
              </div>
            </li>
            <li class="match-item placeholder">
              <div class="match-teams">Rangers vs Strikers</div>
              <div class="match-meta">
                <span class="match-date">Nov 10, 2025</span>
                <span class="match-status status-completed">Completed</span>
              </div>
            </li>
          </ul>
          <p class="placeholder-note">
            <!-- TODO: Wire real data in Week X -->
            Placeholder data – connect to matches API
          </p>
        </div>
      </aside>

      <!-- Main Content Area -->
      <main class="main-content">
        <!-- Team Performance Overview -->
        <section class="content-section">
          <div class="section-header">
            <h2 class="section-title">
              <span class="section-icon">📊</span>
              Team Performance Overview
            </h2>
            <div class="section-actions">
              <select class="select-input">
                <option>Last 5 Matches</option>
                <option>Last 10 Matches</option>
                <option>This Season</option>
                <option>All Time</option>
              </select>
            </div>
          </div>
          <div class="section-content">
            <!-- TODO: Wire real data in Week X -->
            <div class="performance-grid">
              <div class="performance-card placeholder">
                <div class="perf-chart-placeholder">
                  <span class="chart-icon">📈</span>
                  <span class="chart-label">Run Rate Trend</span>
                </div>
                <div class="perf-summary">
                  <span class="perf-value">7.2</span>
                  <span class="perf-label">Avg Run Rate</span>
                </div>
              </div>
              <div class="performance-card placeholder">
                <div class="perf-chart-placeholder">
                  <span class="chart-icon">🎯</span>
                  <span class="chart-label">Wickets by Type</span>
                </div>
                <div class="perf-summary">
                  <span class="perf-value">18</span>
                  <span class="perf-label">Total Wickets</span>
                </div>
              </div>
              <div class="performance-card placeholder">
                <div class="perf-chart-placeholder">
                  <span class="chart-icon">🏆</span>
                  <span class="chart-label">Win/Loss Ratio</span>
                </div>
                <div class="perf-summary">
                  <span class="perf-value">3-2</span>
                  <span class="perf-label">W/L Record</span>
                </div>
              </div>
              <div class="performance-card placeholder">
                <div class="perf-chart-placeholder">
                  <span class="chart-icon">⚡</span>
                  <span class="chart-label">Powerplay Performance</span>
                </div>
                <div class="perf-summary">
                  <span class="perf-value">52</span>
                  <span class="perf-label">Avg PP Score</span>
                </div>
              </div>
            </div>
            <p class="placeholder-note">
              <!-- TODO: Wire real data in Week X -->
              Placeholder charts – connect to analytics API and integrate Chart.js/D3
            </p>
          </div>
        </section>

        <!-- Custom Queries / Exports -->
        <section class="content-section">
          <div class="section-header">
            <h2 class="section-title">
              <span class="section-icon">🔍</span>
              Custom Queries & Exports
            </h2>
          </div>
          <div class="section-content">
            <!-- TODO: Wire real data in Week X -->
            <div class="query-builder placeholder">
              <div class="query-row">
                <label class="query-label">Metric:</label>
                <select class="select-input">
                  <option>Batting Average</option>
                  <option>Strike Rate</option>
                  <option>Economy Rate</option>
                  <option>Wickets Taken</option>
                </select>
              </div>
              <div class="query-row">
                <label class="query-label">Group By:</label>
                <select class="select-input">
                  <option>Player</option>
                  <option>Team</option>
                  <option>Match</option>
                  <option>Phase</option>
                </select>
              </div>
              <div class="query-row">
                <label class="query-label">Date Range:</label>
                <input type="date" class="date-input" />
                <span class="query-separator">to</span>
                <input type="date" class="date-input" />
              </div>
              <div class="query-actions">
                <button class="btn btn-primary">Run Query</button>
                <button class="btn btn-secondary">Export CSV</button>
                <button class="btn btn-secondary">Export PDF</button>
              </div>
            </div>

            <div class="query-results placeholder">
              <div class="results-header">
                <span class="results-title">Query Results</span>
                <span class="results-count">0 rows</span>
              </div>
              <div class="results-table-placeholder">
                <p class="no-results">Run a query to see results here</p>
              </div>
            </div>
            <p class="placeholder-note">
              <!-- TODO: Wire real data in Week X -->
              Placeholder UI – implement query builder and export functionality
            </p>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.analyst-workspace {
  padding: var(--space-5) var(--space-4);
  max-width: 1400px;
  margin: 0 auto;
  color: var(--color-text);
}

/* Page Header */
.page-header {
  margin-bottom: var(--space-5);
}

.page-title {
  font-family: var(--font-heading);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  margin: 0 0 var(--space-2);
}

.page-subtitle {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* Workspace Layout */
.workspace-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: var(--space-5);
}

/* Matches Panel (Sidebar) */
.matches-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  height: fit-content;
  position: sticky;
  top: var(--space-4);
}

.panel-header {
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-heading);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-3);
  color: var(--color-text);
}

.panel-icon {
  font-size: 1.25rem;
}

.search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.panel-content {
  padding: var(--space-3);
  max-height: 500px;
  overflow-y: auto;
}

/* Match List */
.match-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.match-item {
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.match-item:hover {
  border-color: var(--color-primary);
}

.match-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.match-teams {
  font-weight: var(--font-medium);
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.match-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-xs);
}

.match-date {
  color: var(--color-text-muted);
}

.match-status {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: var(--font-semibold);
}

.status-completed {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.status-live {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.status-upcoming {
  background: var(--color-info-soft);
  color: var(--color-info);
}

/* Main Content */
.main-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* Content Section */
.content-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-heading);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0;
  color: var(--color-text);
}

.section-icon {
  font-size: 1.25rem;
}

.section-actions {
  display: flex;
  gap: var(--space-2);
}

.section-content {
  padding: var(--space-4);
}

/* Select Input */
.select-input {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  cursor: pointer;
}

.select-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Performance Grid */
.performance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}

.performance-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  text-align: center;
}

.perf-chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100px;
  background: var(--color-surface);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
}

.chart-icon {
  font-size: 2rem;
  margin-bottom: var(--space-1);
}

.chart-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.perf-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.perf-value {
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
}

.perf-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Query Builder */
.query-builder {
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.query-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}

.query-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
  min-width: 80px;
}

.query-separator {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.date-input {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
}

.date-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.query-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

/* Buttons */
.btn {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-primary {
  background: var(--color-primary);
  color: #0f172a;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-secondary {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border-strong);
}

.btn-secondary:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary);
}

/* Query Results */
.query-results {
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-subtle);
}

.results-title {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.results-count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.results-table-placeholder {
  padding: var(--space-8);
  text-align: center;
}

.no-results {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

/* Placeholder Note */
.placeholder-note {
  margin: var(--space-4) 0 0;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  text-align: center;
  font-style: italic;
}

/* Responsive */
@media (max-width: 900px) {
  .workspace-layout {
    grid-template-columns: 1fr;
  }

  .matches-panel {
    position: static;
    max-height: none;
  }

  .panel-content {
    max-height: 300px;
  }
}

@media (max-width: 640px) {
  .analyst-workspace {
    padding: var(--space-4) var(--space-3);
  }

  .page-title {
    font-size: var(--text-2xl);
  }

  .performance-grid {
    grid-template-columns: 1fr;
  }

  .query-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .query-label {
    min-width: auto;
  }

  .query-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
