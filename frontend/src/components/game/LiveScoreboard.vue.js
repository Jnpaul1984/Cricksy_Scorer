/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import { useRoleBadge } from '@/composables/useRoleBadge';
import { useGameStore } from '@/stores/gameStore';
const gameStore = useGameStore();
// Captain/Keeper badge composable
const currentGame = computed(() => gameStore.currentGame);
const teamAName = computed(() => String(currentGame.value?.team_a?.name ?? ''));
// Note: battingTeamName is defined below in "Computed properties" section
const isBattingTeamA = computed(() => String(currentGame.value?.batting_team_name ?? '') === teamAName.value);
const { roleBadge } = useRoleBadge({ currentGame, isBattingTeamA });
// Props (none needed - component reads from store)
// Current striker/non-striker
const strikerId = computed(() => String(currentGame.value?.current_striker_id ?? ''));
const nonStrikerId = computed(() => String(currentGame.value?.current_non_striker_id ?? ''));
const strikerName = computed(() => {
    const id = strikerId.value;
    if (!id || !currentGame.value)
        return '';
    const players = [
        ...(currentGame.value.team_a?.players || []),
        ...(currentGame.value.team_b?.players || []),
    ];
    return players.find((p) => String(p.id) === id)?.name || '';
});
const nonStrikerName = computed(() => {
    const id = nonStrikerId.value;
    if (!id || !currentGame.value)
        return '';
    const players = [
        ...(currentGame.value.team_a?.players || []),
        ...(currentGame.value.team_b?.players || []),
    ];
    return players.find((p) => String(p.id) === id)?.name || '';
});
// Computed properties
const battingTeamName = computed(() => gameStore.currentGame?.batting_team_name || 'Team');
const totalRuns = computed(() => gameStore.currentGame?.total_runs || 0);
const totalWickets = computed(() => gameStore.currentGame?.total_wickets || 0);
const currentInning = computed(() => gameStore.currentGame?.current_inning || 1);
const oversDisplay = computed(() => {
    if (!gameStore.currentGame)
        return '0.0';
    const { overs_completed, balls_this_over } = gameStore.currentGame;
    return `${overs_completed}.${balls_this_over}`;
});
const targetRuns = computed(() => gameStore.currentGame?.target || null);
const runsRequired = computed(() => {
    if (!targetRuns.value || !gameStore.currentGame)
        return null;
    const required = targetRuns.value - gameStore.currentGame.total_runs;
    return required > 0 ? required : null;
});
const gameStatusText = computed(() => {
    const status = String(gameStore.currentGame?.status || '').toLowerCase();
    switch (status) {
        case 'in_progress':
            return 'Live';
        case 'innings_break':
            return 'Innings Break';
        case 'completed':
            return gameStore.currentGame?.result || 'Match Completed';
        default:
            return 'Waiting';
    }
});
const statusClass = computed(() => {
    const status = String(gameStore.currentGame?.status || '').toLowerCase();
    return {
        'status-live': status === 'in_progress',
        'status-break': status === 'innings_break',
        'status-completed': status === 'completed',
    };
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['batter']} */ ;
/** @type {__VLS_StyleScopedClasses['live-scoreboard']} */ ;
/** @type {__VLS_StyleScopedClasses['main-score']} */ ;
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
/** @type {__VLS_StyleScopedClasses['scoreboard-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "live-scoreboard" },
});
/** @type {__VLS_StyleScopedClasses['live-scoreboard']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "scoreboard-header" },
});
/** @type {__VLS_StyleScopedClasses['scoreboard-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "team-name" },
});
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
(__VLS_ctx.battingTeamName);
if (__VLS_ctx.currentInning > 1) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "innings-indicator" },
    });
    /** @type {__VLS_StyleScopedClasses['innings-indicator']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "score-display" },
});
/** @type {__VLS_StyleScopedClasses['score-display']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "main-score" },
});
/** @type {__VLS_StyleScopedClasses['main-score']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "runs" },
});
/** @type {__VLS_StyleScopedClasses['runs']} */ ;
(__VLS_ctx.totalRuns);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "separator" },
});
/** @type {__VLS_StyleScopedClasses['separator']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "wickets" },
});
/** @type {__VLS_StyleScopedClasses['wickets']} */ ;
(__VLS_ctx.totalWickets);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "overs-display" },
});
/** @type {__VLS_StyleScopedClasses['overs-display']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "overs-label" },
});
/** @type {__VLS_StyleScopedClasses['overs-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "overs-value" },
});
/** @type {__VLS_StyleScopedClasses['overs-value']} */ ;
(__VLS_ctx.oversDisplay);
if (__VLS_ctx.strikerName || __VLS_ctx.nonStrikerName) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "batters-display" },
    });
    /** @type {__VLS_StyleScopedClasses['batters-display']} */ ;
    if (__VLS_ctx.strikerName) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "batter striker" },
        });
        /** @type {__VLS_StyleScopedClasses['batter']} */ ;
        /** @type {__VLS_StyleScopedClasses['striker']} */ ;
        (__VLS_ctx.strikerName);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
        (__VLS_ctx.roleBadge(__VLS_ctx.strikerId));
    }
    if (__VLS_ctx.strikerName && __VLS_ctx.nonStrikerName) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "separator-dot" },
        });
        /** @type {__VLS_StyleScopedClasses['separator-dot']} */ ;
    }
    if (__VLS_ctx.nonStrikerName) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "batter" },
        });
        /** @type {__VLS_StyleScopedClasses['batter']} */ ;
        (__VLS_ctx.nonStrikerName);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
        (__VLS_ctx.roleBadge(__VLS_ctx.nonStrikerId));
    }
}
if (__VLS_ctx.targetRuns) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "target-display" },
    });
    /** @type {__VLS_StyleScopedClasses['target-display']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "target-label" },
    });
    /** @type {__VLS_StyleScopedClasses['target-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "target-value" },
    });
    /** @type {__VLS_StyleScopedClasses['target-value']} */ ;
    (__VLS_ctx.targetRuns);
    if (__VLS_ctx.runsRequired) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "required-info" },
        });
        /** @type {__VLS_StyleScopedClasses['required-info']} */ ;
        (__VLS_ctx.runsRequired);
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "game-status" },
    ...{ class: (__VLS_ctx.statusClass) },
});
/** @type {__VLS_StyleScopedClasses['game-status']} */ ;
(__VLS_ctx.gameStatusText);
// @ts-ignore
[battingTeamName, currentInning, totalRuns, totalWickets, oversDisplay, strikerName, strikerName, strikerName, strikerName, nonStrikerName, nonStrikerName, nonStrikerName, nonStrikerName, roleBadge, roleBadge, strikerId, nonStrikerId, targetRuns, targetRuns, runsRequired, runsRequired, statusClass, gameStatusText,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
