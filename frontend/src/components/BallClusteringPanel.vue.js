/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted, onUnmounted } from "vue";
import { useBallClustering } from "../composables/useBallClustering";
const props = withDefaults(defineProps(), {
    autoRefresh: true,
    refreshIntervalSeconds: 20,
});
const { fetchBowlerClusters, fetchBatterVulnerabilities } = useBallClustering();
// State
const analysisType = ref("bowler");
const selectedPlayer = ref(props.playerId || "");
const bowlerProfile = ref(null);
const batterVulnerability = ref(null);
const loading = ref(false);
const error = ref(null);
const autoRefresh = ref(props.autoRefresh);
const refreshIntervalSeconds = ref(props.refreshIntervalSeconds);
const lastUpdated = ref("");
let refreshInterval = null;
// Methods
function getEffectivenessClass(effectiveness) {
    if (effectiveness > 70)
        return "high-effectiveness";
    if (effectiveness > 40)
        return "medium-effectiveness";
    return "low-effectiveness";
}
function formatClusterName(cluster) {
    return cluster.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}
async function loadData() {
    if (!selectedPlayer.value)
        return;
    loading.value = true;
    error.value = null;
    try {
        if (analysisType.value === "bowler") {
            const result = await fetchBowlerClusters(selectedPlayer.value);
            bowlerProfile.value = result?.profile || null;
        }
        else {
            const result = await fetchBatterVulnerabilities(selectedPlayer.value);
            batterVulnerability.value = result?.vulnerability || null;
        }
        lastUpdated.value = new Date().toLocaleTimeString();
    }
    catch (err) {
        error.value = err.message || "Failed to load data";
    }
    finally {
        loading.value = false;
    }
}
function refreshData() {
    loadData();
}
function clearError() {
    error.value = null;
}
function startAutoRefresh() {
    if (autoRefresh.value && !refreshInterval) {
        refreshInterval = window.setInterval(() => {
            loadData();
        }, refreshIntervalSeconds.value * 1000);
    }
}
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}
// Lifecycle
onMounted(() => {
    if (props.playerId) {
        selectedPlayer.value = props.playerId;
        loadData();
    }
    startAutoRefresh();
});
onUnmounted(() => {
    stopAutoRefresh();
});
const __VLS_defaults = {
    autoRefresh: true,
    refreshIntervalSeconds: 20,
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
/** @type {__VLS_StyleScopedClasses['error-state']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['clustering-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['clusters-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "clustering-panel" },
});
/** @type {__VLS_StyleScopedClasses['clustering-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-header" },
});
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "panel-title" },
});
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "icon" },
});
/** @type {__VLS_StyleScopedClasses['icon']} */ ;
if (!__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.refreshData) },
        ...{ class: "refresh-btn" },
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
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-state" },
    });
    /** @type {__VLS_StyleScopedClasses['error-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.clearError) },
        ...{ class: "retry-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "content" },
    });
    /** @type {__VLS_StyleScopedClasses['content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "controls" },
    });
    /** @type {__VLS_StyleScopedClasses['controls']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        ...{ onChange: (__VLS_ctx.refreshData) },
        value: (__VLS_ctx.analysisType),
        ...{ class: "select-control" },
    });
    /** @type {__VLS_StyleScopedClasses['select-control']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bowler",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "batter",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        ...{ onChange: (__VLS_ctx.refreshData) },
        value: (__VLS_ctx.selectedPlayer),
        ...{ class: "select-control" },
    });
    /** @type {__VLS_StyleScopedClasses['select-control']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "b1",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "b2",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "p1",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "p2",
    });
    if (__VLS_ctx.analysisType === 'bowler' && __VLS_ctx.bowlerProfile) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "bowler-section" },
        });
        /** @type {__VLS_StyleScopedClasses['bowler-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.bowlerProfile.total_deliveries);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.bowlerProfile.variation_score);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (Math.round(__VLS_ctx.bowlerProfile.clustering_accuracy));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value text-sm" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
        (__VLS_ctx.bowlerProfile.most_effective_cluster);
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "clusters-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['clusters-grid']} */ ;
        for (const [cluster] of __VLS_vFor((__VLS_ctx.bowlerProfile.delivery_clusters))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (cluster.cluster_id),
                ...{ class: "cluster-card" },
            });
            /** @type {__VLS_StyleScopedClasses['cluster-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cluster-header" },
            });
            /** @type {__VLS_StyleScopedClasses['cluster-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cluster-name" },
            });
            /** @type {__VLS_StyleScopedClasses['cluster-name']} */ ;
            (cluster.cluster_name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "effectiveness-badge" },
                ...{ class: (__VLS_ctx.getEffectivenessClass(cluster.effectiveness_percentage)) },
            });
            /** @type {__VLS_StyleScopedClasses['effectiveness-badge']} */ ;
            (Math.round(cluster.effectiveness_percentage));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cluster-stats" },
            });
            /** @type {__VLS_StyleScopedClasses['cluster-stats']} */ ;
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
            (cluster.sample_count);
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
            (Math.round(cluster.success_rate));
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
            (cluster.average_runs_conceded);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "description" },
            });
            /** @type {__VLS_StyleScopedClasses['description']} */ ;
            (cluster.description);
            // @ts-ignore
            [loading, loading, refreshData, refreshData, refreshData, error, error, clearError, analysisType, analysisType, selectedPlayer, bowlerProfile, bowlerProfile, bowlerProfile, bowlerProfile, bowlerProfile, bowlerProfile, getEffectivenessClass,];
        }
    }
    if (__VLS_ctx.analysisType === 'batter' && __VLS_ctx.batterVulnerability) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "batter-section" },
        });
        /** @type {__VLS_StyleScopedClasses['batter-section']} */ ;
        if (__VLS_ctx.batterVulnerability.vulnerable_clusters.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "vulnerability-container" },
            });
            /** @type {__VLS_StyleScopedClasses['vulnerability-container']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "tags-list" },
            });
            /** @type {__VLS_StyleScopedClasses['tags-list']} */ ;
            for (const [cluster] of __VLS_vFor((__VLS_ctx.batterVulnerability.vulnerable_clusters))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    key: (cluster),
                    ...{ class: "tag tag-danger" },
                });
                /** @type {__VLS_StyleScopedClasses['tag']} */ ;
                /** @type {__VLS_StyleScopedClasses['tag-danger']} */ ;
                (__VLS_ctx.formatClusterName(cluster));
                // @ts-ignore
                [analysisType, batterVulnerability, batterVulnerability, batterVulnerability, formatClusterName,];
            }
        }
        if (__VLS_ctx.batterVulnerability.strong_against.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "strength-container" },
            });
            /** @type {__VLS_StyleScopedClasses['strength-container']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "tags-list" },
            });
            /** @type {__VLS_StyleScopedClasses['tags-list']} */ ;
            for (const [cluster] of __VLS_vFor((__VLS_ctx.batterVulnerability.strong_against))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    key: (cluster),
                    ...{ class: "tag tag-success" },
                });
                /** @type {__VLS_StyleScopedClasses['tag']} */ ;
                /** @type {__VLS_StyleScopedClasses['tag-success']} */ ;
                (__VLS_ctx.formatClusterName(cluster));
                // @ts-ignore
                [batterVulnerability, batterVulnerability, formatClusterName,];
            }
        }
        if (__VLS_ctx.batterVulnerability.recommended_bowling_strategy) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "strategy-container" },
            });
            /** @type {__VLS_StyleScopedClasses['strategy-container']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "strategy-box" },
            });
            /** @type {__VLS_StyleScopedClasses['strategy-box']} */ ;
            (__VLS_ctx.batterVulnerability.recommended_bowling_strategy);
        }
        if (__VLS_ctx.batterVulnerability.dismissal_delivery_types.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "dismissal-container" },
            });
            /** @type {__VLS_StyleScopedClasses['dismissal-container']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "tags-list" },
            });
            /** @type {__VLS_StyleScopedClasses['tags-list']} */ ;
            for (const [dtype] of __VLS_vFor((__VLS_ctx.batterVulnerability.dismissal_delivery_types))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    key: (dtype),
                    ...{ class: "tag tag-warning" },
                });
                /** @type {__VLS_StyleScopedClasses['tag']} */ ;
                /** @type {__VLS_StyleScopedClasses['tag-warning']} */ ;
                (__VLS_ctx.formatClusterName(dtype));
                // @ts-ignore
                [batterVulnerability, batterVulnerability, batterVulnerability, batterVulnerability, formatClusterName,];
            }
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "footer" },
    });
    /** @type {__VLS_StyleScopedClasses['footer']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "refresh-toggle" },
    });
    /** @type {__VLS_StyleScopedClasses['refresh-toggle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "checkbox",
    });
    (__VLS_ctx.autoRefresh);
    (__VLS_ctx.refreshIntervalSeconds);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "last-updated" },
    });
    /** @type {__VLS_StyleScopedClasses['last-updated']} */ ;
    (__VLS_ctx.lastUpdated);
}
// @ts-ignore
[autoRefresh, refreshIntervalSeconds, lastUpdated,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
