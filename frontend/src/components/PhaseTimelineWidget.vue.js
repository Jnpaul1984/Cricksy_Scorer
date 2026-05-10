/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    loading: false,
    error: null,
    predictions: null,
    onRefresh: undefined,
});
const currentPhase = computed(() => props.phaseData?.current_phase || 'powerplay');
function formatPhaseName(phase) {
    const names = {
        powerplay: '⚡ Powerplay',
        middle: '📊 Middle Overs',
        death: '🔥 Death Overs',
        mini_death: '⚠️ Mini-Death',
    };
    return names[phase] || phase;
}
function formatTrend(trend) {
    const icons = {
        increasing: '📈 Increasing',
        decreasing: '📉 Decreasing',
        stable: '➡️ Stable',
    };
    return icons[trend] || trend;
}
function isPhaseCompleted(phase) {
    return phase.phase_number < (props.phaseData?.phase_index || 0);
}
function getEfficiencyClass(efficiency) {
    if (efficiency >= 100)
        return 'excellent';
    if (efficiency >= 85)
        return 'good';
    if (efficiency >= 70)
        return 'average';
    return 'poor';
}
function getProbabilityClass(prob) {
    if (prob >= 0.8)
        return 'very-high';
    if (prob >= 0.6)
        return 'high';
    if (prob >= 0.4)
        return 'moderate';
    return 'low';
}
const __VLS_defaults = {
    loading: false,
    error: null,
    predictions: null,
    onRefresh: undefined,
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
/** @type {__VLS_StyleScopedClasses['phase-timeline-widget']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
/** @type {__VLS_StyleScopedClasses['phases-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "phase-timeline-widget" },
});
/** @type {__VLS_StyleScopedClasses['phase-timeline-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "widget-header" },
});
/** @type {__VLS_StyleScopedClasses['widget-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-actions" },
});
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
if (__VLS_ctx.currentPhase) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "current-phase-badge" },
        ...{ class: (__VLS_ctx.currentPhase) },
    });
    /** @type {__VLS_StyleScopedClasses['current-phase-badge']} */ ;
    (__VLS_ctx.formatPhaseName(__VLS_ctx.currentPhase));
}
if (__VLS_ctx.onRefresh) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.onRefresh) },
        ...{ class: "refresh-btn" },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
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
if (__VLS_ctx.error && !__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-state" },
    });
    /** @type {__VLS_StyleScopedClasses['error-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
}
if (__VLS_ctx.phaseData && !__VLS_ctx.loading && !__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "timeline-container" },
    });
    /** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "phases-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['phases-grid']} */ ;
    for (const [phase] of __VLS_vFor((__VLS_ctx.phaseData.phases))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`phase-${phase.phase_number}`),
            ...{ class: "phase-card" },
            ...{ class: ({
                    active: phase.phase_name === __VLS_ctx.currentPhase,
                    completed: __VLS_ctx.isPhaseCompleted(phase),
                }) },
        });
        /** @type {__VLS_StyleScopedClasses['phase-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        /** @type {__VLS_StyleScopedClasses['completed']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-header" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        (__VLS_ctx.formatPhaseName(phase.phase_name));
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "over-range" },
        });
        /** @type {__VLS_StyleScopedClasses['over-range']} */ ;
        (phase.start_over);
        (phase.end_over);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-stats']} */ ;
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
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (phase.total_runs);
        (Math.round(phase.expected_runs_in_phase));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-fill" },
            ...{ style: ({ width: `${Math.min(phase.actual_vs_expected_pct, 100)}%` }) },
            ...{ class: (__VLS_ctx.getEfficiencyClass(phase.actual_vs_expected_pct)) },
        });
        /** @type {__VLS_StyleScopedClasses['stat-fill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-pct" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-pct']} */ ;
        (Math.round(phase.actual_vs_expected_pct));
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
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (phase.run_rate.toFixed(1));
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
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (phase.total_wickets);
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
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (phase.boundary_count);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "phase-indicators" },
        });
        /** @type {__VLS_StyleScopedClasses['phase-indicators']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-label" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-fill aggression" },
            ...{ style: ({ width: `${Math.min(phase.aggressive_index * 100, 100)}%` }) },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-fill']} */ ;
        /** @type {__VLS_StyleScopedClasses['aggression']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-value" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-value']} */ ;
        ((phase.aggressive_index * 100).toFixed(0));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-label" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-fill dots" },
            ...{ style: ({ width: `${(phase.dot_ball_count / phase.total_deliveries) * 100}%` }) },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-fill']} */ ;
        /** @type {__VLS_StyleScopedClasses['dots']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-value" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-value']} */ ;
        (phase.dot_ball_count);
        (phase.total_deliveries);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-label" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "indicator-fill wickets" },
            ...{ style: ({ width: `${Math.min(phase.wicket_rate * 20, 100)}%` }) },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-fill']} */ ;
        /** @type {__VLS_StyleScopedClasses['wickets']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "indicator-value" },
        });
        /** @type {__VLS_StyleScopedClasses['indicator-value']} */ ;
        (phase.wicket_rate.toFixed(2));
        // @ts-ignore
        [currentPhase, currentPhase, currentPhase, currentPhase, formatPhaseName, formatPhaseName, onRefresh, onRefresh, loading, loading, loading, loading, error, error, error, phaseData, phaseData, isPhaseCompleted, getEfficiencyClass,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-section" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-item" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.phaseData.summary.total_runs);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-item" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.phaseData.summary.total_wickets);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-item" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.phaseData.summary.overall_run_rate.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-item" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (Math.round(__VLS_ctx.phaseData.summary.overall_expected_runs));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-item" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: (`trend-${__VLS_ctx.phaseData.summary.acceleration_trend}`) },
    });
    (__VLS_ctx.formatTrend(__VLS_ctx.phaseData.summary.acceleration_trend));
    if (__VLS_ctx.predictions) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "predictions-section" },
        });
        /** @type {__VLS_StyleScopedClasses['predictions-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "predictions-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['predictions-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "prediction-item" },
        });
        /** @type {__VLS_StyleScopedClasses['prediction-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.predictions.match_prediction.projected_total);
        if (__VLS_ctx.predictions.match_prediction.win_probability) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "prediction-item" },
            });
            /** @type {__VLS_StyleScopedClasses['prediction-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: (__VLS_ctx.getProbabilityClass(__VLS_ctx.predictions.match_prediction.win_probability)) },
            });
            ((__VLS_ctx.predictions.match_prediction.win_probability * 100).toFixed(0));
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "prediction-item" },
        });
        /** @type {__VLS_StyleScopedClasses['prediction-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        ((__VLS_ctx.predictions.match_prediction.confidence * 100).toFixed(0));
    }
}
if (!__VLS_ctx.phaseData && !__VLS_ctx.loading && !__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[loading, error, phaseData, phaseData, phaseData, phaseData, phaseData, phaseData, phaseData, formatTrend, predictions, predictions, predictions, predictions, predictions, predictions, getProbabilityClass,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
