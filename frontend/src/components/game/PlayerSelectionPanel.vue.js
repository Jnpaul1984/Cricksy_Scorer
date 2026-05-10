/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import PlayerSelector from './PlayerSelector.vue';
import { useGameStore } from '@/stores/gameStore';
const gameStore = useGameStore();
// Computed properties
const availableBatsmen = computed(() => gameStore.availableBatsmen || []);
const availableBowlers = computed(() => gameStore.availableBowlers || []);
const validationErrors = computed(() => {
    const errors = [];
    if (!gameStore.uiState.selectedStrikerId) {
        errors.push('Please select a striker');
    }
    if (!gameStore.uiState.selectedNonStrikerId) {
        errors.push('Please select a non-striker');
    }
    if (!gameStore.uiState.selectedBowlerId) {
        errors.push('Please select a bowler');
    }
    if (gameStore.uiState.selectedStrikerId === gameStore.uiState.selectedNonStrikerId) {
        errors.push('Striker and non-striker cannot be the same player');
    }
    return errors;
});
const statusClass = computed(() => ({
    'status-ready': gameStore.canScoreDelivery,
    'status-incomplete': !gameStore.canScoreDelivery && validationErrors.value.length > 0,
    'status-disabled': !gameStore.isGameActive,
}));
const statusIcon = computed(() => {
    if (!gameStore.isGameActive)
        return '⏸️';
    if (gameStore.canScoreDelivery)
        return '✅';
    return '⚠️';
});
const statusMessage = computed(() => {
    if (!gameStore.isGameActive) {
        return 'Game is not active';
    }
    if (gameStore.canScoreDelivery) {
        return 'Ready to score deliveries';
    }
    if (validationErrors.value.length > 0) {
        return `${validationErrors.value.length} selection${validationErrors.value.length > 1 ? 's' : ''} required`;
    }
    return 'Complete player selection';
});
// Event handlers
const handleStrikerSelected = (player) => {
    console.log('Striker selected:', player?.name || 'None');
};
const handleNonStrikerSelected = (player) => {
    console.log('Non-striker selected:', player?.name || 'None');
};
const handleBowlerSelected = (player) => {
    console.log('Bowler selected:', player?.name || 'None');
};
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['player-selection-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['selection-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
/** @type {__VLS_StyleScopedClasses['selection-status']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-selection-panel" },
});
/** @type {__VLS_StyleScopedClasses['player-selection-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "panel-title" },
});
/** @type {__VLS_StyleScopedClasses['panel-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "selection-grid" },
});
/** @type {__VLS_StyleScopedClasses['selection-grid']} */ ;
const __VLS_0 = PlayerSelector;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBatsmen),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedStrikerId),
    label: "Striker",
    required: (true),
    excludePlayerIds: (__VLS_ctx.gameStore.uiState.selectedNonStrikerId ? [__VLS_ctx.gameStore.uiState.selectedNonStrikerId] : []),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The batsman currently facing the bowler",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBatsmen),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedStrikerId),
    label: "Striker",
    required: (true),
    excludePlayerIds: (__VLS_ctx.gameStore.uiState.selectedNonStrikerId ? [__VLS_ctx.gameStore.uiState.selectedNonStrikerId] : []),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The batsman currently facing the bowler",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ 'update:selectedPlayerId': {} },
    { 'onUpdate:selectedPlayerId': (__VLS_ctx.gameStore.setSelectedStriker) });
const __VLS_7 = ({ playerSelected: {} },
    { onPlayerSelected: (__VLS_ctx.handleStrikerSelected) });
var __VLS_3;
var __VLS_4;
const __VLS_8 = PlayerSelector;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBatsmen),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedNonStrikerId),
    label: "Non-Striker",
    required: (true),
    excludePlayerIds: (__VLS_ctx.gameStore.uiState.selectedStrikerId ? [__VLS_ctx.gameStore.uiState.selectedStrikerId] : []),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The batsman at the non-striker's end",
}));
const __VLS_10 = __VLS_9({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBatsmen),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedNonStrikerId),
    label: "Non-Striker",
    required: (true),
    excludePlayerIds: (__VLS_ctx.gameStore.uiState.selectedStrikerId ? [__VLS_ctx.gameStore.uiState.selectedStrikerId] : []),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The batsman at the non-striker's end",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ 'update:selectedPlayerId': {} },
    { 'onUpdate:selectedPlayerId': (__VLS_ctx.gameStore.setSelectedNonStriker) });
const __VLS_15 = ({ playerSelected: {} },
    { onPlayerSelected: (__VLS_ctx.handleNonStrikerSelected) });
var __VLS_11;
var __VLS_12;
const __VLS_16 = PlayerSelector;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBowlers),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedBowlerId),
    label: "Bowler",
    required: (true),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The player bowling this over",
}));
const __VLS_18 = __VLS_17({
    ...{ 'onUpdate:selectedPlayerId': {} },
    ...{ 'onPlayerSelected': {} },
    players: (__VLS_ctx.availableBowlers),
    selectedPlayerId: (__VLS_ctx.gameStore.uiState.selectedBowlerId),
    label: "Bowler",
    required: (true),
    disabled: (!__VLS_ctx.gameStore.isGameActive),
    loading: (__VLS_ctx.gameStore.operationLoading.scoreDelivery),
    hint: "The player bowling this over",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_21;
const __VLS_22 = ({ 'update:selectedPlayerId': {} },
    { 'onUpdate:selectedPlayerId': (__VLS_ctx.gameStore.setSelectedBowler) });
const __VLS_23 = ({ playerSelected: {} },
    { onPlayerSelected: (__VLS_ctx.handleBowlerSelected) });
var __VLS_19;
var __VLS_20;
if (__VLS_ctx.validationErrors.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "validation-errors" },
    });
    /** @type {__VLS_StyleScopedClasses['validation-errors']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "errors-title" },
    });
    /** @type {__VLS_StyleScopedClasses['errors-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "errors-list" },
    });
    /** @type {__VLS_StyleScopedClasses['errors-list']} */ ;
    for (const [error] of __VLS_vFor((__VLS_ctx.validationErrors))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (error),
            ...{ class: "error-item" },
        });
        /** @type {__VLS_StyleScopedClasses['error-item']} */ ;
        (error);
        // @ts-ignore
        [availableBatsmen, availableBatsmen, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, gameStore, handleStrikerSelected, handleNonStrikerSelected, availableBowlers, handleBowlerSelected, validationErrors, validationErrors,];
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "selection-status" },
    ...{ class: (__VLS_ctx.statusClass) },
});
/** @type {__VLS_StyleScopedClasses['selection-status']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "status-icon" },
});
/** @type {__VLS_StyleScopedClasses['status-icon']} */ ;
(__VLS_ctx.statusIcon);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "status-text" },
});
/** @type {__VLS_StyleScopedClasses['status-text']} */ ;
(__VLS_ctx.statusMessage);
// @ts-ignore
[statusClass, statusIcon, statusMessage,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
