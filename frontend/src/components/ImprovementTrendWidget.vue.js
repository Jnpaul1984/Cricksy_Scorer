/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted } from 'vue';
import { usePlayerImprovement } from '../composables/usePlayerImprovement';
const props = withDefaults(defineProps(), {
    monthsToAnalyze: 6,
});
const selectedMetric = ref('all');
const { summaryData, loading, error, fetchImprovementSummary } = usePlayerImprovement();
onMounted(() => {
    fetchImprovementSummary(props.playerId, props.monthsToAnalyze);
});
const formatRole = (role) => {
    const roleMap = {
        opener: 'Opener',
        top_order: 'Top Order',
        middle_order: 'Middle Order',
        finisher: 'Finisher',
        bowler: 'Bowler',
        all_rounder: 'All-rounder',
    };
    return roleMap[role] || role;
};
const showTrendIcon = (trend) => {
    if (trend === 'improving')
        return '📈';
    if (trend === 'declining')
        return '📉';
    return '➡️';
};
const formatPeriod = (month) => {
    const date = new Date(month + '-01');
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};
const formatMonth = (month) => {
    const date = new Date(month + '-01');
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};
const filteredMetrics = (metrics) => {
    if (selectedMetric.value === 'all') {
        return metrics;
    }
    return selectedMetric.value in metrics ? { [selectedMetric.value]: metrics[selectedMetric.value] } : {};
};
const getMetricWidth = (percentage) => {
    const base = 50; // Base width for 0%
    const scale = Math.min(Math.abs(percentage), 50); // Cap at 50 units
    const width = base + (percentage > 0 ? scale : -scale);
    return `${Math.max(0, width)}%`;
};
const __VLS_defaults = {
    monthsToAnalyze: 6,
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
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
/** @type {__VLS_StyleScopedClasses['improving']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
/** @type {__VLS_StyleScopedClasses['declining']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
/** @type {__VLS_StyleScopedClasses['stable']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-metric']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-trend']} */ ;
/** @type {__VLS_StyleScopedClasses['improving']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-trend']} */ ;
/** @type {__VLS_StyleScopedClasses['declining']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-trend']} */ ;
/** @type {__VLS_StyleScopedClasses['stable']} */ ;
/** @type {__VLS_StyleScopedClasses['widget-header']} */ ;
/** @type {__VLS_StyleScopedClasses['header-controls']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['latest-metrics']} */ ;
/** @type {__VLS_StyleScopedClasses['details-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "improvement-widget" },
});
/** @type {__VLS_StyleScopedClasses['improvement-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "widget-header" },
});
/** @type {__VLS_StyleScopedClasses['widget-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "widget-title" },
});
/** @type {__VLS_StyleScopedClasses['widget-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-controls" },
});
/** @type {__VLS_StyleScopedClasses['header-controls']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.selectedMetric),
    ...{ class: "metric-select" },
});
/** @type {__VLS_StyleScopedClasses['metric-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "all",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "batting_average",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "strike_rate",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "consistency",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "dismissal_rate",
});
if (__VLS_ctx.summaryData) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: (['trend-badge', __VLS_ctx.summaryData.overall_trend]) },
    });
    /** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
    (__VLS_ctx.summaryData.overall_trend);
}
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
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error-message" },
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    (__VLS_ctx.error);
}
else if (__VLS_ctx.summaryData) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "improvement-content" },
    });
    /** @type {__VLS_StyleScopedClasses['improvement-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-section" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-card" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.summaryData.improvement_score);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.summaryData.months_analyzed);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.formatRole(__VLS_ctx.summaryData.latest_stats.role));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "latest-metrics" },
    });
    /** @type {__VLS_StyleScopedClasses['latest-metrics']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-item" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-name" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.summaryData.latest_stats.batting_average);
    if (__VLS_ctx.summaryData.latest_improvements.batting_average) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-change" },
            ...{ class: (__VLS_ctx.summaryData.latest_improvements.batting_average.trend) },
        });
        /** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
        (__VLS_ctx.showTrendIcon(__VLS_ctx.summaryData.latest_improvements.batting_average.trend));
        (__VLS_ctx.summaryData.latest_improvements.batting_average.percentage_change);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-item" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-name" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.summaryData.latest_stats.strike_rate);
    if (__VLS_ctx.summaryData.latest_improvements.strike_rate) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-change" },
            ...{ class: (__VLS_ctx.summaryData.latest_improvements.strike_rate.trend) },
        });
        /** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
        (__VLS_ctx.showTrendIcon(__VLS_ctx.summaryData.latest_improvements.strike_rate.trend));
        (__VLS_ctx.summaryData.latest_improvements.strike_rate.percentage_change);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "metric-item" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-name" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "metric-value" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
    (__VLS_ctx.summaryData.latest_stats.consistency_score);
    if (__VLS_ctx.summaryData.latest_improvements.consistency) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-change" },
            ...{ class: (__VLS_ctx.summaryData.latest_improvements.consistency.trend) },
        });
        /** @type {__VLS_StyleScopedClasses['metric-change']} */ ;
        (__VLS_ctx.showTrendIcon(__VLS_ctx.summaryData.latest_improvements.consistency.trend));
        (__VLS_ctx.summaryData.latest_improvements.consistency.percentage_change);
    }
    if (__VLS_ctx.summaryData.highlights && __VLS_ctx.summaryData.highlights.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "highlights-section" },
        });
        /** @type {__VLS_StyleScopedClasses['highlights-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "section-title" },
        });
        /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "highlights-list" },
        });
        /** @type {__VLS_StyleScopedClasses['highlights-list']} */ ;
        for (const [highlight, idx] of __VLS_vFor((__VLS_ctx.summaryData.highlights))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "highlight-item" },
            });
            /** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
            (highlight);
            // @ts-ignore
            [selectedMetric, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, summaryData, loading, error, error, formatRole, showTrendIcon, showTrendIcon, showTrendIcon,];
        }
    }
    if (__VLS_ctx.summaryData.historical_improvements && __VLS_ctx.summaryData.historical_improvements.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "trends-section" },
        });
        /** @type {__VLS_StyleScopedClasses['trends-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "section-title" },
        });
        /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "trends-timeline" },
        });
        /** @type {__VLS_StyleScopedClasses['trends-timeline']} */ ;
        for (const [period, idx] of __VLS_vFor((__VLS_ctx.summaryData.historical_improvements))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "trend-card" },
            });
            /** @type {__VLS_StyleScopedClasses['trend-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "trend-header" },
            });
            /** @type {__VLS_StyleScopedClasses['trend-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "period-label" },
            });
            /** @type {__VLS_StyleScopedClasses['period-label']} */ ;
            (__VLS_ctx.formatPeriod(period.from_month));
            (__VLS_ctx.formatPeriod(period.to_month));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "trend-metrics" },
            });
            /** @type {__VLS_StyleScopedClasses['trend-metrics']} */ ;
            for (const [metric, metricName] of __VLS_vFor((__VLS_ctx.filteredMetrics(period.metrics)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (metricName),
                    ...{ class: "trend-metric" },
                });
                /** @type {__VLS_StyleScopedClasses['trend-metric']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "metric-name" },
                });
                /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
                (metric.metric_name);
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "metric-bar" },
                });
                /** @type {__VLS_StyleScopedClasses['metric-bar']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: (['metric-trend', metric.trend]) },
                    ...{ style: ({ width: __VLS_ctx.getMetricWidth(metric.percentage_change) }) },
                });
                /** @type {__VLS_StyleScopedClasses['metric-trend']} */ ;
                (metric.percentage_change);
                // @ts-ignore
                [summaryData, summaryData, summaryData, formatPeriod, formatPeriod, filteredMetrics, getMetricWidth,];
            }
            // @ts-ignore
            [];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "details-section" },
    });
    /** @type {__VLS_StyleScopedClasses['details-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "details-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['details-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "detail-item" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-label" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-value" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
    (__VLS_ctx.summaryData.latest_stats.matches_played);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "detail-item" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-label" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-value" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
    (__VLS_ctx.summaryData.latest_stats.innings_played);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "detail-item" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-label" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "detail-value" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
    (__VLS_ctx.formatMonth(__VLS_ctx.summaryData.latest_month));
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[summaryData, summaryData, summaryData, formatMonth,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
