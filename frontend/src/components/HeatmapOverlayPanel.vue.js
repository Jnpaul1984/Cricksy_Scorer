/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useHeatmaps } from "../composables/useHeatmaps";
const props = withDefaults(defineProps(), {
    autoRefresh: true,
    refreshIntervalSeconds: 15,
});
const { fetchScoresHeatmap, fetchDismissalHeatmap, fetchReleaseZones, fetchMatchup } = useHeatmaps();
// State
const selectedPlayer = ref(props.playerId || "");
const selectedBowler = ref("");
const heatmapType = ref("scoring");
const heatmapData = ref([]);
const matchupData = ref(null);
const loading = ref(false);
const error = ref(null);
const autoRefresh = ref(props.autoRefresh);
const refreshIntervalSeconds = ref(props.refreshIntervalSeconds);
const lastUpdated = ref("");
let refreshInterval = null;
// Computed properties
const totalEvents = computed(() => heatmapData.value.reduce((sum, p) => sum + p.count, 0));
const averageIntensity = computed(() => {
    const avg = heatmapData.value.reduce((sum, p) => sum + p.value, 0) / (heatmapData.value.length || 1);
    return Math.round(avg);
});
const maxCount = computed(() => Math.max(...heatmapData.value.map(p => p.count), 1));
const peakZone = computed(() => {
    if (heatmapData.value.length === 0)
        return "N/A";
    const peak = heatmapData.value.reduce((max, p) => (p.value > max.value ? p : max));
    return formatZoneName(peak.zone);
});
const coveragePercentage = computed(() => {
    const uniqueZones = new Set(heatmapData.value.map(p => p.zone)).size;
    return Math.round((uniqueZones / 11) * 100); // 11 total zones
});
const sortedPoints = computed(() => {
    return [...heatmapData.value].sort((a, b) => b.value - a.value);
});
// Methods
function getHeatColor(value) {
    if (value > 80)
        return "#ff0000"; // Red - hottest
    if (value > 60)
        return "#ff7f00"; // Orange
    if (value > 40)
        return "#ffff00"; // Yellow
    if (value > 20)
        return "#00ff00"; // Green
    return "#0000ff"; // Blue - coolest
}
function formatZoneName(zone) {
    return zone
        .split("_")
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}
async function loadHeatmapData() {
    if (!selectedPlayer.value && !selectedBowler.value)
        return;
    loading.value = true;
    error.value = null;
    try {
        if (heatmapType.value === "scoring") {
            const result = await fetchScoresHeatmap(selectedPlayer.value);
            if (result?.heatmap?.data_points) {
                heatmapData.value = result.heatmap.data_points;
            }
        }
        else if (heatmapType.value === "dismissals") {
            const result = await fetchDismissalHeatmap(selectedPlayer.value);
            if (result?.heatmap?.data_points) {
                heatmapData.value = result.heatmap.data_points;
            }
        }
        else if (heatmapType.value === "release" && selectedBowler.value) {
            const result = await fetchReleaseZones(selectedBowler.value);
            if (result?.heatmap?.data_points) {
                heatmapData.value = result.heatmap.data_points;
            }
        }
        // Load matchup if both players selected
        if (selectedPlayer.value && selectedBowler.value) {
            const matchup = await fetchMatchup(selectedPlayer.value, selectedBowler.value);
            if (matchup?.matchup) {
                matchupData.value = matchup.matchup;
            }
        }
        lastUpdated.value = new Date().toLocaleTimeString();
    }
    catch (err) {
        error.value = err.message || "Failed to load heatmap data";
    }
    finally {
        loading.value = false;
    }
}
async function refreshData() {
    await loadHeatmapData();
}
function clearError() {
    error.value = null;
}
function onPlayerChange() {
    selectedBowler.value = "";
    loadHeatmapData();
}
function onBowlerChange() {
    loadHeatmapData();
}
function onHeatmapTypeChange() {
    loadHeatmapData();
}
function startAutoRefresh() {
    if (autoRefresh.value && !refreshInterval) {
        refreshInterval = window.setInterval(() => {
            loadHeatmapData();
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
        loadHeatmapData();
    }
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
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['refresh-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['error-state']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-point']} */ ;
/** @type {__VLS_StyleScopedClasses['points-table']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-section']} */ ;
/** @type {__VLS_StyleScopedClasses['refresh-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-cards']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['controls']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['footer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "heatmap-panel" },
});
/** @type {__VLS_StyleScopedClasses['heatmap-panel']} */ ;
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
if (!__VLS_ctx.loading && __VLS_ctx.selectedPlayer) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.refreshData) },
        ...{ class: "refresh-btn" },
        title: "Refresh heatmap",
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
else if (!__VLS_ctx.selectedPlayer && !__VLS_ctx.selectedBowler) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "no-data-state" },
    });
    /** @type {__VLS_StyleScopedClasses['no-data-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "heatmap-content" },
    });
    /** @type {__VLS_StyleScopedClasses['heatmap-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "controls" },
    });
    /** @type {__VLS_StyleScopedClasses['controls']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        ...{ onChange: (__VLS_ctx.onHeatmapTypeChange) },
        value: (__VLS_ctx.heatmapType),
        ...{ class: "heatmap-select" },
    });
    /** @type {__VLS_StyleScopedClasses['heatmap-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "scoring",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "dismissals",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "release",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        ...{ onChange: (__VLS_ctx.onPlayerChange) },
        value: (__VLS_ctx.selectedPlayer),
        ...{ class: "player-select" },
    });
    /** @type {__VLS_StyleScopedClasses['player-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "p1",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "p2",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "p3",
    });
    if (__VLS_ctx.heatmapType === 'release') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
            ...{ onChange: (__VLS_ctx.onBowlerChange) },
            value: (__VLS_ctx.selectedBowler),
            ...{ class: "player-select" },
        });
        /** @type {__VLS_StyleScopedClasses['player-select']} */ ;
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
            value: "b3",
        });
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pitch-container" },
    });
    /** @type {__VLS_StyleScopedClasses['pitch-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
        ...{ class: "pitch-svg" },
        viewBox: "0 0 100 100",
        xmlns: "http://www.w3.org/2000/svg",
    });
    /** @type {__VLS_StyleScopedClasses['pitch-svg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
        x: "0",
        y: "0",
        width: "100",
        height: "100",
        fill: "#0d5a2c",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "0",
        y1: "50",
        x2: "100",
        y2: "50",
        stroke: "white",
        'stroke-width': "0.5",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "35",
        y1: "0",
        x2: "35",
        y2: "100",
        stroke: "white",
        'stroke-width': "0.5",
        opacity: "0.3",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "65",
        y1: "0",
        x2: "65",
        y2: "100",
        stroke: "white",
        'stroke-width': "0.5",
        opacity: "0.3",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
        cx: "50",
        cy: "5",
        r: "1",
        fill: "yellow",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
        cx: "50",
        cy: "95",
        r: "1",
        fill: "yellow",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "30",
        y1: "10",
        x2: "70",
        y2: "10",
        stroke: "white",
        'stroke-width': "0.3",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "30",
        y1: "90",
        x2: "70",
        y2: "90",
        stroke: "white",
        'stroke-width': "0.3",
    });
    for (const [point] of __VLS_vFor((__VLS_ctx.heatmapData))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            key: (`${point.zone}-${point.x_coordinate}`),
            cx: (point.x_coordinate),
            cy: (point.y_coordinate),
            r: (Math.max(2, (point.count / __VLS_ctx.maxCount) * 5 + 2)),
            fill: (__VLS_ctx.getHeatColor(point.value)),
            opacity: (0.7 + (point.value / 100) * 0.3),
            title: (`${point.zone}: ${point.detail}`),
            ...{ class: "heatmap-point" },
        });
        /** @type {__VLS_StyleScopedClasses['heatmap-point']} */ ;
        // @ts-ignore
        [loading, loading, selectedPlayer, selectedPlayer, selectedPlayer, refreshData, error, error, clearError, selectedBowler, selectedBowler, onHeatmapTypeChange, heatmapType, heatmapType, onPlayerChange, onBowlerChange, heatmapData, maxCount, getHeatColor,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend" },
    });
    /** @type {__VLS_StyleScopedClasses['legend']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-title" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-gradient" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-gradient']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "gradient-bar" },
    });
    /** @type {__VLS_StyleScopedClasses['gradient-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "gradient-labels" },
    });
    /** @type {__VLS_StyleScopedClasses['gradient-labels']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
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
    (__VLS_ctx.totalEvents);
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
    (__VLS_ctx.averageIntensity);
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
    (__VLS_ctx.peakZone);
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
    (__VLS_ctx.coveragePercentage);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "points-table" },
    });
    /** @type {__VLS_StyleScopedClasses['points-table']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [point] of __VLS_vFor((__VLS_ctx.sortedPoints))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (point.zone),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "zone-cell" },
        });
        /** @type {__VLS_StyleScopedClasses['zone-cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "zone-badge" },
            ...{ style: ({ backgroundColor: __VLS_ctx.getHeatColor(point.value) }) },
        });
        /** @type {__VLS_StyleScopedClasses['zone-badge']} */ ;
        (__VLS_ctx.formatZoneName(point.zone));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (point.count);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "intensity-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['intensity-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "intensity-fill" },
            ...{ style: ({
                    width: point.value + '%',
                    backgroundColor: __VLS_ctx.getHeatColor(point.value),
                }) },
        });
        /** @type {__VLS_StyleScopedClasses['intensity-fill']} */ ;
        (Math.round(point.value));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (point.detail);
        // @ts-ignore
        [getHeatColor, getHeatColor, totalEvents, averageIntensity, peakZone, coveragePercentage, sortedPoints, formatZoneName,];
    }
    if (__VLS_ctx.matchupData) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "matchup-section" },
        });
        /** @type {__VLS_StyleScopedClasses['matchup-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "matchup-cards" },
        });
        /** @type {__VLS_StyleScopedClasses['matchup-cards']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "matchup-card" },
        });
        /** @type {__VLS_StyleScopedClasses['matchup-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-label" },
        });
        /** @type {__VLS_StyleScopedClasses['card-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        if (__VLS_ctx.matchupData.dangerous_areas.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (__VLS_ctx.matchupData.dangerous_areas.join(", "));
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "text-muted" },
            });
            /** @type {__VLS_StyleScopedClasses['text-muted']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "matchup-card" },
        });
        /** @type {__VLS_StyleScopedClasses['matchup-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-label" },
        });
        /** @type {__VLS_StyleScopedClasses['card-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        if (__VLS_ctx.matchupData.weak_overlap_areas.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (__VLS_ctx.matchupData.weak_overlap_areas.join(", "));
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "text-muted" },
            });
            /** @type {__VLS_StyleScopedClasses['text-muted']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "matchup-card" },
        });
        /** @type {__VLS_StyleScopedClasses['matchup-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-label" },
        });
        /** @type {__VLS_StyleScopedClasses['card-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-content" },
        });
        /** @type {__VLS_StyleScopedClasses['card-content']} */ ;
        (__VLS_ctx.matchupData.recommendation);
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
[matchupData, matchupData, matchupData, matchupData, matchupData, matchupData, autoRefresh, refreshIntervalSeconds, lastUpdated,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
