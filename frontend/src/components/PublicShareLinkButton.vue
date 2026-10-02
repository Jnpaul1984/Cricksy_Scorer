<script setup lang="ts">
import { ref } from 'vue'; import { useRouter } from 'vue-router';
const props = defineProps<{ path: string; label?: string }>(); const router = useRouter(); const copied = ref(false);
async function copy() { const href = router.resolve(props.path).href; const base = router.options.history.base.replace(/#$/, '').replace(/\/$/, ''); const canonical = base && !href.startsWith(base) ? `${base}/${href.replace(/^\//, '')}` : href; try { await navigator.clipboard?.writeText(new URL(canonical, window.location.origin).toString()); copied.value = true; } catch { copied.value = false; } }
</script><template><span><button type="button" @click="copy">{{ copied ? 'Link copied' : (label || 'Copy link') }}</button><RouterLink :to="path">Open link</RouterLink></span></template>
