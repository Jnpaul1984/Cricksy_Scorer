/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
const activeStat = ref('batters');
const bitterSort = ref('runs');
const bowlerSort = ref('wickets');
const teamSort = ref('wins');
const statTabs = [
    { id: 'batters', icon: '🏏', label: 'Batters' },
    { id: 'bowlers', icon: '🎯', label: 'Bowlers' },
    { id: 'teams', icon: '👥', label: 'Teams' },
    { id: 'records', icon: '🏆', label: 'Records' },
];
// Backend endpoint availability
const backendEndpointAvailable = false;
const requiredEndpoint = 'GET /tournaments/{tournamentId}/leaderboards';
// All generator functions removed - these created celebrity mock data
// When backend available, populate from real tournament leaderboard data
const batters = computed(() => backendEndpointAvailable ? [] : []);
const bowlers = computed(() => backendEndpointAvailable ? [] : []);
const teams = computed(() => backendEndpointAvailable ? [] : []);
const records = computed(() => backendEndpointAvailable ? [] : []);
const sortedBatters = computed(() => {
    const sorted = [...batters.value];
    switch (bitterSort.value) {
        case 'runs':
            return sorted.sort((a, b) => b.runs - a.runs);
        case 'avg':
            return sorted.sort((a, b) => b.average - a.average);
        case 'sr':
            return sorted.sort((a, b) => b.strikeRate - a.strikeRate);
    }
});
const sortedBowlers = computed(() => {
    const sorted = [...bowlers.value];
    switch (bowlerSort.value) {
        case 'wickets':
            return sorted.sort((a, b) => b.wickets - a.wickets);
        case 'economy':
            return sorted.sort((a, b) => a.economy - b.economy);
        case 'avg':
            return sorted.sort((a, b) => a.runs / a.wickets - (b.runs / b.wickets));
    }
});
const sortedTeams = computed(() => {
    const sorted = [...teams.value];
    switch (teamSort.value) {
        case 'wins':
            return sorted.sort((a, b) => b.wins - a.wins);
        case 'avgRuns':
            return sorted.sort((a, b) => b.avgRuns - a.avgRuns);
        case 'winRate':
            return sorted.sort((a, b) => b.wins / (b.wins + b.losses) - a.wins / (a.wins + a.losses));
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['unavailable-message']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['table-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['team-card']} */ ;
/** @type {__VLS_StyleScopedClasses['record-card']} */ ;
/** @type {__VLS_StyleScopedClasses['table-header']} */ ;
/** @type {__VLS_StyleScopedClasses['table-row']} */ ;
/** @type {__VLS_StyleScopedClasses['team-stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['records-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['record-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-stats" },
});
/** @type {__VLS_StyleScopedClasses['fan-stats']} */ ;
if (!__VLS_ctx.backendEndpointAvailable) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-unavailable" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-unavailable']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "unavailable-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['unavailable-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "unavailable-title" },
    });
    /** @type {__VLS_StyleScopedClasses['unavailable-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "unavailable-message" },
    });
    /** @type {__VLS_StyleScopedClasses['unavailable-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({});
    (__VLS_ctx.requiredEndpoint);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "unavailable-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['unavailable-hint']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-header" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
        ...{ class: "stats-title" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "stats-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-tabs" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-tabs']} */ ;
    for (const [tab] of __VLS_vFor((__VLS_ctx.statTabs))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.backendEndpointAvailable))
                        return;
                    __VLS_ctx.activeStat = tab.id;
                    // @ts-ignore
                    [backendEndpointAvailable, requiredEndpoint, statTabs, activeStat,];
                } },
            key: (tab.id),
            ...{ class: "stat-tab" },
            ...{ class: ({ active: __VLS_ctx.activeStat === tab.id }) },
        });
        /** @type {__VLS_StyleScopedClasses['stat-tab']} */ ;
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        (tab.icon);
        (tab.label);
        // @ts-ignore
        [activeStat,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-container" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-container']} */ ;
    if (__VLS_ctx.activeStat === 'batters') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-section" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "section-header" },
        });
        /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
            value: (__VLS_ctx.bitterSort),
            ...{ class: "sort-select" },
        });
        /** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "runs",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "avg",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "sr",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-table" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "table-header" },
        });
        /** @type {__VLS_StyleScopedClasses['table-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-rank" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-rank']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-name" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-name']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        for (const [batter, idx] of __VLS_vFor((__VLS_ctx.sortedBatters))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (batter.id),
                ...{ class: "table-row" },
            });
            /** @type {__VLS_StyleScopedClasses['table-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-rank" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-rank']} */ ;
            (idx + 1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-name" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-name']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-info" },
            });
            /** @type {__VLS_StyleScopedClasses['player-info']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-avatar" },
            });
            /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
            (batter.initials);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-name" },
            });
            /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
            (batter.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-team" },
            });
            /** @type {__VLS_StyleScopedClasses['player-team']} */ ;
            (batter.team);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (batter.runs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (batter.average.toFixed(2));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
                ...{ class: (`sr-${batter.strikeRate > 130 ? 'high' : batter.strikeRate > 100 ? 'normal' : 'low'}`) },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (batter.strikeRate.toFixed(1));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            (batter.matches);
            // @ts-ignore
            [activeStat, bitterSort, sortedBatters,];
        }
    }
    else if (__VLS_ctx.activeStat === 'bowlers') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-section" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "section-header" },
        });
        /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
            value: (__VLS_ctx.bowlerSort),
            ...{ class: "sort-select" },
        });
        /** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "wickets",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "economy",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "avg",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-table" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "table-header" },
        });
        /** @type {__VLS_StyleScopedClasses['table-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-rank" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-rank']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-name" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-name']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "col col-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['col']} */ ;
        /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
        for (const [bowler, idx] of __VLS_vFor((__VLS_ctx.sortedBowlers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (bowler.id),
                ...{ class: "table-row" },
            });
            /** @type {__VLS_StyleScopedClasses['table-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-rank" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-rank']} */ ;
            (idx + 1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-name" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-name']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-info" },
            });
            /** @type {__VLS_StyleScopedClasses['player-info']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-avatar" },
            });
            /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
            (bowler.initials);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-name" },
            });
            /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
            (bowler.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-team" },
            });
            /** @type {__VLS_StyleScopedClasses['player-team']} */ ;
            (bowler.team);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value wickets" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            /** @type {__VLS_StyleScopedClasses['wickets']} */ ;
            (bowler.wickets);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (bowler.runs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
                ...{ class: (`economy-${bowler.economy < 6 ? 'excellent' : bowler.economy < 8 ? 'good' : 'poor'}`) },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (bowler.economy.toFixed(2));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "col col-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['col']} */ ;
            /** @type {__VLS_StyleScopedClasses['col-stat']} */ ;
            (bowler.matches);
            // @ts-ignore
            [activeStat, bowlerSort, sortedBowlers,];
        }
    }
    else if (__VLS_ctx.activeStat === 'teams') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-section" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "section-header" },
        });
        /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
            value: (__VLS_ctx.teamSort),
            ...{ class: "sort-select" },
        });
        /** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "wins",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "avgRuns",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: "winRate",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "team-stats-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['team-stats-grid']} */ ;
        for (const [team] of __VLS_vFor((__VLS_ctx.sortedTeams))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (team.id),
                ...{ class: "team-card" },
            });
            /** @type {__VLS_StyleScopedClasses['team-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "team-header" },
            });
            /** @type {__VLS_StyleScopedClasses['team-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
                ...{ class: "team-name" },
            });
            /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
            (team.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "team-badge" },
                ...{ class: (`badge-${team.wins > team.losses ? 'winning' : 'struggling'}`) },
            });
            /** @type {__VLS_StyleScopedClasses['team-badge']} */ ;
            (team.wins);
            (team.losses);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "team-stats" },
            });
            /** @type {__VLS_StyleScopedClasses['team-stats']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat" },
            });
            /** @type {__VLS_StyleScopedClasses['stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-val" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-val']} */ ;
            (team.avgRuns);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat" },
            });
            /** @type {__VLS_StyleScopedClasses['stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-val" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-val']} */ ;
            (((team.wins / (team.wins + team.losses)) * 100).toFixed(0));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat" },
            });
            /** @type {__VLS_StyleScopedClasses['stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-val" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-val']} */ ;
            (team.wins + team.losses);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "team-form" },
            });
            /** @type {__VLS_StyleScopedClasses['team-form']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "form-label" },
            });
            /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-dots" },
            });
            /** @type {__VLS_StyleScopedClasses['form-dots']} */ ;
            for (const [result, idx] of __VLS_vFor((team.form))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span)({
                    key: (idx),
                    ...{ class: "form-dot" },
                    ...{ class: (`result-${result.toLowerCase()}`) },
                    title: (result),
                });
                /** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
                // @ts-ignore
                [activeStat, teamSort, sortedTeams,];
            }
            // @ts-ignore
            [];
        }
    }
    else if (__VLS_ctx.activeStat === 'records') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-section" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "section-header" },
        });
        /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "records-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['records-grid']} */ ;
        for (const [record] of __VLS_vFor((__VLS_ctx.records))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (record.id),
                ...{ class: "record-card" },
            });
            /** @type {__VLS_StyleScopedClasses['record-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "record-icon" },
            });
            /** @type {__VLS_StyleScopedClasses['record-icon']} */ ;
            (record.icon);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "record-content" },
            });
            /** @type {__VLS_StyleScopedClasses['record-content']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "record-title" },
            });
            /** @type {__VLS_StyleScopedClasses['record-title']} */ ;
            (record.title);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "record-value" },
            });
            /** @type {__VLS_StyleScopedClasses['record-value']} */ ;
            (record.value);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "record-holder" },
            });
            /** @type {__VLS_StyleScopedClasses['record-holder']} */ ;
            (record.holder);
            // @ts-ignore
            [activeStat, records,];
        }
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
