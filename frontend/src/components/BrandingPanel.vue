<template>
  <div class="branding-panel">
    <!-- Header -->
    <div class="panel-header">
      <h2>Organization Branding</h2>
      <button
        @click="refreshBranding"
        :disabled="loading"
        class="btn-refresh"
      >
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="state-loading">
      <div class="spinner"></div>
      <p>Loading branding configuration...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-error">
      <p class="error-message">{{ error }}</p>
      <button @click="clearError" class="btn-secondary">Dismiss</button>
    </div>

    <!-- Main Content -->
    <div v-else-if="brandingData" class="branding-content">
      <!-- Logo Preview -->
      <section class="section-preview">
        <h3>Logo Preview</h3>
        <div class="logo-container">
          <img
            v-if="brandingData.assets.logo_url"
            :src="brandingData.assets.logo_url"
            alt="Organization logo"
            class="org-logo"
          />
          <div v-else class="logo-placeholder">
            <span>No logo uploaded</span>
          </div>
        </div>
      </section>

      <!-- Color Palette -->
      <section class="section-colors">
        <h3>Color Palette</h3>
        <div class="color-grid">
          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.primary }"
            ></div>
            <span class="color-label">Primary</span>
            <code class="color-code">{{ brandingData.colors.primary }}</code>
          </div>

          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.secondary }"
            ></div>
            <span class="color-label">Secondary</span>
            <code class="color-code">{{ brandingData.colors.secondary }}</code>
          </div>

          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.accent }"
            ></div>
            <span class="color-label">Accent</span>
            <code class="color-code">{{ brandingData.colors.accent }}</code>
          </div>

          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.success }"
            ></div>
            <span class="color-label">Success</span>
            <code class="color-code">{{ brandingData.colors.success }}</code>
          </div>

          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.warning }"
            ></div>
            <span class="color-label">Warning</span>
            <code class="color-code">{{ brandingData.colors.warning }}</code>
          </div>

          <div class="color-item">
            <div
              class="color-swatch"
              :style="{ backgroundColor: brandingData.colors.error }"
            ></div>
            <span class="color-label">Error</span>
            <code class="color-code">{{ brandingData.colors.error }}</code>
          </div>
        </div>
      </section>

      <!-- Typography -->
      <section v-if="brandingData.typography" class="section-typography">
        <h3>Typography</h3>
        <div class="typography-grid">
          <div class="typography-item">
            <label>Primary Font:</label>
            <span class="font-value">{{ brandingData.typography.primary_font }}</span>
          </div>
          <div class="typography-item">
            <label>Heading Size:</label>
            <span class="font-value">{{ brandingData.typography.heading_size }}px</span>
          </div>
          <div class="typography-item">
            <label>Body Size:</label>
            <span class="font-value">{{ brandingData.typography.body_size }}px</span>
          </div>
          <div class="typography-item">
            <label>Line Height:</label>
            <span class="font-value">{{ brandingData.typography.line_height }}</span>
          </div>
        </div>
      </section>

      <!-- Application Scope -->
      <section class="section-scope">
        <h3>Application Scope</h3>
        <div class="scope-checkboxes">
          <label class="checkbox-label">
            <input type="checkbox" v-model="brandingData.apply_to.viewer" disabled />
            <span>Apply to Viewer</span>
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="brandingData.apply_to.scoreboard" disabled />
            <span>Apply to Scoreboard</span>
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="brandingData.apply_to.admin" disabled />
            <span>Apply to Admin</span>
          </label>
        </div>
      </section>

      <!-- Brand Assets -->
      <section v-if="Object.keys(brandingData.assets).length > 0" class="section-assets">
        <h3>Brand Assets</h3>
        <div class="assets-list">
          <div
            v-for="(asset, idx) in Object.values(brandingData.assets)"
            :key="idx"
            class="asset-item"
          >
            <span class="asset-type">{{ asset.type }}</span>
            <span class="asset-name">{{ asset.name }}</span>
            <span v-if="asset.dimensions" class="asset-dimensions">
              {{ asset.dimensions[0] }}×{{ asset.dimensions[1] }}px
            </span>
          </div>
        </div>
      </section>

      <!-- Theme Status -->
      <section class="section-status">
        <h3>Theme Status</h3>
        <div class="status-info">
          <div class="status-row">
            <span>Status:</span>
            <span :class="['status-badge', { active: brandingData.is_active }]">
              {{ brandingData.is_active ? 'Active' : 'Inactive' }}
            </span>
          </div>
          <div class="status-row">
            <span>Created:</span>
            <span class="timestamp">{{ formatDate(brandingData.created_at) }}</span>
          </div>
          <div class="status-row">
            <span>Updated:</span>
            <span class="timestamp">{{ formatDate(brandingData.updated_at) }}</span>
          </div>
        </div>
      </section>
    </div>

    <!-- No Data State -->
    <div v-else class="state-no-data">
      <p>No branding configuration found.</p>
      <p class="help-text">Create a branding theme via the API to get started.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useBranding } from '@/composables/useBranding'

interface BrandingData {
  theme_id: string
  org_id: string
  org_name: string
  colors: {
    primary: string
    secondary: string
    accent: string
    success: string
    warning: string
    error: string
    info: string
  }
  assets: Record<string, any>
  typography: {
    primary_font: string
    heading_size: number
    body_size: number
    line_height?: number
  } | null
  apply_to: {
    viewer: boolean
    scoreboard: boolean
    admin: boolean
  }
  is_active: boolean
  created_at: string
  updated_at: string
}

const props = defineProps<{
  orgId?: string
  autoRefresh?: boolean
  refreshIntervalSeconds?: number
}>()

const emit = defineEmits<{
  'branding-loaded': [data: BrandingData]
}>()

const { fetchOrgBranding } = useBranding()

const brandingData = ref<BrandingData | null>(null)
const loading = ref(false)
const error = ref('')
const autoRefreshInterval = ref<ReturnType<typeof setInterval> | null>(null)

const loadBranding = async () => {
  if (!props.orgId) {
    error.value = 'Organization ID required'
    return
  }

  try {
    loading.value = true
    error.value = ''

    const data = await fetchOrgBranding(props.orgId)
    if (data) {
      brandingData.value = data
      emit('branding-loaded', data)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load branding'
  } finally {
    loading.value = false
  }
}

const refreshBranding = async () => {
  await loadBranding()
}

const clearError = () => {
  error.value = ''
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

const startAutoRefresh = () => {
  if (!props.autoRefresh) return

  autoRefreshInterval.value = setInterval(
    () => loadBranding(),
    (props.refreshIntervalSeconds || 30) * 1000
  )
}

const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
}

onMounted(() => {
  loadBranding()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.branding-panel {
  background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 2px solid rgba(0, 0, 0, 0.1);
  padding-bottom: 12px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: #1f2937;
}

.btn-refresh {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* States */
.state-loading,
.state-error,
.state-no-data {
  text-align: center;
  padding: 48px 24px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  color: #dc2626;
  margin-bottom: 16px;
  font-size: 0.95rem;
}

.btn-secondary {
  background-color: #6b7280;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}

.help-text {
  color: #6b7280;
  font-size: 0.9rem;
  margin: 8px 0 0 0;
}

/* Content Sections */
.branding-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

section h3 {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #1f2937;
}

/* Logo Preview */
.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  background: #f9fafb;
  border-radius: 6px;
}

.org-logo {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.logo-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 1rem;
}

/* Color Grid */
.color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}

.color-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.color-swatch {
  width: 100%;
  height: 80px;
  border-radius: 6px;
  border: 2px solid #e5e7eb;
  cursor: pointer;
  transition: transform 0.2s;
}

.color-swatch:hover {
  transform: scale(1.05);
}

.color-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}

.color-code {
  font-family: monospace;
  font-size: 0.8rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 3px;
}

/* Typography */
.typography-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.typography-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.typography-item label {
  font-weight: 600;
  color: #374151;
}

.font-value {
  font-family: monospace;
  color: #6b7280;
}

/* Application Scope */
.scope-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.95rem;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Assets List */
.assets-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.asset-item {
  display: grid;
  grid-template-columns: 80px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
}

.asset-type {
  font-weight: 600;
  color: #1f2937;
  text-transform: capitalize;
}

.asset-name {
  color: #374151;
}

.asset-dimensions {
  font-size: 0.85rem;
  color: #9ca3af;
}

/* Status Info */
.status-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e5e7eb;
}

.status-row:last-child {
  border-bottom: none;
}

.status-row > span:first-child {
  font-weight: 600;
  color: #374151;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  background: #fee2e2;
  color: #991b1b;
}

.status-badge.active {
  background: #dcfce7;
  color: #166534;
}

.timestamp {
  font-family: monospace;
  font-size: 0.85rem;
  color: #6b7280;
}

/* Responsive */
@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .color-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }

  .typography-grid {
    grid-template-columns: 1fr;
  }

  .asset-item {
    grid-template-columns: 1fr;
  }
}
</style>
