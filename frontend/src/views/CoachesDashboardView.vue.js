/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { BaseCard, BaseButton, BaseBadge, BaseInput } from '@/components';
import DevDashboardWidget from '@/components/DevDashboardWidget.vue';
import LiveMatchCardCoach from '@/components/LiveMatchCardCoach.vue';
import { useGameStore } from '@/stores/gameStore';
const router = useRouter();
const gameStore = useGameStore();
// --- Selectors (readonly) ---
const selectedTeam = ref('');
// Pull current game ID from store if available
const currentGameId = computed(() => gameStore.currentGame?.id ?? '');
const hasActiveMatch = computed(() => !!currentGameId.value);
const matchStatus = computed(() => {
    if (!hasActiveMatch.value)
        return 'NO MATCH';
    const status = gameStore.currentGame?.status;
    if (status === 'IN_PROGRESS')
        return 'LIVE';
    if (status === 'COMPLETED')
        return 'COMPLETED';
    return status ?? 'PENDING';
});
const matchStatusVariant = computed(() => {
    switch (matchStatus.value) {
        case 'LIVE':
            return 'success';
        case 'COMPLETED':
            return 'neutral';
        case 'NO MATCH':
            return 'warning';
        default:
            return 'neutral';
    }
});
// --- Key Players (FIX A5: Use real scorecard data) ---
const keyPlayers = computed(() => {
    const battingScorecard = gameStore.currentGame?.batting_scorecard ?? {};
    const bowlingScorecard = gameStore.currentGame?.bowling_scorecard ?? {};
    // Combine batting and bowling stats for players
    const playerStats = {};
    // Add batting stats
    Object.entries(battingScorecard).forEach(([id, stats]) => {
        playerStats[id] = {
            id,
            name: stats.player_name,
            runs: stats.runs,
            ballsFaced: stats.balls_faced,
            wickets: 0,
            roles: []
        };
    });
    // Add bowling stats
    Object.entries(bowlingScorecard).forEach(([id, stats]) => {
        if (playerStats[id]) {
            playerStats[id].wickets = stats.wickets_taken;
        }
        else {
            playerStats[id] = {
                id,
                name: stats.player_name,
                runs: 0,
                ballsFaced: 0,
                wickets: stats.wickets_taken,
                roles: []
            };
        }
    });
    // Calculate average and sort by impact
    return Object.values(playerStats)
        .map(p => ({
        ...p,
        avg: p.ballsFaced > 0 ? (p.runs / p.ballsFaced * 100) : 0, // Strike rate
    }))
        .sort((a, b) => (b.runs + b.wickets * 20) - (a.runs + a.wickets * 20)) // Simple impact score
        .slice(0, 6);
});
// --- Season Stats (TODO: Wire to API when org endpoints ready) ---
const seasonStats = ref({
    matches: 0,
    wins: 0,
    losses: 0,
    nrr: '—',
});
// Note: Blocked by backend - needs GET /organizations/{orgId}/stats
// --- Coach Notes (local only for now) ---
const coachNote = ref('');
const noteSaved = ref(false);
function saveNote() {
    // TODO: Persist to backend or local storage
    noteSaved.value = true;
    setTimeout(() => {
        noteSaved.value = false;
    }, 2000);
}
// --- Navigation Actions ---
function openScoring() {
    if (currentGameId.value) {
        router.push({ name: 'GameScoringView', params: { gameId: currentGameId.value } });
    }
    else {
        router.push({ name: 'setup' });
    }
}
function openAnalyst() {
    router.push({ name: 'AnalystWorkspace' });
}
function goToSetup() {
    router.push({ name: 'setup' });
}
function goToLeaderboard() {
    router.push({ name: 'leaderboard' });
}
function goToAnalytics() {
    router.push({ name: 'AnalyticsView' });
}
function goToVideoSessions() {
    router.push({ name: 'CoachProPlusVideoSessions' });
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['notes-input']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coaches-page" },
});
/** @type {__VLS_StyleScopedClasses['coaches-page']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "section",
    padding: "lg",
    ...{ class: "coaches-dashboard" },
}));
const __VLS_2 = __VLS_1({
    as: "section",
    padding: "lg",
    ...{ class: "coaches-dashboard" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['coaches-dashboard']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "dashboard-header" },
});
/** @type {__VLS_StyleScopedClasses['dashboard-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "title-block" },
});
/** @type {__VLS_StyleScopedClasses['title-block']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-actions" },
});
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
BaseInput;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    modelValue: (__VLS_ctx.selectedTeam),
    placeholder: "Select team...",
    ...{ class: "team-selector" },
}));
const __VLS_8 = __VLS_7({
    modelValue: (__VLS_ctx.selectedTeam),
    placeholder: "Select team...",
    ...{ class: "team-selector" },
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
/** @type {__VLS_StyleScopedClasses['team-selector']} */ ;
let __VLS_11;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent1(__VLS_11, new __VLS_11({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}));
const __VLS_13 = __VLS_12({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_12));
let __VLS_16;
const __VLS_17 = ({ click: {} },
    { onClick: (__VLS_ctx.openScoring) });
const { default: __VLS_18 } = __VLS_14.slots;
// @ts-ignore
[selectedTeam, openScoring,];
var __VLS_14;
var __VLS_15;
let __VLS_19;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_20 = __VLS_asFunctionalComponent1(__VLS_19, new __VLS_19({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_21 = __VLS_20({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_20));
let __VLS_24;
const __VLS_25 = ({ click: {} },
    { onClick: (__VLS_ctx.openAnalyst) });
const { default: __VLS_26 } = __VLS_22.slots;
// @ts-ignore
[openAnalyst,];
var __VLS_22;
var __VLS_23;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid-main" },
});
/** @type {__VLS_StyleScopedClasses['grid-main']} */ ;
let __VLS_27;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_28 = __VLS_asFunctionalComponent1(__VLS_27, new __VLS_27({
    as: "section",
    padding: "md",
    ...{ class: "match-snapshot" },
}));
const __VLS_29 = __VLS_28({
    as: "section",
    padding: "md",
    ...{ class: "match-snapshot" },
}, ...__VLS_functionalComponentArgsRest(__VLS_28));
/** @type {__VLS_StyleScopedClasses['match-snapshot']} */ ;
const { default: __VLS_32 } = __VLS_30.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header" },
});
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
let __VLS_33;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_34 = __VLS_asFunctionalComponent1(__VLS_33, new __VLS_33({
    variant: (__VLS_ctx.matchStatusVariant),
}));
const __VLS_35 = __VLS_34({
    variant: (__VLS_ctx.matchStatusVariant),
}, ...__VLS_functionalComponentArgsRest(__VLS_34));
const { default: __VLS_38 } = __VLS_36.slots;
(__VLS_ctx.matchStatus);
// @ts-ignore
[matchStatusVariant, matchStatus,];
var __VLS_36;
if (__VLS_ctx.hasActiveMatch) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "scoreboard-container" },
    });
    /** @type {__VLS_StyleScopedClasses['scoreboard-container']} */ ;
    const __VLS_39 = LiveMatchCardCoach;
    // @ts-ignore
    const __VLS_40 = __VLS_asFunctionalComponent1(__VLS_39, new __VLS_39({
        gameId: (__VLS_ctx.currentGameId),
        canAction: (true),
    }));
    const __VLS_41 = __VLS_40({
        gameId: (__VLS_ctx.currentGameId),
        canAction: (true),
    }, ...__VLS_functionalComponentArgsRest(__VLS_40));
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    let __VLS_44;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent1(__VLS_44, new __VLS_44({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
    }));
    const __VLS_46 = __VLS_45({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    let __VLS_49;
    const __VLS_50 = ({ click: {} },
        { onClick: (__VLS_ctx.goToSetup) });
    const { default: __VLS_51 } = __VLS_47.slots;
    // @ts-ignore
    [hasActiveMatch, currentGameId, goToSetup,];
    var __VLS_47;
    var __VLS_48;
}
// @ts-ignore
[];
var __VLS_30;
let __VLS_52;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_53 = __VLS_asFunctionalComponent1(__VLS_52, new __VLS_52({
    as: "section",
    padding: "md",
    ...{ class: "key-players" },
}));
const __VLS_54 = __VLS_53({
    as: "section",
    padding: "md",
    ...{ class: "key-players" },
}, ...__VLS_functionalComponentArgsRest(__VLS_53));
/** @type {__VLS_StyleScopedClasses['key-players']} */ ;
const { default: __VLS_57 } = __VLS_55.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header" },
});
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "players-grid" },
});
/** @type {__VLS_StyleScopedClasses['players-grid']} */ ;
for (const [player] of __VLS_vFor((__VLS_ctx.keyPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (player.id),
        ...{ class: "player-card" },
    });
    /** @type {__VLS_StyleScopedClasses['player-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-info" },
    });
    /** @type {__VLS_StyleScopedClasses['player-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "player-name" },
    });
    /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
    (player.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-roles" },
    });
    /** @type {__VLS_StyleScopedClasses['player-roles']} */ ;
    for (const [role] of __VLS_vFor((player.roles))) {
        let __VLS_58;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_59 = __VLS_asFunctionalComponent1(__VLS_58, new __VLS_58({
            key: (role),
            variant: "neutral",
            condensed: true,
        }));
        const __VLS_60 = __VLS_59({
            key: (role),
            variant: "neutral",
            condensed: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_59));
        const { default: __VLS_63 } = __VLS_61.slots;
        (role);
        // @ts-ignore
        [keyPlayers,];
        var __VLS_61;
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['player-stats']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.runs);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.wickets);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (player.avg);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    // @ts-ignore
    [];
}
// @ts-ignore
[];
var __VLS_55;
__VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
    ...{ class: "grid-side" },
});
/** @type {__VLS_StyleScopedClasses['grid-side']} */ ;
let __VLS_64;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_65 = __VLS_asFunctionalComponent1(__VLS_64, new __VLS_64({
    as: "section",
    padding: "md",
    ...{ class: "quick-stats" },
}));
const __VLS_66 = __VLS_65({
    as: "section",
    padding: "md",
    ...{ class: "quick-stats" },
}, ...__VLS_functionalComponentArgsRest(__VLS_65));
/** @type {__VLS_StyleScopedClasses['quick-stats']} */ ;
const { default: __VLS_69 } = __VLS_67.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stats-grid" },
});
/** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-tile" },
});
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.seasonStats.matches);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-tile" },
});
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.seasonStats.wins);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-tile" },
});
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.seasonStats.losses);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-tile" },
});
/** @type {__VLS_StyleScopedClasses['stat-tile']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.seasonStats.nrr);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
// @ts-ignore
[seasonStats, seasonStats, seasonStats, seasonStats,];
var __VLS_67;
let __VLS_70;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_71 = __VLS_asFunctionalComponent1(__VLS_70, new __VLS_70({
    as: "section",
    padding: "md",
    ...{ class: "coach-notes" },
}));
const __VLS_72 = __VLS_71({
    as: "section",
    padding: "md",
    ...{ class: "coach-notes" },
}, ...__VLS_functionalComponentArgsRest(__VLS_71));
/** @type {__VLS_StyleScopedClasses['coach-notes']} */ ;
const { default: __VLS_75 } = __VLS_73.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.coachNote),
    ...{ class: "notes-input" },
    placeholder: "Add notes about tactics, player form, or upcoming match prep...",
    rows: "6",
});
/** @type {__VLS_StyleScopedClasses['notes-input']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "notes-actions" },
});
/** @type {__VLS_StyleScopedClasses['notes-actions']} */ ;
let __VLS_76;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent1(__VLS_76, new __VLS_76({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "sm",
    disabled: (!__VLS_ctx.coachNote.trim()),
}));
const __VLS_78 = __VLS_77({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "sm",
    disabled: (!__VLS_ctx.coachNote.trim()),
}, ...__VLS_functionalComponentArgsRest(__VLS_77));
let __VLS_81;
const __VLS_82 = ({ click: {} },
    { onClick: (__VLS_ctx.saveNote) });
const { default: __VLS_83 } = __VLS_79.slots;
// @ts-ignore
[coachNote, coachNote, saveNote,];
var __VLS_79;
var __VLS_80;
if (__VLS_ctx.noteSaved) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "note-saved" },
    });
    /** @type {__VLS_StyleScopedClasses['note-saved']} */ ;
}
// @ts-ignore
[noteSaved,];
var __VLS_73;
let __VLS_84;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_85 = __VLS_asFunctionalComponent1(__VLS_84, new __VLS_84({
    as: "section",
    padding: "md",
    ...{ class: "quick-links" },
}));
const __VLS_86 = __VLS_85({
    as: "section",
    padding: "md",
    ...{ class: "quick-links" },
}, ...__VLS_functionalComponentArgsRest(__VLS_85));
/** @type {__VLS_StyleScopedClasses['quick-links']} */ ;
const { default: __VLS_89 } = __VLS_87.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "links-list" },
});
/** @type {__VLS_StyleScopedClasses['links-list']} */ ;
let __VLS_90;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_91 = __VLS_asFunctionalComponent1(__VLS_90, new __VLS_90({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}));
const __VLS_92 = __VLS_91({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_91));
let __VLS_95;
const __VLS_96 = ({ click: {} },
    { onClick: (__VLS_ctx.goToLeaderboard) });
const { default: __VLS_97 } = __VLS_93.slots;
// @ts-ignore
[goToLeaderboard,];
var __VLS_93;
var __VLS_94;
let __VLS_98;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_99 = __VLS_asFunctionalComponent1(__VLS_98, new __VLS_98({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}));
const __VLS_100 = __VLS_99({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_99));
let __VLS_103;
const __VLS_104 = ({ click: {} },
    { onClick: (__VLS_ctx.goToAnalytics) });
const { default: __VLS_105 } = __VLS_101.slots;
// @ts-ignore
[goToAnalytics,];
var __VLS_101;
var __VLS_102;
let __VLS_106;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_107 = __VLS_asFunctionalComponent1(__VLS_106, new __VLS_106({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}));
const __VLS_108 = __VLS_107({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    fullWidth: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_107));
let __VLS_111;
const __VLS_112 = ({ click: {} },
    { onClick: (__VLS_ctx.goToVideoSessions) });
const { default: __VLS_113 } = __VLS_109.slots;
// @ts-ignore
[goToVideoSessions,];
var __VLS_109;
var __VLS_110;
// @ts-ignore
[];
var __VLS_87;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dev-dashboard-section" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['dev-dashboard-section']} */ ;
const __VLS_114 = DevDashboardWidget;
// @ts-ignore
const __VLS_115 = __VLS_asFunctionalComponent1(__VLS_114, new __VLS_114({}));
const __VLS_116 = __VLS_115({}, ...__VLS_functionalComponentArgsRest(__VLS_115));
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
