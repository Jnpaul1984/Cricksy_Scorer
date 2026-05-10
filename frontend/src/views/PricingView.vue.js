/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { usePricingStore } from '@/stores/pricingStore';
import { API_BASE } from '@/services/api';
// ============================================================================
// Pricing Store - Single Source of Truth
// ============================================================================
const pricingStore = usePricingStore();
// Fetch pricing on component mount if not already loaded
onMounted(async () => {
    if (pricingStore.displayPlans.length === 0) {
        await pricingStore.fetchPricing();
    }
});
// Retry function
const retryFetch = async () => {
    await pricingStore.fetchPricing();
};
// Error message formatting
const errorMessage = computed(() => {
    if (!pricingStore.error)
        return '';
    const isDev = import.meta.env.DEV;
    const status = pricingStore.httpStatus;
    if (isDev) {
        // Show technical details in dev
        return `Error ${status || 'Unknown'}: ${pricingStore.error}`;
    }
    else {
        // User-friendly message in production
        if (status === 404) {
            return 'Pricing information is currently unavailable.';
        }
        else if (status && status >= 500) {
            return 'Our pricing service is temporarily down. Please try again in a few moments.';
        }
        else {
            return 'Unable to load pricing plans at this time.';
        }
    }
});
// ============================================================================
// Production API Warning Detection
// ============================================================================
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;
const isWindowOriginFallback = computed(() => {
    if (!isProduction)
        return false;
    const windowOrigin = typeof window !== 'undefined'
        ? `${window.location.protocol}//${window.location.host}`
        : '';
    return API_BASE === windowOrigin;
});
// ============================================================================
// Price Formatting Helper
// ============================================================================
function formatPlanPrice(plan) {
    if (plan.isContactSales || plan.monthlyPrice === null) {
        return { amount: 'Contact us', period: '' };
    }
    if (plan.monthlyPrice === 0) {
        return { amount: 'Free', period: 'forever' };
    }
    return { amount: plan.monthlyDisplay, period: '/month' };
}
// ============================================================================
// Display Plans
// ============================================================================
const displayPlans = computed(() => {
    return pricingStore.individualDisplayPlans.map((plan) => {
        const { amount, period } = formatPlanPrice(plan);
        // Convert features array to PlanFeature format for template
        const features = plan.features.map((text) => ({
            text,
            included: true
        }));
        return {
            id: plan.id,
            backendId: plan.backendId,
            name: plan.name,
            price: amount,
            period: period,
            description: plan.tagline,
            features,
            recommended: plan.highlight,
            cta: plan.ctaLabel,
            ctaLink: plan.monthlyPrice === 0 ? '/fan' : '/login'
        };
    });
});
// Show scoring is free message from API
const scoringIsFreeBanner = computed(() => pricingStore.scoringIsFree);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['pricing-error']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-card']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-item']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-item']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-excluded']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-excluded']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['cta-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['cta-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['back-link']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing-title']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['plans-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing" },
});
/** @type {__VLS_StyleScopedClasses['pricing']} */ ;
if (__VLS_ctx.isWindowOriginFallback) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "api-warning-banner" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['api-warning-banner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.br)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ style: {} },
    });
}
if (__VLS_ctx.pricingStore.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pricing-loading" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-loading']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.pricingStore.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pricing-error" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-error']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ style: {} },
    });
    (__VLS_ctx.errorMessage);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.retryFetch) },
        disabled: (__VLS_ctx.pricingStore.loading),
        ...{ style: {} },
        ...{ style: (__VLS_ctx.pricingStore.loading ? 'opacity: 0.6; cursor: not-allowed;' : '') },
    });
    (__VLS_ctx.pricingStore.loading ? 'Retrying...' : '🔄 Retry');
    if (__VLS_ctx.isDevelopment) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ style: {} },
        });
        (__VLS_ctx.pricingStore.lastFetchAttempt);
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "pricing-header" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({
        ...{ class: "pricing-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "pricing-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-subtitle']} */ ;
    if (__VLS_ctx.scoringIsFreeBanner) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "scoring-free-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['scoring-free-badge']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "plans-section" },
    });
    /** @type {__VLS_StyleScopedClasses['plans-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "plans-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['plans-grid']} */ ;
    for (const [plan] of __VLS_vFor((__VLS_ctx.displayPlans))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (plan.id),
            ...{ class: "plan-card" },
            ...{ class: ({ 'plan-recommended': plan.recommended }) },
        });
        /** @type {__VLS_StyleScopedClasses['plan-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['plan-recommended']} */ ;
        if (plan.recommended) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "plan-badge" },
            });
            /** @type {__VLS_StyleScopedClasses['plan-badge']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "plan-name" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-name']} */ ;
        (plan.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "plan-price" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-price']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "price-amount" },
        });
        /** @type {__VLS_StyleScopedClasses['price-amount']} */ ;
        (plan.price);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "price-period" },
        });
        /** @type {__VLS_StyleScopedClasses['price-period']} */ ;
        (plan.period);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "plan-description" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-description']} */ ;
        (plan.description);
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "plan-features" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
        for (const [feature] of __VLS_vFor((plan.features))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (feature.text),
                ...{ class: "feature-item" },
                ...{ class: ({ 'feature-excluded': !feature.included }) },
            });
            /** @type {__VLS_StyleScopedClasses['feature-item']} */ ;
            /** @type {__VLS_StyleScopedClasses['feature-excluded']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "feature-icon" },
            });
            /** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
            (feature.included ? '✓' : '✗');
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "feature-text" },
            });
            /** @type {__VLS_StyleScopedClasses['feature-text']} */ ;
            (feature.text);
            // @ts-ignore
            [isWindowOriginFallback, pricingStore, pricingStore, pricingStore, pricingStore, pricingStore, pricingStore, errorMessage, retryFetch, isDevelopment, scoringIsFreeBanner, displayPlans,];
        }
        let __VLS_0;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
            to: (plan.ctaLink),
            ...{ class: "plan-cta" },
            ...{ class: (plan.recommended ? 'cta-primary' : 'cta-secondary') },
        }));
        const __VLS_2 = __VLS_1({
            to: (plan.ctaLink),
            ...{ class: "plan-cta" },
            ...{ class: (plan.recommended ? 'cta-primary' : 'cta-secondary') },
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        /** @type {__VLS_StyleScopedClasses['plan-cta']} */ ;
        const { default: __VLS_5 } = __VLS_3.slots;
        (plan.cta);
        // @ts-ignore
        [];
        var __VLS_3;
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "pricing-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-footer']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "pricing-note" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-note']} */ ;
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        to: "/",
        ...{ class: "back-link" },
    }));
    const __VLS_8 = __VLS_7({
        to: "/",
        ...{ class: "back-link" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    /** @type {__VLS_StyleScopedClasses['back-link']} */ ;
    const { default: __VLS_11 } = __VLS_9.slots;
    // @ts-ignore
    [];
    var __VLS_9;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
