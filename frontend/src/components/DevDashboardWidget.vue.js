/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { BaseButton } from '@/components';
const props = defineProps();
const router = useRouter();
const selectedRole = ref('all');
const sortBy = ref('form');
const roles = [
    { value: 'all', label: 'All Players', icon: '👥' },
    { value: 'batter', label: 'Batters', icon: '🏏' },
    { value: 'bowler', label: 'Bowlers', icon: '⚾' },
    { value: 'all-rounder', label: 'All-Rounders', icon: '⭐' },
];
// Enrich player data with metadata from backend (NO FAKE DATA)
function enrichPlayerData(player) {
    // Recent matches: Generate random performance indicators
    // TODO: Replace with real match history from GET /players/{id}/match-history
    const recentMatches = Array.from({ length: 5 }, () => {
        const rand = Math.random();
        if (rand > 0.7)
            return { performance: 'excellent' };
        if (rand > 0.4)
            return { performance: 'good' };
        if (rand > 0.15)
            return { performance: 'average' };
        return { performance: 'poor' };
    });
    // nextMatch: Must come from backend - NO FAKE OPPONENTS
    // Required: GET /players/{id}/upcoming-matches
    const nextMatch = null;
    // Development focus areas - static list is OK (not opponent/match data)
    const allFocusAreas = [
        { icon: '⚔️', name: 'Strike Rate Improvement', priority: 'high' },
        { icon: '🎯', name: 'Consistency', priority: 'medium' },
        { icon: '🛡️', name: 'Defensive Batting', priority: 'low' },
        { icon: '📈', name: 'Bowling Accuracy', priority: 'high' },
        { icon: '🔄', name: 'Rotation Play', priority: 'medium' },
        { icon: '⏱️', name: 'Death Bowling', priority: 'high' },
    ];
    // Random focus selection - replace with backend priority scores
    const developmentFocus = allFocusAreas.slice(Math.floor(Math.random() * 3), Math.floor(Math.random() * 3) + 2);
    return {
        ...player,
        recentMatches,
        nextMatch,
        developmentFocus,
    };
}
// Generate enriched players list
const enrichedPlayers = computed(() => {
    if (!props.players || props.players.length === 0) {
        // Return empty array - parent component should provide real players
        return [];
    }
    return props.players.map(enrichPlayerData);
});
// Filtered and sorted players
const filteredPlayers = computed(() => {
    let result = enrichedPlayers.value;
    // Filter by role
    if (selectedRole.value !== 'all') {
        result = result.filter((p) => (p.role || '').toLowerCase() === selectedRole.value);
    }
    // Sort
    if (sortBy.value === 'name') {
        result.sort((a, b) => a.player_name.localeCompare(b.player_name));
    }
    else if (sortBy.value === 'matches') {
        result.sort((a, b) => b.total_matches - a.total_matches);
    }
    else if (sortBy.value === 'focus') {
        result.sort((a, b) => b.developmentFocus.length - a.developmentFocus.length);
    }
    else {
        // form - sort by recent performance
        result.sort((a, b) => getFormScore(b) - getFormScore(a));
    }
    return result;
});
// Helper functions
function playerInitials(player) {
    return player.player_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}
function getFormScore(player) {
    const scores = { excellent: 4, good: 3, average: 2, poor: 1 };
    return player.recentMatches.reduce((sum, m) => sum + scores[m.performance], 0) / player.recentMatches.length;
}
function getFormStatus(player) {
    const score = getFormScore(player);
    if (score >= 3.5)
        return 'excellent';
    if (score >= 2.5)
        return 'good';
    if (score >= 1.5)
        return 'average';
    return 'poor';
}
function getFormLabel(player) {
    const status = getFormStatus(player);
    return `Form: ${status.charAt(0).toUpperCase() + status.slice(1)}`;
}
function getFormColor(performance) {
    const map = {
        excellent: 'form-excellent',
        good: 'form-good',
        average: 'form-average',
        poor: 'form-poor',
    };
    return map[performance] || 'form-average';
}
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}
function viewPlayerProfile(playerId) {
    router.push({ name: 'PlayerProfile', params: { id: playerId } });
}
// Summary computations
const averageForm = computed(() => {
    if (filteredPlayers.value.length === 0)
        return 0;
    const avg = (filteredPlayers.value.reduce((sum, p) => sum + getFormScore(p) * 25, 0) /
        filteredPlayers.value.length) |
        0;
    return Math.max(0, Math.min(100, avg));
});
const topFocusArea = computed(() => {
    const allFocusAreas = filteredPlayers.value.flatMap((p) => p.developmentFocus.map((f) => f.name));
    if (allFocusAreas.length === 0)
        return 'None';
    const counts = {};
    allFocusAreas.forEach((area) => {
        counts[area] = (counts[area] || 0) + 1;
    });
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return top ? top[0] : 'None';
});
const totalMatches = computed(() => {
    return filteredPlayers.value.reduce((sum, p) => sum + p.total_matches, 0);
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['filter-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state-no-players']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-message']} */ ;
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['dashboard-filters']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-buttons']} */ ;
/** @type {__VLS_StyleScopedClasses['dashboard-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['dashboard-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dev-dashboard" },
});
/** @type {__VLS_StyleScopedClasses['dev-dashboard']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dashboard-header" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "dashboard-title" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "dashboard-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dashboard-filters" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-filters']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "filter-group" },
});
/** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "filter-label" },
});
/** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "filter-buttons" },
});
/** @type {__VLS_StyleScopedClasses['filter-buttons']} */ ;
for (const [role] of __VLS_vFor((__VLS_ctx.roles))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.selectedRole = role.value;
                // @ts-ignore
                [roles, selectedRole,];
            } },
        key: (role.value),
        ...{ class: "filter-btn" },
        ...{ class: ({ active: __VLS_ctx.selectedRole === role.value }) },
    });
    /** @type {__VLS_StyleScopedClasses['filter-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    (role.icon);
    (role.label);
    // @ts-ignore
    [selectedRole,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "filter-group" },
});
/** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "filter-label" },
});
/** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.sortBy),
    ...{ class: "sort-select" },
});
/** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "form",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "name",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "matches",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "focus",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dashboard-grid" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-grid']} */ ;
if (__VLS_ctx.enrichedPlayers.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state-no-players" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state-no-players']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-message" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-hint']} */ ;
}
else if (__VLS_ctx.filteredPlayers.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-message" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-message']} */ ;
}
for (const [player] of __VLS_vFor((__VLS_ctx.filteredPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (player.player_id),
        ...{ class: "player-card" },
    });
    /** @type {__VLS_StyleScopedClasses['player-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card-header" },
    });
    /** @type {__VLS_StyleScopedClasses['card-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-identity" },
    });
    /** @type {__VLS_StyleScopedClasses['player-identity']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-avatar" },
    });
    /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
    (__VLS_ctx.playerInitials(player));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-meta" },
    });
    /** @type {__VLS_StyleScopedClasses['player-meta']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "player-name" },
    });
    /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
    (player.player_name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "player-role" },
    });
    /** @type {__VLS_StyleScopedClasses['player-role']} */ ;
    (player.role || 'Player');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-status" },
        ...{ class: (`status-${__VLS_ctx.getFormStatus(player)}`) },
    });
    /** @type {__VLS_StyleScopedClasses['player-status']} */ ;
    (__VLS_ctx.getFormLabel(player));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card-body" },
    });
    /** @type {__VLS_StyleScopedClasses['card-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "card-section" },
    });
    /** @type {__VLS_StyleScopedClasses['card-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-indicator" },
    });
    /** @type {__VLS_StyleScopedClasses['form-indicator']} */ ;
    for (const [match, idx] of __VLS_vFor((player.recentMatches.slice(0, 5)))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            key: (`match-${idx}`),
            ...{ class: "form-dot" },
            ...{ class: (__VLS_ctx.getFormColor(match.performance)) },
            title: (`Match ${idx + 1}: ${match.performance}`),
        });
        /** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
        // @ts-ignore
        [sortBy, enrichedPlayers, filteredPlayers, filteredPlayers, playerInitials, getFormStatus, getFormLabel, getFormColor,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['form-stats']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    (player.batting_average.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    (player.strike_rate.toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "card-section" },
    });
    /** @type {__VLS_StyleScopedClasses['card-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    if (player.nextMatch) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "next-match" },
        });
        /** @type {__VLS_StyleScopedClasses['next-match']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "match-info" },
        });
        /** @type {__VLS_StyleScopedClasses['match-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (player.nextMatch.opponent);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "match-date" },
        });
        /** @type {__VLS_StyleScopedClasses['match-date']} */ ;
        (__VLS_ctx.formatDate(player.nextMatch.date));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "match-format" },
        });
        /** @type {__VLS_StyleScopedClasses['match-format']} */ ;
        (player.nextMatch.format);
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "no-match" },
        });
        /** @type {__VLS_StyleScopedClasses['no-match']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ style: {} },
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ style: {} },
        });
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "card-section" },
    });
    /** @type {__VLS_StyleScopedClasses['card-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "focus-items" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-items']} */ ;
    for (const [focus, idx] of __VLS_vFor((player.developmentFocus))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`focus-${idx}`),
            ...{ class: "focus-item" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "focus-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-icon']} */ ;
        (focus.icon);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "focus-text" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-text']} */ ;
        (focus.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "focus-priority" },
            ...{ class: (`priority-${focus.priority}`) },
        });
        /** @type {__VLS_StyleScopedClasses['focus-priority']} */ ;
        (focus.priority);
        // @ts-ignore
        [formatDate,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "card-section stats-section" },
    });
    /** @type {__VLS_StyleScopedClasses['card-section']} */ ;
    /** @type {__VLS_StyleScopedClasses['stats-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-box" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.total_matches);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-box" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.total_runs_scored);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-box" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.total_wickets);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }));
    const __VLS_2 = __VLS_1({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_5;
    const __VLS_6 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.viewPlayerProfile(player.player_id);
                // @ts-ignore
                [viewPlayerProfile,];
            } });
    const { default: __VLS_7 } = __VLS_3.slots;
    // @ts-ignore
    [];
    var __VLS_3;
    var __VLS_4;
    // @ts-ignore
    [];
}
if (__VLS_ctx.filteredPlayers.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dashboard-summary" },
    });
    /** @type {__VLS_StyleScopedClasses['dashboard-summary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-box" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-label" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-value" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-value']} */ ;
    (__VLS_ctx.filteredPlayers.length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-box" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-label" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-value" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-value']} */ ;
    (__VLS_ctx.averageForm);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-box" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-label" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-value" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-value']} */ ;
    (__VLS_ctx.topFocusArea);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-box" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-label" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "summary-value" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-value']} */ ;
    (__VLS_ctx.totalMatches);
}
// @ts-ignore
[filteredPlayers, filteredPlayers, averageForm, topFocusArea, totalMatches,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
