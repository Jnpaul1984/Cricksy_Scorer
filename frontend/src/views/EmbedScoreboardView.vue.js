/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import ScoreboardWidget from '@/components/ScoreboardWidget.vue';
import { useProjectorMode } from '@/composables/useProjectorMode';
import { useGameStore } from '@/stores/gameStore';
import { API_BASE } from '@/utils/api';
const route = useRoute();
const gameId = computed(() => String(route.params.gameId));
const gameStore = useGameStore();
const q = route.query;
const theme = q.theme === 'dark' ? 'dark'
    : q.theme === 'light' ? 'light'
        : 'auto';
const title = q.title || '';
const logo = q.logo || '';
const sponsorsUrl = q.sponsorsUrl || '';
const sponsorRotateMs = Number(q.sponsorRotateMs ?? 8000);
const sponsorClickable = String(q.sponsorClickable ?? 'false') === 'true';
const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : '';
const apiBase = (q.apiBase || API_BASE || fallbackOrigin).replace(/\/$/, '');
/**
 * Projector mode config
 */
const projectorMode = useProjectorMode(q);
const rootStyle = computed(() => projectorMode.cssVariables.value);
onMounted(() => {
    gameStore.setPublicViewerMode(true);
});
onBeforeUnmount(() => {
    gameStore.setPublicViewerMode(false);
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['embed-wrap']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "embed-wrap" },
    ...{ style: (__VLS_ctx.rootStyle) },
});
/** @type {__VLS_StyleScopedClasses['embed-wrap']} */ ;
const __VLS_0 = ScoreboardWidget;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    theme: (__VLS_ctx.theme),
    title: (__VLS_ctx.title),
    logo: (__VLS_ctx.logo),
    apiBase: (__VLS_ctx.apiBase),
    gameId: (__VLS_ctx.gameId),
    sponsorsUrl: (__VLS_ctx.sponsorsUrl),
    sponsorRotateMs: (__VLS_ctx.sponsorRotateMs),
    sponsorClickable: (__VLS_ctx.sponsorClickable),
}));
const __VLS_2 = __VLS_1({
    theme: (__VLS_ctx.theme),
    title: (__VLS_ctx.title),
    logo: (__VLS_ctx.logo),
    apiBase: (__VLS_ctx.apiBase),
    gameId: (__VLS_ctx.gameId),
    sponsorsUrl: (__VLS_ctx.sponsorsUrl),
    sponsorRotateMs: (__VLS_ctx.sponsorRotateMs),
    sponsorClickable: (__VLS_ctx.sponsorClickable),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
// @ts-ignore
[rootStyle, theme, title, logo, apiBase, gameId, sponsorsUrl, sponsorRotateMs, sponsorClickable,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
