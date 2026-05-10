/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const emit = defineEmits();
const gameStore = useGameStore();
const proTooltip = 'Requires Coach Pro or Organization Pro';
/** Local UI state */
const submitting = ref(false);
const isDisabled = computed(() => submitting.value || !props.canScore);
/** Main action */
async function score(runs) {
    console.log('[RunButtons] CLICK', { runs });
    if (!props.canScore) {
        console.warn('[RunButtons] blocked: canScore=false', {
            strikerId: props.strikerId,
            nonStrikerId: props.nonStrikerId,
            bowlerId: props.bowlerId,
        });
        return;
    }
    if (submitting.value) {
        console.warn('[RunButtons] blocked: already submitting');
        return;
    }
    submitting.value = true;
    try {
        const payload = {
            striker_id: props.strikerId,
            non_striker_id: props.nonStrikerId,
            bowler_id: props.bowlerId,
            runs_scored: runs,
            is_wicket: false,
            commentary: props.commentary ?? ''
        };
        console.log('[RunButtons] SUBMIT', payload);
        const res = await gameStore.submitDelivery(props.gameId, payload);
        console.log('[RunButtons] OK', res);
        // No manual swap here — rotation handled by server + snapshot/store merge
        emit('scored', payload);
    }
    catch (e) {
        console.error('[RunButtons] FAIL', e);
        emit('error', e?.message || 'Failed to score runs');
    }
    finally {
        submitting.value = false;
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
/** @type {__VLS_StyleScopedClasses['run-button']} */ ;
/** @type {__VLS_StyleScopedClasses['run-button']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "runs-section" },
    role: "group",
    'aria-label': "Runs Scored",
});
/** @type {__VLS_StyleScopedClasses['runs-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "runs-buttons" },
});
/** @type {__VLS_StyleScopedClasses['runs-buttons']} */ ;
for (const [runs] of __VLS_vFor(([0, 1, 2, 3, 4, 5, 6]))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.score(runs);
                // @ts-ignore
                [score,];
            } },
        key: (runs),
        type: "button",
        disabled: (__VLS_ctx.isDisabled),
        'aria-disabled': (__VLS_ctx.isDisabled ? 'true' : 'false'),
        title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : __VLS_ctx.isDisabled ? 'Select striker, non-striker (different) and bowler first' : `Record ${runs} run${runs === 1 ? '' : 's'}`),
        ...{ class: (['run-button', `runs-${runs}`]) },
    });
    /** @type {__VLS_StyleScopedClasses['run-button']} */ ;
    (runs);
    // @ts-ignore
    [isDisabled, isDisabled, isDisabled, canScore, proTooltip,];
}
if (__VLS_ctx.submitting) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "submitting" },
    });
    /** @type {__VLS_StyleScopedClasses['submitting']} */ ;
}
// @ts-ignore
[submitting,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
