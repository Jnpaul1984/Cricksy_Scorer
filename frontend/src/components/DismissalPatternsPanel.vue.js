/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted, onUnmounted } from 'vue';
import { useDismissalPatterns } from '../composables/useDismissalPatterns';
const props = withDefaults(defineProps(), {
    autoRefresh: true,
    refreshIntervalSeconds: 15,
});
const emit = defineEmits();
const { fetchPlayerAnalysis, fetchTeamAnalysis, loading } = useDismissalPatterns();
const playerName = ref('');
const error = ref('');
const vulnerabilityScore = ref(0);
const riskLevel = ref('low');
const totalDismissals = ref(0);
const primaryVulnerability = ref('');
const secondaryVulnerabilities = ref([]);
const topPatterns = ref([]);
const criticalSituations = ref([]);
const improvementAreas = ref([]);
const dismissalsByType = ref({});
const dismissalsByPhase = ref({});
const lastUpdated = ref('');
let refreshInterval = null;
async function loadAnalysis() {
    error.value = '';
    lastUpdated.value = new Date().toLocaleTimeString();
    try {
        let data;
        if (props.playerId) {
            data = await fetchPlayerAnalysis(props.playerId);
        }
        else if (props.gameId && props.teamSide) {
            data = await fetchTeamAnalysis(props.gameId, props.teamSide);
        }
        else {
            error.value = 'No player or game ID provided';
            return;
        }
        if (data) {
            const analysis = data.analysis;
            if (analysis) {
                vulnerabilityScore.value = analysis.overall_vulnerability_score || 0;
                totalDismissals.value = analysis.total_dismissals || 0;
                primaryVulnerability.value = analysis.primary_vulnerability || '';
                secondaryVulnerabilities.value = analysis.secondary_vulnerabilities || [];
                topPatterns.value = analysis.top_patterns || [];
                criticalSituations.value = analysis.critical_situations || [];
                improvementAreas.value = analysis.improvement_areas || [];
                dismissalsByType.value = analysis.dismissals_by_type || {};
                dismissalsByPhase.value = analysis.dismissals_by_phase || {};
                // Set risk level
                if (vulnerabilityScore.value >= 70) {
                    riskLevel.value = 'critical';
                }
                else if (vulnerabilityScore.value >= 50) {
                    riskLevel.value = 'high';
                }
                else if (vulnerabilityScore.value >= 30) {
                    riskLevel.value = 'medium';
                }
                else {
                    riskLevel.value = 'low';
                }
                if (data.player_name) {
                    playerName.value = data.player_name;
                }
                emit('analysisLoaded', data);
            }
        }
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load analysis';
        emit('error', error.value);
    }
}
function refresh() {
    loadAnalysis();
}
function startAutoRefresh() {
    if (props.autoRefresh && refreshInterval === null) {
        refreshInterval = window.setInterval(() => {
            loadAnalysis();
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
    loadAnalysis();
    startAutoRefresh();
});
onUnmounted(() => {
    stopAutoRefresh();
});
const __VLS_defaults = {
    autoRefresh: true,
    refreshIntervalSeconds: 15,
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
/** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['score-value']} */ ;
/** @type {__VLS_StyleScopedClasses['score-value']} */ ;
/** @type {__VLS_StyleScopedClasses['score-value']} */ ;
/** @type {__VLS_StyleScopedClasses['score-value']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
/** @type {__VLS_StyleScopedClasses['patterns-section']} */ ;
/** @type {__VLS_StyleScopedClasses['pattern-card']} */ ;
/** @type {__VLS_StyleScopedClasses['pattern-card']} */ ;
/** @type {__VLS_StyleScopedClasses['pattern-card']} */ ;
/** @type {__VLS_StyleScopedClasses['pattern-recommendation']} */ ;
/** @type {__VLS_StyleScopedClasses['pattern-recommendation']} */ ;
/** @type {__VLS_StyleScopedClasses['situations-section']} */ ;
/** @type {__VLS_StyleScopedClasses['risk-high']} */ ;
/** @type {__VLS_StyleScopedClasses['risk-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['risk-low']} */ ;
/** @type {__VLS_StyleScopedClasses['situation-header']} */ ;
/** @type {__VLS_StyleScopedClasses['situation-stat']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['situation-stat']} */ ;
/** @type {__VLS_StyleScopedClasses['value']} */ ;
/** @type {__VLS_StyleScopedClasses['vulnerabilities-section']} */ ;
/** @type {__VLS_StyleScopedClasses['improvement-section']} */ ;
/** @type {__VLS_StyleScopedClasses['breakdown-section']} */ ;
/** @type {__VLS_StyleScopedClasses['breakdown-entry']} */ ;
/** @type {__VLS_StyleScopedClasses['breakdown-entry']} */ ;
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['dismissal-patterns-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['score-card']} */ ;
/** @type {__VLS_StyleScopedClasses['patterns-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['situations-list']} */ ;
/** @type {__VLS_StyleScopedClasses['breakdown-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dismissal-patterns-panel" },
});
/** @type {__VLS_StyleScopedClasses['dismissal-patterns-panel']} */ ;
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
else if (!__VLS_ctx.vulnerabilityScore || __VLS_ctx.vulnerabilityScore === 0) {
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
        ...{ class: "analysis-container" },
    });
    /** @type {__VLS_StyleScopedClasses['analysis-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-card" },
    });
    /** @type {__VLS_StyleScopedClasses['score-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-display" },
    });
    /** @type {__VLS_StyleScopedClasses['score-display']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-value" },
        ...{ class: (`risk-${__VLS_ctx.riskLevel}`) },
    });
    /** @type {__VLS_StyleScopedClasses['score-value']} */ ;
    (__VLS_ctx.vulnerabilityScore.toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-label" },
    });
    /** @type {__VLS_StyleScopedClasses['score-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-details" },
    });
    /** @type {__VLS_StyleScopedClasses['score-details']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "detail-row" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
        ...{ class: (`risk-badge-${__VLS_ctx.riskLevel}`) },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.riskLevel.toUpperCase());
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "detail-row" },
    });
    /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.totalDismissals);
    if (__VLS_ctx.primaryVulnerability) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "detail-row" },
        });
        /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "value" },
        });
        /** @type {__VLS_StyleScopedClasses['value']} */ ;
        (__VLS_ctx.primaryVulnerability);
    }
    if (__VLS_ctx.topPatterns.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "patterns-section" },
        });
        /** @type {__VLS_StyleScopedClasses['patterns-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "patterns-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['patterns-grid']} */ ;
        for (const [pattern, idx] of __VLS_vFor((__VLS_ctx.topPatterns))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: (['pattern-card', `severity-${pattern.severity}`]) },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pattern-header" },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
                ...{ class: "pattern-name" },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-name']} */ ;
            (pattern.pattern_name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "severity-badge" },
                ...{ class: (`badge-${pattern.severity}`) },
            });
            /** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
            (pattern.severity.toUpperCase());
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pattern-stats" },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-stats']} */ ;
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
            (pattern.dismissal_count);
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
            (pattern.dismissal_percentage);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat" },
            });
            /** @type {__VLS_StyleScopedClasses['stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "confidence-bar" },
            });
            /** @type {__VLS_StyleScopedClasses['confidence-bar']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "confidence-fill" },
                ...{ style: ({ width: ((pattern.confidence || 0.5) * 100) + '%' }) },
            });
            /** @type {__VLS_StyleScopedClasses['confidence-fill']} */ ;
            (((pattern.confidence || 0.5) * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pattern-context" },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-context']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            (pattern.context);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "pattern-recommendation" },
            });
            /** @type {__VLS_StyleScopedClasses['pattern-recommendation']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            (pattern.recommendation);
            // @ts-ignore
            [playerName, playerName, loading, error, error, refresh, vulnerabilityScore, vulnerabilityScore, vulnerabilityScore, riskLevel, riskLevel, riskLevel, totalDismissals, primaryVulnerability, primaryVulnerability, topPatterns, topPatterns,];
        }
    }
    if (__VLS_ctx.criticalSituations.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "situations-section" },
        });
        /** @type {__VLS_StyleScopedClasses['situations-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "situations-list" },
        });
        /** @type {__VLS_StyleScopedClasses['situations-list']} */ ;
        for (const [situation, idx] of __VLS_vFor((__VLS_ctx.criticalSituations))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: (['situation-card', `risk-${situation.risk_level}`]) },
            });
            /** @type {__VLS_StyleScopedClasses['situation-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "situation-header" },
            });
            /** @type {__VLS_StyleScopedClasses['situation-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
            (situation.situation_type);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "risk-badge" },
                ...{ class: (`risk-badge-${situation.risk_level}`) },
            });
            /** @type {__VLS_StyleScopedClasses['risk-badge']} */ ;
            (situation.risk_level.toUpperCase());
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "situation-description" },
            });
            /** @type {__VLS_StyleScopedClasses['situation-description']} */ ;
            (situation.scenario_description);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "situation-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['situation-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (situation.dismissal_count);
            // @ts-ignore
            [criticalSituations, criticalSituations,];
        }
    }
    if (__VLS_ctx.secondaryVulnerabilities.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "vulnerabilities-section" },
        });
        /** @type {__VLS_StyleScopedClasses['vulnerabilities-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "vulnerabilities-list" },
        });
        /** @type {__VLS_StyleScopedClasses['vulnerabilities-list']} */ ;
        for (const [vuln, idx] of __VLS_vFor((__VLS_ctx.secondaryVulnerabilities))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "vulnerability-item" },
            });
            /** @type {__VLS_StyleScopedClasses['vulnerability-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "vulnerability-tag" },
            });
            /** @type {__VLS_StyleScopedClasses['vulnerability-tag']} */ ;
            (vuln);
            // @ts-ignore
            [secondaryVulnerabilities, secondaryVulnerabilities,];
        }
    }
    if (__VLS_ctx.improvementAreas.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "improvement-section" },
        });
        /** @type {__VLS_StyleScopedClasses['improvement-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.ol, __VLS_intrinsics.ol)({
            ...{ class: "improvement-list" },
        });
        /** @type {__VLS_StyleScopedClasses['improvement-list']} */ ;
        for (const [area, idx] of __VLS_vFor((__VLS_ctx.improvementAreas))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (idx),
                ...{ class: "improvement-item" },
            });
            /** @type {__VLS_StyleScopedClasses['improvement-item']} */ ;
            (area);
            // @ts-ignore
            [improvementAreas, improvementAreas,];
        }
    }
    if (__VLS_ctx.dismissalsByType && Object.keys(__VLS_ctx.dismissalsByType).length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "breakdown-section" },
        });
        /** @type {__VLS_StyleScopedClasses['breakdown-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "breakdown-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['breakdown-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "breakdown-item" },
        });
        /** @type {__VLS_StyleScopedClasses['breakdown-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "breakdown-list" },
        });
        /** @type {__VLS_StyleScopedClasses['breakdown-list']} */ ;
        for (const [count, type] of __VLS_vFor((__VLS_ctx.dismissalsByType))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (type),
                ...{ class: "breakdown-entry" },
            });
            /** @type {__VLS_StyleScopedClasses['breakdown-entry']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "type" },
            });
            /** @type {__VLS_StyleScopedClasses['type']} */ ;
            (type);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "count" },
            });
            /** @type {__VLS_StyleScopedClasses['count']} */ ;
            (count);
            // @ts-ignore
            [dismissalsByType, dismissalsByType, dismissalsByType,];
        }
        if (__VLS_ctx.dismissalsByPhase) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "breakdown-item" },
            });
            /** @type {__VLS_StyleScopedClasses['breakdown-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "breakdown-list" },
            });
            /** @type {__VLS_StyleScopedClasses['breakdown-list']} */ ;
            for (const [count, phase] of __VLS_vFor((__VLS_ctx.dismissalsByPhase))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (phase),
                    ...{ class: "breakdown-entry" },
                });
                /** @type {__VLS_StyleScopedClasses['breakdown-entry']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "type" },
                });
                /** @type {__VLS_StyleScopedClasses['type']} */ ;
                (phase);
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "count" },
                });
                /** @type {__VLS_StyleScopedClasses['count']} */ ;
                (count);
                // @ts-ignore
                [dismissalsByPhase, dismissalsByPhase,];
            }
        }
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
(__VLS_ctx.lastUpdated);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.refresh) },
    ...{ class: "refresh-btn" },
});
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
// @ts-ignore
[refresh, lastUpdated,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
