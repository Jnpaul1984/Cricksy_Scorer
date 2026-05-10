/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref } from 'vue';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const emit = defineEmits();
const gameStore = useGameStore();
const byeRuns = ref(1);
const legByeRuns = ref(1);
const proTooltip = 'Requires Coach Pro or Organization Pro';
/**
 * Record an extra delivery
 * extra: 'wd' (wide), 'nb' (no-ball), 'b' (bye), 'lb' (leg-bye)
 */
async function score(extra, runs = 1) {
    if (!props.canScore)
        return;
    try {
        const payload = {
            striker_id: props.strikerId,
            non_striker_id: props.nonStrikerId,
            bowler_id: props.bowlerId,
            runs_scored: runs,
            extra,
            is_wicket: false,
            commentary: props.commentary ?? ''
        };
        await gameStore.submitDelivery(props.gameId, payload);
        emit('scored', payload);
    }
    catch (e) {
        console.error(e);
        emit('error', e?.message || 'Failed to score extra');
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
/** @type {__VLS_StyleScopedClasses['extra-button']} */ ;
/** @type {__VLS_StyleScopedClasses['extras-row']} */ ;
/** @type {__VLS_StyleScopedClasses['extras-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-section" },
});
/** @type {__VLS_StyleScopedClasses['extras-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-buttons" },
});
/** @type {__VLS_StyleScopedClasses['extras-buttons']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.score('wd', 1);
            // @ts-ignore
            [score,];
        } },
    ...{ class: "extra-button wide" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
});
/** @type {__VLS_StyleScopedClasses['extra-button']} */ ;
/** @type {__VLS_StyleScopedClasses['wide']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.score('nb', 1);
            // @ts-ignore
            [score, canScore, canScore, proTooltip,];
        } },
    ...{ class: "extra-button no-ball" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
});
/** @type {__VLS_StyleScopedClasses['extra-button']} */ ;
/** @type {__VLS_StyleScopedClasses['no-ball']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-row" },
});
/** @type {__VLS_StyleScopedClasses['extras-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "sel-byes",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    id: "sel-byes",
    value: (__VLS_ctx.byeRuns),
    disabled: (!__VLS_ctx.canScore),
    title: "Byes",
    'aria-describedby': "sel-byes-hint",
});
for (const [n] of __VLS_vFor(([1, 2, 3, 4]))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: ('b-' + n),
        value: (n),
    });
    (n);
    // @ts-ignore
    [canScore, canScore, canScore, proTooltip, byeRuns,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
    id: "sel-byes-hint",
    ...{ class: "sr-only" },
});
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.score('b', __VLS_ctx.byeRuns);
            // @ts-ignore
            [score, byeRuns,];
        } },
    ...{ class: "extra-button bye" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
});
/** @type {__VLS_StyleScopedClasses['extra-button']} */ ;
/** @type {__VLS_StyleScopedClasses['bye']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-row" },
});
/** @type {__VLS_StyleScopedClasses['extras-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    for: "sel-leg-byes",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    id: "sel-leg-byes",
    value: (__VLS_ctx.legByeRuns),
    disabled: (!__VLS_ctx.canScore),
    title: "Leg byes",
    'aria-describedby': "sel-leg-byes-hint",
});
for (const [n] of __VLS_vFor(([1, 2, 3, 4]))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: ('lb-' + n),
        value: (n),
    });
    (n);
    // @ts-ignore
    [canScore, canScore, canScore, proTooltip, legByeRuns,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
    id: "sel-leg-byes-hint",
    ...{ class: "sr-only" },
});
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.score('lb', __VLS_ctx.legByeRuns);
            // @ts-ignore
            [score, legByeRuns,];
        } },
    ...{ class: "extra-button leg-bye" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
});
/** @type {__VLS_StyleScopedClasses['extra-button']} */ ;
/** @type {__VLS_StyleScopedClasses['leg-bye']} */ ;
// @ts-ignore
[canScore, canScore, proTooltip,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
