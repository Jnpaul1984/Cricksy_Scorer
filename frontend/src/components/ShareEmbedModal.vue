<template>
  <div v-if="open" class="backdrop" @click.self="close">
    <div class="card" role="dialog" aria-modal="true" aria-labelledby="share-title">
      <header class="hdr">
        <h3 id="share-title">Share & Monetize</h3>
        <button class="x" @click="close" aria-label="Close">✕</button>
      </header>

      <section class="body">
        <label class="lbl">Embed this scoreboard</label>

        <div class="code-wrap">
          <textarea
            ref="codeRef"
            class="code"
            readonly
            :value="iframeCode"
            aria-label="Embed code"
          ></textarea>
          <button class="copy" @click="copy">
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>

        <div class="note">
          <strong>Tip (TV/OBS):</strong> Add a “Browser Source” with the iframe’s
          <code>src</code> URL (or paste this into a small HTML file). Set width to your canvas,
          height ~{{ height }}px, and enable transparency if you want the rounded corners to blend.
        </div>
      </section>

      <footer class="ftr">
        <a class="preview" :href="embedUrl" target="_blank" rel="noopener">Open preview</a>
        <button class="primary" @click="copy">{{ copied ? 'Copied!' : 'Copy embed' }}</button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  gameId: string
  theme?: 'auto' | 'dark' | 'light'
  title?: string
  logo?: string
  sponsorsUrl?: string
  height?: number
}>(), {
  theme: 'auto',
  title: '',
  logo: '',
  sponsorsUrl: '',
  height: 180,
})

const emit = defineEmits<{ (e:'update:modelValue', v:boolean): void }>()

const codeRef = ref<HTMLTextAreaElement | null>(null)
const copied = ref(false)
const open = computed(() => props.modelValue)

function close() { emit('update:modelValue', false) }

const embedUrl = computed(() => {
  const origin = window.location.origin
  // If you’re using Vue Router hash mode (default in many Vite templates)
  const base = origin + '/#'
  const path = `/embed/scoreboard/${encodeURIComponent(props.gameId)}`
  const qs = new URLSearchParams()
  if (props.theme && props.theme !== 'auto') qs.set('theme', props.theme)
  if (props.title) qs.set('title', props.title)
  if (props.logo) qs.set('logo', props.logo)
  if (props.sponsorsUrl) qs.set('sponsorsUrl', props.sponsorsUrl)
  // You can expose sponsorClickable/rotateMs here later if needed.
  const q = qs.toString()
  return q ? `${base}${path}?${q}` : `${base}${path}`
})

const iframeCode = computed(() => {
  // width 100% so it fits host, fixed height to avoid reflow
  return `<iframe src="${embedUrl.value}" width="100%" height="${props.height}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`
})

async function copy() {
  const txt = iframeCode.value
  try {
    // Primary (modern)
    await navigator.clipboard.writeText(txt)
    copied.value = true
  } catch {
    // Fallback (mobile Safari etc.)
    if (codeRef.value) {
      codeRef.value.focus()
      codeRef.value.select()
      try { document.execCommand('copy') } catch {}
      copied.value = true
    }
  }
  // Reset label after a moment
  window.setTimeout(() => (copied.value = false), 1600)
}

watch(open, (o) => {
  if (o) setTimeout(() => codeRef.value?.select(), 50)
})
</script>

<style scoped>
.backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.45);
  display: grid; place-items: center;
  padding: 16px;
  z-index: 60;
}
.card {
  width: min(720px, 96vw);
  background: #0b0f1a;
  color: #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0,0,0,.5);
  overflow: hidden;
}
.hdr, .ftr { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hdr { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,.06); }
.ftr { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,.06); }
.hdr h3 { font-size: 16px; margin: 0; letter-spacing: .01em; }
.x { background: transparent; border: 0; color: #9ca3af; font-size: 18px; cursor: pointer; }
.body { padding: 14px 16px; display: grid; gap: 12px; }
.lbl { font-size: 12px; color: #9ca3af; }
.code-wrap { position: relative; }
.code {
  width: 100%; min-height: 110px; resize: vertical;
  background: #0f172a; color: #e5e7eb; border: 1px solid rgba(255,255,255,.08);
  border-radius: 12px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px; line-height: 1.4;
}
.copy {
  position: absolute; top: 8px; right: 8px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.06);
  color: #e5e7eb; border-radius: 10px; padding: 6px 10px; font-size: 12px;
  cursor: pointer;
}
.note { font-size: 12px; color: #9ca3af; }
.note code { background: rgba(255,255,255,.06); padding: 1px 6px; border-radius: 6px; }
.primary, .preview {
  appearance: none; border-radius: 10px; padding: 8px 12px; font-weight: 600; font-size: 14px; text-decoration: none;
}
.primary {
  border: 0; background: #22d3ee; color: #0b0f1a; cursor: pointer;
}
.preview {
  color: #e5e7eb; border: 1px solid rgba(255,255,255,.12);
}
@media (prefers-color-scheme: light) {
  .card { background: #ffffff; color: #111827; }
  .code { background: #f9fafb; color: #111827; border-color: #e5e7eb; }
  .x { color: #6b7280; }
  .note { color: #6b7280; }
  .preview { color: #111827; border-color: #e5e7eb; }
}
</style>
