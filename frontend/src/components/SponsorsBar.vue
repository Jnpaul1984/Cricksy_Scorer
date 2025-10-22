<template>
  <div class="sbar" role="region" aria-label="Sponsors">
    <div class="rail" :style="railStyle">
      <button
        v-if="showArrows"
        class="nav prev"
        aria-label="Previous sponsor"
        @click="prev"
      >‹</button>

      <div class="viewport" @mouseenter="pause" @mouseleave="resume">
        <transition name="fade" mode="out-in">
          <div :key="activeKey" class="slide">
            <a
              v-if="sponsorClickable && current?.clickUrl"
              class="logo-link"
              :href="current.clickUrl"
              target="_blank"
              rel="noopener"
              @click="emitClick(current)"
            >
              <img v-if="current" class="logo" :src="current.logoUrl" :alt="current.name" />
            </a>
            <div v-else class="logo-wrap">
              <img v-if="current" class="logo" :src="current.logoUrl" :alt="current.name" />
            </div>
          </div>
        </transition>
      </div>

      <button
        v-if="showArrows"
        class="nav next"
        aria-label="Next sponsor"
        @click="next"
      >›</button>
    </div>

    <div v-if="sponsors.length > 1" class="dots">
      <button
        v-for="(sp, i) in sponsors"
        :key="sp.id ?? i"
        class="dot"
        :class="{ active: i === idx }"
        :aria-label="`Go to ${sp.name}`"
        @click="go(i)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'

export type Sponsor = {
  id?: number | string
  name: string
  logoUrl: string
  clickUrl?: string | null
  // optional: weight, surfaces…
}

const props = withDefaults(defineProps<{
  sponsors: Sponsor[]
  sponsorRotateMs?: number
  sponsorClickable?: boolean
  showArrows?: boolean
}>(), {
  sponsors: () => [],
  sponsorRotateMs: 8000,
  sponsorClickable: false,
  showArrows: false,
})

const emit = defineEmits<{
  (e: 'impression', payload: Sponsor | null): void
  (e: 'click', payload: Sponsor | null): void
}>()

const idx = ref(0)
const timer = ref<number | null>(null)
const hovered = ref(false)

const safeSponsors = computed(() => (props.sponsors || []).filter(s => !!s && !!s.logoUrl))
const count = computed(() => safeSponsors.value.length)
const current = computed(() => safeSponsors.value.length ? safeSponsors.value[idx.value % safeSponsors.value.length] : null)
const activeKey = computed(() => current.value ? (current.value.id ?? idx.value) : `empty-${idx.value}`)

const start = () => {
  stop()
  if (count.value <= 1) return
  timer.value = window.setInterval(() => {
    if (!hovered.value) next()
  }, props.sponsorRotateMs)
}
const stop = () => { if (timer.value) { clearInterval(timer.value); timer.value = null } }
const pause = () => { hovered.value = true }
const resume = () => { hovered.value = false }

const next = () => { if (count.value) idx.value = (idx.value + 1) % count.value }
const prev = () => { if (count.value) idx.value = (idx.value - 1 + count.value) % count.value }
const go = (i: number) => { if (count.value) idx.value = i % count.value }

const showArrows = computed(() => props.showArrows && count.value > 1)
const railStyle = computed(() => ({}))

function emitClick(sp: Sponsor | null) {
  emit('click', sp)
}

watch(current, (sp) => {
  // Fire an impression event every time the visible sponsor changes
  emit('impression', sp ?? null)
})

watch(() => props.sponsorRotateMs, () => start())
watch(safeSponsors, () => { idx.value = 0; start() })

onMounted(() => { start(); emit('impression', current.value ?? null) })
onBeforeUnmount(() => stop())
</script>

<style scoped>
.sbar {
  width: 100%;
  display: grid;
  gap: 8px;
}
.rail {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
}
.viewport {
  position: relative;
  min-height: 56px;
  display: grid;
  place-items: center;
  padding: 6px 8px;
}
.slide {
  width: 100%;
  display: grid;
  place-items: center;
}
.logo-wrap, .logo-link {
  display: grid;
  place-items: center;
  width: 100%;
}
.logo {
  max-height: 44px;
  max-width: 100%;
  object-fit: contain;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,.2));
}
.nav {
  background: transparent;
  border: none;
  color: #aaa;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 8px;
}
.nav:hover { color: #fff; }
.dots {
  display: flex;
  gap: 6px;
  justify-content: center;
}
.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  border: none;
  background: #6b7280;
  opacity: .5;
  cursor: pointer;
}
.dot.active { opacity: 1; background: #e5e7eb; }
.fade-enter-active, .fade-leave-active { transition: opacity .35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
