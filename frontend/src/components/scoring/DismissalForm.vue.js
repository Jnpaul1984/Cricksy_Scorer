/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const emit = defineEmits();
const gameStore = useGameStore();
const proTooltip = 'Requires Coach Pro or Organization Pro';
const dismissalType = ref('bowled');
const dismissed = ref('striker');
const fielderId = ref('');
const note = ref('');
const dismissedPlayerId = computed(() => dismissed.value === 'striker' ? props.strikerId : props.nonStrikerId);
const DISMISSALS = [
    { value: 'bowled', label: 'Bowled' },
    { value: 'caught', label: 'Caught' },
    { value: 'lbw', label: 'LBW' },
    { value: 'stumped', label: 'Stumped' },
    { value: 'run_out', label: 'Run Out' },
    { value: 'hit_wicket', label: 'Hit Wicket' },
    { value: 'obstructing_the_field', label: 'Obstructing the Field' },
    { value: 'hit_ball_twice', label: 'Hit the Ball Twice' },
    { value: 'timed_out', label: 'Timed Out' },
    { value: 'retired_out', label: 'Retired - Out' },
    { value: 'handled_ball', label: 'Handled the Ball (legacy)' },
];
// Enable button only when we have IDs to submit and scoring is allowed
const canSubmit = computed(() => props.canScore && !!props.strikerId && !!props.nonStrikerId && !!props.bowlerId);
async function submit() {
    if (!canSubmit.value)
        return;
    try {
        const payload = {
            striker_id: props.strikerId,
            non_striker_id: props.nonStrikerId,
            bowler_id: props.bowlerId,
            runs_scored: 0,
            is_wicket: true,
            dismissal_type: dismissalType.value,
            dismissed_player_id: dismissedPlayerId.value || props.strikerId,
            commentary: note.value.trim(),
            // fielder_id: fielderId.value || undefined // enable when API supports it
        };
        await gameStore.submitDelivery(props.gameId, payload);
        emit('scored', payload);
    }
    catch (e) {
        console.error(e);
        emit('error', e?.message || 'Failed to record dismissal');
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
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "dismissal-form" },
});
/** @type {__VLS_StyleScopedClasses['dismissal-form']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "sel-dismissal-type",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    id: "sel-dismissal-type",
    value: (__VLS_ctx.dismissalType),
    disabled: (!__VLS_ctx.canScore),
    title: "Dismissal type",
    'aria-describedby': "sel-dismissal-type-hint",
});
for (const [d] of __VLS_vFor((__VLS_ctx.DISMISSALS))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (d.value),
        value: (d.value),
    });
    (d.label);
    // @ts-ignore
    [dismissalType, canScore, DISMISSALS,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
    id: "sel-dismissal-type-hint",
    ...{ class: "sr-only" },
});
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "lbl" },
});
/** @type {__VLS_StyleScopedClasses['lbl']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toggle" },
    role: "radiogroup",
    'aria-labelledby': "dismissed-group-label",
});
/** @type {__VLS_StyleScopedClasses['toggle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    id: "dismissed-group-label",
    ...{ class: "sr-only" },
});
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "rad-striker",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    id: "rad-striker",
    type: "radio",
    value: "striker",
    disabled: (!__VLS_ctx.canScore),
});
(__VLS_ctx.dismissed);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "rad-nonstriker",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    id: "rad-nonstriker",
    type: "radio",
    value: "non_striker",
    disabled: (!__VLS_ctx.canScore),
});
(__VLS_ctx.dismissed);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "sel-fielder",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    id: "sel-fielder",
    value: (__VLS_ctx.fielderId),
    disabled: (!__VLS_ctx.canScore),
    title: "Fielder",
    'aria-describedby': "sel-fielder-hint",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "",
});
for (const [p] of __VLS_vFor((__VLS_ctx.battingPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (p.id),
        value: (p.id),
    });
    (p.name);
    // @ts-ignore
    [canScore, canScore, canScore, dismissed, dismissed, fielderId, battingPlayers,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
    id: "sel-fielder-hint",
    ...{ class: "sr-only" },
});
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "txt-note",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
    id: "txt-note",
    value: (__VLS_ctx.note),
    rows: "2",
    placeholder: "e.g., Bowled through the gate.",
    disabled: (!__VLS_ctx.canScore),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.submit) },
    ...{ class: "submit" },
    disabled: (!__VLS_ctx.canSubmit),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : !__VLS_ctx.canSubmit ? 'Select striker, non-striker, bowler, and dismissal first' : undefined),
});
/** @type {__VLS_StyleScopedClasses['submit']} */ ;
// @ts-ignore
[canScore, canScore, note, submit, canSubmit, canSubmit, proTooltip,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
