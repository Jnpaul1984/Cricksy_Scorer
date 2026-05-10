/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, watch } from 'vue';
const props = defineProps();
const emit = defineEmits();
const isEditing = computed(() => !!props.team?.id);
const modalTitle = computed(() => isEditing.value ? 'Edit Team' : 'Create Team');
// Form state
const teamName = ref('');
const homeGround = ref('');
const season = ref('');
const selectedCoachId = ref(null);
const selectedPlayerIds = ref(new Set());
const isSubmitting = ref(false);
// Reset form when modal opens/closes or team changes
watch(() => [props.visible, props.team], () => {
    if (props.visible && props.team) {
        teamName.value = props.team.name;
        homeGround.value = props.team.home_ground || '';
        season.value = props.team.season || '';
        selectedCoachId.value = props.team.coach_id || null;
        selectedPlayerIds.value = new Set(props.team.players.map(p => p.id));
    }
    else if (props.visible && !props.team) {
        teamName.value = '';
        homeGround.value = '';
        season.value = '';
        selectedCoachId.value = null;
        selectedPlayerIds.value = new Set();
    }
}, { immediate: true });
const canSubmit = computed(() => teamName.value.trim().length > 0 && !isSubmitting.value);
const selectedCoach = computed(() => {
    if (!selectedCoachId.value)
        return null;
    return props.availableCoaches?.find(c => c.id === selectedCoachId.value) || null;
});
const selectedPlayers = computed(() => {
    if (!props.availablePlayers)
        return [];
    return props.availablePlayers.filter(p => selectedPlayerIds.value.has(p.id));
});
function togglePlayer(playerId) {
    const newSet = new Set(selectedPlayerIds.value);
    if (newSet.has(playerId)) {
        newSet.delete(playerId);
    }
    else {
        newSet.add(playerId);
    }
    selectedPlayerIds.value = newSet;
}
function isPlayerSelected(playerId) {
    return selectedPlayerIds.value.has(playerId);
}
function close() {
    emit('update:visible', false);
}
async function submit() {
    if (!canSubmit.value)
        return;
    isSubmitting.value = true;
    try {
        const teamData = {
            id: props.team?.id,
            name: teamName.value.trim(),
            home_ground: homeGround.value.trim() || undefined,
            season: season.value.trim() || undefined,
            coach_id: selectedCoachId.value || undefined,
            coach_name: selectedCoach.value?.name,
            players: selectedPlayers.value,
            competitions: props.team?.competitions || []
        };
        emit('saved', teamData);
        close();
    }
    finally {
        isSubmitting.value = false;
    }
}
function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
        close();
    }
}
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
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
/** @type {__VLS_StyleScopedClasses['player-checkbox']} */ ;
/** @type {__VLS_StyleScopedClasses['player-checkbox']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--secondary']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Teleport | typeof __VLS_components.Teleport} */
Teleport;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "body",
}));
const __VLS_2 = __VLS_1({
    to: "body",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.Transition | typeof __VLS_components.Transition} */
Transition;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    name: "fade",
}));
const __VLS_8 = __VLS_7({
    name: "fade",
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
const { default: __VLS_11 } = __VLS_9.slots;
if (__VLS_ctx.visible) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.handleBackdropClick) },
        ...{ class: "modal-backdrop" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "modal-header" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.modalTitle);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.close) },
        'aria-label': "Close",
        ...{ class: "close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.submit) },
        ...{ class: "modal-body" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "required" },
    });
    /** @type {__VLS_StyleScopedClasses['required']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.teamName),
        type: "text",
        ...{ class: "ds-input" },
        placeholder: "e.g., Sunrisers Hyderabad",
        required: true,
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.homeGround),
        type: "text",
        ...{ class: "ds-input" },
        placeholder: "e.g., Rajiv Gandhi Stadium",
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.season),
        type: "text",
        ...{ class: "ds-input" },
        placeholder: "e.g., 2024-25",
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedCoachId),
        ...{ class: "ds-input ds-select" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    /** @type {__VLS_StyleScopedClasses['ds-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
    });
    for (const [coach] of __VLS_vFor((__VLS_ctx.availableCoaches))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (coach.id),
            value: (coach.id),
        });
        (coach.name);
        // @ts-ignore
        [visible, handleBackdropClick, modalTitle, close, submit, teamName, homeGround, season, selectedCoachId, availableCoaches,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "players-multiselect" },
    });
    /** @type {__VLS_StyleScopedClasses['players-multiselect']} */ ;
    if (__VLS_ctx.availablePlayers && __VLS_ctx.availablePlayers.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "players-list" },
        });
        /** @type {__VLS_StyleScopedClasses['players-list']} */ ;
        for (const [player] of __VLS_vFor((__VLS_ctx.availablePlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
                key: (player.id),
                ...{ class: "player-checkbox" },
            });
            /** @type {__VLS_StyleScopedClasses['player-checkbox']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
                ...{ onChange: (...[$event]) => {
                        if (!(__VLS_ctx.visible))
                            return;
                        if (!(__VLS_ctx.availablePlayers && __VLS_ctx.availablePlayers.length > 0))
                            return;
                        __VLS_ctx.togglePlayer(player.id);
                        // @ts-ignore
                        [availablePlayers, availablePlayers, availablePlayers, togglePlayer,];
                    } },
                type: "checkbox",
                checked: (__VLS_ctx.isPlayerSelected(player.id)),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "player-name" },
            });
            /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
            (player.name);
            // @ts-ignore
            [isPlayerSelected,];
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "no-players-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['no-players-hint']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "field-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['field-hint']} */ ;
    (__VLS_ctx.selectedPlayers.length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
        ...{ class: "modal-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "ds-btn ds-btn--secondary" },
        type: "button",
    });
    /** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['ds-btn--secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.submit) },
        ...{ class: "ds-btn ds-btn--primary" },
        disabled: (!__VLS_ctx.canSubmit),
    });
    /** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
    (__VLS_ctx.isSubmitting ? 'Saving...' : (__VLS_ctx.isEditing ? 'Save Changes' : 'Create Team'));
}
// @ts-ignore
[close, submit, selectedPlayers, canSubmit, isSubmitting, isEditing,];
var __VLS_9;
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
