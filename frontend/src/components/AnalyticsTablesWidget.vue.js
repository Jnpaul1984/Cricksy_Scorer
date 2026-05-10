/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
const props = defineProps();
const activeChart = ref('manhattan');
const hoverDelivery = ref(null);
const hoverWormBall = ref(null);
const hoverScatterMatch = ref(null);
// Chart type options
const chartTypes = [
    { id: 'manhattan', label: '📊 Manhattan', description: 'Runs per delivery' },
    { id: 'worm', label: '🐛 Worm', description: 'Cumulative progression' },
    { id: 'scatter', label: '⚡ Scatter', description: 'Strike rate analysis' },
];
// Delivery data - NO FAKE DATA
// Required: GET /games/{id}/deliveries with proper aggregation
const manhattan = ref([]);
// Worm chart data (cumulative)
const wormChartWidth = 600;
const wormChartHeight = 250;
const maxRuns = computed(() => {
    const total = manhattan.value.reduce((sum, d) => sum + d.runs, 0);
    return Math.ceil(total / 10) * 10;
});
const wormPoints = computed(() => {
    let cumulativeRuns = 0;
    return manhattan.value.map((delivery, idx) => {
        cumulativeRuns += delivery.runs;
        const x = ((idx + 1) / manhattan.value.length) * wormChartWidth;
        const y = wormChartHeight - (cumulativeRuns / maxRuns.value) * wormChartHeight * 0.85;
        return {
            x,
            y,
            cumulativeRuns,
            deliveryType: delivery.type,
            isWicket: delivery.type === 'wicket',
        };
    });
});
const wormLinePoints = computed(() => {
    return wormPoints.value.map((p) => `${p.x},${p.y}`).join(' ');
});
const totalRuns = computed(() => manhattan.value.reduce((sum, d) => sum + d.runs, 0));
const totalDeliveries = computed(() => manhattan.value.length);
const totalWickets = computed(() => manhattan.value.filter((d) => d.type === 'wicket').length);
const runRate = computed(() => (totalRuns.value / totalDeliveries.value) * 6);
// Scatter chart dimensions (layout constants, not data)
const scatterWidth = 500;
const scatterHeight = 300;
// Scatter chart data - NO FAKE DATA
// Required: GET /games/{id}/deliveries aggregated by match
const scatterPoints = ref([]);
// Color mapping
function getRunColor(runs) {
    if (runs === 0)
        return '#6b7280'; // gray for dot
    if (runs === 1)
        return '#10b981'; // green for single
    if (runs === 2)
        return '#f59e0b'; // amber for double
    return '#ef4444'; // red for boundary/wicket
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
/** @type {__VLS_StyleScopedClasses['chart-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-info']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-info']} */ ;
/** @type {__VLS_StyleScopedClasses['delivery-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['worm-point']} */ ;
/** @type {__VLS_StyleScopedClasses['scatter-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['scatter-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['scatter-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['scatter-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics-controls']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['manhattan-plot']} */ ;
/** @type {__VLS_StyleScopedClasses['worm-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-legend']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-tables-widget" },
});
/** @type {__VLS_StyleScopedClasses['analytics-tables-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-header" },
});
/** @type {__VLS_StyleScopedClasses['analytics-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "analytics-title" },
});
/** @type {__VLS_StyleScopedClasses['analytics-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-controls" },
});
/** @type {__VLS_StyleScopedClasses['analytics-controls']} */ ;
for (const [chart] of __VLS_vFor((__VLS_ctx.chartTypes))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.activeChart = chart.id;
                // @ts-ignore
                [chartTypes, activeChart,];
            } },
        key: (chart.id),
        ...{ class: "chart-tab" },
        ...{ class: ({ active: __VLS_ctx.activeChart === chart.id }) },
        title: (chart.description),
    });
    /** @type {__VLS_StyleScopedClasses['chart-tab']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    (chart.label);
    // @ts-ignore
    [activeChart,];
}
if (__VLS_ctx.activeChart === 'manhattan') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-info" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "manhattan-plot" },
    });
    /** @type {__VLS_StyleScopedClasses['manhattan-plot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "manhattan-axis-y" },
    });
    /** @type {__VLS_StyleScopedClasses['manhattan-axis-y']} */ ;
    for (const [i] of __VLS_vFor((5))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            key: (`y-${i}`),
            ...{ class: "y-label" },
        });
        /** @type {__VLS_StyleScopedClasses['y-label']} */ ;
        ((5 - i) * 2);
        // @ts-ignore
        [activeChart,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "manhattan-area" },
    });
    /** @type {__VLS_StyleScopedClasses['manhattan-area']} */ ;
    for (const [delivery, idx] of __VLS_vFor((__VLS_ctx.manhattan))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`delivery-${idx}`),
            ...{ class: "delivery-bar-wrapper" },
        });
        /** @type {__VLS_StyleScopedClasses['delivery-bar-wrapper']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ onMouseenter: (...[$event]) => {
                    if (!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    __VLS_ctx.hoverDelivery = idx;
                    // @ts-ignore
                    [manhattan, hoverDelivery,];
                } },
            ...{ onMouseleave: (...[$event]) => {
                    if (!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    __VLS_ctx.hoverDelivery = null;
                    // @ts-ignore
                    [hoverDelivery,];
                } },
            ...{ class: "delivery-bar" },
            ...{ style: ({
                    height: (delivery.runs / 10) * 100 + '%',
                    backgroundColor: __VLS_ctx.getRunColor(delivery.runs),
                }) },
            title: (`Ball ${idx + 1}: ${delivery.runs} runs (${delivery.type})`),
        });
        /** @type {__VLS_StyleScopedClasses['delivery-bar']} */ ;
        if (__VLS_ctx.hoverDelivery === idx) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "hover-label" },
            });
            /** @type {__VLS_StyleScopedClasses['hover-label']} */ ;
            (delivery.runs);
        }
        // @ts-ignore
        [hoverDelivery, getRunColor,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "manhattan-axis-x" },
    });
    /** @type {__VLS_StyleScopedClasses['manhattan-axis-x']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-legend" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-legend']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
}
else if (__VLS_ctx.activeChart === 'worm') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-info" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "worm-chart-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['worm-chart-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        ...{ class: "worm-chart" },
        viewBox: (`0 0 ${__VLS_ctx.wormChartWidth} ${__VLS_ctx.wormChartHeight}`),
    });
    /** @type {__VLS_StyleScopedClasses['worm-chart']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
        ...{ class: "grid" },
    });
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    for (const [i] of __VLS_vFor((5))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
            key: (`grid-h-${i}`),
            x1: (0),
            y1: ((i / 5) * __VLS_ctx.wormChartHeight),
            x2: (__VLS_ctx.wormChartWidth),
            y2: ((i / 5) * __VLS_ctx.wormChartHeight),
            stroke: "#e5e7eb",
            'stroke-width': "1",
        });
        // @ts-ignore
        [activeChart, wormChartWidth, wormChartWidth, wormChartHeight, wormChartHeight, wormChartHeight,];
    }
    for (const [i] of __VLS_vFor((10))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
            key: (`grid-v-${i}`),
            x1: ((i / 10) * __VLS_ctx.wormChartWidth),
            y1: (0),
            x2: ((i / 10) * __VLS_ctx.wormChartWidth),
            y2: (__VLS_ctx.wormChartHeight),
            stroke: "#e5e7eb",
            'stroke-width': "1",
        });
        // @ts-ignore
        [wormChartWidth, wormChartWidth, wormChartHeight,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.polyline)({
        points: (__VLS_ctx.wormLinePoints),
        ...{ class: "worm-line" },
    });
    /** @type {__VLS_StyleScopedClasses['worm-line']} */ ;
    for (const [point, idx] of __VLS_vFor((__VLS_ctx.wormPoints))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            ...{ onMouseenter: (...[$event]) => {
                    if (!!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    if (!(__VLS_ctx.activeChart === 'worm'))
                        return;
                    __VLS_ctx.hoverWormBall = idx;
                    // @ts-ignore
                    [wormLinePoints, wormPoints, hoverWormBall,];
                } },
            ...{ onMouseleave: (...[$event]) => {
                    if (!!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    if (!(__VLS_ctx.activeChart === 'worm'))
                        return;
                    __VLS_ctx.hoverWormBall = null;
                    // @ts-ignore
                    [hoverWormBall,];
                } },
            key: (`point-${idx}`),
            cx: (point.x),
            cy: (point.y),
            r: "3",
            ...{ class: "worm-point" },
            ...{ class: ({ 'worm-point-wicket': point.isWicket }) },
            title: (`Ball ${idx + 1}: ${point.cumulativeRuns} runs (${point.deliveryType})`),
        });
        /** @type {__VLS_StyleScopedClasses['worm-point']} */ ;
        /** @type {__VLS_StyleScopedClasses['worm-point-wicket']} */ ;
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.hoverWormBall !== null) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
            ...{ class: "hover-info" },
        });
        /** @type {__VLS_StyleScopedClasses['hover-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: (__VLS_ctx.wormPoints[__VLS_ctx.hoverWormBall].x),
            cy: (__VLS_ctx.wormPoints[__VLS_ctx.hoverWormBall].y),
            r: "5",
            fill: "none",
            stroke: "#3b82f6",
            'stroke-width': "2",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: (__VLS_ctx.wormPoints[__VLS_ctx.hoverWormBall].x),
            y: (__VLS_ctx.wormPoints[__VLS_ctx.hoverWormBall].y - 15),
            'text-anchor': "middle",
            ...{ class: "worm-hover-text" },
        });
        /** @type {__VLS_StyleScopedClasses['worm-hover-text']} */ ;
        (__VLS_ctx.wormPoints[__VLS_ctx.hoverWormBall].cumulativeRuns);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: "10",
        y: "20",
        ...{ class: "axis-label" },
    });
    /** @type {__VLS_StyleScopedClasses['axis-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (__VLS_ctx.wormChartWidth - 50),
        y: (__VLS_ctx.wormChartHeight - 5),
        ...{ class: "axis-label" },
    });
    /** @type {__VLS_StyleScopedClasses['axis-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "worm-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['worm-stats']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.totalRuns);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.totalDeliveries);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.runRate.toFixed(2));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.totalWickets);
}
else if (__VLS_ctx.activeChart === 'scatter') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-info" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "scatter-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['scatter-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        ...{ class: "scatter-chart" },
        viewBox: (`0 0 ${__VLS_ctx.scatterWidth} ${__VLS_ctx.scatterHeight}`),
    });
    /** @type {__VLS_StyleScopedClasses['scatter-chart']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
        ...{ class: "grid" },
    });
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    for (const [i] of __VLS_vFor((4))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
            key: (`sgrid-h-${i}`),
            x1: (0),
            y1: ((i / 4) * __VLS_ctx.scatterHeight),
            x2: (__VLS_ctx.scatterWidth),
            y2: ((i / 4) * __VLS_ctx.scatterHeight),
            stroke: "#e5e7eb",
            'stroke-width': "1",
        });
        // @ts-ignore
        [activeChart, wormChartWidth, wormChartHeight, wormPoints, wormPoints, wormPoints, wormPoints, wormPoints, hoverWormBall, hoverWormBall, hoverWormBall, hoverWormBall, hoverWormBall, hoverWormBall, totalRuns, totalDeliveries, runRate, totalWickets, scatterWidth, scatterWidth, scatterHeight, scatterHeight, scatterHeight,];
    }
    for (const [i] of __VLS_vFor((4))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
            key: (`sgrid-v-${i}`),
            x1: ((i / 4) * __VLS_ctx.scatterWidth),
            y1: (0),
            x2: ((i / 4) * __VLS_ctx.scatterWidth),
            y2: (__VLS_ctx.scatterHeight),
            stroke: "#e5e7eb",
            'stroke-width': "1",
        });
        // @ts-ignore
        [scatterWidth, scatterWidth, scatterHeight,];
    }
    for (const [point, idx] of __VLS_vFor((__VLS_ctx.scatterPoints))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            ...{ onMouseenter: (...[$event]) => {
                    if (!!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    if (!!(__VLS_ctx.activeChart === 'worm'))
                        return;
                    if (!(__VLS_ctx.activeChart === 'scatter'))
                        return;
                    __VLS_ctx.hoverScatterMatch = idx;
                    // @ts-ignore
                    [scatterPoints, hoverScatterMatch,];
                } },
            ...{ onMouseleave: (...[$event]) => {
                    if (!!(__VLS_ctx.activeChart === 'manhattan'))
                        return;
                    if (!!(__VLS_ctx.activeChart === 'worm'))
                        return;
                    if (!(__VLS_ctx.activeChart === 'scatter'))
                        return;
                    __VLS_ctx.hoverScatterMatch = null;
                    // @ts-ignore
                    [hoverScatterMatch,];
                } },
            key: (`scatter-${idx}`),
            cx: (point.x),
            cy: (point.y),
            r: (4),
            ...{ class: (['scatter-dot', point.colorClass]) },
            title: (`Match ${idx + 1}: ${point.balls} balls, ${point.runs} runs (SR: ${point.sr.toFixed(0)})`),
        });
        /** @type {__VLS_StyleScopedClasses['scatter-dot']} */ ;
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.hoverScatterMatch !== null) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
            ...{ class: "scatter-hover" },
        });
        /** @type {__VLS_StyleScopedClasses['scatter-hover']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: (__VLS_ctx.scatterPoints[__VLS_ctx.hoverScatterMatch].x),
            cy: (__VLS_ctx.scatterPoints[__VLS_ctx.hoverScatterMatch].y),
            r: "6",
            fill: "none",
            stroke: "#3b82f6",
            'stroke-width': "2",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: (__VLS_ctx.scatterPoints[__VLS_ctx.hoverScatterMatch].x),
            y: (__VLS_ctx.scatterPoints[__VLS_ctx.hoverScatterMatch].y - 15),
            'text-anchor': "middle",
            ...{ class: "scatter-hover-text" },
        });
        /** @type {__VLS_StyleScopedClasses['scatter-hover-text']} */ ;
        (__VLS_ctx.scatterPoints[__VLS_ctx.hoverScatterMatch].sr.toFixed(0));
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: "10",
        y: "20",
        ...{ class: "axis-label" },
    });
    /** @type {__VLS_StyleScopedClasses['axis-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (__VLS_ctx.scatterWidth - 50),
        y: (__VLS_ctx.scatterHeight - 5),
        ...{ class: "axis-label" },
    });
    /** @type {__VLS_StyleScopedClasses['axis-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-legend" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-legend']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-dot" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['color-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
}
// @ts-ignore
[scatterWidth, scatterHeight, scatterPoints, scatterPoints, scatterPoints, scatterPoints, scatterPoints, hoverScatterMatch, hoverScatterMatch, hoverScatterMatch, hoverScatterMatch, hoverScatterMatch, hoverScatterMatch,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
