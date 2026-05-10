/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = defineProps();
// Computed: Overall compliance percentage
const overallCompliance = computed(() => {
    if (!props.outcomes?.overall_compliance_pct)
        return 0;
    return Math.round(props.outcomes.overall_compliance_pct * 100);
});
// Computed: Compliance badge CSS class
const complianceClass = computed(() => {
    const pct = overallCompliance.value;
    if (pct >= 80)
        return 'excellent';
    if (pct >= 60)
        return 'good';
    if (pct >= 40)
        return 'fair';
    return 'poor';
});
// Computed: Zone outcomes with enriched data
const zoneOutcomes = computed(() => {
    if (!props.outcomes?.zones)
        return [];
    return props.outcomes.zones.map((zone) => ({
        ...zone,
        delta: zone.actual_accuracy - zone.target_accuracy,
    }));
});
// Computed: Metric outcomes with enriched data
const metricOutcomes = computed(() => {
    if (!props.outcomes?.metrics)
        return [];
    return props.outcomes.metrics.map((metric) => ({
        ...metric,
        delta: metric.actual_score !== null ? metric.actual_score - metric.target_score : null,
    }));
});
// Utility: Format delta with + or - prefix
function formatDelta(delta) {
    if (delta === null)
        return 'N/A';
    const formatted = (delta * 100).toFixed(0);
    return delta >= 0 ? `+${formatted}%` : `${formatted}%`;
}
// Utility: CSS class for delta (positive = green, negative = red)
function deltaClass(delta) {
    if (delta === null)
        return '';
    if (delta >= 0.05)
        return 'positive';
    if (delta <= -0.05)
        return 'negative';
    return 'neutral';
}
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['compliance-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['compliance-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['compliance-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['compliance-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-section']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-section']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta']} */ ;
/** @type {__VLS_StyleScopedClasses['delta']} */ ;
/** @type {__VLS_StyleScopedClasses['delta']} */ ;
/** @type {__VLS_StyleScopedClasses['no-outcomes']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "outcomes-viewer" },
});
/** @type {__VLS_StyleScopedClasses['outcomes-viewer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "compliance-badge" },
    ...{ class: (__VLS_ctx.complianceClass) },
});
/** @type {__VLS_StyleScopedClasses['compliance-badge']} */ ;
(__VLS_ctx.overallCompliance);
if (__VLS_ctx.zoneOutcomes.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "outcomes-section" },
    });
    /** @type {__VLS_StyleScopedClasses['outcomes-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "outcomes-table" },
    });
    /** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [outcome] of __VLS_vFor((__VLS_ctx.zoneOutcomes))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (outcome.zone_name),
            ...{ class: (outcome.pass ? 'pass' : 'fail') },
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "zone-name" },
        });
        /** @type {__VLS_StyleScopedClasses['zone-name']} */ ;
        (outcome.zone_name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "target" },
        });
        /** @type {__VLS_StyleScopedClasses['target']} */ ;
        ((outcome.target_accuracy * 100).toFixed(0));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "actual" },
        });
        /** @type {__VLS_StyleScopedClasses['actual']} */ ;
        ((outcome.actual_accuracy * 100).toFixed(0));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "delta" },
            ...{ class: (__VLS_ctx.deltaClass(outcome.delta)) },
        });
        /** @type {__VLS_StyleScopedClasses['delta']} */ ;
        (__VLS_ctx.formatDelta(outcome.delta));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "status" },
        });
        /** @type {__VLS_StyleScopedClasses['status']} */ ;
        (outcome.pass ? '✅' : '❌');
        // @ts-ignore
        [complianceClass, overallCompliance, zoneOutcomes, zoneOutcomes, deltaClass, formatDelta,];
    }
}
if (__VLS_ctx.metricOutcomes.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "outcomes-section" },
    });
    /** @type {__VLS_StyleScopedClasses['outcomes-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "outcomes-table" },
    });
    /** @type {__VLS_StyleScopedClasses['outcomes-table']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [outcome] of __VLS_vFor((__VLS_ctx.metricOutcomes))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (outcome.code),
            ...{ class: (outcome.pass ? 'pass' : 'fail') },
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "metric-name" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
        (outcome.title);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "target" },
        });
        /** @type {__VLS_StyleScopedClasses['target']} */ ;
        (outcome.target_score.toFixed(2));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "actual" },
        });
        /** @type {__VLS_StyleScopedClasses['actual']} */ ;
        (outcome.actual_score !== null ? outcome.actual_score.toFixed(2) : 'N/A');
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "delta" },
            ...{ class: (__VLS_ctx.deltaClass(outcome.delta)) },
        });
        /** @type {__VLS_StyleScopedClasses['delta']} */ ;
        (__VLS_ctx.formatDelta(outcome.delta));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "status" },
        });
        /** @type {__VLS_StyleScopedClasses['status']} */ ;
        (outcome.pass ? '✅' : '❌');
        // @ts-ignore
        [deltaClass, formatDelta, metricOutcomes, metricOutcomes,];
    }
}
if (__VLS_ctx.zoneOutcomes.length === 0 && __VLS_ctx.metricOutcomes.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-outcomes" },
    });
    /** @type {__VLS_StyleScopedClasses['no-outcomes']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[zoneOutcomes, metricOutcomes,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
