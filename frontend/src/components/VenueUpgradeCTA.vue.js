/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { useRouter } from 'vue-router';
import { BaseButton, BaseBadge } from '@/components';
import { usePricingStore } from '@/stores/pricingStore';
const props = withDefaults(defineProps(), {
    tagline: 'Remove branding, add your logo, and unlock professional broadcast features.',
    recommendedPlan: 'venue-scoring-pro',
});
// ============================================================================
// Setup
// ============================================================================
const pricingStore = usePricingStore();
const router = useRouter();
// ============================================================================
// Actions
// ============================================================================
function handleUpgrade(planId) {
    const plan = pricingStore.getPlanById(planId);
    if (plan?.isContactSales) {
        // Contact sales flow
        const email = 'sales@cricksy.ai';
        const subject = `Venue Upgrade: ${plan.name}`;
        const body = `Hi,\n\nI'm interested in upgrading my cricket ground with ${plan.name}.\n\nPlease contact me with more details.\n\nThanks`;
        window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }
    else {
        // Navigate to pricing page with plan preselected
        router.push({ path: '/pricing', query: { plan: planId, type: 'venue' } });
    }
}
const __VLS_defaults = {
    tagline: 'Remove branding, add your logo, and unlock professional broadcast features.',
    recommendedPlan: 'venue-scoring-pro',
};
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['upgrade-content']} */ ;
/** @type {__VLS_StyleScopedClasses['venue-plan-option']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-header']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-features-compact']} */ ;
/** @type {__VLS_StyleScopedClasses['view-all-plans']} */ ;
/** @type {__VLS_StyleScopedClasses['venue-upgrade-cta']} */ ;
/** @type {__VLS_StyleScopedClasses['venue-plans']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "venue-upgrade-cta" },
});
/** @type {__VLS_StyleScopedClasses['venue-upgrade-cta']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "upgrade-content" },
});
/** @type {__VLS_StyleScopedClasses['upgrade-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "upgrade-icon" },
});
/** @type {__VLS_StyleScopedClasses['upgrade-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "upgrade-tagline" },
});
/** @type {__VLS_StyleScopedClasses['upgrade-tagline']} */ ;
(__VLS_ctx.tagline);
if (!__VLS_ctx.pricingStore.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "venue-plans" },
    });
    /** @type {__VLS_StyleScopedClasses['venue-plans']} */ ;
    for (const [plan] of __VLS_vFor((__VLS_ctx.pricingStore.venueDisplayPlans))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (plan.id),
            ...{ class: "venue-plan-option" },
            ...{ class: ({ 'plan-recommended': plan.id === __VLS_ctx.recommendedPlan }) },
        });
        /** @type {__VLS_StyleScopedClasses['venue-plan-option']} */ ;
        /** @type {__VLS_StyleScopedClasses['plan-recommended']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "plan-header" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (plan.name);
        if (plan.id === __VLS_ctx.recommendedPlan) {
            let __VLS_0;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
                variant: "primary",
                size: "sm",
            }));
            const __VLS_2 = __VLS_1({
                variant: "primary",
                size: "sm",
            }, ...__VLS_functionalComponentArgsRest(__VLS_1));
            const { default: __VLS_5 } = __VLS_3.slots;
            // @ts-ignore
            [tagline, pricingStore, pricingStore, recommendedPlan, recommendedPlan,];
            var __VLS_3;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "plan-price" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-price']} */ ;
        (plan.monthlyDisplay);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "plan-tagline" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-tagline']} */ ;
        (plan.tagline);
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "plan-features-compact" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-features-compact']} */ ;
        for (const [feature, idx] of __VLS_vFor((plan.features.slice(0, 3)))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (idx),
            });
            (feature);
            // @ts-ignore
            [];
        }
        if (plan.features.length > 3) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                ...{ class: "more-features" },
            });
            /** @type {__VLS_StyleScopedClasses['more-features']} */ ;
            (plan.features.length - 3);
        }
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            ...{ 'onClick': {} },
            variant: (plan.id === __VLS_ctx.recommendedPlan ? 'primary' : 'ghost'),
            size: "sm",
        }));
        const __VLS_8 = __VLS_7({
            ...{ 'onClick': {} },
            variant: (plan.id === __VLS_ctx.recommendedPlan ? 'primary' : 'ghost'),
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        let __VLS_11;
        const __VLS_12 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(!__VLS_ctx.pricingStore.loading))
                        return;
                    __VLS_ctx.handleUpgrade(plan.id);
                    // @ts-ignore
                    [recommendedPlan, handleUpgrade,];
                } });
        const { default: __VLS_13 } = __VLS_9.slots;
        (plan.isContactSales ? 'Contact Sales' : 'Upgrade Ground');
        // @ts-ignore
        [];
        var __VLS_9;
        var __VLS_10;
        // @ts-ignore
        [];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
}
let __VLS_14;
/** @ts-ignore @type { | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link'] | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link']} */
routerLink;
// @ts-ignore
const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
    to: "/pricing",
    ...{ class: "view-all-plans" },
}));
const __VLS_16 = __VLS_15({
    to: "/pricing",
    ...{ class: "view-all-plans" },
}, ...__VLS_functionalComponentArgsRest(__VLS_15));
/** @type {__VLS_StyleScopedClasses['view-all-plans']} */ ;
const { default: __VLS_19 } = __VLS_17.slots;
// @ts-ignore
[];
var __VLS_17;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
