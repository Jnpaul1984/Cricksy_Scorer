/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, watch } from 'vue';
import { getStoredToken } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const auth = useAuthStore();
// Profile state - initialize from store
const profileName = ref('');
const profileEmail = ref('');
const profileSaving = ref(false);
const profileMessage = ref(null);
// Preferences state
const preferredFormat = ref('t20');
const darkMode = ref(true);
const preferencesSaving = ref(false);
const preferencesMessage = ref(null);
// Auth state - use store getters
const isLoggedIn = computed(() => auth.isLoggedIn);
const userRole = computed(() => auth.role?.toLowerCase() || 'free');
const userSubscription = computed(() => auth.subscription);
// Plan info mapping
const planInfo = {
    free: {
        label: 'Free',
        color: '#888',
        features: ['Basic scoring', 'View matches', 'Limited AI features'],
    },
    player_pro: {
        label: 'Player Pro',
        color: '#10b981',
        features: ['Performance analytics', 'AI insights', 'Player profile'],
    },
    coach_pro: {
        label: 'Coach Pro',
        color: '#3b82f6',
        features: ['Team management', 'Session notes', 'Advanced analytics'],
    },
    analyst_pro: {
        label: 'Analyst Pro',
        color: '#8b5cf6',
        features: ['Match case studies', 'Export reports', 'Full AI access'],
    },
    org_pro: {
        label: 'Organization Pro',
        color: '#f59e0b',
        features: ['Unlimited seats', 'Tournament management', 'Priority support'],
    },
    superuser: {
        label: 'Administrator',
        color: '#ef4444',
        features: ['Full system access', 'User management', 'All features'],
    },
};
const currentPlan = computed(() => planInfo[userRole.value] || planInfo.free);
// Subscription info from store or fallback
const subscriptionInfo = computed(() => ({
    plan: userSubscription.value?.plan || userRole.value,
    planLabel: currentPlan.value.label,
    renewalDate: userSubscription.value?.renewal_date || null,
    status: userSubscription.value?.status || 'active',
    tokensUsed: userSubscription.value?.tokens_used || 0,
    tokensLimit: userSubscription.value?.tokens_limit || null,
}));
// Can upgrade
const canUpgrade = computed(() => ['free', 'player_pro'].includes(userRole.value));
const canDowngrade = computed(() => !['free', 'superuser'].includes(userRole.value));
// Load user data from store
function loadUserData() {
    // Use store getters for profile data
    profileEmail.value = auth.userEmail;
    profileName.value = auth.userName;
    // Load preferences from localStorage
    const savedPrefs = localStorage.getItem('cricksy-preferences');
    if (savedPrefs) {
        try {
            const prefs = JSON.parse(savedPrefs);
            preferredFormat.value = prefs.format || 't20';
            darkMode.value = prefs.darkMode ?? true;
        }
        catch {
            // Ignore parse errors
        }
    }
}
// Save profile
async function saveProfile() {
    profileSaving.value = true;
    profileMessage.value = null;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        // Note: Backend would need an endpoint for this
        // For now, just simulate success
        await new Promise(resolve => setTimeout(resolve, 500));
        profileMessage.value = { type: 'success', text: 'Profile updated successfully' };
        setTimeout(() => { profileMessage.value = null; }, 3000);
    }
    catch (err) {
        profileMessage.value = { type: 'error', text: err.message || 'Failed to update profile' };
    }
    finally {
        profileSaving.value = false;
    }
}
// Save preferences
function savePreferences() {
    preferencesSaving.value = true;
    preferencesMessage.value = null;
    try {
        const prefs = {
            format: preferredFormat.value,
            darkMode: darkMode.value,
        };
        localStorage.setItem('cricksy-preferences', JSON.stringify(prefs));
        // Apply dark mode
        document.documentElement.classList.toggle('light-mode', !darkMode.value);
        preferencesMessage.value = { type: 'success', text: 'Preferences saved' };
        setTimeout(() => { preferencesMessage.value = null; }, 3000);
    }
    catch {
        preferencesMessage.value = { type: 'error', text: 'Failed to save preferences' };
    }
    finally {
        preferencesSaving.value = false;
    }
}
// Handle delete account
function handleDeleteAccount() {
    alert('Contact support to delete your account');
}
// Watch dark mode changes
watch(darkMode, (newValue) => {
    document.documentElement.classList.toggle('light-mode', !newValue);
});
onMounted(() => {
    if (isLoggedIn.value) {
        loadUserData();
    }
});
// Reload when user changes
watch(() => auth.user, () => {
    if (auth.user) {
        loadUserData();
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['banner']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
/** @type {__VLS_StyleScopedClasses['radio-option']} */ ;
/** @type {__VLS_StyleScopedClasses['toggle-switch']} */ ;
/** @type {__VLS_StyleScopedClasses['toggle-switch']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['toggle-thumb']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-upgrade']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-downgrade']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-usage']} */ ;
/** @type {__VLS_StyleScopedClasses['billing-note']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['danger-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['danger-info']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['settings-view']} */ ;
/** @type {__VLS_StyleScopedClasses['plan-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['danger-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "settings-view" },
});
/** @type {__VLS_StyleScopedClasses['settings-view']} */ ;
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "banner info" },
    });
    /** @type {__VLS_StyleScopedClasses['banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['info']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        to: "/login",
        ...{ class: "link-inline" },
    }));
    const __VLS_2 = __VLS_1({
        to: "/login",
        ...{ class: "link-inline" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['link-inline']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    // @ts-ignore
    [isLoggedIn,];
    var __VLS_3;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
if (__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "settings-content" },
    });
    /** @type {__VLS_StyleScopedClasses['settings-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "settings-section" },
    });
    /** @type {__VLS_StyleScopedClasses['settings-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-header" },
    });
    /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-body" },
    });
    /** @type {__VLS_StyleScopedClasses['section-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.profileName),
        type: "text",
        ...{ class: "ds-input" },
        placeholder: "Your name",
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "email",
        ...{ class: "ds-input" },
        disabled: true,
    });
    (__VLS_ctx.profileEmail);
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "field-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['field-hint']} */ ;
    if (__VLS_ctx.profileMessage) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "message" },
            ...{ class: (__VLS_ctx.profileMessage.type) },
        });
        /** @type {__VLS_StyleScopedClasses['message']} */ ;
        (__VLS_ctx.profileMessage.text);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.saveProfile) },
        ...{ class: "btn-primary" },
        disabled: (__VLS_ctx.profileSaving),
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    (__VLS_ctx.profileSaving ? 'Saving...' : 'Save Profile');
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "settings-section" },
    });
    /** @type {__VLS_StyleScopedClasses['settings-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-header" },
    });
    /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-body" },
    });
    /** @type {__VLS_StyleScopedClasses['section-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "radio-group" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "radio-option" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-option']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "radio",
        value: "t20",
    });
    (__VLS_ctx.preferredFormat);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "radio-label" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "radio-option" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-option']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "radio",
        value: "odi",
    });
    (__VLS_ctx.preferredFormat);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "radio-label" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "radio-option" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-option']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "radio",
        value: "test",
    });
    (__VLS_ctx.preferredFormat);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "radio-label" },
    });
    /** @type {__VLS_StyleScopedClasses['radio-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "toggle-row" },
    });
    /** @type {__VLS_StyleScopedClasses['toggle-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "toggle-label" },
    });
    /** @type {__VLS_StyleScopedClasses['toggle-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.isLoggedIn))
                    return;
                __VLS_ctx.darkMode = !__VLS_ctx.darkMode;
                // @ts-ignore
                [isLoggedIn, profileName, profileEmail, profileMessage, profileMessage, profileMessage, saveProfile, profileSaving, profileSaving, preferredFormat, preferredFormat, preferredFormat, darkMode, darkMode,];
            } },
        ...{ class: "toggle-switch" },
        ...{ class: ({ active: __VLS_ctx.darkMode }) },
        role: "switch",
        'aria-checked': (__VLS_ctx.darkMode),
    });
    /** @type {__VLS_StyleScopedClasses['toggle-switch']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span)({
        ...{ class: "toggle-thumb" },
    });
    /** @type {__VLS_StyleScopedClasses['toggle-thumb']} */ ;
    if (__VLS_ctx.preferencesMessage) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "message" },
            ...{ class: (__VLS_ctx.preferencesMessage.type) },
        });
        /** @type {__VLS_StyleScopedClasses['message']} */ ;
        (__VLS_ctx.preferencesMessage.text);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.savePreferences) },
        ...{ class: "btn-primary" },
        disabled: (__VLS_ctx.preferencesSaving),
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    (__VLS_ctx.preferencesSaving ? 'Saving...' : 'Save Preferences');
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "settings-section subscription-section" },
    });
    /** @type {__VLS_StyleScopedClasses['settings-section']} */ ;
    /** @type {__VLS_StyleScopedClasses['subscription-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-header" },
    });
    /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-body" },
    });
    /** @type {__VLS_StyleScopedClasses['section-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "subscription-card" },
        ...{ style: ({ '--plan-color': __VLS_ctx.currentPlan.color }) },
    });
    /** @type {__VLS_StyleScopedClasses['subscription-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "plan-header" },
    });
    /** @type {__VLS_StyleScopedClasses['plan-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "plan-badge" },
        ...{ style: ({ background: __VLS_ctx.currentPlan.color }) },
    });
    /** @type {__VLS_StyleScopedClasses['plan-badge']} */ ;
    (__VLS_ctx.currentPlan.label);
    if (__VLS_ctx.subscriptionInfo.status === 'active') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "status-active" },
        });
        /** @type {__VLS_StyleScopedClasses['status-active']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "plan-features" },
    });
    /** @type {__VLS_StyleScopedClasses['plan-features']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    for (const [feature] of __VLS_vFor((__VLS_ctx.currentPlan.features))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (feature),
        });
        (feature);
        // @ts-ignore
        [darkMode, darkMode, preferencesMessage, preferencesMessage, preferencesMessage, savePreferences, preferencesSaving, preferencesSaving, currentPlan, currentPlan, currentPlan, currentPlan, subscriptionInfo,];
    }
    if (__VLS_ctx.subscriptionInfo.renewalDate) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "renewal-info" },
        });
        /** @type {__VLS_StyleScopedClasses['renewal-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "renewal-label" },
        });
        /** @type {__VLS_StyleScopedClasses['renewal-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "renewal-date" },
        });
        /** @type {__VLS_StyleScopedClasses['renewal-date']} */ ;
        (__VLS_ctx.subscriptionInfo.renewalDate);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "plan-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['plan-actions']} */ ;
    if (__VLS_ctx.canUpgrade) {
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            to: "/pricing",
            ...{ class: "btn-upgrade" },
        }));
        const __VLS_8 = __VLS_7({
            to: "/pricing",
            ...{ class: "btn-upgrade" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        /** @type {__VLS_StyleScopedClasses['btn-upgrade']} */ ;
        const { default: __VLS_11 } = __VLS_9.slots;
        // @ts-ignore
        [subscriptionInfo, subscriptionInfo, canUpgrade,];
        var __VLS_9;
    }
    if (__VLS_ctx.canDowngrade) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (() => { }) },
            ...{ class: "btn-downgrade" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-downgrade']} */ ;
    }
    let __VLS_12;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
        to: "/usage",
        ...{ class: "btn-usage" },
    }));
    const __VLS_14 = __VLS_13({
        to: "/usage",
        ...{ class: "btn-usage" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    /** @type {__VLS_StyleScopedClasses['btn-usage']} */ ;
    const { default: __VLS_17 } = __VLS_15.slots;
    // @ts-ignore
    [canDowngrade,];
    var __VLS_15;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "billing-note" },
    });
    /** @type {__VLS_StyleScopedClasses['billing-note']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
        href: "mailto:support@cricksy.com",
        ...{ class: "link" },
    });
    /** @type {__VLS_StyleScopedClasses['link']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "settings-section danger-section" },
    });
    /** @type {__VLS_StyleScopedClasses['settings-section']} */ ;
    /** @type {__VLS_StyleScopedClasses['danger-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-header" },
    });
    /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-body" },
    });
    /** @type {__VLS_StyleScopedClasses['section-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "danger-item" },
    });
    /** @type {__VLS_StyleScopedClasses['danger-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "danger-info" },
    });
    /** @type {__VLS_StyleScopedClasses['danger-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.handleDeleteAccount) },
        ...{ class: "btn-danger" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
}
// @ts-ignore
[handleDeleteAccount,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
