/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, ref } from 'vue';
const props = withDefaults(defineProps(), {
    loading: false,
    error: null,
    compact: false,
});
const showFullStats = ref(false);
// Specialization badge styling
const specializationColor = computed(() => {
    if (!props.summary)
        return '#9ca3af';
    const spec = props.summary.specialization.toLowerCase();
    const colors = {
        'opener': '#3b82f6', // Blue
        'finisher': '#f59e0b', // Amber
        'bowler': '#ef4444', // Red
        'all-rounder': '#8b5cf6', // Purple
        'batter': '#10b981', // Green
    };
    return colors[spec] || '#9ca3af';
});
const specializationBgColor = computed(() => {
    if (!props.summary)
        return 'rgba(156, 163, 175, 0.1)';
    const spec = props.summary.specialization.toLowerCase();
    const colors = {
        'opener': 'rgba(59, 130, 246, 0.1)', // Blue
        'finisher': 'rgba(245, 158, 11, 0.1)', // Amber
        'bowler': 'rgba(239, 68, 68, 0.1)', // Red
        'all-rounder': 'rgba(139, 92, 246, 0.1)', // Purple
        'batter': 'rgba(16, 185, 129, 0.1)', // Green
    };
    return colors[spec] || 'rgba(156, 163, 175, 0.1)';
});
// Trend arrow indicator
const trendArrow = computed(() => {
    if (!props.summary)
        return '→';
    const trend = props.summary.recent_form.trend;
    if (trend === 'improving')
        return '📈';
    if (trend === 'declining')
        return '📉';
    return '→';
});
const trendText = computed(() => {
    if (!props.summary)
        return 'No data';
    return props.summary.recent_form.trend.charAt(0).toUpperCase() +
        props.summary.recent_form.trend.slice(1);
});
const __VLS_defaults = {
    loading: false,
    error: null,
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
/** @type {__VLS_StyleScopedClasses['player-career-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-text']} */ ;
/** @type {__VLS_StyleScopedClasses['highlights-section']} */ ;
/** @type {__VLS_StyleScopedClasses['highlights-list']} */ ;
/** @type {__VLS_StyleScopedClasses['recent-form-section']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-section']} */ ;
/** @type {__VLS_StyleScopedClasses['toggle-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['best-performance']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-header']} */ ;
/** @type {__VLS_StyleScopedClasses['quick-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['highlights-list']} */ ;
/** @type {__VLS_StyleScopedClasses['player-name']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-career-summary" },
    ...{ class: ({ compact: __VLS_ctx.compact }) },
});
/** @type {__VLS_StyleScopedClasses['player-career-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-state" },
    });
    /** @type {__VLS_StyleScopedClasses['error-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
}
else if (__VLS_ctx.summary) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-content" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-header" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-info" },
    });
    /** @type {__VLS_StyleScopedClasses['player-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
        ...{ class: "player-name" },
    });
    /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
    (__VLS_ctx.summary.player_name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "specialization-badge" },
        ...{ style: ({ backgroundColor: __VLS_ctx.specializationBgColor, borderColor: __VLS_ctx.specializationColor }) },
    });
    /** @type {__VLS_StyleScopedClasses['specialization-badge']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge-label" },
    });
    /** @type {__VLS_StyleScopedClasses['badge-label']} */ ;
    (__VLS_ctx.summary.specialization);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge-confidence" },
    });
    /** @type {__VLS_StyleScopedClasses['badge-confidence']} */ ;
    ((__VLS_ctx.summary.specialization_confidence * 100).toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "quick-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['quick-stats']} */ ;
    if (__VLS_ctx.summary.batting_stats.matches) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-pill" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.summary.batting_stats.matches);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    }
    if (__VLS_ctx.summary.batting_stats.total_runs) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-pill" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.summary.batting_stats.total_runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    }
    if (__VLS_ctx.summary.batting_stats.average) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-pill" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.summary.batting_stats.average);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-text" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.summary.career_summary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "highlights-section" },
    });
    /** @type {__VLS_StyleScopedClasses['highlights-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "highlights-list" },
    });
    /** @type {__VLS_StyleScopedClasses['highlights-list']} */ ;
    for (const [highlight, idx] of __VLS_vFor((__VLS_ctx.summary.career_highlights))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (idx),
        });
        (highlight);
        // @ts-ignore
        [compact, loading, error, error, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, specializationBgColor, specializationColor,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "recent-form-section" },
    });
    /** @type {__VLS_StyleScopedClasses['recent-form-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-metrics" },
    });
    /** @type {__VLS_StyleScopedClasses['form-metrics']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-metric" },
    });
    /** @type {__VLS_StyleScopedClasses['form-metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "form-label" },
    });
    /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "trend-indicator" },
    });
    /** @type {__VLS_StyleScopedClasses['trend-indicator']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "trend-arrow" },
    });
    /** @type {__VLS_StyleScopedClasses['trend-arrow']} */ ;
    (__VLS_ctx.trendArrow);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "trend-text" },
    });
    /** @type {__VLS_StyleScopedClasses['trend-text']} */ ;
    (__VLS_ctx.trendText);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-metric" },
    });
    /** @type {__VLS_StyleScopedClasses['form-metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "form-label" },
    });
    /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "form-value" },
    });
    /** @type {__VLS_StyleScopedClasses['form-value']} */ ;
    (__VLS_ctx.summary.recent_form.recent_average.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-metric" },
    });
    /** @type {__VLS_StyleScopedClasses['form-metric']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "form-label" },
    });
    /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "form-value" },
    });
    /** @type {__VLS_StyleScopedClasses['form-value']} */ ;
    (__VLS_ctx.summary.recent_form.last_match_performance);
    if (__VLS_ctx.summary.batting_stats.matches) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-section" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-header" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    if (!(__VLS_ctx.summary))
                        return;
                    if (!(__VLS_ctx.summary.batting_stats.matches))
                        return;
                    __VLS_ctx.showFullStats = !__VLS_ctx.showFullStats;
                    // @ts-ignore
                    [summary, summary, summary, trendArrow, trendText, showFullStats, showFullStats,];
                } },
            ...{ class: "toggle-btn" },
        });
        /** @type {__VLS_StyleScopedClasses['toggle-btn']} */ ;
        (__VLS_ctx.showFullStats ? '▼' : '▶');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-summary" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-summary']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.batting_stats.average);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.batting_stats.strike_rate);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "consistency-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['consistency-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "consistency-fill" },
            ...{ style: ({ width: __VLS_ctx.summary.batting_stats.consistency_score + '%' }) },
        });
        /** @type {__VLS_StyleScopedClasses['consistency-fill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value-small" },
        });
        /** @type {__VLS_StyleScopedClasses['value-small']} */ ;
        (__VLS_ctx.summary.batting_stats.consistency_score.toFixed(0));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-grid" },
        });
        __VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.showFullStats) }, null, null);
        /** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.matches);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.total_runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.best_score);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.centuries);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.fifties);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.fours);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.sixes);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.boundary_percentage.toFixed(1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-box" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "large-value" },
        });
        /** @type {__VLS_StyleScopedClasses['large-value']} */ ;
        (__VLS_ctx.summary.batting_stats.dismissal_rate.toFixed(0));
        if (__VLS_ctx.summary.best_performances.best_batting) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "best-performance" },
            });
            /** @type {__VLS_StyleScopedClasses['best-performance']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "performance-details" },
            });
            /** @type {__VLS_StyleScopedClasses['performance-details']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_batting.runs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_batting.balls_faced);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_batting.fours);
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_batting.sixes);
        }
    }
    if (__VLS_ctx.summary.bowling_stats.matches) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-section bowling" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-section']} */ ;
        /** @type {__VLS_StyleScopedClasses['bowling']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "bowling-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['bowling-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.bowling_stats.total_wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.bowling_stats.economy_rate);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.bowling_stats.average_wickets_per_match.toFixed(2));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-item" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.summary.bowling_stats.maiden_percentage.toFixed(1));
        if (__VLS_ctx.summary.best_performances.best_bowling) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "best-performance" },
            });
            /** @type {__VLS_StyleScopedClasses['best-performance']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "performance-details" },
            });
            /** @type {__VLS_StyleScopedClasses['performance-details']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_bowling.wickets);
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_bowling.runs_conceded);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_bowling.overs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.summary.best_performances.best_bowling.economy);
        }
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, summary, showFullStats, showFullStats,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
