/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { usePlayerFormTracker } from '@/composables/usePlayerFormTracker';
const props = defineProps();
const { formData, colorMap, trendEmoji, getFormClass, getFormLabel, getTrendLabel } = usePlayerFormTracker({ value: props.profile });
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['form-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['form-tracker-header']} */ ;
/** @type {__VLS_StyleScopedClasses['form-tracker-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['form-chart']} */ ;
/** @type {__VLS_StyleScopedClasses['form-legend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-tracker-widget" },
});
/** @type {__VLS_StyleScopedClasses['form-tracker-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-tracker-header" },
});
/** @type {__VLS_StyleScopedClasses['form-tracker-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "form-tracker-title" },
});
/** @type {__VLS_StyleScopedClasses['form-tracker-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-tracker-summary" },
});
/** @type {__VLS_StyleScopedClasses['form-tracker-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-badge" },
    ...{ class: (`form-badge--${__VLS_ctx.formData.recentForm}`) },
});
/** @type {__VLS_StyleScopedClasses['form-badge']} */ ;
(__VLS_ctx.getFormLabel(__VLS_ctx.formData.recentForm));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "trend-indicator" },
    title: (`Form: ${__VLS_ctx.getTrendLabel(__VLS_ctx.formData.overallTrend)}`),
});
/** @type {__VLS_StyleScopedClasses['trend-indicator']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "trend-arrow" },
});
/** @type {__VLS_StyleScopedClasses['trend-arrow']} */ ;
(__VLS_ctx.trendEmoji[__VLS_ctx.formData.overallTrend]);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "trend-label" },
});
/** @type {__VLS_StyleScopedClasses['trend-label']} */ ;
(__VLS_ctx.getTrendLabel(__VLS_ctx.formData.overallTrend));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-chart" },
});
/** @type {__VLS_StyleScopedClasses['form-chart']} */ ;
for (const [match] of __VLS_vFor((__VLS_ctx.formData.matches))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (match.matchIndex),
        ...{ class: "form-bar-container" },
        title: (`Match ${match.matchIndex}: SR ${match.strikeRate.toFixed(1)}`),
    });
    /** @type {__VLS_StyleScopedClasses['form-bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "form-bar" },
        ...{ class: (__VLS_ctx.getFormClass(match.performance)) },
        ...{ style: ({
                height: `${(match.strikeRate / 200) * 100}%`,
                backgroundColor: __VLS_ctx.colorMap[match.performance],
            }) },
    });
    /** @type {__VLS_StyleScopedClasses['form-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-label" },
    });
    /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
    (match.matchIndex);
    // @ts-ignore
    [formData, formData, formData, formData, formData, formData, getFormLabel, getTrendLabel, getTrendLabel, trendEmoji, getFormClass, colorMap,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-legend" },
});
/** @type {__VLS_StyleScopedClasses['form-legend']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "legend-item" },
});
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "legend-color good" },
});
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['good']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "legend-item" },
});
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "legend-color average" },
});
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['average']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "legend-item" },
});
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "legend-color poor" },
});
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['poor']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "form-stats" },
});
/** @type {__VLS_StyleScopedClasses['form-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-row" },
});
/** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
    ...{ class: (`form-${__VLS_ctx.formData.averagePerformance}`) },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.getFormLabel(__VLS_ctx.formData.averagePerformance));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-row" },
});
/** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.trendEmoji[__VLS_ctx.formData.overallTrend]);
(__VLS_ctx.getTrendLabel(__VLS_ctx.formData.overallTrend));
// @ts-ignore
[formData, formData, formData, formData, getFormLabel, getTrendLabel, trendEmoji,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
