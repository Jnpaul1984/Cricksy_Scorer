/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, } from 'chart.js';
import { computed } from 'vue';
import { Bar } from 'vue-chartjs';
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);
const props = defineProps();
const colors = ['#2563eb', '#f97316', '#22c55e', '#a855f7'];
const chartData = computed(() => ({
    labels: props.labels,
    datasets: props.series.map((s, idx) => ({
        label: s.label,
        data: s.data,
        backgroundColor: colors[idx % colors.length],
        borderRadius: 4,
    })),
}));
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
                    return `${label}: ${value} runs`;
                }
            }
        },
    },
    scales: {
        x: {
            stacked: false,
            grid: {
                display: false,
            }
        },
        y: {
            beginAtZero: true,
            title: {
                display: true,
                text: 'Runs per Over',
            },
            ticks: {
                precision: 0,
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
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "chart" },
});
/** @type {__VLS_StyleScopedClasses['chart']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Bar} */
Bar;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    data: (__VLS_ctx.chartData),
    options: (__VLS_ctx.options),
}));
const __VLS_2 = __VLS_1({
    data: (__VLS_ctx.chartData),
    options: (__VLS_ctx.options),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
// @ts-ignore
[chartData, options,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
