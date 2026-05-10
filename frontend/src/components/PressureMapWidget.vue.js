/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import Chart from 'chart.js/auto';
import { ref, onMounted, watch } from 'vue';
const props = withDefaults(defineProps(), {
    pressureData: null,
    loading: false
});
const activeView = ref('timeline');
const pressureChart = ref();
let chartInstance = null;
const getPressureClass = (score) => {
    if (!score)
        return 'low';
    if (score < 20)
        return 'low';
    if (score < 40)
        return 'moderate';
    if (score < 60)
        return 'building';
    if (score < 80)
        return 'high';
    return 'extreme';
};
const initChart = () => {
    if (!pressureChart.value || !props.pressureData?.pressure_points)
        return;
    // Destroy existing chart
    if (chartInstance) {
        chartInstance.destroy();
    }
    const pressureScores = props.pressureData.pressure_points.map(p => p.pressure_score);
    const deliveryLabels = props.pressureData.pressure_points.map(p => `Over ${p.over_num.toFixed(1)}`);
    // Color coding by pressure level
    const backgroundColors = pressureScores.map(score => {
        if (score < 20)
            return 'rgba(76, 175, 80, 0.6)'; // Green - Low
        if (score < 40)
            return 'rgba(255, 193, 7, 0.6)'; // Yellow - Moderate
        if (score < 60)
            return 'rgba(255, 152, 0, 0.6)'; // Orange - Building
        if (score < 80)
            return 'rgba(244, 67, 54, 0.6)'; // Red - High
        return 'rgba(156, 39, 176, 0.6)'; // Purple - Extreme
    });
    const borderColors = pressureScores.map(score => {
        if (score < 20)
            return 'rgba(76, 175, 80, 1)';
        if (score < 40)
            return 'rgba(255, 193, 7, 1)';
        if (score < 60)
            return 'rgba(255, 152, 0, 1)';
        if (score < 80)
            return 'rgba(244, 67, 54, 1)';
        return 'rgba(156, 39, 176, 1)';
    });
    const ctx = pressureChart.value.getContext('2d');
    if (!ctx)
        return;
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: deliveryLabels,
            datasets: [
                {
                    label: 'Pressure Score',
                    data: pressureScores,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: borderColors,
                    pointBorderColor: borderColors,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function (context) {
                            const point = props.pressureData?.pressure_points[context.dataIndex];
                            if (point) {
                                return [
                                    `Level: ${point.pressure_level.toUpperCase()}`,
                                    `Runs: ${point.cumulative_stats?.runs || 0}`,
                                    `RRR: ${point.rates?.required_run_rate?.toFixed(2) || 'N/A'}`
                                ];
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        font: { size: 11 }
                    },
                    title: {
                        display: true,
                        text: 'Pressure Score (0-100)'
                    }
                },
                x: {
                    ticks: {
                        font: { size: 10 },
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            }
        }
    });
};
onMounted(() => {
    initChart();
});
watch(() => props.pressureData, () => {
    initChart();
});
const __VLS_defaults = {
    pressureData: null,
    loading: false
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
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
/** @type {__VLS_StyleScopedClasses['moderate']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
/** @type {__VLS_StyleScopedClasses['building']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
/** @type {__VLS_StyleScopedClasses['extreme']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['moderate']} */ ;
/** @type {__VLS_StyleScopedClasses['building']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['extreme']} */ ;
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['moderate']} */ ;
/** @type {__VLS_StyleScopedClasses['building']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['extreme']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['moderate']} */ ;
/** @type {__VLS_StyleScopedClasses['building']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['extreme']} */ ;
/** @type {__VLS_StyleScopedClasses['moment-level']} */ ;
/** @type {__VLS_StyleScopedClasses['pressure-map-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['pressure-header']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pressure-map-widget" },
});
/** @type {__VLS_StyleScopedClasses['pressure-map-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pressure-header" },
});
/** @type {__VLS_StyleScopedClasses['pressure-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "widget-title" },
});
/** @type {__VLS_StyleScopedClasses['widget-title']} */ ;
if (__VLS_ctx.pressureData?.summary) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-stats']} */ ;
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
        ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.summary.average_pressure)) },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.pressureData.summary.average_pressure.toFixed(1));
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
        ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.summary.peak_pressure)) },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.pressureData.summary.peak_pressure.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-item" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value critical" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    /** @type {__VLS_StyleScopedClasses['critical']} */ ;
    (__VLS_ctx.pressureData.summary.critical_moments);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "view-tabs" },
});
/** @type {__VLS_StyleScopedClasses['view-tabs']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeView = 'timeline';
            // @ts-ignore
            [pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, getPressureClass, getPressureClass, activeView,];
        } },
    ...{ class: (['tab-btn', { active: __VLS_ctx.activeView === 'timeline' }]) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeView = 'phases';
            // @ts-ignore
            [activeView, activeView,];
        } },
    ...{ class: (['tab-btn', { active: __VLS_ctx.activeView === 'phases' }]) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeView = 'moments';
            // @ts-ignore
            [activeView, activeView,];
        } },
    ...{ class: (['tab-btn', { active: __VLS_ctx.activeView === 'moments' }]) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
}
else if (!__VLS_ctx.pressureData || !__VLS_ctx.pressureData.pressure_points?.length) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.activeView === 'timeline') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pressure-timeline" },
    });
    /** @type {__VLS_StyleScopedClasses['pressure-timeline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.canvas, __VLS_intrinsics.canvas)({
        ref: "pressureChart",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "timeline-legend" },
    });
    /** @type {__VLS_StyleScopedClasses['timeline-legend']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item low" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['low']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-box" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item moderate" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['moderate']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-box" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item building" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['building']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-box" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item high" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['high']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-box" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item extreme" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['extreme']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-box" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
}
else if (__VLS_ctx.activeView === 'phases') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pressure-phases" },
    });
    /** @type {__VLS_StyleScopedClasses['pressure-phases']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "phases-container" },
    });
    /** @type {__VLS_StyleScopedClasses['phases-container']} */ ;
    if (__VLS_ctx.pressureData.phases) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-card" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-header powerplay" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-header']} */ ;
        /** @type {__VLS_StyleScopedClasses['powerplay']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "phase-deliveries" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-deliveries']} */ ;
        (__VLS_ctx.pressureData.phases.powerplay?.length || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.powerplay_stats?.avg_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.powerplay_stats?.avg_pressure?.toFixed(1) || 'N/A');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.powerplay_stats?.peak_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.powerplay_stats?.peak_pressure?.toFixed(1) || 'N/A');
    }
    if (__VLS_ctx.pressureData.phases) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-card" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-header middle" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-header']} */ ;
        /** @type {__VLS_StyleScopedClasses['middle']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "phase-deliveries" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-deliveries']} */ ;
        (__VLS_ctx.pressureData.phases.middle?.length || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.middle_stats?.avg_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.middle_stats?.avg_pressure?.toFixed(1) || 'N/A');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.middle_stats?.peak_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.middle_stats?.peak_pressure?.toFixed(1) || 'N/A');
    }
    if (__VLS_ctx.pressureData.phases) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-card" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-header death" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-header']} */ ;
        /** @type {__VLS_StyleScopedClasses['death']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "phase-deliveries" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-deliveries']} */ ;
        (__VLS_ctx.pressureData.phases.death?.length || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.death_stats?.avg_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.death_stats?.avg_pressure?.toFixed(1) || 'N/A');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
            ...{ class: (__VLS_ctx.getPressureClass(__VLS_ctx.pressureData.phases.death_stats?.peak_pressure)) },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.pressureData.phases.death_stats?.peak_pressure?.toFixed(1) || 'N/A');
    }
}
else if (__VLS_ctx.activeView === 'moments') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "critical-moments" },
    });
    /** @type {__VLS_StyleScopedClasses['critical-moments']} */ ;
    if (__VLS_ctx.pressureData.peak_moments?.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "moments-list" },
        });
        /** @type {__VLS_StyleScopedClasses['moments-list']} */ ;
        for (const [moment, idx] of __VLS_vFor((__VLS_ctx.pressureData.peak_moments.slice(0, 8)))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "moment-card" },
                ...{ class: (__VLS_ctx.getPressureClass(moment.pressure_score)) },
            });
            /** @type {__VLS_StyleScopedClasses['moment-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "moment-delivery" },
            });
            /** @type {__VLS_StyleScopedClasses['moment-delivery']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "delivery-num" },
            });
            /** @type {__VLS_StyleScopedClasses['delivery-num']} */ ;
            (moment.delivery_num);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "over-num" },
            });
            /** @type {__VLS_StyleScopedClasses['over-num']} */ ;
            (moment.over_num.toFixed(1));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "moment-pressure" },
            });
            /** @type {__VLS_StyleScopedClasses['moment-pressure']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pressure-bar" },
            });
            /** @type {__VLS_StyleScopedClasses['pressure-bar']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pressure-fill" },
                ...{ style: ({ width: (moment.pressure_score / 100 * 100) + '%' }) },
            });
            /** @type {__VLS_StyleScopedClasses['pressure-fill']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "pressure-score" },
            });
            /** @type {__VLS_StyleScopedClasses['pressure-score']} */ ;
            (moment.pressure_score.toFixed(1));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "moment-context" },
            });
            /** @type {__VLS_StyleScopedClasses['moment-context']} */ ;
            if (moment.cumulative_stats) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "context-item" },
                });
                /** @type {__VLS_StyleScopedClasses['context-item']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "label" },
                });
                /** @type {__VLS_StyleScopedClasses['label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "value" },
                });
                /** @type {__VLS_StyleScopedClasses['value']} */ ;
                (moment.cumulative_stats.runs);
                (moment.cumulative_stats.wickets);
            }
            if (moment.cumulative_stats) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "context-item" },
                });
                /** @type {__VLS_StyleScopedClasses['context-item']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "label" },
                });
                /** @type {__VLS_StyleScopedClasses['label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "value" },
                });
                /** @type {__VLS_StyleScopedClasses['value']} */ ;
                (moment.cumulative_stats.strike_rate?.toFixed(1));
            }
            if (moment.rates) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "context-item" },
                });
                /** @type {__VLS_StyleScopedClasses['context-item']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "label" },
                });
                /** @type {__VLS_StyleScopedClasses['label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "value" },
                });
                /** @type {__VLS_StyleScopedClasses['value']} */ ;
                (moment.rates.required_run_rate?.toFixed(2));
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "moment-level" },
            });
            /** @type {__VLS_StyleScopedClasses['moment-level']} */ ;
            (moment.pressure_level?.toUpperCase());
            // @ts-ignore
            [pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, pressureData, getPressureClass, getPressureClass, getPressureClass, getPressureClass, getPressureClass, getPressureClass, getPressureClass, activeView, activeView, activeView, activeView, loading,];
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "no-moments" },
        });
        /** @type {__VLS_StyleScopedClasses['no-moments']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
