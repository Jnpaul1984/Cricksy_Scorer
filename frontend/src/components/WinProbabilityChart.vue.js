/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler, } from 'chart.js';
import { storeToRefs } from 'pinia';
import { computed, ref, watch } from 'vue';
import { Line } from 'vue-chartjs';
import { BaseCard, BaseBadge } from '@/components';
import { useGameStore } from '@/stores/gameStore';
// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);
const props = withDefaults(defineProps(), {
    showChart: false,
    maxHistory: 50,
});
const gameStore = useGameStore();
const { currentPrediction, currentGame } = storeToRefs(gameStore);
const prediction = computed(() => currentPrediction.value);
// Check if we're in first innings (no target means first innings)
const isFirstInnings = computed(() => {
    return !currentGame.value?.target;
});
// Get current run rate from game state
const currentRunRate = computed(() => {
    return currentGame.value?.current_run_rate || 0;
});
// Historical data for chart
const predictionHistory = ref([]);
// Watch for prediction updates and add to history
watch(() => currentPrediction.value, (newPred) => {
    if (newPred && props.showChart) {
        // Get current over from game state
        const currentGame = gameStore.currentGame;
        const oversCompleted = currentGame?.overs_completed ?? 0;
        const ballsThisOver = currentGame?.balls_this_over ?? 0;
        const currentOver = `${oversCompleted}.${ballsThisOver}`;
        predictionHistory.value.push({
            over: currentOver,
            battingProb: newPred.batting_team_win_prob,
            bowlingProb: newPred.bowling_team_win_prob,
        });
        // Keep only last N predictions
        if (predictionHistory.value.length > props.maxHistory) {
            predictionHistory.value = predictionHistory.value.slice(-props.maxHistory);
        }
    }
});
const chartData = computed(() => ({
    labels: predictionHistory.value.map(p => p.over),
    datasets: [
        {
            label: prediction.value?.batting_team || 'Batting',
            data: predictionHistory.value.map(p => p.battingProb),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.3,
            fill: true,
        },
        {
            label: prediction.value?.bowling_team || 'Bowling',
            data: predictionHistory.value.map(p => p.bowlingProb),
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            tension: 0.3,
            fill: true,
        },
    ],
}));
const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
        },
        tooltip: {
            callbacks: {
                label: (context) => {
                    const value = context.parsed.y ?? 0;
                    return `${context.dataset.label}: ${value.toFixed(1)}%`;
                },
            },
        },
    },
    scales: {
        y: {
            min: 0,
            max: 100,
            ticks: {
                callback: (value) => `${value}%`,
            },
        },
        x: {
            title: {
                display: true,
                text: 'Overs',
            },
        },
    },
}));
const __VLS_defaults = {
    showChart: false,
    maxHistory: 50,
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
/** @type {__VLS_StyleScopedClasses['prob-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['prob-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['no-data']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ class: "win-prob-chart" },
    padding: "md",
}));
const __VLS_2 = __VLS_1({
    ...{ class: "win-prob-chart" },
    padding: "md",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['win-prob-chart']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "title" },
});
/** @type {__VLS_StyleScopedClasses['title']} */ ;
(__VLS_ctx.isFirstInnings ? 'Score Prediction' : 'Win Probability');
if (__VLS_ctx.prediction) {
    let __VLS_7;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_8 = __VLS_asFunctionalComponent1(__VLS_7, new __VLS_7({
        variant: "neutral",
        size: "sm",
    }));
    const __VLS_9 = __VLS_8({
        variant: "neutral",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_8));
    const { default: __VLS_12 } = __VLS_10.slots;
    (__VLS_ctx.prediction.confidence.toFixed(0));
    // @ts-ignore
    [isFirstInnings, prediction, prediction,];
    var __VLS_10;
}
if (__VLS_ctx.prediction && __VLS_ctx.isFirstInnings && __VLS_ctx.prediction.factors?.projected_score) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-prediction" },
    });
    /** @type {__VLS_StyleScopedClasses['score-prediction']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "projected-score" },
    });
    /** @type {__VLS_StyleScopedClasses['projected-score']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-label" },
    });
    /** @type {__VLS_StyleScopedClasses['score-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-value" },
    });
    /** @type {__VLS_StyleScopedClasses['score-value']} */ ;
    (Math.round(__VLS_ctx.prediction.factors.projected_score));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-details" },
    });
    /** @type {__VLS_StyleScopedClasses['score-details']} */ ;
    (Math.round(__VLS_ctx.prediction.factors.par_score || 0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: ({ 'above-par': __VLS_ctx.prediction.factors.projected_score > (__VLS_ctx.prediction.factors.par_score || 0), 'below-par': __VLS_ctx.prediction.factors.projected_score < (__VLS_ctx.prediction.factors.par_score || 0) }) },
    });
    /** @type {__VLS_StyleScopedClasses['above-par']} */ ;
    /** @type {__VLS_StyleScopedClasses['below-par']} */ ;
    (__VLS_ctx.prediction.factors.projected_score > (__VLS_ctx.prediction.factors.par_score || 0) ? '+' : '');
    (Math.round(__VLS_ctx.prediction.factors.projected_score - (__VLS_ctx.prediction.factors.par_score || 0)));
}
if (__VLS_ctx.prediction && !__VLS_ctx.isFirstInnings) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "probability-bars" },
    });
    /** @type {__VLS_StyleScopedClasses['probability-bars']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-prob batting" },
    });
    /** @type {__VLS_StyleScopedClasses['team-prob']} */ ;
    /** @type {__VLS_StyleScopedClasses['batting']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-name" },
    });
    /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
    (__VLS_ctx.prediction.batting_team || 'Batting');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "prob-bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['prob-bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "prob-bar" },
        ...{ style: ({ width: `${__VLS_ctx.prediction.batting_team_win_prob}%` }) },
    });
    /** @type {__VLS_StyleScopedClasses['prob-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "prob-value" },
    });
    /** @type {__VLS_StyleScopedClasses['prob-value']} */ ;
    (__VLS_ctx.prediction.batting_team_win_prob.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-prob bowling" },
    });
    /** @type {__VLS_StyleScopedClasses['team-prob']} */ ;
    /** @type {__VLS_StyleScopedClasses['bowling']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-name" },
    });
    /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
    (__VLS_ctx.prediction.bowling_team || 'Bowling');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "prob-bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['prob-bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "prob-bar" },
        ...{ style: ({ width: `${__VLS_ctx.prediction.bowling_team_win_prob}%` }) },
    });
    /** @type {__VLS_StyleScopedClasses['prob-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "prob-value" },
    });
    /** @type {__VLS_StyleScopedClasses['prob-value']} */ ;
    (__VLS_ctx.prediction.bowling_team_win_prob.toFixed(1));
}
if (__VLS_ctx.prediction?.factors) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "factors" },
    });
    /** @type {__VLS_StyleScopedClasses['factors']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "factors-title" },
    });
    /** @type {__VLS_StyleScopedClasses['factors-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "factors-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['factors-grid']} */ ;
    if (!__VLS_ctx.isFirstInnings) {
        if (__VLS_ctx.prediction.factors.required_run_rate != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.required_run_rate.toFixed(2));
        }
        if (__VLS_ctx.prediction.factors.current_run_rate != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.current_run_rate.toFixed(2));
        }
        if (__VLS_ctx.prediction.factors.runs_needed != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.runs_needed);
        }
        if (__VLS_ctx.prediction.factors.balls_remaining != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.balls_remaining);
        }
        if (__VLS_ctx.prediction.factors.wickets_remaining != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.wickets_remaining);
        }
    }
    else {
        if (__VLS_ctx.currentRunRate != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.currentRunRate.toFixed(2));
        }
        if (__VLS_ctx.prediction.factors.wickets_remaining != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.wickets_remaining);
        }
        if (__VLS_ctx.prediction.factors.balls_remaining != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-label" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "factor-value" },
            });
            /** @type {__VLS_StyleScopedClasses['factor-value']} */ ;
            (__VLS_ctx.prediction.factors.balls_remaining);
        }
    }
}
if (__VLS_ctx.showChart && __VLS_ctx.chartData.labels && __VLS_ctx.chartData.labels.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "chart-container" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
    let __VLS_13;
    /** @ts-ignore @type { | typeof __VLS_components.Line} */
    Line;
    // @ts-ignore
    const __VLS_14 = __VLS_asFunctionalComponent1(__VLS_13, new __VLS_13({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.chartOptions),
    }));
    const __VLS_15 = __VLS_14({
        data: (__VLS_ctx.chartData),
        options: (__VLS_ctx.chartOptions),
    }, ...__VLS_functionalComponentArgsRest(__VLS_14));
}
if (!__VLS_ctx.prediction) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-data" },
    });
    /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[isFirstInnings, isFirstInnings, isFirstInnings, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, currentRunRate, currentRunRate, showChart, chartData, chartData, chartData, chartOptions,];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
