/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler, } from 'chart.js';
import { computed, ref, watch } from 'vue';
import { Line } from 'vue-chartjs';
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);
const props = withDefaults(defineProps(), {
    battingTeam: undefined,
    bowlingTeam: undefined,
    theme: 'dark',
});
// Store history of predictions
const predictionHistory = ref([]);
watch(() => props.currentPrediction, (newPred) => {
    if (newPred && newPred.confidence > 0) {
        // For now, use a simple counter for overs (in real scenario, get from game state)
        const over = `${predictionHistory.value.length + 1}`;
        predictionHistory.value.push({
            over,
            battingProb: newPred.batting_team_win_prob,
            bowlingProb: newPred.bowling_team_win_prob,
        });
        // Keep only last 50 data points
        if (predictionHistory.value.length > 50) {
            predictionHistory.value.shift();
        }
    }
}, { deep: true });
const chartData = computed(() => {
    const labels = predictionHistory.value.map((p) => p.over);
    return {
        labels,
        datasets: [
            {
                label: props.battingTeam || 'Batting Team',
                data: predictionHistory.value.map((p) => p.battingProb),
                borderColor: props.theme === 'dark' ? '#4ade80' : '#22c55e',
                backgroundColor: props.theme === 'dark' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 5,
            },
            {
                label: props.bowlingTeam || 'Bowling Team',
                data: predictionHistory.value.map((p) => p.bowlingProb),
                borderColor: props.theme === 'dark' ? '#f87171' : '#ef4444',
                backgroundColor: props.theme === 'dark' ? 'rgba(248, 113, 113, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 5,
            },
        ],
    };
});
const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            display: true,
            position: 'top',
            labels: {
                color: props.theme === 'dark' ? '#e5e7eb' : '#374151',
                font: {
                    size: 12,
                },
            },
        },
        title: {
            display: false,
        },
        tooltip: {
            backgroundColor: props.theme === 'dark' ? '#1f2937' : '#ffffff',
            titleColor: props.theme === 'dark' ? '#f3f4f6' : '#111827',
            bodyColor: props.theme === 'dark' ? '#e5e7eb' : '#374151',
            borderColor: props.theme === 'dark' ? '#374151' : '#e5e7eb',
            borderWidth: 1,
            callbacks: {
                label: function (context) {
                    const yValue = context.parsed?.y;
                    if (typeof yValue !== 'number') {
                        return context.dataset.label ?? '';
                    }
                    const label = context.dataset.label ?? 'Value';
                    return `${label}: ${yValue.toFixed(1)}%`;
                },
            },
        },
    },
    scales: {
        x: {
            display: true,
            title: {
                display: true,
                text: 'Progress',
                color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
            },
            ticks: {
                color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
            },
            grid: {
                color: props.theme === 'dark' ? '#374151' : '#e5e7eb',
            },
        },
        y: {
            display: true,
            min: 0,
            max: 100,
            title: {
                display: true,
                text: 'Win Probability (%)',
                color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
            },
            ticks: {
                color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
                callback: function (value) {
                    return value + '%';
                },
            },
            grid: {
                color: props.theme === 'dark' ? '#374151' : '#e5e7eb',
            },
        },
    },
}));
const __VLS_defaults = {
    battingTeam: undefined,
    bowlingTeam: undefined,
    theme: 'dark',
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
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "win-probability-chart" },
});
/** @type {__VLS_StyleScopedClasses['win-probability-chart']} */ ;
if (__VLS_ctx.currentPrediction && __VLS_ctx.currentPrediction.confidence > 0) {
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
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-data" },
    });
    /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[currentPrediction, currentPrediction, chartData, chartOptions,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
