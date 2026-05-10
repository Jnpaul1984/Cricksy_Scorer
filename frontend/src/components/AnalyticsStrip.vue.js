/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = defineProps();
const strikerDotPct = computed(() => {
    const balls = props.strikerBalls || 0;
    const dots = props.strikerDots || 0;
    return balls > 0 ? `${Math.round((dots / balls) * 100)}%` : '—';
});
const bowlerDotPct = computed(() => {
    const balls = props.bowlerBalls || 0;
    const dots = props.bowlerDots || 0;
    return balls > 0 ? `${Math.round((dots / balls) * 100)}%` : '—';
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['as-card']} */ ;
/** @type {__VLS_StyleScopedClasses['as-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "as-root" },
});
/** @type {__VLS_StyleScopedClasses['as-root']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-cards" },
});
/** @type {__VLS_StyleScopedClasses['as-cards']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-card" },
});
/** @type {__VLS_StyleScopedClasses['as-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-title" },
});
/** @type {__VLS_StyleScopedClasses['as-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-row" },
});
/** @type {__VLS_StyleScopedClasses['as-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-label" },
});
/** @type {__VLS_StyleScopedClasses['as-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-val" },
});
/** @type {__VLS_StyleScopedClasses['as-val']} */ ;
(__VLS_ctx.snapshot?.batsmen.striker.name || '-');
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-row" },
});
/** @type {__VLS_StyleScopedClasses['as-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-label" },
});
/** @type {__VLS_StyleScopedClasses['as-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-val" },
});
/** @type {__VLS_StyleScopedClasses['as-val']} */ ;
(__VLS_ctx.snapshot?.batsmen.striker.runs ?? 0);
(__VLS_ctx.snapshot?.batsmen.striker.balls ?? 0);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-row" },
});
/** @type {__VLS_StyleScopedClasses['as-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-label" },
});
/** @type {__VLS_StyleScopedClasses['as-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-val" },
});
/** @type {__VLS_StyleScopedClasses['as-val']} */ ;
(__VLS_ctx.strikerDotPct);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-card" },
});
/** @type {__VLS_StyleScopedClasses['as-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-title" },
});
/** @type {__VLS_StyleScopedClasses['as-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "as-row" },
});
/** @type {__VLS_StyleScopedClasses['as-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-label" },
});
/** @type {__VLS_StyleScopedClasses['as-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "as-val" },
});
/** @type {__VLS_StyleScopedClasses['as-val']} */ ;
(__VLS_ctx.bowlerDotPct);
// @ts-ignore
[snapshot, snapshot, snapshot, strikerDotPct, bowlerDotPct,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
