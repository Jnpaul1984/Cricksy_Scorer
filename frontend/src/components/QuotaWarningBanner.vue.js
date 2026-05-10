/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, watch } from 'vue';
import { API_BASE, getStoredToken } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const auth = useAuthStore();
// State
const quotaUsed = ref(0);
const quotaLimit = ref(null);
const quotaPercentage = ref(0);
const loading = ref(false);
const dismissed = ref(false);
const lastFetchTime = ref(0);
// Check if user is authenticated
const isLoggedIn = computed(() => !!auth.token);
// Should show banner (80%+ usage, not unlimited, not dismissed)
const shouldShow = computed(() => {
    if (!isLoggedIn.value)
        return false;
    if (dismissed.value)
        return false;
    if (quotaLimit.value === null)
        return false; // Unlimited
    return quotaPercentage.value >= 80;
});
// Can upgrade (free or player_pro)
const canUpgrade = computed(() => {
    const role = auth.role?.toLowerCase() || '';
    return ['free', 'player_pro'].includes(role);
});
// Warning level
const warningLevel = computed(() => {
    if (quotaPercentage.value >= 95)
        return 'critical';
    if (quotaPercentage.value >= 90)
        return 'danger';
    return 'warning';
});
// Message based on percentage
const message = computed(() => {
    const pct = Math.round(quotaPercentage.value);
    if (pct >= 100) {
        return `You've reached your AI allowance limit for this period.`;
    }
    if (pct >= 95) {
        return `You've used ${pct}% of your AI allowance — almost at the limit!`;
    }
    return `You've used ${pct}% of your AI allowance this period.`;
});
// Fetch quota from API
async function fetchQuota() {
    // Rate limit: don't fetch more than once per 5 minutes
    const now = Date.now();
    if (now - lastFetchTime.value < 5 * 60 * 1000 && lastFetchTime.value > 0) {
        return;
    }
    if (!isLoggedIn.value)
        return;
    loading.value = true;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const res = await fetch(`${API_BASE}/api/ai-usage/my-usage`, { headers });
        if (res.ok) {
            const data = await res.json();
            quotaUsed.value = data.quota?.used || 0;
            quotaLimit.value = data.quota?.limit || null;
            quotaPercentage.value = data.quota?.percentage || 0;
            lastFetchTime.value = now;
        }
    }
    catch (err) {
        console.error('Failed to fetch AI quota:', err);
    }
    finally {
        loading.value = false;
    }
}
function dismiss() {
    dismissed.value = true;
    // Store in sessionStorage so it stays dismissed for the session
    sessionStorage.setItem('quota-banner-dismissed', 'true');
}
// Restore dismissed state
onMounted(() => {
    if (sessionStorage.getItem('quota-banner-dismissed') === 'true') {
        dismissed.value = true;
    }
    fetchQuota();
});
// Re-fetch when user logs in
watch(() => auth.token, (newToken) => {
    if (newToken) {
        dismissed.value = false;
        sessionStorage.removeItem('quota-banner-dismissed');
        fetchQuota();
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['quota-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['quota-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['quota-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['view-usage-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['dismiss-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['quota-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['banner-message']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-btn']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Transition | typeof __VLS_components.Transition} */
Transition;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    name: "slide-down",
}));
const __VLS_2 = __VLS_1({
    name: "slide-down",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
if (__VLS_ctx.shouldShow) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "quota-banner" },
        ...{ class: (__VLS_ctx.warningLevel) },
    });
    /** @type {__VLS_StyleScopedClasses['quota-banner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "banner-content" },
    });
    /** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "banner-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['banner-icon']} */ ;
    (__VLS_ctx.warningLevel === 'critical' ? '🚫' : __VLS_ctx.warningLevel === 'danger' ? '⚠️' : '📊');
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "banner-message" },
    });
    /** @type {__VLS_StyleScopedClasses['banner-message']} */ ;
    (__VLS_ctx.message);
    if (__VLS_ctx.canUpgrade) {
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            to: "/pricing",
            ...{ class: "upgrade-btn" },
        }));
        const __VLS_8 = __VLS_7({
            to: "/pricing",
            ...{ class: "upgrade-btn" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        /** @type {__VLS_StyleScopedClasses['upgrade-btn']} */ ;
        const { default: __VLS_11 } = __VLS_9.slots;
        // @ts-ignore
        [shouldShow, warningLevel, warningLevel, warningLevel, message, canUpgrade,];
        var __VLS_9;
    }
    else {
        let __VLS_12;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
            to: "/usage",
            ...{ class: "view-usage-btn" },
        }));
        const __VLS_14 = __VLS_13({
            to: "/usage",
            ...{ class: "view-usage-btn" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_13));
        /** @type {__VLS_StyleScopedClasses['view-usage-btn']} */ ;
        const { default: __VLS_17 } = __VLS_15.slots;
        // @ts-ignore
        [];
        var __VLS_15;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.dismiss) },
        ...{ class: "dismiss-btn" },
        'aria-label': "Dismiss",
    });
    /** @type {__VLS_StyleScopedClasses['dismiss-btn']} */ ;
}
// @ts-ignore
[dismiss,];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
