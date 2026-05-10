/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, } from 'chart.js';
import { ref, computed, onMounted } from 'vue';
import { Line } from 'vue-chartjs';
import { compareJobs } from '@/services/coachPlusVideoService';
// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);
const props = defineProps();
// State
const loading = ref(false);
const error = ref(null);
const comparisonData = ref(null);
// Computed: Flatten all improvements from deltas
const allImprovements = computed(() => {
    if (!comparisonData.value?.deltas)
        return [];
    return comparisonData.value.deltas.flatMap((d) => d.improvements);
});
// Computed: Flatten all regressions from deltas
const allRegressions = computed(() => {
    if (!comparisonData.value?.deltas)
        return [];
    return comparisonData.value.deltas.flatMap((d) => d.regressions);
});
// Computed: Chart data for timeline
const chartData = computed(() => {
    if (!comparisonData.value?.timeline) {
        return {
            labels: [],
            datasets: [],
        };
    }
    const timeline = comparisonData.value.timeline;
    const labels = timeline.map((point, idx) => `Job ${idx + 1}`);
    // Extract unique metric codes
    const metricCodes = new Set();
    timeline.forEach((point) => {
        Object.keys(point.metric_scores).forEach((code) => metricCodes.add(code));
    });
    // Generate color palette
    const colors = [
        '#3498db',
        '#e74c3c',
        '#2ecc71',
        '#f39c12',
        '#9b59b6',
        '#1abc9c',
        '#34495e',
        '#e67e22',
    ];
    // Create dataset for each metric
    const datasets = Array.from(metricCodes).map((code, index) => {
        const color = colors[index % colors.length];
        return {
            label: code.replace(/_/g, ' '),
            data: timeline.map((point) => (point.metric_scores[code] !== undefined ? point.metric_scores[code] * 100 : null)),
            borderColor: color,
            backgroundColor: color + '33', // Add transparency
            tension: 0.3,
            fill: false,
        };
    });
    return {
        labels,
        datasets,
    };
});
// Computed: Chart options
const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
        },
        title: {
            display: true,
            text: 'Metric Scores Over Time',
        },
        tooltip: {
            callbacks: {
                label: (context) => {
                    const label = context.dataset.label || '';
                    const value = context.parsed.y !== null ? context.parsed.y.toFixed(1) + '%' : 'N/A';
                    return `${label}: ${value}`;
                },
            },
        },
    },
    scales: {
        y: {
            min: 0,
            max: 100,
            ticks: {
                callback: (value) => value + '%',
            },
            title: {
                display: true,
                text: 'Score (%)',
            },
        },
        x: {
            title: {
                display: true,
                text: 'Session',
            },
        },
    },
}));
// Computed: Check if there are significant changes
const hasSignificantChanges = computed(() => {
    if (!comparisonData.value)
        return false;
    return (allImprovements.value.length > 0 ||
        allRegressions.value.length > 0 ||
        comparisonData.value.persistent_issues.length > 0);
});
// Methods
async function fetchComparison() {
    loading.value = true;
    error.value = null;
    try {
        const response = await compareJobs(props.sessionId, props.selectedJobIds);
        comparisonData.value = response;
    }
    catch (err) {
        error.value = err.message || 'Failed to load comparison data';
    }
    finally {
        loading.value = false;
    }
}
// Lifecycle
onMounted(() => {
    if (props.selectedJobIds.length >= 2) {
        fetchComparison();
    }
    else {
        error.value = 'Please select at least 2 sessions to compare';
    }
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
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['comparison-results']} */ ;
/** @type {__VLS_StyleScopedClasses['comparison-results']} */ ;
/** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
/** @type {__VLS_StyleScopedClasses['delta']} */ ;
/** @type {__VLS_StyleScopedClasses['delta']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['no-changes']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "session-comparison" },
});
/** @type {__VLS_StyleScopedClasses['session-comparison']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
(__VLS_ctx.selectedJobIds.length);
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading" },
    });
    /** @type {__VLS_StyleScopedClasses['loading']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
}
if (!__VLS_ctx.loading && !__VLS_ctx.error && __VLS_ctx.comparisonData) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "comparison-results" },
    });
    /** @type {__VLS_StyleScopedClasses['comparison-results']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "timeline-section" },
    });
    /** @type {__VLS_StyleScopedClasses['timeline-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.Line} */
    Line;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.chartOptions),
    }));
    const __VLS_2 = __VLS_1({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.chartOptions),
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    if (__VLS_ctx.allImprovements.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "improvements-section" },
        });
        /** @type {__VLS_StyleScopedClasses['improvements-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "delta-table" },
        });
        /** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [improvement, idx] of __VLS_vFor((__VLS_ctx.allImprovements))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (idx),
                ...{ class: "improvement-row" },
            });
            /** @type {__VLS_StyleScopedClasses['improvement-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "metric-name" },
            });
            /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
            (improvement.code);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "from-session" },
            });
            /** @type {__VLS_StyleScopedClasses['from-session']} */ ;
            ((improvement.from_score * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "to-session" },
            });
            /** @type {__VLS_StyleScopedClasses['to-session']} */ ;
            ((improvement.to_score * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "delta positive" },
            });
            /** @type {__VLS_StyleScopedClasses['delta']} */ ;
            /** @type {__VLS_StyleScopedClasses['positive']} */ ;
            ((improvement.delta * 100).toFixed(0));
            // @ts-ignore
            [selectedJobIds, loading, loading, error, error, error, comparisonData, chartData, chartOptions, allImprovements, allImprovements,];
        }
    }
    if (__VLS_ctx.allRegressions.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "regressions-section" },
        });
        /** @type {__VLS_StyleScopedClasses['regressions-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "delta-table" },
        });
        /** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [regression, idx] of __VLS_vFor((__VLS_ctx.allRegressions))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (idx),
                ...{ class: "regression-row" },
            });
            /** @type {__VLS_StyleScopedClasses['regression-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "metric-name" },
            });
            /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
            (regression.code);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "from-session" },
            });
            /** @type {__VLS_StyleScopedClasses['from-session']} */ ;
            ((regression.from_score * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "to-session" },
            });
            /** @type {__VLS_StyleScopedClasses['to-session']} */ ;
            ((regression.to_score * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "delta negative" },
            });
            /** @type {__VLS_StyleScopedClasses['delta']} */ ;
            /** @type {__VLS_StyleScopedClasses['negative']} */ ;
            ((regression.delta * 100).toFixed(0));
            // @ts-ignore
            [allRegressions, allRegressions,];
        }
    }
    if (__VLS_ctx.comparisonData.persistent_issues.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "persistent-issues-section" },
        });
        /** @type {__VLS_StyleScopedClasses['persistent-issues-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "delta-table" },
        });
        /** @type {__VLS_StyleScopedClasses['delta-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [issue] of __VLS_vFor((__VLS_ctx.comparisonData.persistent_issues))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (issue.code),
                ...{ class: "issue-row" },
            });
            /** @type {__VLS_StyleScopedClasses['issue-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "metric-name" },
            });
            /** @type {__VLS_StyleScopedClasses['metric-name']} */ ;
            (issue.title);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "avg-score" },
            });
            /** @type {__VLS_StyleScopedClasses['avg-score']} */ ;
            ((issue.avg_score * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "sessions-count" },
            });
            /** @type {__VLS_StyleScopedClasses['sessions-count']} */ ;
            (issue.occurrences);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "trend" },
            });
            /** @type {__VLS_StyleScopedClasses['trend']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: (['trend-badge', issue.trend]) },
            });
            /** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
            (issue.trend);
            // @ts-ignore
            [comparisonData, comparisonData,];
        }
    }
    if (!__VLS_ctx.hasSignificantChanges) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "no-changes" },
        });
        /** @type {__VLS_StyleScopedClasses['no-changes']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
// @ts-ignore
[hasSignificantChanges,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
