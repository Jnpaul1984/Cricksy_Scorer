/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useTrainingDrills } from '../composables/useTrainingDrills';
const props = withDefaults(defineProps(), {
    autoRefresh: true,
    refreshIntervalSeconds: 10,
});
const emit = defineEmits();
const { fetchPlayerDrills, fetchTeamDrills, loading, error: composableError, } = useTrainingDrills();
const drills = ref([]);
const playerName = ref('');
const error = ref('');
let refreshInterval = null;
const highPriorityCount = computed(() => drills.value.filter((d) => d.severity === 'high').length);
const mediumPriorityCount = computed(() => drills.value.filter((d) => d.severity === 'medium').length);
const lowPriorityCount = computed(() => drills.value.filter((d) => d.severity === 'low').length);
const totalWeeklyHours = computed(() => {
    const total = drills.value.reduce((sum, d) => {
        const frequency = d.recommended_frequency || 'weekly';
        let multiplier = 1;
        if (frequency === 'daily')
            multiplier = 7;
        else if (frequency === '3x/week')
            multiplier = 3;
        else
            multiplier = 1; // weekly
        return sum + (d.duration_minutes * multiplier) / 60;
    }, 0);
    return total.toFixed(1);
});
const focusAreas = computed(() => {
    const areas = new Set(drills.value.map((d) => d.focus_area));
    return Array.from(areas).sort();
});
async function loadDrills() {
    error.value = '';
    try {
        if (props.playerId) {
            const data = await fetchPlayerDrills(props.playerId);
            if (data) {
                playerName.value = data.player_name || '';
                if (data.drill_plan?.drills) {
                    drills.value = data.drill_plan.drills;
                }
                else if (data.drills) {
                    drills.value = data.drills;
                }
                else {
                    drills.value = [];
                }
            }
        }
        else if (props.gameId && props.teamSide) {
            const data = await fetchTeamDrills(props.gameId, props.teamSide);
            if (data && data.team_drills && data.team_drills.length > 0) {
                // For team drills, show drills from first player
                drills.value = data.team_drills[0]?.drill_plan?.drills || [];
            }
            else {
                drills.value = [];
            }
        }
        else {
            error.value = 'No player or game ID provided';
            return;
        }
        emit('drillsLoaded', drills.value);
    }
    catch (err) {
        error.value =
            err instanceof Error ? err.message : 'Failed to load training drills';
        emit('error', error.value);
    }
}
function refresh() {
    loadDrills();
}
function startAutoRefresh() {
    if (props.autoRefresh && refreshInterval === null) {
        refreshInterval = window.setInterval(() => {
            loadDrills();
        }, props.refreshIntervalSeconds * 1000);
    }
}
function stopAutoRefresh() {
    if (refreshInterval !== null) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}
onMounted(() => {
    loadDrills();
    startAutoRefresh();
});
onUnmounted(() => {
    stopAutoRefresh();
});
const __VLS_defaults = {
    autoRefresh: true,
    refreshIntervalSeconds: 10,
};
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['state-message']} */ ;
/** @type {__VLS_StyleScopedClasses['state-message']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-areas']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['medium']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-reason']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-frequency']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-improvement']} */ ;
/** @type {__VLS_StyleScopedClasses['start-drill-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['start-drill-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['training-drills-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['drills-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['training-drills-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "training-drills-panel" },
});
/** @type {__VLS_StyleScopedClasses['training-drills-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-header" },
});
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
if (__VLS_ctx.playerName) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "player-name" },
    });
    /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
    (__VLS_ctx.playerName);
}
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-message" },
    });
    /** @type {__VLS_StyleScopedClasses['state-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-message error" },
    });
    /** @type {__VLS_StyleScopedClasses['state-message']} */ ;
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.refresh) },
        ...{ class: "retry-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
}
else if (!__VLS_ctx.drills || __VLS_ctx.drills.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-message" },
    });
    /** @type {__VLS_StyleScopedClasses['state-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "text-sm" },
    });
    /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "drills-container" },
    });
    /** @type {__VLS_StyleScopedClasses['drills-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-stats']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.drills.length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card high" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['high']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.highPriorityCount);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card medium" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['medium']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.mediumPriorityCount);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card low" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['low']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.lowPriorityCount);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.totalWeeklyHours);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    if (__VLS_ctx.focusAreas.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "focus-areas" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-areas']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "focus-tags" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-tags']} */ ;
        for (const [area] of __VLS_vFor((__VLS_ctx.focusAreas))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                key: (area),
                ...{ class: "focus-tag" },
            });
            /** @type {__VLS_StyleScopedClasses['focus-tag']} */ ;
            (area);
            // @ts-ignore
            [playerName, playerName, loading, error, error, refresh, drills, drills, drills, highPriorityCount, mediumPriorityCount, lowPriorityCount, totalWeeklyHours, focusAreas, focusAreas,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "drills-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['drills-grid']} */ ;
    for (const [drill] of __VLS_vFor((__VLS_ctx.drills))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (drill.drill_id),
            ...{ class: (['drill-card', `severity-${drill.severity.toLowerCase()}`]) },
        });
        /** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "severity-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
        if (drill.severity === 'high') {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "badge high" },
            });
            /** @type {__VLS_StyleScopedClasses['badge']} */ ;
            /** @type {__VLS_StyleScopedClasses['high']} */ ;
        }
        else if (drill.severity === 'medium') {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "badge medium" },
            });
            /** @type {__VLS_StyleScopedClasses['badge']} */ ;
            /** @type {__VLS_StyleScopedClasses['medium']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "badge low" },
            });
            /** @type {__VLS_StyleScopedClasses['badge']} */ ;
            /** @type {__VLS_StyleScopedClasses['low']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "drill-info" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "drill-name" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-name']} */ ;
        (drill.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "drill-category" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-category']} */ ;
        (drill.category);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "drill-description" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-description']} */ ;
        (drill.description);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "drill-details" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-details']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "detail-item" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-label" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-value" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
        (drill.reps_or_count);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "detail-item" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-label" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-value" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
        (drill.duration_minutes);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "detail-item" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-label" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-value" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-value']} */ ;
        (drill.focus_area);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "detail-item" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail-label" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "difficulty-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['difficulty-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "difficulty-fill" },
            ...{ style: ({ width: (drill.difficulty * 10) + '%' }) },
        });
        /** @type {__VLS_StyleScopedClasses['difficulty-fill']} */ ;
        (drill.difficulty);
        if (drill.reason) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "drill-reason" },
            });
            /** @type {__VLS_StyleScopedClasses['drill-reason']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (drill.reason);
        }
        if (drill.recommended_frequency) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "drill-frequency" },
            });
            /** @type {__VLS_StyleScopedClasses['drill-frequency']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (drill.recommended_frequency);
        }
        if (drill.expected_improvement) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "drill-improvement" },
            });
            /** @type {__VLS_StyleScopedClasses['drill-improvement']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (drill.expected_improvement);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ class: "start-drill-btn" },
        });
        /** @type {__VLS_StyleScopedClasses['start-drill-btn']} */ ;
        // @ts-ignore
        [drills,];
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "footer-info" },
});
/** @type {__VLS_StyleScopedClasses['footer-info']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "refresh-info" },
});
/** @type {__VLS_StyleScopedClasses['refresh-info']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.refresh) },
    ...{ class: "refresh-btn" },
});
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
// @ts-ignore
[refresh,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
