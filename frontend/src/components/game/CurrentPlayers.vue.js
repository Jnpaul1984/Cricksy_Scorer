/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import { useGameStore } from '@/stores/gameStore';
const gameStore = useGameStore();
// Computed properties
const strikerName = computed(() => gameStore.currentStriker?.name || null);
const nonStrikerName = computed(() => gameStore.currentNonStriker?.name || null);
const bowlerName = computed(() => gameStore.selectedBowler?.name || null);
const strikerStats = computed(() => {
    if (!gameStore.currentGame?.current_striker_id)
        return null;
    return gameStore.currentGame.batting_scorecard[gameStore.currentGame.current_striker_id] || null;
});
const nonStrikerStats = computed(() => {
    if (!gameStore.currentGame?.current_non_striker_id)
        return null;
    return gameStore.currentGame.batting_scorecard[gameStore.currentGame.current_non_striker_id] || null;
});
const bowlerStats = computed(() => {
    if (!gameStore.uiState.selectedBowlerId)
        return null;
    return gameStore.currentGame?.bowling_scorecard[gameStore.uiState.selectedBowlerId] || null;
});
const canSwapBatsmen = computed(() => strikerName.value && nonStrikerName.value && gameStore.isGameActive);
const loading = computed(() => gameStore.uiState.loading);
// Methods
const handleSwapBatsmen = () => {
    gameStore.swapBatsmen();
};
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['swap-button']} */ ;
/** @type {__VLS_StyleScopedClasses['swap-button']} */ ;
/** @type {__VLS_StyleScopedClasses['swap-button']} */ ;
/** @type {__VLS_StyleScopedClasses['current-players']} */ ;
/** @type {__VLS_StyleScopedClasses['players-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "current-players" },
});
/** @type {__VLS_StyleScopedClasses['current-players']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "players-grid" },
});
/** @type {__VLS_StyleScopedClasses['players-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-card striker" },
});
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['striker']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-role" },
});
/** @type {__VLS_StyleScopedClasses['player-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-icon" },
});
/** @type {__VLS_StyleScopedClasses['role-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-text" },
});
/** @type {__VLS_StyleScopedClasses['role-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-info" },
});
/** @type {__VLS_StyleScopedClasses['player-info']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-name" },
});
/** @type {__VLS_StyleScopedClasses['player-name']} */ ;
(__VLS_ctx.strikerName || 'Not selected');
if (__VLS_ctx.strikerStats) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['player-stats']} */ ;
    (__VLS_ctx.strikerStats.runs);
    (__VLS_ctx.strikerStats.balls_faced);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-card non-striker" },
});
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['non-striker']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-role" },
});
/** @type {__VLS_StyleScopedClasses['player-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-icon" },
});
/** @type {__VLS_StyleScopedClasses['role-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-text" },
});
/** @type {__VLS_StyleScopedClasses['role-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-info" },
});
/** @type {__VLS_StyleScopedClasses['player-info']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-name" },
});
/** @type {__VLS_StyleScopedClasses['player-name']} */ ;
(__VLS_ctx.nonStrikerName || 'Not selected');
if (__VLS_ctx.nonStrikerStats) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['player-stats']} */ ;
    (__VLS_ctx.nonStrikerStats.runs);
    (__VLS_ctx.nonStrikerStats.balls_faced);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-card bowler" },
});
/** @type {__VLS_StyleScopedClasses['player-card']} */ ;
/** @type {__VLS_StyleScopedClasses['bowler']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-role" },
});
/** @type {__VLS_StyleScopedClasses['player-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-icon" },
});
/** @type {__VLS_StyleScopedClasses['role-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "role-text" },
});
/** @type {__VLS_StyleScopedClasses['role-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-info" },
});
/** @type {__VLS_StyleScopedClasses['player-info']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-name" },
});
/** @type {__VLS_StyleScopedClasses['player-name']} */ ;
(__VLS_ctx.bowlerName || 'Not selected');
if (__VLS_ctx.bowlerStats) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['player-stats']} */ ;
    (__VLS_ctx.bowlerStats.overs_bowled);
    (__VLS_ctx.bowlerStats.runs_conceded);
}
if (__VLS_ctx.canSwapBatsmen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.handleSwapBatsmen) },
        ...{ class: "swap-button" },
        disabled: (__VLS_ctx.loading),
        type: "button",
    });
    /** @type {__VLS_StyleScopedClasses['swap-button']} */ ;
}
// @ts-ignore
[strikerName, strikerStats, strikerStats, strikerStats, nonStrikerName, nonStrikerStats, nonStrikerStats, nonStrikerStats, bowlerName, bowlerStats, bowlerStats, bowlerStats, canSwapBatsmen, handleSwapBatsmen, loading,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
