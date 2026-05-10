/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from "vue";
import BaseBadge from "./BaseBadge.vue";
import BaseButton from "./BaseButton.vue";
import BaseCard from "./BaseCard.vue";
const props = withDefaults(defineProps(), {
    title: "AI Callouts",
    description: "Key insights Cricksy AI thinks you should know.",
    loading: false,
    maxItems: 5,
    dense: false,
    showViewAllButton: false,
});
const emit = defineEmits();
const limitedCallouts = computed(() => {
    if (!props.callouts)
        return [];
    if (!props.maxItems || props.callouts.length <= props.maxItems) {
        return props.callouts;
    }
    return props.callouts.slice(0, props.maxItems);
});
const isEmpty = computed(() => !props.loading && (!props.callouts || props.callouts.length === 0));
function severityToVariant(severity) {
    switch (severity) {
        case "positive":
            return "success";
        case "warning":
            return "warning";
        case "critical":
            return "danger";
        default:
            return "neutral";
    }
}
function handleCalloutClick(callout) {
    emit("select", callout);
}
function handleViewAll() {
    emit("viewAll");
}
const __VLS_defaults = {
    title: "AI Callouts",
    description: "Key insights Cricksy AI thinks you should know.",
    loading: false,
    maxItems: 5,
    dense: false,
    showViewAllButton: false,
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
/** @type {__VLS_StyleScopedClasses['ai-callouts-empty']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callout-row']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callout-row']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callouts-list']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callout-item']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callouts-list']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callout-title']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callouts-list']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-callout-body']} */ ;
const __VLS_0 = BaseCard || BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    padding: "md",
    ...{ class: "ai-callouts-panel" },
}));
const __VLS_2 = __VLS_1({
    padding: "md",
    ...{ class: "ai-callouts-panel" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['ai-callouts-panel']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "ai-callouts-header" },
});
/** @type {__VLS_StyleScopedClasses['ai-callouts-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "ai-callouts-title" },
});
/** @type {__VLS_StyleScopedClasses['ai-callouts-title']} */ ;
(__VLS_ctx.title);
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "ai-callouts-description" },
});
/** @type {__VLS_StyleScopedClasses['ai-callouts-description']} */ ;
(__VLS_ctx.description);
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ai-callouts-skeleton" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-skeleton']} */ ;
    for (const [n] of __VLS_vFor((3))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (n),
            ...{ class: "skeleton-item" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line skeleton-line--title" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
        /** @type {__VLS_StyleScopedClasses['skeleton-line--title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line skeleton-line--body" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
        /** @type {__VLS_StyleScopedClasses['skeleton-line--body']} */ ;
        // @ts-ignore
        [title, description, loading,];
    }
}
else if (__VLS_ctx.isEmpty) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ai-callouts-empty" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-empty']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "ai-callouts-empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-empty-hint']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "ai-callouts-list" },
        'data-dense': (__VLS_ctx.dense),
    });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-list']} */ ;
    for (const [callout] of __VLS_vFor((__VLS_ctx.limitedCallouts))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (callout.id),
            ...{ class: "ai-callout-item" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.isEmpty))
                        return;
                    __VLS_ctx.handleCalloutClick(callout);
                    // @ts-ignore
                    [isEmpty, dense, limitedCallouts, handleCalloutClick,];
                } },
            type: "button",
            ...{ class: "ai-callout-row" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-callout-main" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-main']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-callout-title-row" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-title-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "ai-callout-title" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-title']} */ ;
        (callout.title);
        if (callout.severity) {
            const __VLS_7 = BaseBadge || BaseBadge;
            // @ts-ignore
            const __VLS_8 = __VLS_asFunctionalComponent1(__VLS_7, new __VLS_7({
                variant: (__VLS_ctx.severityToVariant(callout.severity)),
                uppercase: (false),
            }));
            const __VLS_9 = __VLS_8({
                variant: (__VLS_ctx.severityToVariant(callout.severity)),
                uppercase: (false),
            }, ...__VLS_functionalComponentArgsRest(__VLS_8));
            const { default: __VLS_12 } = __VLS_10.slots;
            (callout.severity);
            // @ts-ignore
            [severityToVariant,];
            var __VLS_10;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "ai-callout-body" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-body']} */ ;
        (callout.body);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-callout-meta" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-callout-meta']} */ ;
        if (callout.category) {
            const __VLS_13 = BaseBadge || BaseBadge;
            // @ts-ignore
            const __VLS_14 = __VLS_asFunctionalComponent1(__VLS_13, new __VLS_13({
                variant: "neutral",
                uppercase: (false),
            }));
            const __VLS_15 = __VLS_14({
                variant: "neutral",
                uppercase: (false),
            }, ...__VLS_functionalComponentArgsRest(__VLS_14));
            const { default: __VLS_18 } = __VLS_16.slots;
            (callout.category);
            // @ts-ignore
            [];
            var __VLS_16;
        }
        if (callout.scope) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "ai-callout-scope" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-callout-scope']} */ ;
            (callout.scope);
        }
        // @ts-ignore
        [];
    }
}
if (__VLS_ctx.showViewAllButton && !__VLS_ctx.loading && !__VLS_ctx.isEmpty) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ai-callouts-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-footer']} */ ;
    const __VLS_19 = BaseButton || BaseButton;
    // @ts-ignore
    const __VLS_20 = __VLS_asFunctionalComponent1(__VLS_19, new __VLS_19({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        ...{ class: "ai-callouts-view-all" },
    }));
    const __VLS_21 = __VLS_20({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        ...{ class: "ai-callouts-view-all" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_20));
    let __VLS_24;
    const __VLS_25 = ({ click: {} },
        { onClick: (__VLS_ctx.handleViewAll) });
    /** @type {__VLS_StyleScopedClasses['ai-callouts-view-all']} */ ;
    const { default: __VLS_26 } = __VLS_22.slots;
    // @ts-ignore
    [loading, isEmpty, showViewAllButton, handleViewAll,];
    var __VLS_22;
    var __VLS_23;
}
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
