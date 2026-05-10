/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { BaseCard, BaseButton, BaseBadge } from '@/components';
import { usePricingStore } from '@/stores/pricingStore';
// ----------------------------------------------------------------------------
// Pinia Store - SINGLE SOURCE OF TRUTH
// ----------------------------------------------------------------------------
const pricingStore = usePricingStore();
const router = useRouter();
const billingPeriod = ref('monthly');
// Fetch pricing on component mount
onMounted(async () => {
    if (pricingStore.displayPlans.length === 0) {
        await pricingStore.fetchPricing();
    }
});
// ----------------------------------------------------------------------------
// Computed display plans with billing period
// ----------------------------------------------------------------------------
const displayPlans = computed(() => pricingStore.individualDisplayPlans.map((plan) => {
    const price = billingPeriod.value === 'monthly' ? plan.monthlyPrice : plan.annualPrice;
    let priceDisplay;
    if (plan.isContactSales) {
        priceDisplay = 'Contact Sales';
    }
    else if (price === 0) {
        priceDisplay = '$0';
    }
    else {
        priceDisplay = billingPeriod.value === 'monthly' ? plan.monthlyDisplay : plan.annualDisplay;
    }
    return {
        ...plan,
        price,
        priceDisplay,
    };
}));
function setBilling(period) {
    billingPeriod.value = period;
}
function goToSignup(planId) {
    // Navigate to signup with plan preselected (adjust path as needed)
    router.push({ path: '/auth/register', query: { plan: planId } });
}
function handleContactSales(planId) {
    // Open contact form or email (could also navigate to a contact page)
    // For now, show a message and optionally open email client
    const email = 'sales@cricksy.ai';
    const subject = `Cricksy ${planId.replace(/-/g, ' ')} Pricing Inquiry`;
    const body = `Hi,\n\nI'm interested in learning more about the ${planId} plan for my organization.\n\nPlease contact me with more details.\n\nThanks`;
    window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
// ----------------------------------------------------------------------------
// Trial info helper
// ----------------------------------------------------------------------------
function trialInfoFor(planId) {
    switch (planId) {
        case 'free-scoring': // Backend: free_scoring
            return null; // Free plan has no trial
        case 'player-pro':
        case 'coach-pro':
        case 'coach-pro-plus':
        case 'analyst-pro':
            return { trialLabel: '14-day free trial' };
        case 'org-pro': // Org plans consolidated
        case 'org-starter':
        case 'org-growth':
        case 'org-elite':
            return { trialLabel: '30-day free trial', cardRequired: true };
        default:
            return null;
    }
}
// ----------------------------------------------------------------------------
// Feature matrix
// ----------------------------------------------------------------------------
const matrixRows = [
    { key: 'match_scoring', label: 'Manual match scoring' },
    { key: 'live_viewer', label: 'Live text scoreboard & public viewer' },
    { key: 'basic_stats', label: 'Basic player stats & history' },
    { key: 'career_dashboard', label: 'Full player career dashboard' },
    { key: 'form_tracker', label: 'Form & season graphs' },
    { key: 'ai_player_insights', label: 'AI player insights (career summaries)' },
    { key: 'coach_tools', label: 'Coach tools (session notes, dev dashboard)' },
    { key: 'ai_session_summaries', label: 'AI session summaries' },
    { key: 'analyst_workspace', label: 'Analyst workspace & advanced analytics' },
    { key: 'exports', label: 'Data exports (CSV/JSON/PDF)' },
    { key: 'org_dashboards', label: 'Org-level dashboards' },
    { key: 'sponsors', label: 'Sponsor panel & branded viewers' },
    { key: 'tournament_mgmt', label: 'Tournament / league management' },
];
function rowIncluded(rowKey, planId) {
    const order = [
        'free',
        'player-pro',
        'coach-pro',
        'coach-pro-plus',
        'analyst-pro',
        'org-starter',
        'org-growth',
        'org-elite',
    ];
    const index = order.indexOf(planId);
    if (index === -1)
        return false;
    switch (rowKey) {
        // Free and up
        case 'match_scoring':
        case 'live_viewer':
        case 'basic_stats':
            return index >= 0;
        // Scorers Pro and up
        case 'career_dashboard':
        case 'form_tracker':
        case 'ai_player_insights':
            return index >= 1;
        // Coach Pro and up
        case 'coach_tools':
        case 'ai_session_summaries':
            return index >= 2;
        // Analyst Pro and up
        case 'analyst_workspace':
        case 'exports':
            return index >= 3;
        // Org Starter and up
        case 'org_dashboards':
        case 'sponsors':
        case 'tournament_mgmt':
            return index >= 4;
        default:
            return false;
    }
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hero-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['billing-label']} */ ;
/** @type {__VLS_StyleScopedClasses['billing-label']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-title-row']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-price']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-price']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-trial']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing-error']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-matrix']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-matrix']} */ ;
/** @type {__VLS_StyleScopedClasses['matrix-header']} */ ;
/** @type {__VLS_StyleScopedClasses['matrix-row']} */ ;
/** @type {__VLS_StyleScopedClasses['matrix-row']} */ ;
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing-page" },
});
/** @type {__VLS_StyleScopedClasses['pricing-page']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "pricing-hero" },
});
/** @type {__VLS_StyleScopedClasses['pricing-hero']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-copy" },
});
/** @type {__VLS_StyleScopedClasses['hero-copy']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "billing-toggle" },
});
/** @type {__VLS_StyleScopedClasses['billing-toggle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.setBilling('monthly');
            // @ts-ignore
            [setBilling,];
        } },
    ...{ class: (['billing-label', __VLS_ctx.billingPeriod === 'monthly' && 'is-active']) },
});
/** @type {__VLS_StyleScopedClasses['billing-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "billing-divider" },
});
/** @type {__VLS_StyleScopedClasses['billing-divider']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.setBilling('annual');
            // @ts-ignore
            [setBilling, billingPeriod,];
        } },
    ...{ class: (['billing-label', __VLS_ctx.billingPeriod === 'annual' && 'is-active']) },
});
/** @type {__VLS_StyleScopedClasses['billing-label']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    variant: "success",
    uppercase: (false),
}));
const __VLS_2 = __VLS_1({
    variant: "success",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
// @ts-ignore
[billingPeriod,];
var __VLS_3;
if (__VLS_ctx.pricingStore.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "plans-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['plans-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pricing-loading" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-loading']} */ ;
}
else if (__VLS_ctx.pricingStore.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "plans-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['plans-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pricing-error" },
    });
    /** @type {__VLS_StyleScopedClasses['pricing-error']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "plans-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['plans-grid']} */ ;
    for (const [plan] of __VLS_vFor((__VLS_ctx.displayPlans))) {
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            key: (plan.id),
            padding: "lg",
            ...{ class: "plan-card" },
            ...{ class: ({ 'plan-card--highlight': plan.highlight }) },
        }));
        const __VLS_8 = __VLS_7({
            key: (plan.id),
            padding: "lg",
            ...{ class: "plan-card" },
            ...{ class: ({ 'plan-card--highlight': plan.highlight }) },
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        /** @type {__VLS_StyleScopedClasses['plan-card']} */ ;
        /** @type {__VLS_StyleScopedClasses['plan-card--highlight']} */ ;
        const { default: __VLS_11 } = __VLS_9.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
            ...{ class: "plan-header" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "plan-title-row" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-title-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        (plan.name);
        if (plan.highlight) {
            let __VLS_12;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
                variant: "primary",
            }));
            const __VLS_14 = __VLS_13({
                variant: "primary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_13));
            const { default: __VLS_17 } = __VLS_15.slots;
            // @ts-ignore
            [pricingStore, pricingStore, displayPlans,];
            var __VLS_15;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "plan-tagline" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-tagline']} */ ;
        (plan.tagline);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "plan-price" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-price']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "amount" },
        });
        /** @type {__VLS_StyleScopedClasses['amount']} */ ;
        (plan.priceDisplay);
        if (!plan.isContactSales) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "period" },
            });
            /** @type {__VLS_StyleScopedClasses['period']} */ ;
            (__VLS_ctx.billingPeriod === 'monthly' ? 'month' : 'year');
        }
        if (__VLS_ctx.trialInfoFor(plan.id)) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "plan-trial" },
            });
            /** @type {__VLS_StyleScopedClasses['plan-trial']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            (__VLS_ctx.trialInfoFor(plan.id)?.trialLabel);
            if (__VLS_ctx.trialInfoFor(plan.id)?.cardRequired) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "plan-trial-hint" },
                });
                /** @type {__VLS_StyleScopedClasses['plan-trial-hint']} */ ;
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "plan-features" },
        });
        /** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
        for (const [feature] of __VLS_vFor((plan.features))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (feature),
                ...{ class: "plan-feature-item" },
            });
            /** @type {__VLS_StyleScopedClasses['plan-feature-item']} */ ;
            (feature);
            // @ts-ignore
            [billingPeriod, trialInfoFor, trialInfoFor, trialInfoFor,];
        }
        let __VLS_18;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
            ...{ 'onClick': {} },
            variant: "primary",
            size: "md",
            ...{ class: "plan-cta" },
        }));
        const __VLS_20 = __VLS_19({
            ...{ 'onClick': {} },
            variant: "primary",
            size: "md",
            ...{ class: "plan-cta" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_19));
        let __VLS_23;
        const __VLS_24 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.pricingStore.loading))
                        return;
                    if (!!(__VLS_ctx.pricingStore.error))
                        return;
                    plan.isContactSales ? __VLS_ctx.handleContactSales(plan.id) : __VLS_ctx.goToSignup(plan.id);
                    // @ts-ignore
                    [handleContactSales, goToSignup,];
                } });
        /** @type {__VLS_StyleScopedClasses['plan-cta']} */ ;
        const { default: __VLS_25 } = __VLS_21.slots;
        (plan.ctaLabel);
        // @ts-ignore
        [];
        var __VLS_21;
        var __VLS_22;
        // @ts-ignore
        [];
        var __VLS_9;
        // @ts-ignore
        [];
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "feature-matrix" },
});
/** @type {__VLS_StyleScopedClasses['feature-matrix']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
let __VLS_26;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
    padding: "lg",
    ...{ class: "matrix-card" },
}));
const __VLS_28 = __VLS_27({
    padding: "lg",
    ...{ class: "matrix-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_27));
/** @type {__VLS_StyleScopedClasses['matrix-card']} */ ;
const { default: __VLS_31 } = __VLS_29.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matrix" },
});
/** @type {__VLS_StyleScopedClasses['matrix']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matrix-header" },
});
/** @type {__VLS_StyleScopedClasses['matrix-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matrix-feature-col" },
});
/** @type {__VLS_StyleScopedClasses['matrix-feature-col']} */ ;
for (const [plan] of __VLS_vFor((__VLS_ctx.displayPlans))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (plan.id),
        ...{ class: "matrix-plan-col" },
    });
    /** @type {__VLS_StyleScopedClasses['matrix-plan-col']} */ ;
    (plan.name);
    // @ts-ignore
    [displayPlans,];
}
for (const [row] of __VLS_vFor((__VLS_ctx.matrixRows))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (row.key),
        ...{ class: "matrix-row" },
    });
    /** @type {__VLS_StyleScopedClasses['matrix-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "matrix-feature-col" },
    });
    /** @type {__VLS_StyleScopedClasses['matrix-feature-col']} */ ;
    (row.label);
    for (const [plan] of __VLS_vFor((__VLS_ctx.displayPlans))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (plan.id + row.key),
            ...{ class: "matrix-plan-col" },
        });
        /** @type {__VLS_StyleScopedClasses['matrix-plan-col']} */ ;
        if (__VLS_ctx.rowIncluded(row.key, plan.id)) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        }
        // @ts-ignore
        [displayPlans, matrixRows, rowIncluded,];
    }
    // @ts-ignore
    [];
}
// @ts-ignore
[];
var __VLS_29;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "pricing-final-cta" },
});
/** @type {__VLS_StyleScopedClasses['pricing-final-cta']} */ ;
let __VLS_32;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent1(__VLS_32, new __VLS_32({
    padding: "lg",
    ...{ class: "final-card" },
}));
const __VLS_34 = __VLS_33({
    padding: "lg",
    ...{ class: "final-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
const { default: __VLS_37 } = __VLS_35.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
let __VLS_38;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_39 = __VLS_asFunctionalComponent1(__VLS_38, new __VLS_38({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}));
const __VLS_40 = __VLS_39({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}, ...__VLS_functionalComponentArgsRest(__VLS_39));
let __VLS_43;
const __VLS_44 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.goToSignup('free');
            // @ts-ignore
            [goToSignup,];
        } });
const { default: __VLS_45 } = __VLS_41.slots;
// @ts-ignore
[];
var __VLS_41;
var __VLS_42;
// @ts-ignore
[];
var __VLS_35;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
