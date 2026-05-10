/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { onMounted, onBeforeUnmount } from 'vue';
import ScoreboardWidget from '@/components/ScoreboardWidget.vue';
import { useGameStore } from '@/stores/gameStore';
// Provide a test-only hook on this route to inject a match fixture
// into the Pinia store so the widget can render the result banner.
function applyMatch(match) {
    const store = useGameStore();
    store.currentGame = {
        id: 'e2e',
        team_a: { name: match?.teams?.[0] ?? 'Team A', players: [] },
        team_b: { name: match?.teams?.[1] ?? 'Team B', players: [] },
        status: 'completed',
        current_inning: 2,
        result: { result_text: match?.result?.summary ?? '' },
    };
}
;
window.loadMatch = (match) => applyMatch(match);
function onE2eMatch() {
    const pending = window.__pendingMatch;
    if (pending)
        applyMatch(pending);
}
onMounted(() => {
    // If Cypress pushed a match before this view loaded, apply it now
    onE2eMatch();
    // Listen for future pushes
    window.addEventListener('e2e:match', onE2eMatch);
});
onBeforeUnmount(() => {
    window.removeEventListener('e2e:match', onE2eMatch);
});
const __VLS_ctx = {};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ style: {} },
});
const __VLS_0 = ScoreboardWidget;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    gameId: ('e2e'),
}));
const __VLS_2 = __VLS_1({
    gameId: ('e2e'),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
