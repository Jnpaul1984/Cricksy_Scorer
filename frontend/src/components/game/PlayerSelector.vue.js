/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    disabled: false,
    loading: false,
    required: false,
    excludePlayerIds: () => [],
    error: '',
    hint: '',
});
const emit = defineEmits();
// Computed
const selectId = computed(() => `player-select-${props.label.toLowerCase().replace(/\s+/g, '-')}`);
const errorId = computed(() => `${selectId.value}-error`);
const availablePlayers = computed(() => props.players.filter(player => !props.excludePlayerIds.includes(player.id)));
const selectorClass = computed(() => ({
    'has-error': !!props.error,
    'is-disabled': props.disabled || props.loading,
    'is-loading': props.loading,
}));
// Methods
const handleSelectionChange = (event) => {
    const target = event.target;
    const playerId = target.value || null;
    emit('update:selectedPlayerId', playerId);
    const selectedPlayer = playerId
        ? props.players.find(p => p.id === playerId) || null
        : null;
    emit('player-selected', selectedPlayer);
};
const isPlayerDisabled = (playerId) => {
    return props.excludePlayerIds.includes(playerId);
};
const getDisabledReason = (playerId) => {
    if (props.excludePlayerIds.includes(playerId)) {
        return 'Already selected';
    }
    return '';
};
const __VLS_defaults = {
    disabled: false,
    loading: false,
    required: false,
    excludePlayerIds: () => [],
    error: '',
    hint: '',
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
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['has-error']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['error-message']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['selector-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-selector" },
});
/** @type {__VLS_StyleScopedClasses['player-selector']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: (__VLS_ctx.selectId),
    ...{ class: "selector-label" },
});
/** @type {__VLS_StyleScopedClasses['selector-label']} */ ;
(__VLS_ctx.label);
if (__VLS_ctx.required) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "required-indicator" },
    });
    /** @type {__VLS_StyleScopedClasses['required-indicator']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    ...{ onChange: (__VLS_ctx.handleSelectionChange) },
    id: (__VLS_ctx.selectId),
    value: (__VLS_ctx.selectedPlayerId),
    disabled: (__VLS_ctx.disabled || __VLS_ctx.loading),
    ...{ class: (__VLS_ctx.selectorClass) },
    ...{ class: "player-select" },
    'aria-describedby': (__VLS_ctx.errorId),
});
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "",
});
(__VLS_ctx.label);
for (const [player] of __VLS_vFor((__VLS_ctx.availablePlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (player.id),
        value: (player.id),
        disabled: (__VLS_ctx.isPlayerDisabled(player.id)),
    });
    (player.name);
    if (__VLS_ctx.isPlayerDisabled(player.id)) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "disabled-reason" },
        });
        /** @type {__VLS_StyleScopedClasses['disabled-reason']} */ ;
        (__VLS_ctx.getDisabledReason(player.id));
    }
    // @ts-ignore
    [selectId, selectId, label, label, required, handleSelectionChange, selectedPlayerId, disabled, loading, selectorClass, errorId, availablePlayers, isPlayerDisabled, isPlayerDisabled, getDisabledReason,];
}
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        id: (__VLS_ctx.errorId),
        ...{ class: "error-message" },
        role: "alert",
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    (__VLS_ctx.error);
}
if (__VLS_ctx.hint) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "hint-message" },
    });
    /** @type {__VLS_StyleScopedClasses['hint-message']} */ ;
    (__VLS_ctx.hint);
}
// @ts-ignore
[errorId, error, error, hint, hint,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
