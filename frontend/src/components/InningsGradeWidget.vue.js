/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    theme: 'dark',
    compact: false,
});
// Grade badge styling
const gradeColor = computed(() => {
    if (!props.gradeData)
        return '#9ca3af';
    const grade = props.gradeData.grade;
    const colors = {
        'A+': '#22c55e', // Bright green
        'A': '#84cc16', // Lime
        'B': '#eab308', // Yellow
        'C': '#f97316', // Orange
        'D': '#ef4444', // Red
    };
    return colors[grade] || '#9ca3af';
});
const gradeBgColor = computed(() => {
    if (!props.gradeData)
        return 'rgba(156, 163, 175, 0.1)';
    const grade = props.gradeData.grade;
    const colors = {
        'A+': 'rgba(34, 197, 94, 0.1)', // Green
        'A': 'rgba(132, 204, 22, 0.1)', // Lime
        'B': 'rgba(234, 179, 8, 0.1)', // Yellow
        'C': 'rgba(249, 115, 22, 0.1)', // Orange
        'D': 'rgba(239, 68, 68, 0.1)', // Red
    };
    return colors[grade] || 'rgba(156, 163, 175, 0.1)';
});
const gradeDescription = computed(() => {
    if (!props.gradeData)
        return 'No grade data';
    const descriptions = {
        'A+': 'Exceptional - Outstanding performance',
        'A': 'Very Good - Excellent batting display',
        'B': 'Good - Solid innings performance',
        'C': 'Average - Acceptable but below par',
        'D': 'Below Average - Struggled against opposition',
    };
    return descriptions[props.gradeData.grade] || 'Unknown';
});
const resolvedTheme = computed(() => {
    if (props.theme === 'dark')
        return 'dark';
    return 'light';
});
const __VLS_defaults = {
    theme: 'dark',
    compact: false,
};
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['innings-grade-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['no-data']} */ ;
/** @type {__VLS_StyleScopedClasses['grade-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['grade-letter']} */ ;
/** @type {__VLS_StyleScopedClasses['metrics-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "innings-grade-widget" },
    ...{ class: ({ compact: __VLS_ctx.compact }) },
});
/** @type {__VLS_StyleScopedClasses['innings-grade-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
if (__VLS_ctx.gradeData) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grade-display" },
    });
    /** @type {__VLS_StyleScopedClasses['grade-display']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grade-badge-section" },
    });
    /** @type {__VLS_StyleScopedClasses['grade-badge-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grade-badge" },
        ...{ style: ({ backgroundColor: __VLS_ctx.gradeBgColor, borderColor: __VLS_ctx.gradeColor }) },
    });
    /** @type {__VLS_StyleScopedClasses['grade-badge']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grade-letter" },
        ...{ style: ({ color: __VLS_ctx.gradeColor }) },
    });
    /** @type {__VLS_StyleScopedClasses['grade-letter']} */ ;
    (__VLS_ctx.gradeData.grade);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grade-description" },
    });
    /** @type {__VLS_StyleScopedClasses['grade-description']} */ ;
    (__VLS_ctx.gradeDescription);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metrics-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['metrics-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric" },
    });
    /** @type {__VLS_StyleScopedClasses['metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-label" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.gradeData.run_rate.toFixed(2));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-unit" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-unit']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric" },
    });
    /** @type {__VLS_StyleScopedClasses['metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-label" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.gradeData.score_percentage.toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-unit" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-unit']} */ ;
    (__VLS_ctx.gradeData.par_score);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric" },
    });
    /** @type {__VLS_StyleScopedClasses['metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-label" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.gradeData.wickets_lost);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-unit" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-unit']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric" },
    });
    /** @type {__VLS_StyleScopedClasses['metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-label" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.gradeData.boundary_count);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-unit" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-unit']} */ ;
    (__VLS_ctx.gradeData.boundary_percentage.toFixed(0));
    if (!__VLS_ctx.compact) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factors-section" },
        });
        /** @type {__VLS_StyleScopedClasses['factors-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "factors-title" },
        });
        /** @type {__VLS_StyleScopedClasses['factors-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factors-list" },
        });
        /** @type {__VLS_StyleScopedClasses['factors-list']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factor-item" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-text" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-text']} */ ;
        (__VLS_ctx.gradeData.grade_factors.score_percentage_contribution);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factor-item" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-text" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-text']} */ ;
        (__VLS_ctx.gradeData.grade_factors.wicket_efficiency_contribution);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factor-item" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-text" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-text']} */ ;
        (__VLS_ctx.gradeData.grade_factors.strike_rotation_contribution);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factor-item" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "factor-text" },
        });
        /** @type {__VLS_StyleScopedClasses['factor-text']} */ ;
        (__VLS_ctx.gradeData.grade_factors.boundary_efficiency_contribution);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-breakdown" },
    });
    /** @type {__VLS_StyleScopedClasses['score-breakdown']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "breakdown-row" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-label" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-value" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-value']} */ ;
    (__VLS_ctx.gradeData.total_runs);
    (__VLS_ctx.gradeData.wickets_lost);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "breakdown-row" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-label" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-value" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-value']} */ ;
    (__VLS_ctx.gradeData.overs_played);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "breakdown-row" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-label" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "breakdown-value" },
    });
    /** @type {__VLS_StyleScopedClasses['breakdown-value']} */ ;
    (__VLS_ctx.gradeData.par_score);
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-data" },
    });
    /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[compact, compact, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeData, gradeBgColor, gradeColor, gradeColor, gradeDescription,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
