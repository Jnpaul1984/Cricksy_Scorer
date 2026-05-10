/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import WinProbabilityChart from '@/components/analytics/WinProbabilityChart.vue';
const props = withDefaults(defineProps(), {
    battingTeam: undefined,
    bowlingTeam: undefined,
    theme: 'dark',
    showChart: true,
    compact: false,
});
const battingColor = computed(() => {
    if (!props.prediction)
        return '#9ca3af';
    const prob = props.prediction.batting_team_win_prob;
    if (prob >= 70)
        return '#22c55e'; // Green
    if (prob >= 50)
        return '#eab308'; // Yellow
    return '#ef4444'; // Red
});
const bowlingColor = computed(() => {
    if (!props.prediction)
        return '#9ca3af';
    const prob = props.prediction.bowling_team_win_prob;
    if (prob >= 70)
        return '#22c55e'; // Green
    if (prob >= 50)
        return '#eab308'; // Yellow
    return '#ef4444'; // Red
});
const battingBarWidth = computed(() => {
    if (!props.prediction)
        return '50%';
    return `${props.prediction.batting_team_win_prob}%`;
});
const bowlingBarWidth = computed(() => {
    if (!props.prediction)
        return '50%';
    return `${props.prediction.bowling_team_win_prob}%`;
});
const formattedBattingTeam = computed(() => {
    return props.prediction?.batting_team || props.battingTeam || 'Batting Team';
});
const formattedBowlingTeam = computed(() => {
    return props.prediction?.bowling_team || props.bowlingTeam || 'Bowling Team';
});
const resolvedTheme = computed(() => {
    if (props.theme === 'dark')
        return 'dark';
    return 'light';
});
const __VLS_defaults = {
    battingTeam: undefined,
    bowlingTeam: undefined,
    theme: 'dark',
    showChart: true,
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
/** @type {__VLS_StyleScopedClasses['win-probability-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['percentage']} */ ;
/** @type {__VLS_StyleScopedClasses['batting']} */ ;
/** @type {__VLS_StyleScopedClasses['percentage']} */ ;
/** @type {__VLS_StyleScopedClasses['bowling']} */ ;
/** @type {__VLS_StyleScopedClasses['factor']} */ ;
/** @type {__VLS_StyleScopedClasses['factor']} */ ;
/** @type {__VLS_StyleScopedClasses['no-prediction']} */ ;
/** @type {__VLS_StyleScopedClasses['team-row']} */ ;
/** @type {__VLS_StyleScopedClasses['factors']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "win-probability-widget" },
    ...{ class: ({ compact: __VLS_ctx.compact }) },
});
/** @type {__VLS_StyleScopedClasses['win-probability-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
if (__VLS_ctx.prediction && __VLS_ctx.prediction.confidence > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "prediction-display" },
    });
    /** @type {__VLS_StyleScopedClasses['prediction-display']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "header" },
    });
    /** @type {__VLS_StyleScopedClasses['header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "confidence" },
        title: (`Confidence: ${__VLS_ctx.prediction.confidence}%`),
    });
    /** @type {__VLS_StyleScopedClasses['confidence']} */ ;
    (__VLS_ctx.prediction.confidence.toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "probability-bars" },
    });
    /** @type {__VLS_StyleScopedClasses['probability-bars']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-row" },
    });
    /** @type {__VLS_StyleScopedClasses['team-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-name batting" },
    });
    /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
    /** @type {__VLS_StyleScopedClasses['batting']} */ ;
    (__VLS_ctx.formattedBattingTeam);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "bar batting-bar" },
        ...{ style: ({ width: __VLS_ctx.battingBarWidth, backgroundColor: __VLS_ctx.battingColor }) },
    });
    /** @type {__VLS_StyleScopedClasses['bar']} */ ;
    /** @type {__VLS_StyleScopedClasses['batting-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "percentage batting" },
    });
    /** @type {__VLS_StyleScopedClasses['percentage']} */ ;
    /** @type {__VLS_StyleScopedClasses['batting']} */ ;
    (__VLS_ctx.prediction.batting_team_win_prob.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-row" },
    });
    /** @type {__VLS_StyleScopedClasses['team-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-name bowling" },
    });
    /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
    /** @type {__VLS_StyleScopedClasses['bowling']} */ ;
    (__VLS_ctx.formattedBowlingTeam);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "bar bowling-bar" },
        ...{ style: ({ width: __VLS_ctx.bowlingBarWidth, backgroundColor: __VLS_ctx.bowlingColor }) },
    });
    /** @type {__VLS_StyleScopedClasses['bar']} */ ;
    /** @type {__VLS_StyleScopedClasses['bowling-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "percentage bowling" },
    });
    /** @type {__VLS_StyleScopedClasses['percentage']} */ ;
    /** @type {__VLS_StyleScopedClasses['bowling']} */ ;
    (__VLS_ctx.prediction.bowling_team_win_prob.toFixed(1));
    if (__VLS_ctx.prediction.factors && !__VLS_ctx.compact) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "factors" },
        });
        /** @type {__VLS_StyleScopedClasses['factors']} */ ;
        if (__VLS_ctx.prediction.factors.runs_needed !== undefined) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.prediction.factors.runs_needed);
        }
        if (__VLS_ctx.prediction.factors.balls_remaining !== undefined) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.prediction.factors.balls_remaining);
        }
        if (__VLS_ctx.prediction.factors.required_run_rate !== undefined) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.prediction.factors.required_run_rate.toFixed(2));
        }
        if (__VLS_ctx.prediction.factors.wickets_remaining !== undefined) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.prediction.factors.wickets_remaining);
        }
        if (__VLS_ctx.prediction.factors.projected_score !== undefined) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "factor" },
            });
            /** @type {__VLS_StyleScopedClasses['factor']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.prediction.factors.projected_score);
        }
    }
    if (__VLS_ctx.showChart && !__VLS_ctx.compact) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chart-section" },
        });
        /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
        const __VLS_0 = WinProbabilityChart;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
            currentPrediction: (__VLS_ctx.prediction),
            battingTeam: (__VLS_ctx.formattedBattingTeam),
            bowlingTeam: (__VLS_ctx.formattedBowlingTeam),
            theme: (__VLS_ctx.resolvedTheme),
        }));
        const __VLS_2 = __VLS_1({
            currentPrediction: (__VLS_ctx.prediction),
            battingTeam: (__VLS_ctx.formattedBattingTeam),
            bowlingTeam: (__VLS_ctx.formattedBowlingTeam),
            theme: (__VLS_ctx.resolvedTheme),
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-prediction" },
    });
    /** @type {__VLS_StyleScopedClasses['no-prediction']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[compact, compact, compact, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, prediction, formattedBattingTeam, formattedBattingTeam, battingBarWidth, battingColor, formattedBowlingTeam, formattedBowlingTeam, bowlingBarWidth, bowlingColor, showChart, resolvedTheme,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
