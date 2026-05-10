/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler, } from 'chart.js';
import { ref, computed } from 'vue';
import { Line, Bar } from 'vue-chartjs';
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler);
const props = defineProps();
const activeStat = ref('runs');
// Format stat with fallback
const formatStat = (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value))
        return '—';
    return value.toFixed(decimals);
};
const matchData = computed(() => {
    // Return empty array - data must come from backend
    return [];
});
// Cumulative runs chart
const cumulativeRunsChart = computed(() => {
    if (matchData.value.length === 0)
        return null;
    let cumulative = 0;
    const labels = matchData.value.map((m) => `M${m.matchNum}`);
    const data = matchData.value.map((m) => {
        cumulative += m.runs;
        return cumulative;
    });
    return {
        data: {
            labels,
            datasets: [
                {
                    label: 'Cumulative Runs',
                    data,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { font: { size: 12 } } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 11 } } },
            },
        },
    };
});
// Runs per innings chart
const runsPerInningsChart = computed(() => {
    if (matchData.value.length === 0)
        return null;
    const labels = matchData.value.map((m) => `M${m.matchNum}`);
    const data = matchData.value.map((m) => m.runs);
    return {
        data: {
            labels,
            datasets: [
                {
                    label: 'Runs per Innings',
                    data,
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { font: { size: 12 } } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 11 } } },
            },
        },
    };
});
// Cumulative wickets chart
const cumulativeWicketsChart = computed(() => {
    if (matchData.value.length === 0)
        return null;
    let cumulative = 0;
    const labels = matchData.value.map((m) => `M${m.matchNum}`);
    const data = matchData.value.map((m) => {
        cumulative += m.wickets;
        return cumulative;
    });
    return {
        data: {
            labels,
            datasets: [
                {
                    label: 'Cumulative Wickets',
                    data,
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { font: { size: 12 } } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 11 } } },
            },
        },
    };
});
// Wickets per innings chart
const wicketsPerInningsChart = computed(() => {
    if (matchData.value.length === 0)
        return null;
    const labels = matchData.value.map((m) => `M${m.matchNum}`);
    const data = matchData.value.map((m) => m.wickets);
    return {
        data: {
            labels,
            datasets: [
                {
                    label: 'Wickets per Innings',
                    data,
                    backgroundColor: 'rgba(249, 115, 22, 0.7)',
                    borderColor: 'rgb(249, 115, 22)',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { font: { size: 12 } } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 11 } } },
            },
        },
    };
});
// Rolling average chart
const rollingAverageChart = computed(() => {
    if (matchData.value.length < 5)
        return null;
    const labels = [];
    const data = [];
    for (let i = 4; i < matchData.value.length; i++) {
        const window = matchData.value.slice(i - 4, i + 1);
        const avg = window.reduce((sum, m) => sum + m.runs, 0) / window.length;
        labels.push(`M${matchData.value[i].matchNum}`);
        data.push(Math.round(avg * 10) / 10);
    }
    return {
        data: {
            labels,
            datasets: [
                {
                    label: 'Rolling Average (5-match)',
                    data,
                    borderColor: 'rgb(168, 85, 247)',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { font: { size: 12 } } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { font: { size: 11 } } },
                x: { ticks: { font: { size: 11 } } },
            },
        },
    };
});
// Peak performance
const peakMatch = computed(() => {
    if (matchData.value.length === 0)
        return '—';
    const max = matchData.value.reduce((prev, current) => (prev.runs > current.runs ? prev : current));
    return `${max.runs} runs (Match ${max.matchNum})`;
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
/** @type {__VLS_StyleScopedClasses['stat-tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['season-graphs-header']} */ ;
/** @type {__VLS_StyleScopedClasses['season-controls']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
/** @type {__VLS_StyleScopedClasses['season-highlights']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "season-graphs-widget" },
});
/** @type {__VLS_StyleScopedClasses['season-graphs-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "season-graphs-header" },
});
/** @type {__VLS_StyleScopedClasses['season-graphs-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "season-graphs-title" },
});
/** @type {__VLS_StyleScopedClasses['season-graphs-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "season-controls" },
});
/** @type {__VLS_StyleScopedClasses['season-controls']} */ ;
for (const [stat] of __VLS_vFor((['runs', 'wickets', 'average']))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.activeStat = stat;
                // @ts-ignore
                [activeStat,];
            } },
        key: (stat),
        ...{ class: "stat-tab-btn" },
        ...{ class: ({ active: __VLS_ctx.activeStat === stat }) },
    });
    /** @type {__VLS_StyleScopedClasses['stat-tab-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    (stat === 'runs' ? '🏃 Runs' : stat === 'wickets' ? '⚾ Wickets' : '📈 Average');
    // @ts-ignore
    [activeStat,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "charts-container" },
});
/** @type {__VLS_StyleScopedClasses['charts-container']} */ ;
if (__VLS_ctx.activeStat === 'runs') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-section" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.cumulativeRunsChart) {
        let __VLS_0;
        /** @ts-ignore @type { | typeof __VLS_components.Line} */
        Line;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
            data: (__VLS_ctx.cumulativeRunsChart.data),
            options: (__VLS_ctx.cumulativeRunsChart.options),
        }));
        const __VLS_2 = __VLS_1({
            data: (__VLS_ctx.cumulativeRunsChart.data),
            options: (__VLS_ctx.cumulativeRunsChart.options),
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.runsPerInningsChart) {
        let __VLS_5;
        /** @ts-ignore @type { | typeof __VLS_components.Bar} */
        Bar;
        // @ts-ignore
        const __VLS_6 = __VLS_asFunctionalComponent1(__VLS_5, new __VLS_5({
            data: (__VLS_ctx.runsPerInningsChart.data),
            options: (__VLS_ctx.runsPerInningsChart.options),
        }));
        const __VLS_7 = __VLS_6({
            data: (__VLS_ctx.runsPerInningsChart.data),
            options: (__VLS_ctx.runsPerInningsChart.options),
        }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    }
}
if (__VLS_ctx.activeStat === 'wickets') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-section" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.cumulativeWicketsChart) {
        let __VLS_10;
        /** @ts-ignore @type { | typeof __VLS_components.Line} */
        Line;
        // @ts-ignore
        const __VLS_11 = __VLS_asFunctionalComponent1(__VLS_10, new __VLS_10({
            data: (__VLS_ctx.cumulativeWicketsChart.data),
            options: (__VLS_ctx.cumulativeWicketsChart.options),
        }));
        const __VLS_12 = __VLS_11({
            data: (__VLS_ctx.cumulativeWicketsChart.data),
            options: (__VLS_ctx.cumulativeWicketsChart.options),
        }, ...__VLS_functionalComponentArgsRest(__VLS_11));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.wicketsPerInningsChart) {
        let __VLS_15;
        /** @ts-ignore @type { | typeof __VLS_components.Bar} */
        Bar;
        // @ts-ignore
        const __VLS_16 = __VLS_asFunctionalComponent1(__VLS_15, new __VLS_15({
            data: (__VLS_ctx.wicketsPerInningsChart.data),
            options: (__VLS_ctx.wicketsPerInningsChart.options),
        }));
        const __VLS_17 = __VLS_16({
            data: (__VLS_ctx.wicketsPerInningsChart.data),
            options: (__VLS_ctx.wicketsPerInningsChart.options),
        }, ...__VLS_functionalComponentArgsRest(__VLS_16));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    }
}
if (__VLS_ctx.activeStat === 'average') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-section" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-wrapper full-width" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-wrapper']} */ ;
    /** @type {__VLS_StyleScopedClasses['full-width']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.rollingAverageChart) {
        let __VLS_20;
        /** @ts-ignore @type { | typeof __VLS_components.Line} */
        Line;
        // @ts-ignore
        const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
            data: (__VLS_ctx.rollingAverageChart.data),
            options: (__VLS_ctx.rollingAverageChart.options),
        }));
        const __VLS_22 = __VLS_21({
            data: (__VLS_ctx.rollingAverageChart.data),
            options: (__VLS_ctx.rollingAverageChart.options),
        }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "season-highlights" },
});
/** @type {__VLS_StyleScopedClasses['season-highlights']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "highlight-item" },
});
/** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-label" },
});
/** @type {__VLS_StyleScopedClasses['highlight-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-value" },
});
/** @type {__VLS_StyleScopedClasses['highlight-value']} */ ;
(__VLS_ctx.peakMatch);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "highlight-item" },
});
/** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-label" },
});
/** @type {__VLS_StyleScopedClasses['highlight-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-value" },
});
/** @type {__VLS_StyleScopedClasses['highlight-value']} */ ;
(__VLS_ctx.profile?.total_matches || 0);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "highlight-item" },
});
/** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-label" },
});
/** @type {__VLS_StyleScopedClasses['highlight-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-value" },
});
/** @type {__VLS_StyleScopedClasses['highlight-value']} */ ;
(__VLS_ctx.formatStat(__VLS_ctx.profile?.batting_average));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "highlight-item" },
});
/** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-label" },
});
/** @type {__VLS_StyleScopedClasses['highlight-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "highlight-value" },
});
/** @type {__VLS_StyleScopedClasses['highlight-value']} */ ;
(__VLS_ctx.formatStat(__VLS_ctx.profile?.strike_rate));
// @ts-ignore
[activeStat, activeStat, activeStat, cumulativeRunsChart, cumulativeRunsChart, cumulativeRunsChart, runsPerInningsChart, runsPerInningsChart, runsPerInningsChart, cumulativeWicketsChart, cumulativeWicketsChart, cumulativeWicketsChart, wicketsPerInningsChart, wicketsPerInningsChart, wicketsPerInningsChart, rollingAverageChart, rollingAverageChart, rollingAverageChart, peakMatch, profile, profile, profile, formatStat, formatStat,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
