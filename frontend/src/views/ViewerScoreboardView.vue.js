/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import { useRoute } from 'vue-router';
import { BaseButton, BaseCard, BaseBadge } from '@/components';
import ScoreboardWidget from '@/components/ScoreboardWidget.vue';
import { useProjectorMode } from '@/composables/useProjectorMode';
import { useGameStore } from '@/stores/gameStore';
import { API_BASE } from '@/utils/api';
/**
 * Route & params
 */
const route = useRoute();
const gameId = computed(() => String(route.params.gameId || ''));
/**
 * Query param helpers (allow overrides from the URL)
 * e.g.  /#/viewer/123?apiBase=https://api.example.com&sponsorsUrl=https://…/sponsors.json
 *       &title=My%20Match&logo=https://…/logo.png&theme=dark
 */
const q = route.query;
const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : '';
const apiBase = computed(() => (q.apiBase || API_BASE || fallbackOrigin).replace(/\/$/, ''));
const gameStore = useGameStore();
const sponsorsUrl = computed(() => q.sponsorsUrl ||
    `${apiBase.value}/games/${encodeURIComponent(gameId.value)}/sponsors`);
const resolvedTitle = computed(() => q.title || `Match ${gameId.value.slice(0, 8)}…`);
const resolvedLogo = computed(() => q.logo || '');
const resolvedTheme = ref(q.theme || 'auto');
/**
 * Projector mode config
 */
const projectorMode = useProjectorMode(q);
const rootStyle = computed(() => projectorMode.cssVariables.value);
/**
 * If theme=auto, pick one based on prefers-color-scheme
 */
onMounted(() => {
    gameStore.setPublicViewerMode(true);
    if (resolvedTheme.value === 'auto' && typeof window !== 'undefined' && window.matchMedia) {
        resolvedTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
});
onBeforeUnmount(() => {
    gameStore.setPublicViewerMode(false);
});
/**
 * Shareable viewer URL that keeps current overrides
 */
const viewerUrl = computed(() => {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const params = new URLSearchParams();
    if (q.apiBase)
        params.set('apiBase', String(q.apiBase));
    if (q.sponsorsUrl)
        params.set('sponsorsUrl', String(q.sponsorsUrl));
    if (q.title)
        params.set('title', String(q.title));
    if (q.logo)
        params.set('logo', String(q.logo));
    if (q.theme)
        params.set('theme', String(q.theme));
    if (q.preset)
        params.set('preset', String(q.preset));
    if (q.layout)
        params.set('layout', String(q.layout));
    if (q.scale)
        params.set('scale', String(q.scale));
    if (q.density)
        params.set('density', String(q.density));
    if (q.safeArea)
        params.set('safeArea', String(q.safeArea));
    const qs = params.toString();
    return `${origin}/#/viewer/${encodeURIComponent(gameId.value)}${qs ? `?${qs}` : ''}`;
});
function openInNewTab() {
    if (!gameId.value)
        return;
    window.open(viewerUrl.value, '_blank', 'noopener');
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['bar']} */ ;
/** @type {__VLS_StyleScopedClasses['left']} */ ;
/** @type {__VLS_StyleScopedClasses['right']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "view-wrap" },
    ...{ style: (__VLS_ctx.rootStyle) },
});
/** @type {__VLS_StyleScopedClasses['view-wrap']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "header",
    padding: "sm",
    ...{ class: "bar" },
}));
const __VLS_2 = __VLS_1({
    as: "header",
    padding: "sm",
    ...{ class: "bar" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (!__VLS_ctx.projectorMode.isProjectorMode.value) }, null, null);
/** @type {__VLS_StyleScopedClasses['bar']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "left" },
});
/** @type {__VLS_StyleScopedClasses['left']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "title" },
});
/** @type {__VLS_StyleScopedClasses['title']} */ ;
if (__VLS_ctx.gameId) {
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        variant: "neutral",
        uppercase: (false),
    }));
    const __VLS_8 = __VLS_7({
        variant: "neutral",
        uppercase: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    const { default: __VLS_11 } = __VLS_9.slots;
    (__VLS_ctx.gameId.slice(0, 8));
    // @ts-ignore
    [rootStyle, projectorMode, gameId, gameId,];
    var __VLS_9;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "right" },
});
/** @type {__VLS_StyleScopedClasses['right']} */ ;
let __VLS_12;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}));
const __VLS_14 = __VLS_13({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
let __VLS_17;
const __VLS_18 = ({ click: {} },
    { onClick: (__VLS_ctx.openInNewTab) });
const { default: __VLS_19 } = __VLS_15.slots;
// @ts-ignore
[openInNewTab,];
var __VLS_15;
var __VLS_16;
__VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
    ...{ class: "ds-btn ds-btn--ghost ds-btn--sm" },
    href: (__VLS_ctx.viewerUrl),
    target: "_blank",
    rel: "noopener",
});
/** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--sm']} */ ;
// @ts-ignore
[viewerUrl,];
var __VLS_3;
let __VLS_20;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
    as: "section",
    padding: (__VLS_ctx.projectorMode.isProjectorMode.value ? 'md' : 'lg'),
    ...{ class: "stage" },
}));
const __VLS_22 = __VLS_21({
    as: "section",
    padding: (__VLS_ctx.projectorMode.isProjectorMode.value ? 'md' : 'lg'),
    ...{ class: "stage" },
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
/** @type {__VLS_StyleScopedClasses['stage']} */ ;
const { default: __VLS_25 } = __VLS_23.slots;
const __VLS_26 = ScoreboardWidget;
// @ts-ignore
const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
    gameId: (__VLS_ctx.gameId),
    title: (__VLS_ctx.resolvedTitle),
    theme: (__VLS_ctx.resolvedTheme),
    logo: (__VLS_ctx.resolvedLogo),
    apiBase: (__VLS_ctx.apiBase),
    sponsorsUrl: (__VLS_ctx.sponsorsUrl),
    interruptionsMode: "auto",
    pollMs: (5000),
}));
const __VLS_28 = __VLS_27({
    gameId: (__VLS_ctx.gameId),
    title: (__VLS_ctx.resolvedTitle),
    theme: (__VLS_ctx.resolvedTheme),
    logo: (__VLS_ctx.resolvedLogo),
    apiBase: (__VLS_ctx.apiBase),
    sponsorsUrl: (__VLS_ctx.sponsorsUrl),
    interruptionsMode: "auto",
    pollMs: (5000),
}, ...__VLS_functionalComponentArgsRest(__VLS_27));
// @ts-ignore
[projectorMode, gameId, resolvedTitle, resolvedTheme, resolvedLogo, apiBase, sponsorsUrl,];
var __VLS_23;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
