/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from "vue";
import { BaseBadge } from "@/components";
const props = defineProps();
// Confetti only for celebratory events
const confettiOn = computed(() => props.event === "FOUR" || props.event === "SIX" || props.event === "FIFTY" || props.event === "HUNDRED");
// Map event types to badge variants
const badgeVariant = computed(() => {
    switch (props.event) {
        case "FOUR":
        case "FIFTY":
            return "success";
        case "SIX":
        case "HUNDRED":
            return "primary";
        case "WICKET":
        case "DUCK":
            return "danger";
        default:
            return "neutral";
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
/** @type {__VLS_StyleScopedClasses['confetti']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
transition;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    name: "overlay-pop",
}));
const __VLS_2 = __VLS_1({
    name: "overlay-pop",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
if (__VLS_ctx.visible && __VLS_ctx.event) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "event-overlay" },
        role: "status",
        'aria-live': "assertive",
    });
    /** @type {__VLS_StyleScopedClasses['event-overlay']} */ ;
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        variant: (__VLS_ctx.badgeVariant),
        ...{ class: "event-badge" },
        dataKind: (__VLS_ctx.event),
    }));
    const __VLS_8 = __VLS_7({
        variant: (__VLS_ctx.badgeVariant),
        ...{ class: "event-badge" },
        dataKind: (__VLS_ctx.event),
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    /** @type {__VLS_StyleScopedClasses['event-badge']} */ ;
    const { default: __VLS_11 } = __VLS_9.slots;
    if (__VLS_ctx.event === 'FOUR') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.event === 'SIX') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.event === 'WICKET') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.event === 'DUCK') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.event === 'FIFTY') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.event === 'HUNDRED') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    // @ts-ignore
    [visible, event, event, event, event, event, event, event, event, badgeVariant,];
    var __VLS_9;
    if (__VLS_ctx.confettiOn) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "confetti" },
        });
        /** @type {__VLS_StyleScopedClasses['confetti']} */ ;
        for (const [n] of __VLS_vFor((24))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.i)({
                key: (n),
            });
            // @ts-ignore
            [confettiOn,];
        }
    }
}
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
