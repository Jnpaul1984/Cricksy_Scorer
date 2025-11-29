<script setup lang="ts">
/**
 * CoachesDashboardView.vue
 * Coach-focused dashboard for managing players, sessions, and form alerts.
 * Layout-only V1 – data fetching to be wired in future sprints.
 */

// TODO: Wire real data in Week X
// - Fetch players from API
// - Fetch upcoming sessions from calendar/schedule service
// - Fetch form alerts from analytics service
</script>

<template>
  <div class="coach-dashboard">
    <header class="page-header">
      <h1 class="page-title">Coach Dashboard</h1>
      <p class="page-subtitle">Manage your players, sessions, and track performance trends.</p>
    </header>

    <div class="dashboard-grid">
      <!-- My Players Section -->
      <section class="dashboard-card players-section">
        <div class="card-header">
          <h2 class="card-title">
            <span class="card-icon">👥</span>
            My Players
          </h2>
          <button class="card-action-btn">+ Add Player</button>
        </div>
        <div class="card-content">
          <!-- TODO: Wire real data in Week X -->
          <ul class="player-list">
            <li class="player-item placeholder">
              <div class="player-avatar">JS</div>
              <div class="player-info">
                <span class="player-name">John Smith</span>
                <span class="player-role">All-rounder</span>
              </div>
              <span class="player-form form-good">↑ Good</span>
            </li>
            <li class="player-item placeholder">
              <div class="player-avatar">AK</div>
              <div class="player-info">
                <span class="player-name">Arun Kumar</span>
                <span class="player-role">Batsman</span>
              </div>
              <span class="player-form form-neutral">→ Steady</span>
            </li>
            <li class="player-item placeholder">
              <div class="player-avatar">MB</div>
              <div class="player-info">
                <span class="player-name">Mike Brown</span>
                <span class="player-role">Bowler</span>
              </div>
              <span class="player-form form-warning">↓ Needs Work</span>
            </li>
          </ul>
          <p class="placeholder-note">
            <!-- TODO: Wire real data in Week X -->
            Placeholder data – connect to player API
          </p>
        </div>
      </section>

      <!-- Upcoming Sessions Section -->
      <section class="dashboard-card sessions-section">
        <div class="card-header">
          <h2 class="card-title">
            <span class="card-icon">📅</span>
            Upcoming Sessions
          </h2>
          <button class="card-action-btn">Schedule</button>
        </div>
        <div class="card-content">
          <!-- TODO: Wire real data in Week X -->
          <ul class="session-list">
            <li class="session-item placeholder">
              <div class="session-date">
                <span class="date-day">28</span>
                <span class="date-month">Nov</span>
              </div>
              <div class="session-info">
                <span class="session-title">Team Practice</span>
                <span class="session-time">10:00 AM – 12:00 PM</span>
              </div>
            </li>
            <li class="session-item placeholder">
              <div class="session-date">
                <span class="date-day">30</span>
                <span class="date-month">Nov</span>
              </div>
              <div class="session-info">
                <span class="session-title">Batting Drills</span>
                <span class="session-time">2:00 PM – 4:00 PM</span>
              </div>
            </li>
            <li class="session-item placeholder">
              <div class="session-date">
                <span class="date-day">02</span>
                <span class="date-month">Dec</span>
              </div>
              <div class="session-info">
                <span class="session-title">Match vs. City XI</span>
                <span class="session-time">9:00 AM</span>
              </div>
            </li>
          </ul>
          <p class="placeholder-note">
            <!-- TODO: Wire real data in Week X -->
            Placeholder data – connect to calendar/schedule API
          </p>
        </div>
      </section>

      <!-- Recent Form Alerts Section -->
      <section class="dashboard-card alerts-section">
        <div class="card-header">
          <h2 class="card-title">
            <span class="card-icon">⚠️</span>
            Recent Form Alerts
          </h2>
          <button class="card-action-btn">View All</button>
        </div>
        <div class="card-content">
          <!-- TODO: Wire real data in Week X -->
          <ul class="alert-list">
            <li class="alert-item alert-warning placeholder">
              <span class="alert-icon">📉</span>
              <div class="alert-info">
                <span class="alert-title">Mike Brown – Bowling Economy Up</span>
                <span class="alert-desc">Economy rate increased 15% over last 3 matches</span>
              </div>
            </li>
            <li class="alert-item alert-success placeholder">
              <span class="alert-icon">🔥</span>
              <div class="alert-info">
                <span class="alert-title">Arun Kumar – Hot Streak</span>
                <span class="alert-desc">3 consecutive 50+ scores</span>
              </div>
            </li>
            <li class="alert-item alert-info placeholder">
              <span class="alert-icon">💡</span>
              <div class="alert-info">
                <span class="alert-title">John Smith – Milestone Approaching</span>
                <span class="alert-desc">12 runs away from 1000 career runs</span>
              </div>
            </li>
          </ul>
          <p class="placeholder-note">
            <!-- TODO: Wire real data in Week X -->
            Placeholder data – connect to analytics/alerts API
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.coach-dashboard {
  padding: var(--space-5) var(--space-4);
  max-width: 1200px;
  margin: 0 auto;
  color: var(--color-text);
}

/* Page Header */
.page-header {
  margin-bottom: var(--space-6);
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

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-5);
}

/* Dashboard Card */
.dashboard-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-heading);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0;
  color: var(--color-text);
}

.card-icon {
  font-size: 1.25rem;
}

.card-action-btn {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-action-btn:hover {
  background: var(--color-primary);
  color: #0f172a;
}

.card-content {
  padding: var(--space-4);
}

/* Player List */
.player-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.player-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.player-item:last-child {
  border-bottom: none;
}

.player-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  border-radius: var(--radius-pill);
}

.player-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.player-name {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.player-role {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.player-form {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.form-good {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.form-neutral {
  background: var(--color-info-soft);
  color: var(--color-info);
}

.form-warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

/* Session List */
.session-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.session-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.session-item:last-child {
  border-bottom: none;
}

.session-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--color-primary);
  color: #0f172a;
  border-radius: var(--radius-md);
}

.date-day {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  line-height: 1;
}

.date-month {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
}

.session-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.session-title {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.session-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Alert List */
.alert-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  border-radius: var(--radius-md);
}

.alert-item:last-child {
  margin-bottom: 0;
}

.alert-warning {
  background: var(--color-warning-soft);
}

.alert-success {
  background: var(--color-success-soft);
}

.alert-info {
  background: var(--color-info-soft);
}

.alert-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.alert-info-container {
  flex: 1;
}

.alert-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.alert-title {
  font-weight: var(--font-medium);
  color: var(--color-text);
  font-size: var(--text-sm);
}

.alert-desc {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

/* Placeholder Note */
.placeholder-note {
  margin: var(--space-3) 0 0;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  text-align: center;
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .coach-dashboard {
    padding: var(--space-4) var(--space-3);
  }

  .page-title {
    font-size: var(--text-2xl);
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
