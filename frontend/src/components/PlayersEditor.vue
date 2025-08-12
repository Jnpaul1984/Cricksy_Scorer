<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'

type Props = {
  modelValue: string[]
  label?: string
  teamName?: string
  max?: number         // hard cap (e.g., squad size)
  min?: number         // min needed to proceed (for UX hints)
  placeholder?: string
}
const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  label: 'Players',
  teamName: '',
  max: 16,
  min: 2,
  placeholder: 'Type a name and press Enter (or paste a comma/newline list)…',
})
const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'change', value: string[]): void
}>()

const names = ref<string[]>([...props.modelValue])
const quick = ref('')
const warn = ref<string | null>(null)

// keep local in sync if parent replaces the array
watch(
  () => props.modelValue,
  v => { names.value = [...v] },
  { deep: true }
)

// normalize + de-dupe (case-insensitive), strip empties
function normalize(list: string[]) {
  const out: string[] = []
  const seen = new Set<string>()
  for (const raw of list) {
    const n = raw.trim().replace(/\s+/g, ' ')
    if (!n) continue
    const key = n.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(n)
  }
  return out
}

function cap(list: string[]) {
  if (list.length <= props.max) return list
  warn.value = `Only the first ${props.max} players are kept (limit reached).`
  return list.slice(0, props.max)
}

function commit(list: string[]) {
  const cleaned = cap(normalize(list))
  names.value = cleaned
  emit('update:modelValue', cleaned)
  emit('change', cleaned)
}

// row edits
function updateAt(i: number, val: string) {
  const draft = [...names.value]
  draft[i] = val
  commit(draft)
}
function removeAt(i: number) {
  const draft = [...names.value]
  draft.splice(i, 1)
  commit(draft)
}
function move(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= names.value.length) return
  const draft = [...names.value]
  const [it] = draft.splice(i, 1)
  draft.splice(j, 0, it)
  commit(draft)
}

// adding
function addOne(n: string) {
  const merged = [...names.value, n]
  commit(merged)
}
function addManyFromText(text: string) {
  const chunks = text.split(/[\n,;]+/g).map(s => s.trim()).filter(Boolean)
  const merged = [...names.value, ...chunks]
  commit(merged)
}
async function handleQuickEnter() {
  if (!quick.value.trim()) return
  addManyFromText(quick.value)
  quick.value = ''
  await nextTick()
}
function onQuickPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') || ''
  if (!text) return
  e.preventDefault()
  addManyFromText(text)
  quick.value = ''
}

const count = computed(() => names.value.length)
const shortfall = computed(() => Math.max(0, props.min - count.value))
const canAddMore = computed(() => count.value < props.max)
</script>

<template>
  <div class="pe">
    <div class="pe-head">
      <div class="title">
        <strong>{{ label }}</strong>
        <span v-if="teamName" class="muted"> – {{ teamName }}</span>
      </div>
      <div class="count">
        {{ count }} / {{ max }}
        <span v-if="shortfall" class="need">need {{ shortfall }}+</span>
      </div>
    </div>

    <div class="list">
      <div
        v-for="(n, i) in names"
        :key="i"
        class="row"
      >
        <div class="idx">{{ i + 1 }}</div>
        <input
          class="input"
          :placeholder="`Player #${i+1}`"
          :value="n"
          @input="updateAt(i, ($event.target as HTMLInputElement).value)"
        />
        <div class="actions">
          <button type="button" title="Move up" @click="move(i, -1)" :disabled="i===0">↑</button>
          <button type="button" title="Move down" @click="move(i, 1)" :disabled="i===names.length-1">↓</button>
          <button type="button" title="Remove" class="danger" @click="removeAt(i)">✕</button>
        </div>
      </div>
    </div>

    <div class="add">
      <input
        class="quick"
        :placeholder="placeholder"
        v-model="quick"
        @keydown.enter.prevent="handleQuickEnter"
        @paste="onQuickPaste"
      />
      <button type="button" class="add-btn" @click="handleQuickEnter" :disabled="!quick.trim()">Add</button>
      <button type="button" class="clear-btn" @click="commit([])" :disabled="!names.length">Clear</button>
    </div>

    <p v-if="warn" class="warn">⚠ {{ warn }}</p>
    <p class="hint">
      Tips: paste “<em>Alice, Bob, Charlie</em>” or a newline list; duplicates are removed automatically.
    </p>
  </div>
</template>

<style scoped>
.pe{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:14px;padding:12px;color:#fff}
.pe-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.title{font-size:14px}
.muted{opacity:.85}
.count{opacity:.9}
.need{margin-left:8px;color:#ffd54f}
.list{display:grid;gap:8px;max-height:320px;overflow:auto;padding:4px}
.row{display:grid;grid-template-columns:34px 1fr auto;gap:8px;align-items:center;background:rgba(0,0,0,.18);border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:6px}
.idx{width:28px;height:28px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.12);border-radius:8px}
.input{width:100%;padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:#fff}
.actions{display:flex;gap:6px}
.actions button{border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.08);color:#fff;padding:6px 8px;border-radius:8px;cursor:pointer}
.actions button:disabled{opacity:.5;cursor:not-allowed}
.actions .danger{border-color:rgba(244,67,54,.6);color:#ffb3b3}
.add{display:flex;gap:8px;margin-top:10px}
.quick{flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.1);color:#fff}
.add-btn{border:none;background:linear-gradient(135deg,#43a047,#2e7d32);color:#fff;padding:10px 14px;border-radius:10px;cursor:pointer}
.clear-btn{border:1px solid rgba(255,255,255,.3);background:transparent;color:#fff;padding:10px 14px;border-radius:10px;cursor:pointer}
.warn{margin:.5rem 0 0;color:#ffecb3}
.hint{opacity:.8;margin:.35rem 0 0;font-size:.92rem}
</style>
