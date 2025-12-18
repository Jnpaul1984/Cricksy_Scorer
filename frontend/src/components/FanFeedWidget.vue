<template>
  <div class="fan-feed">
    <div class="feed-header">
      <h2 class="feed-title">🔥 Fan Feed</h2>
      <p class="feed-subtitle">Latest updates from followed teams and players</p>
    </div>

    <!-- Feed Controls -->
    <div class="feed-controls">
      <div class="filter-group">
        <label class="filter-label">Filter</label>
        <select v-model="filterType" class="filter-select">
          <option value="all">All Updates</option>
          <option value="matches">Matches Only</option>
          <option value="highlights">Highlights</option>
          <option value="news">News</option>
        </select>
      </div>
      <div class="sort-group">
        <label class="sort-label">Sort</label>
        <select v-model="sortOrder" class="sort-select">
          <option value="recent">Most Recent</option>
          <option value="trending">Trending</option>
          <option value="following">Following</option>
        </select>
      </div>
    </div>

    <!-- Feed Items -->
    <div class="feed-container">
      <div v-if="filteredFeedItems.length === 0" class="empty-state">
        <p class="empty-icon">🏏</p>
        <p class="empty-message">No updates yet</p>
        <p class="empty-hint">Follow teams and players to see their updates here</p>
      </div>

      <div v-for="(item, idx) in paginatedItems" :key="item.id" class="feed-item">
        <!-- Match Card -->
        <div v-if="item.type === 'match'" class="match-card">
          <div class="card-header">
            <div class="entity-info">
              <img :src="item.team1?.logo || ''" :alt="item.team1?.name" class="team-logo" />
              <div class="entity-meta">
                <p class="entity-name">{{ item.team1?.name }} vs {{ item.team2?.name }}</p>
                <p class="entity-date">{{ formatDate(item.timestamp) }}</p>
              </div>
            </div>
            <div class="match-status" :class="`status-${item.status}`">
              {{ item.status }}
            </div>
          </div>

          <div class="card-body">
            <!-- Score Display -->
            <div class="score-section">
              <div class="team-score">
                <p class="team-name">{{ item.team1?.name }}</p>
                <p class="team-runs">{{ item.team1Runs }}/{{ item.team1Wickets }}</p>
                <p class="team-overs">{{ item.team1Overs }} ov</p>
              </div>
              <div class="vs-divider">vs</div>
              <div class="team-score">
                <p class="team-name">{{ item.team2?.name }}</p>
                <p class="team-runs">{{ item.team2Runs }}/{{ item.team2Wickets }}</p>
                <p class="team-overs">{{ item.team2Overs }} ov</p>
              </div>
            </div>

            <!-- Match Details -->
            <div class="match-details">
              <span class="detail">📍 {{ item.venue }}</span>
              <span class="detail">🎯 {{ item.format }}</span>
            </div>

            <!-- Highlights -->
            <div v-if="item.highlights && item.highlights.length > 0" class="highlights">
              <p class="highlights-title">⭐ Highlights</p>
              <ul class="highlights-list">
                <li v-for="(highlight, hidx) in item.highlights.slice(0, 3)" :key="hidx" class="highlight-item">
                  {{ highlight }}
                </li>
              </ul>
            </div>

            <!-- Engagement -->
            <div class="engagement-section">
              <div class="engagement-stat">
                <span class="engagement-icon">❤️</span>
                <span class="engagement-count">{{ item.reactions?.likes || 0 }}</span>
              </div>
              <div class="engagement-stat">
                <span class="engagement-icon">💬</span>
                <span class="engagement-count">{{ item.reactions?.comments || 0 }}</span>
              </div>
              <div class="engagement-stat">
                <span class="engagement-icon">🔄</span>
                <span class="engagement-count">{{ item.reactions?.shares || 0 }}</span>
              </div>
              <div class="engagement-stat">
                <span class="engagement-icon">📊</span>
                <span class="engagement-count">{{ item.reactions?.views || 0 }}</span>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <BaseButton variant="ghost" size="sm" @click="viewMatchDetails(item)">
              View Full Match →
            </BaseButton>
          </div>
        </div>

        <!-- Highlight Card -->
        <div v-else-if="item.type === 'highlight'" class="highlight-card">
          <div class="card-header">
            <div class="entity-info">
              <p class="entity-name">⚡ {{ item.title }}</p>
              <p class="entity-date">{{ formatDate(item.timestamp) }}</p>
            </div>
          </div>
          <div class="card-body">
            <p class="highlight-description">{{ item.description }}</p>
            <div class="highlight-video-placeholder">
              <p>🎬 Video: {{ item.duration }}</p>
            </div>
          </div>
          <div class="card-footer">
            <BaseButton variant="ghost" size="sm">
              Watch Highlight →
            </BaseButton>
          </div>
        </div>

        <!-- News Card -->
        <div v-else-if="item.type === 'news'" class="news-card">
          <div class="card-header">
            <div class="entity-info">
              <p class="entity-name">📰 {{ item.title }}</p>
              <p class="entity-date">{{ formatDate(item.timestamp) }}</p>
            </div>
            <div class="news-source">{{ item.source }}</div>
          </div>
          <div class="card-body">
            <p class="news-snippet">{{ item.snippet }}</p>
          </div>
          <div class="card-footer">
            <BaseButton variant="ghost" size="sm">
              Read More →
            </BaseButton>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <BaseButton
          variant="ghost"
          size="sm"
          :disabled="currentPage === 1"
          @click="currentPage--"
        >
          ← Previous
        </BaseButton>
        <span class="page-info">
          Page {{ currentPage }} of {{ totalPages }}
        </span>
        <BaseButton
          variant="ghost"
          size="sm"
          :disabled="currentPage === totalPages"
          @click="currentPage++"
        >
          Next →
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed } from 'vue'
import { BaseButton } from '@/components'

interface FeedItem {
  id: string
  type: 'match' | 'highlight' | 'news'
  timestamp: string
  // Match fields
  team1?: { name: string; logo: string }
  team2?: { name: string; logo: string }
  team1Runs?: number
  team1Wickets?: number
  team1Overs?: string
  team2Runs?: number
  team2Wickets?: number
  team2Overs?: string
  status?: 'live' | 'completed' | 'upcoming'
  venue?: string
  format?: string
  highlights?: string[]
  // Highlight fields
  title?: string
  description?: string
  duration?: string
  // News fields
  snippet?: string
  source?: string
  // Common
  reactions?: {
    likes: number
    comments: number
    shares: number
    views: number
  }
}

const props = defineProps<{
  items?: FeedItem[]
}>()

const filterType = ref<'all' | 'matches' | 'highlights' | 'news'>('all')
const sortOrder = ref<'recent' | 'trending' | 'following'>('recent')
const currentPage = ref(1)
const itemsPerPage = 5

// Generate mock feed data
function generateMockFeed(): FeedItem[] {
  return [
    {
      id: 'm1',
      type: 'match',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      team1: { name: 'India', logo: '🇮🇳' },
      team2: { name: 'Australia', logo: '🇦🇺' },
      team1Runs: 178,
      team1Wickets: 6,
      team1Overs: '20',
      team2Runs: 165,
      team2Wickets: 8,
      team2Overs: '19.3',
      status: 'completed',
      venue: 'MCG, Melbourne',
      format: 'T20',
      highlights: ['Virat Kohli 67(48)', 'Maxwell 45(22)', 'Great bowling by Bumrah'],
      reactions: { likes: 2450, comments: 340, shares: 890, views: 15600 },
    },
    {
      id: 'h1',
      type: 'highlight',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      title: 'Best Catch of the Tournament',
      description: 'Stunning fielding effort by Virat Kohli near the boundary',
      duration: '0:32',
      reactions: { likes: 1820, comments: 156, shares: 420, views: 8900 },
    },
    {
      id: 'n1',
      type: 'news',
      timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      title: 'India wins by 13 runs, Bumrah named Player of Match',
      snippet:
        'Jasprit Bumrah took 3 crucial wickets in the final overs, helping India secure a commanding victory...',
      source: 'Cricket Express',
      reactions: { likes: 3200, comments: 512, shares: 1200, views: 22000 },
    },
    {
      id: 'm2',
      type: 'match',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      team1: { name: 'England', logo: '🏴󐁧󐁢󐁥󐁮󐁧󐁿' },
      team2: { name: 'Pakistan', logo: '🇵🇰' },
      team1Runs: 156,
      team1Wickets: 5,
      team1Overs: '20',
      team2Runs: 148,
      team2Wickets: 9,
      team2Overs: '20',
      status: 'completed',
      venue: 'The Oval, London',
      format: 'T20',
      highlights: ['Root 52(38)', 'Babar 45(35)', 'England defense strong'],
      reactions: { likes: 1650, comments: 220, shares: 580, views: 9200 },
    },
    {
      id: 'h2',
      type: 'highlight',
      timestamp: new Date(Date.now() - 30 * 60 * 60 * 1000).toISOString(),
      title: 'Six-hitting masterclass by Rohit Sharma',
      description: '5 consecutive sixes in an over - record-breaking performance',
      duration: '1:15',
      reactions: { likes: 4100, comments: 680, shares: 1900, views: 32000 },
    },
    {
      id: 'n2',
      type: 'news',
      timestamp: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
      title: 'Squad announced for World Cup - 5 new faces',
      snippet:
        'The selection committee has named a fresh squad with exciting new talent for the upcoming World Cup...',
      source: 'Sports Today',
      reactions: { likes: 2800, comments: 456, shares: 950, views: 18500 },
    },
    {
      id: 'm3',
      type: 'match',
      timestamp: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      team1: { name: 'South Africa', logo: '🇿🇦' },
      team2: { name: 'Sri Lanka', logo: '🇱🇰' },
      status: 'upcoming',
      venue: 'Cape Town Stadium',
      format: 'T20',
      reactions: { likes: 890, comments: 145, shares: 320, views: 5600 },
    },
  ]
}

const feedItems = computed(() => {
  return props.items || generateMockFeed()
})

const filteredFeedItems = computed(() => {
  let result = feedItems.value

  // Filter by type
  if (filterType.value !== 'all') {
    if (filterType.value === 'matches') {
      result = result.filter((i) => i.type === 'match')
    } else if (filterType.value === 'highlights') {
      result = result.filter((i) => i.type === 'highlight')
    } else if (filterType.value === 'news') {
      result = result.filter((i) => i.type === 'news')
    }
  }

  // Sort
  if (sortOrder.value === 'recent') {
    result.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  } else if (sortOrder.value === 'trending') {
    result.sort((a, b) => (b.reactions?.likes || 0) - (a.reactions?.likes || 0))
  }

  return result
})

const totalPages = computed(() => Math.ceil(filteredFeedItems.value.length / itemsPerPage))

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredFeedItems.value.slice(start, end)
})

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (hours < 1) return 'just now'
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function viewMatchDetails(item: FeedItem) {
  console.log('View match:', item)
  // In real app, navigate to match details view
}
</script>

<style scoped>
.fan-feed {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Header */
.feed-header {
  margin-bottom: var(--space-2);
}

.feed-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.feed-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Controls */
.feed-controls {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.filter-group,
.sort-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-label,
.sort-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.filter-select,
.sort-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  cursor: pointer;
}

.filter-select:focus,
.sort-select:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Container */
.feed-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.empty-state {
  text-align: center;
  padding: var(--space-8) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
}

.empty-icon {
  font-size: 3rem;
  margin: 0;
}

.empty-message {
  margin: var(--space-3) 0 var(--space-2) 0;
  font-size: var(--text-base);
  color: var(--color-text);
  font-weight: 500;
}

.empty-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Feed Items */
.feed-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
  overflow: hidden;
  transition: all 0.3s ease;
}

.feed-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

/* Match Card */
.match-card,
.highlight-card,
.news-card {
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.entity-info {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex: 1;
}

.team-logo {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary);
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.entity-meta {
  min-width: 0;
}

.entity-name {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.entity-date {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.match-status {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.status-live {
  background: #fee2e2;
  color: #991b1b;
}

.status-completed {
  background: #dcfce7;
  color: #166534;
}

.status-upcoming {
  background: #fef3c7;
  color: #92400e;
}

.news-source {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

/* Card Body */
.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  flex: 1;
}

/* Score Section */
.score-section {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.team-score {
  text-align: center;
  flex: 1;
}

.team-name {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.team-runs {
  margin: var(--space-1) 0;
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

.team-overs {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.vs-divider {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  margin: 0 var(--space-3);
}

/* Match Details */
.match-details {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.detail {
  display: inline-flex;
  gap: var(--space-1);
}

/* Highlights */
.highlights {
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.highlights-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.highlights-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.highlight-item {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
}

/* Engagement */
.engagement-section {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.engagement-stat {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.engagement-icon {
  font-size: var(--text-base);
}

.engagement-count {
  font-weight: 600;
  color: var(--color-text);
}

/* News Specific */
.highlight-description {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.5;
}

.highlight-video-placeholder {
  padding: var(--space-4);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-md);
  color: white;
  text-align: center;
  font-weight: 600;
  margin: var(--space-2) 0;
}

.news-snippet {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.6;
}

/* Card Footer */
.card-footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  text-align: right;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.page-info {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

/* Responsive */
@media (max-width: 768px) {
  .feed-controls {
    flex-direction: column;
  }

  .score-section {
    flex-direction: column;
    gap: var(--space-3);
  }

  .engagement-section {
    justify-content: space-around;
  }

  .card-footer {
    text-align: center;
  }

  .pagination {
    flex-direction: column;
  }
}
</style>
