/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { getLeaderboard } from '@/services/playerApi';
const selectedMetric = ref('total_runs');
const loading = ref(true);
const error = ref(null);
const leaderboard = ref(null);
const metricTitles = {
    total_runs: 'Most Runs Scored',
    batting_average: 'Best Batting Average',
    strike_rate: 'Highest Strike Rate',
    centuries: 'Most Centuries',
    total_wickets: 'Most Wickets Taken',
    bowling_average: 'Best Bowling Average',
    economy_rate: 'Best Economy Rate',
    five_wickets: 'Most 5-Wicket Hauls',
};
const metricLabels = {
    total_runs: 'Runs',
    batting_average: 'Average',
    strike_rate: 'SR',
    centuries: '100s',
    total_wickets: 'Wickets',
    bowling_average: 'Average',
    economy_rate: 'Economy',
    five_wickets: '5W',
};
const metricTitle = computed(() => metricTitles[selectedMetric.value]);
const metricLabel = computed(() => metricLabels[selectedMetric.value]);
const loadLeaderboard = async () => {
    loading.value = true;
    error.value = null;
    try {
        leaderboard.value = await getLeaderboard(selectedMetric.value, 10);
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load leaderboard';
    }
    finally {
        loading.value = false;
    }
};
const getRankClass = (rank) => {
    if (rank === 1)
        return 'gold';
    if (rank === 2)
        return 'silver';
    if (rank === 3)
        return 'bronze';
    return '';
};
const getRankDisplay = (rank) => {
    if (rank === 1)
        return '🥇';
    if (rank === 2)
        return '🥈';
    if (rank === 3)
        return '🥉';
    return `#${rank}`;
};
const formatValue = (value) => {
    if (typeof value === 'number') {
        return value.toFixed(2);
    }
    return String(value);
};
const formatAdditionalStats = (stats) => {
    return Object.entries(stats)
        .map(([key, value]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
        return `${label}: ${formatValue(value)}`;
    })
        .join(' | ');
};
const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
};
onMounted(() => {
    loadLeaderboard();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['page-header']} */ ;
/** @type {__VLS_StyleScopedClasses['page-header']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
/** @type {__VLS_StyleScopedClasses['leaderboard-content']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['player-link']} */ ;
/** @type {__VLS_StyleScopedClasses['leaderboard-content']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
/** @type {__VLS_StyleScopedClasses['additional-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "leaderboard-view" },
});
/** @type {__VLS_StyleScopedClasses['leaderboard-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "container" },
});
/** @type {__VLS_StyleScopedClasses['container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "page-header" },
});
/** @type {__VLS_StyleScopedClasses['page-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "metric-selector" },
});
/** @type {__VLS_StyleScopedClasses['metric-selector']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "metric-select",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    ...{ onChange: (__VLS_ctx.loadLeaderboard) },
    id: "metric-select",
    value: (__VLS_ctx.selectedMetric),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "total_runs",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "batting_average",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "strike_rate",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "centuries",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "total_wickets",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "bowling_average",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "economy_rate",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "five_wickets",
});
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-container" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        'aria-busy': "true",
    });
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-container" },
    });
    /** @type {__VLS_StyleScopedClasses['error-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.loadLeaderboard) },
    });
}
else if (__VLS_ctx.leaderboard) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "leaderboard-content" },
    });
    /** @type {__VLS_StyleScopedClasses['leaderboard-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    (__VLS_ctx.metricTitle);
    __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({});
    (__VLS_ctx.formatDate(__VLS_ctx.leaderboard.updated_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "table-responsive" },
    });
    /** @type {__VLS_StyleScopedClasses['table-responsive']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    (__VLS_ctx.metricLabel);
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [entry] of __VLS_vFor((__VLS_ctx.leaderboard.entries))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (entry.player_id),
            ...{ class: ({ 'top-three': entry.rank <= 3 }) },
        });
        /** @type {__VLS_StyleScopedClasses['top-three']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "rank-badge" },
            ...{ class: (__VLS_ctx.getRankClass(entry.rank)) },
        });
        /** @type {__VLS_StyleScopedClasses['rank-badge']} */ ;
        (__VLS_ctx.getRankDisplay(entry.rank));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
            href: (`/players/${entry.player_id}/profile`),
            ...{ class: "player-link" },
        });
        /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
        (entry.player_name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "metric-value" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
        (__VLS_ctx.formatValue(entry.value));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "additional-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['additional-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({});
        (__VLS_ctx.formatAdditionalStats(entry.additional_stats));
        // @ts-ignore
        [loadLeaderboard, loadLeaderboard, selectedMetric, loading, error, error, leaderboard, leaderboard, leaderboard, metricTitle, formatDate, metricLabel, getRankClass, getRankDisplay, formatValue, formatAdditionalStats,];
    }
    if (__VLS_ctx.leaderboard.entries.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "no-data" },
        });
        /** @type {__VLS_StyleScopedClasses['no-data']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
// @ts-ignore
[leaderboard,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
