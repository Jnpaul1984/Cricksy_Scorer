/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { BaseButton } from '@/components';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const game = useGameStore();
const proTooltip = 'Requires Coach Pro or Organization Pro';
async function doRun(n) {
    if (!props.canScore)
        return;
    await game.submitDelivery(props.gameId, {
        striker_id: props.strikerId,
        non_striker_id: props.nonStrikerId,
        bowler_id: props.bowlerId,
        runs_scored: n,
        is_wicket: false
    });
}
async function extra(code) {
    if (!props.canScore)
        return;
    await game.submitDelivery(props.gameId, {
        striker_id: props.strikerId,
        non_striker_id: props.nonStrikerId,
        bowler_id: props.bowlerId,
        runs_scored: 1,
        extra: code,
        is_wicket: false
    });
}
async function wicket() {
    if (!props.canScore)
        return;
    await game.submitDelivery(props.gameId, {
        striker_id: props.strikerId,
        non_striker_id: props.nonStrikerId,
        bowler_id: props.bowlerId,
        runs_scored: 0,
        is_wicket: true,
        dismissal_type: 'bowled'
    });
}
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pad" },
});
/** @type {__VLS_StyleScopedClasses['pad']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row runs" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['runs']} */ ;
for (const [n] of __VLS_vFor(([0, 1, 2, 3, 4, 5, 6]))) {
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        ...{ 'onClick': {} },
        key: (n),
        variant: "primary",
        size: "sm",
        disabled: (!__VLS_ctx.canScore),
        title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
    }));
    const __VLS_2 = __VLS_1({
        ...{ 'onClick': {} },
        key: (n),
        variant: "primary",
        size: "sm",
        disabled: (!__VLS_ctx.canScore),
        title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_5;
    const __VLS_6 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.doRun(n);
                // @ts-ignore
                [canScore, canScore, proTooltip, doRun,];
            } });
    const { default: __VLS_7 } = __VLS_3.slots;
    (n);
    // @ts-ignore
    [];
    var __VLS_3;
    var __VLS_4;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
    ...{ class: "extra-wd" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}));
const __VLS_10 = __VLS_9({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
    ...{ class: "extra-wd" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.extra('wd');
            // @ts-ignore
            [canScore, canScore, proTooltip, extra,];
        } });
/** @type {__VLS_StyleScopedClasses['extra-wd']} */ ;
const { default: __VLS_15 } = __VLS_11.slots;
// @ts-ignore
[];
var __VLS_11;
var __VLS_12;
let __VLS_16;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
    ...{ class: "extra-nb" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}));
const __VLS_18 = __VLS_17({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
    ...{ class: "extra-nb" },
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_21;
const __VLS_22 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.extra('nb');
            // @ts-ignore
            [canScore, canScore, proTooltip, extra,];
        } });
/** @type {__VLS_StyleScopedClasses['extra-nb']} */ ;
const { default: __VLS_23 } = __VLS_19.slots;
// @ts-ignore
[];
var __VLS_19;
var __VLS_20;
let __VLS_24;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
    ...{ 'onClick': {} },
    variant: "danger",
    size: "sm",
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}));
const __VLS_26 = __VLS_25({
    ...{ 'onClick': {} },
    variant: "danger",
    size: "sm",
    disabled: (!__VLS_ctx.canScore),
    title: (!__VLS_ctx.canScore ? __VLS_ctx.proTooltip : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
let __VLS_29;
const __VLS_30 = ({ click: {} },
    { onClick: (__VLS_ctx.wicket) });
const { default: __VLS_31 } = __VLS_27.slots;
// @ts-ignore
[canScore, canScore, proTooltip, wicket,];
var __VLS_27;
var __VLS_28;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
