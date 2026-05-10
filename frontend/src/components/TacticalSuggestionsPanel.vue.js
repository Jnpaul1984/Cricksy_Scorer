/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, watch, onMounted } from 'vue';
import { useTacticalSuggestions } from '@/composables/useTacticalSuggestions';
const props = withDefaults(defineProps(), {
    gameId: undefined,
});
const { suggestions, loading, error, fetchSuggestions } = useTacticalSuggestions();
const lastUpdated = ref('');
// Auto-refresh every 10 seconds if game ID is set
onMounted(async () => {
    if (props.gameId) {
        await refreshSuggestions();
        // Poll for updates
        setInterval(() => {
            if (props.gameId) {
                refreshSuggestions();
            }
        }, 10000);
    }
});
watch(() => props.gameId, async (newGameId) => {
    if (newGameId) {
        await refreshSuggestions();
    }
});
async function refreshSuggestions() {
    if (props.gameId) {
        await fetchSuggestions(props.gameId);
        lastUpdated.value = new Date().toLocaleTimeString();
    }
}
function confidenceClass(confidence) {
    if (confidence >= 0.8)
        return 'confidence-high';
    if (confidence >= 0.6)
        return 'confidence-medium';
    return 'confidence-low';
}
function formatWeakness(weakness) {
    // Convert "DeliveryType.PACE" to "Pace" or just "pace" to "Pace"
    const match = weakness.match(/(?:DeliveryType\.)?(\w+)/i);
    return match ? match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase() : weakness;
}
function formatLine(line) {
    // Convert "off_stump" to "Off stump"
    return line
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
const __VLS_defaults = {
    gameId: undefined,
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
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['suggestion-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['secondary-weakness']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['secondary-weakness']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-1']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-2']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['position-item']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-3']} */ ;
/** @type {__VLS_StyleScopedClasses['priority-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['tactical-suggestions-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['suggestions-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tactical-suggestions-panel" },
});
/** @type {__VLS_StyleScopedClasses['tactical-suggestions-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-header" },
});
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "panel-title" },
});
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
if (__VLS_ctx.gameId) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.refreshSuggestions) },
        disabled: (__VLS_ctx.loading),
        ...{ class: "refresh-btn" },
        title: "Refresh suggestions",
    });
    /** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
}
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-message" },
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    (__VLS_ctx.error);
}
else if (__VLS_ctx.loading) {
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
else if (!__VLS_ctx.suggestions) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "suggestions-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['suggestions-grid']} */ ;
    if (__VLS_ctx.suggestions.best_bowler) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "suggestion-card bowler-card" },
        });
        /** @type {__VLS_StyleScopedClasses['suggestion-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['bowler-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "card-title" },
        });
        /** @type {__VLS_StyleScopedClasses['card-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "bowler-name" },
        });
        /** @type {__VLS_StyleScopedClasses['bowler-name']} */ ;
        (__VLS_ctx.suggestions.best_bowler.bowler_name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "confidence-badge" },
            ...{ class: (__VLS_ctx.confidenceClass(__VLS_ctx.suggestions.best_bowler.confidence)) },
        });
        /** @type {__VLS_StyleScopedClasses['confidence-badge']} */ ;
        ((__VLS_ctx.suggestions.best_bowler.confidence * 100).toFixed(0));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "bowler-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['bowler-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat" },
        });
        /** @type {__VLS_StyleScopedClasses['stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.suggestions.best_bowler.effectiveness_vs_batter.toFixed(1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat" },
        });
        /** @type {__VLS_StyleScopedClasses['stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.suggestions.best_bowler.expected_economy.toFixed(2));
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "reason" },
        });
        /** @type {__VLS_StyleScopedClasses['reason']} */ ;
        (__VLS_ctx.suggestions.best_bowler.reason);
    }
    if (__VLS_ctx.suggestions.weakness) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "suggestion-card weakness-card" },
        });
        /** @type {__VLS_StyleScopedClasses['suggestion-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['weakness-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "card-title" },
        });
        /** @type {__VLS_StyleScopedClasses['card-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "weakness-type" },
        });
        /** @type {__VLS_StyleScopedClasses['weakness-type']} */ ;
        (__VLS_ctx.formatWeakness(__VLS_ctx.suggestions.weakness.primary_weakness));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "weakness-score-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['weakness-score-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "bar-fill" },
            ...{ style: ({ width: __VLS_ctx.suggestions.weakness.weakness_score + '%' }) },
        });
        /** @type {__VLS_StyleScopedClasses['bar-fill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "weakness-score" },
        });
        /** @type {__VLS_StyleScopedClasses['weakness-score']} */ ;
        (__VLS_ctx.suggestions.weakness.weakness_score.toFixed(1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "recommendation-box" },
        });
        /** @type {__VLS_StyleScopedClasses['recommendation-box']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "rec-item" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "rec-label" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "rec-value" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-value']} */ ;
        (__VLS_ctx.formatLine(__VLS_ctx.suggestions.weakness.recommended_line));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "rec-item" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "rec-label" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "rec-value" },
        });
        /** @type {__VLS_StyleScopedClasses['rec-value']} */ ;
        (__VLS_ctx.suggestions.weakness.recommended_length);
        if (__VLS_ctx.suggestions.weakness.recommended_speed) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "rec-item" },
            });
            /** @type {__VLS_StyleScopedClasses['rec-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "rec-label" },
            });
            /** @type {__VLS_StyleScopedClasses['rec-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "rec-value" },
            });
            /** @type {__VLS_StyleScopedClasses['rec-value']} */ ;
            (__VLS_ctx.suggestions.weakness.recommended_speed);
        }
        if (__VLS_ctx.suggestions.weakness.secondary_weakness) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "secondary-weakness" },
            });
            /** @type {__VLS_StyleScopedClasses['secondary-weakness']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.suggestions.weakness.secondary_weakness);
        }
    }
    if (__VLS_ctx.suggestions.fielding && __VLS_ctx.suggestions.fielding.recommended_positions.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "suggestion-card fielding-card" },
        });
        /** @type {__VLS_StyleScopedClasses['suggestion-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['fielding-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "card-title" },
        });
        /** @type {__VLS_StyleScopedClasses['card-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "primary-zone" },
        });
        /** @type {__VLS_StyleScopedClasses['primary-zone']} */ ;
        (__VLS_ctx.suggestions.fielding.primary_zone);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "positions-list" },
        });
        /** @type {__VLS_StyleScopedClasses['positions-list']} */ ;
        for (const [pos] of __VLS_vFor((__VLS_ctx.suggestions.fielding.recommended_positions))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (pos.position),
                ...{ class: "position-item" },
                ...{ class: ({ [`priority-${pos.priority}`]: true }) },
            });
            /** @type {__VLS_StyleScopedClasses['position-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "priority-badge" },
            });
            /** @type {__VLS_StyleScopedClasses['priority-badge']} */ ;
            (pos.priority);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "position-details" },
            });
            /** @type {__VLS_StyleScopedClasses['position-details']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "position-name" },
            });
            /** @type {__VLS_StyleScopedClasses['position-name']} */ ;
            (pos.position);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "coverage-reason" },
            });
            /** @type {__VLS_StyleScopedClasses['coverage-reason']} */ ;
            (pos.coverage_reason);
            // @ts-ignore
            [gameId, refreshSuggestions, loading, loading, error, error, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, confidenceClass, formatWeakness, formatLine,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "fielding-reasoning" },
        });
        /** @type {__VLS_StyleScopedClasses['fielding-reasoning']} */ ;
        (__VLS_ctx.suggestions.fielding.reasoning);
    }
}
if (__VLS_ctx.suggestions) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "timestamp" },
    });
    /** @type {__VLS_StyleScopedClasses['timestamp']} */ ;
    (__VLS_ctx.lastUpdated);
}
// @ts-ignore
[suggestions, suggestions, lastUpdated,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
