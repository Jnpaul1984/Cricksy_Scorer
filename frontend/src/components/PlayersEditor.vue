<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'

import { BaseCard, BaseButton } from '@/components'

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
</script>

<template>
<BaseCard
  as="section"
  class="pe"
  :data-testid="`players-editor-${(teamName || 'team').replace(/\\s+/g, '-').toLowerCase()}`"
>
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
          <BaseButton variant="secondary" size="sm" title="Move up" :disabled="i===0" @click="move(i, -1)">↑</BaseButton>
          <BaseButton variant="secondary" size="sm" title="Move down" :disabled="i===names.length-1" @click="move(i, 1)">↓</BaseButton>
          <BaseButton variant="danger" size="sm" title="Remove" @click="removeAt(i)">✕</BaseButton>
        </div>
      </div>
    </div>

    <div class="add">
      <input
        v-model="quick"
        class="quick"
        :placeholder="placeholder"
        data-testid="players-quick-input"
        @keydown.enter.prevent="handleQuickEnter"
        @paste="onQuickPaste"
      />
      <BaseButton
        variant="primary"
        :disabled="!quick.trim()"
        data-testid="players-add-btn"
        @click="handleQuickEnter"
      >
        Add
      </BaseButton>
      <BaseButton
        variant="secondary"
        :disabled="!names.length"
        data-testid="players-clear-btn"
        @click="commit([])"
      >
        Clear
      </BaseButton>
    </div>

    <p v-if="warn" class="warn">⚠ {{ warn }}</p>
    <p class="hint">
      Tips: paste "<em>Alice, Bob, Charlie</em>" or a newline list; duplicates are removed automatically.
    </p>
  </BaseCard>
</template>

<style scoped>
.pe { color: var(--color-on-surface) }
.pe-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-sm) }
.title { font-size: var(--text-sm) }
.muted { opacity: 0.85 }
.count { opacity: 0.9 }
.need { margin-left: var(--space-sm); color: var(--color-accent) }
.list { display: grid; gap: var(--space-sm); max-height: 320px; overflow: auto; padding: var(--space-xs) }
.row {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  gap: var(--space-sm);
  align-items: center;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-xs)
}
.idx {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt);
  border-radius: var(--radius-sm)
}
.input {
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-alt);
  color: var(--color-on-surface)
}
.actions { display: flex; gap: var(--space-xs) }
.add { display: flex; gap: var(--space-sm); margin-top: var(--space-md) }
.quick {
  flex: 1;
  padding: var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface-alt);
  color: var(--color-on-surface)
}
.warn { margin: var(--space-xs) 0 0; color: var(--color-accent) }
.hint { opacity: 0.8; margin: var(--space-xs) 0 0; font-size: var(--text-sm) }
</style>
