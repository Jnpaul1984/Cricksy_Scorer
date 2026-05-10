/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, } from 'chart.js';
import { computed } from 'vue';
import { Line } from 'vue-chartjs';
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);
const props = defineProps();
const runRateHistory = computed(() => {
    if (!props.oversData || props.oversData.length === 0) {
        // Calculate run rate over the current innings
        const data = [];
        const completedOvers = Math.floor(props.ballsBowled / 6);
        if (completedOvers === 0) {
            return data;
        }
        // For each over, calculate cumulative run rate
        // Run rate = total runs / total overs at that point
        for (let i = 1; i <= completedOvers; i++) {
            const runRate = (props.currentScore / i);
            data.push({ over: i, runRate });
        }
        return data;
    }
    return props.oversData;
});
const chartData = computed(() => {
    const labels = runRateHistory.value.map(d => `Over ${d.over}`);
    const datasets = [];
    // Current run rate line
    datasets.push({
        label: 'Current Run Rate',
        data: runRateHistory.value.map(d => d.runRate),
        borderColor: '#2563eb',
        backgroundColor: '#2563eb',
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        fill: false,
    });
    // Required run rate line (if chasing)
    if (props.requiredRunRate != null && props.requiredRunRate > 0) {
        const rrr = props.requiredRunRate;
        datasets.push({
            label: 'Required Run Rate',
            data: runRateHistory.value.map(() => rrr),
            borderColor: '#f97316',
            backgroundColor: '#f97316',
            borderDash: [5, 5],
            pointRadius: 0,
            pointHoverRadius: 3,
            fill: false,
        });
    }
    return {
        labels,
        datasets,
    };
});
const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                padding: 12,
                usePointStyle: true,
            }
        },
        tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: {
                size: 14,
                weight: 'bold',
            },
            bodyFont: {
                size: 13,
            },
            callbacks: {
                label: function (context) {
                    const label = context.dataset.label || '';
                    const value = context.parsed.y ?? 0;
                    return `${label}: ${value.toFixed(2)} rpo`;
                }
            }
        },
        title: {
            display: true,
            text: 'Run Rate Comparison',
            font: {
                size: 16,
                weight: 'bold',
            }
        }
    },
    scales: {
        x: {
            display: true,
            grid: {
                display: true,
                color: 'rgba(0, 0, 0, 0.05)',
            },
            title: {
                display: true,
                text: 'Overs',
            }
        },
        y: {
            beginAtZero: true,
            title: {
                display: true,
                text: 'Run Rate (runs per over)',
            },
            ticks: {
                precision: 1,
            }
        },
    },
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
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "run-rate-comparison" },
});
/** @type {__VLS_StyleScopedClasses['run-rate-comparison']} */ ;
if (__VLS_ctx.runRateHistory.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart" },
    });
    /** @type {__VLS_StyleScopedClasses['chart']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.Line} */
    Line;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.options),
    }));
    const __VLS_2 = __VLS_1({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.options),
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stats-summary" },
});
/** @type {__VLS_StyleScopedClasses['stats-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-item" },
});
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value current" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['current']} */ ;
(__VLS_ctx.currentRunRate.toFixed(2));
if (__VLS_ctx.requiredRunRate != null && __VLS_ctx.requiredRunRate > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-item" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value required" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    /** @type {__VLS_StyleScopedClasses['required']} */ ;
    (__VLS_ctx.requiredRunRate.toFixed(2));
}
if (__VLS_ctx.requiredRunRate != null && __VLS_ctx.requiredRunRate > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-item" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
        ...{ class: (__VLS_ctx.currentRunRate >= __VLS_ctx.requiredRunRate ? 'ahead' : 'behind') },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (Math.abs(__VLS_ctx.currentRunRate - __VLS_ctx.requiredRunRate).toFixed(2));
    (__VLS_ctx.currentRunRate >= __VLS_ctx.requiredRunRate ? '(ahead)' : '(behind)');
}
// @ts-ignore
[runRateHistory, chartData, options, currentRunRate, currentRunRate, currentRunRate, currentRunRate, requiredRunRate, requiredRunRate, requiredRunRate, requiredRunRate, requiredRunRate, requiredRunRate, requiredRunRate, requiredRunRate,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
