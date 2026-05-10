/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { BaseButton, BaseCard, BaseInput, BaseBadge } from '@/components';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const auth = useAuthStore();
// Form state
const email = ref('');
const role = ref('player_pro');
const plan = ref('player_pro');
const orgId = ref('');
const betaTag = ref('beta_phase1');
const password = ref('');
// UI state
const loading = ref(false);
const error = ref(null);
const createdUser = ref(null);
const copied = ref(false);
const tab = ref('create');
// User list state
const userList = ref([]);
const loadingUsers = ref(false);
const userError = ref(null);
// User action state
const selectedUser = ref(null);
const resetPasswordLoading = ref(false);
const resetPasswordCustom = ref('');
const deactivatingUser = ref(null);
// Auth check
const isSuperAdmin = computed(() => auth.isSuper);
// Role options matching backend RoleEnum
const roleOptions = [
    { value: 'free', label: 'Free' },
    { value: 'player_pro', label: 'Player Pro' },
    { value: 'coach_pro', label: 'Coach Pro' },
    { value: 'analyst_pro', label: 'Analyst Pro' },
    { value: 'org_pro', label: 'Organization Pro' },
];
// Plan options (same as roles in this app)
const planOptions = [
    { value: 'free', label: 'Free' },
    { value: 'player_pro', label: 'Player Pro' },
    { value: 'coach_pro', label: 'Coach Pro' },
    { value: 'analyst_pro', label: 'Analyst Pro' },
    { value: 'org_pro', label: 'Organization Pro' },
];
// Load user list when tab changes
async function loadUsers() {
    loadingUsers.value = true;
    userError.value = null;
    try {
        userList.value = await apiService.listBetaUsers();
    }
    catch (err) {
        userError.value = err.message || 'Failed to load users';
        console.error('Error loading users:', err);
    }
    finally {
        loadingUsers.value = false;
    }
}
async function handleSubmit() {
    // Validate
    if (!email.value.trim()) {
        error.value = 'Email is required';
        return;
    }
    loading.value = true;
    error.value = null;
    createdUser.value = null;
    try {
        const result = await apiService.createBetaUser({
            email: email.value.trim(),
            role: role.value,
            plan: plan.value,
            org_id: orgId.value.trim() || null,
            beta_tag: betaTag.value.trim() || null,
            password: password.value.trim() || null,
        });
        createdUser.value = result;
        // Reload users list
        await loadUsers();
        // Clear form except email for quick reference
        password.value = '';
    }
    catch (err) {
        error.value = err.message || 'Failed to create user';
        console.error('Error creating beta user:', err);
    }
    finally {
        loading.value = false;
    }
}
function clearForm() {
    email.value = '';
    role.value = 'player_pro';
    plan.value = 'player_pro';
    orgId.value = '';
    betaTag.value = 'beta_phase1';
    password.value = '';
    createdUser.value = null;
    error.value = null;
    copied.value = false;
}
async function copyPassword() {
    if (!createdUser.value?.temp_password)
        return;
    try {
        await navigator.clipboard.writeText(createdUser.value.temp_password);
        copied.value = true;
        setTimeout(() => {
            copied.value = false;
        }, 2000);
    }
    catch (err) {
        console.error('Failed to copy:', err);
    }
}
async function handleResetPassword(userId) {
    resetPasswordLoading.value = true;
    userError.value = null;
    try {
        const result = await apiService.resetUserPassword(userId, resetPasswordCustom.value.trim() || null);
        // Show the new password
        alert(`Password reset for ${result.email}\n\n` +
            `New temporary password:\n${result.temp_password}\n\n` +
            'Make sure to send this to the user securely.');
        resetPasswordCustom.value = '';
        selectedUser.value = null;
        await loadUsers();
    }
    catch (err) {
        userError.value = err.message || 'Failed to reset password';
        console.error('Error resetting password:', err);
    }
    finally {
        resetPasswordLoading.value = false;
    }
}
async function handleDeactivateUser(userId) {
    if (!confirm('Are you sure you want to deactivate this user? They will not be able to log in.')) {
        return;
    }
    deactivatingUser.value = userId;
    userError.value = null;
    try {
        await apiService.deactivateUser(userId);
        await loadUsers();
    }
    catch (err) {
        userError.value = err.message || 'Failed to deactivate user';
        console.error('Error deactivating user:', err);
    }
    finally {
        deactivatingUser.value = null;
    }
}
async function handleReactivateUser(userId) {
    deactivatingUser.value = userId;
    userError.value = null;
    try {
        await apiService.reactivateUser(userId);
        await loadUsers();
    }
    catch (err) {
        userError.value = err.message || 'Failed to reactivate user';
        console.error('Error reactivating user:', err);
    }
    finally {
        deactivatingUser.value = null;
    }
}
function switchTab(newTab) {
    tab.value = newTab;
    if (newTab === 'manage') {
        loadUsers();
    }
}
onMounted(() => {
    if (tab.value === 'manage') {
        loadUsers();
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
/** @type {__VLS_StyleScopedClasses['success-content']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
/** @type {__VLS_StyleScopedClasses['reminder-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['access-denied']} */ ;
/** @type {__VLS_StyleScopedClasses['access-denied']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
/** @type {__VLS_StyleScopedClasses['users-table']} */ ;
/** @type {__VLS_StyleScopedClasses['users-table']} */ ;
/** @type {__VLS_StyleScopedClasses['users-table']} */ ;
/** @type {__VLS_StyleScopedClasses['users-table']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "admin-page" },
});
/** @type {__VLS_StyleScopedClasses['admin-page']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({
    ...{ class: "page-title" },
});
/** @type {__VLS_StyleScopedClasses['page-title']} */ ;
if (!__VLS_ctx.isSuperAdmin) {
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        padding: "lg",
    }));
    const __VLS_2 = __VLS_1({
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    const { default: __VLS_5 } = __VLS_3.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "access-denied" },
    });
    /** @type {__VLS_StyleScopedClasses['access-denied']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "access-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['access-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    // @ts-ignore
    [isSuperAdmin,];
    var __VLS_3;
}
else {
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        padding: "md",
        ...{ class: "info-banner" },
    }));
    const __VLS_8 = __VLS_7({
        padding: "md",
        ...{ class: "info-banner" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    /** @type {__VLS_StyleScopedClasses['info-banner']} */ ;
    const { default: __VLS_11 } = __VLS_9.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "banner-content" },
    });
    /** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
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
    [];
    var __VLS_15;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    // @ts-ignore
    [];
    var __VLS_9;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tabs" },
    });
    /** @type {__VLS_StyleScopedClasses['tabs']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.isSuperAdmin))
                    return;
                __VLS_ctx.switchTab('create');
                // @ts-ignore
                [switchTab,];
            } },
        ...{ class: "tab-button" },
        ...{ class: ({ active: __VLS_ctx.tab === 'create' }) },
    });
    /** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.isSuperAdmin))
                    return;
                __VLS_ctx.switchTab('manage');
                // @ts-ignore
                [switchTab, tab,];
            } },
        ...{ class: "tab-button" },
        ...{ class: ({ active: __VLS_ctx.tab === 'manage' }) },
    });
    /** @type {__VLS_StyleScopedClasses['tab-button']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    if (__VLS_ctx.tab === 'create') {
        if (__VLS_ctx.createdUser) {
            let __VLS_18;
            /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
            BaseCard;
            // @ts-ignore
            const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
                padding: "lg",
                ...{ class: "success-card" },
            }));
            const __VLS_20 = __VLS_19({
                padding: "lg",
                ...{ class: "success-card" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_19));
            /** @type {__VLS_StyleScopedClasses['success-card']} */ ;
            const { default: __VLS_23 } = __VLS_21.slots;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "success-content" },
            });
            /** @type {__VLS_StyleScopedClasses['success-content']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "user-details" },
            });
            /** @type {__VLS_StyleScopedClasses['user-details']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "detail-row" },
            });
            /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (__VLS_ctx.createdUser.email);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "detail-row" },
            });
            /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            let __VLS_24;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
                variant: "primary",
            }));
            const __VLS_26 = __VLS_25({
                variant: "primary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_25));
            const { default: __VLS_29 } = __VLS_27.slots;
            (__VLS_ctx.createdUser.role);
            // @ts-ignore
            [tab, tab, createdUser, createdUser, createdUser,];
            var __VLS_27;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "detail-row" },
            });
            /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            let __VLS_30;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
                variant: "neutral",
            }));
            const __VLS_32 = __VLS_31({
                variant: "neutral",
            }, ...__VLS_functionalComponentArgsRest(__VLS_31));
            const { default: __VLS_35 } = __VLS_33.slots;
            (__VLS_ctx.createdUser.plan);
            // @ts-ignore
            [createdUser,];
            var __VLS_33;
            if (__VLS_ctx.createdUser.org_id) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "detail-row" },
                });
                /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "label" },
                });
                /** @type {__VLS_StyleScopedClasses['label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "value" },
                });
                /** @type {__VLS_StyleScopedClasses['value']} */ ;
                (__VLS_ctx.createdUser.org_id);
            }
            if (__VLS_ctx.createdUser.beta_tag) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "detail-row" },
                });
                /** @type {__VLS_StyleScopedClasses['detail-row']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "label" },
                });
                /** @type {__VLS_StyleScopedClasses['label']} */ ;
                let __VLS_36;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
                    variant: "primary",
                }));
                const __VLS_38 = __VLS_37({
                    variant: "primary",
                }, ...__VLS_functionalComponentArgsRest(__VLS_37));
                const { default: __VLS_41 } = __VLS_39.slots;
                (__VLS_ctx.createdUser.beta_tag);
                // @ts-ignore
                [createdUser, createdUser, createdUser, createdUser,];
                var __VLS_39;
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "password-section" },
            });
            /** @type {__VLS_StyleScopedClasses['password-section']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "password-label" },
            });
            /** @type {__VLS_StyleScopedClasses['password-label']} */ ;
            (__VLS_ctx.createdUser.email);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "password-display" },
            });
            /** @type {__VLS_StyleScopedClasses['password-display']} */ ;
            let __VLS_42;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
                variant: "warning",
                ...{ class: "password-badge" },
            }));
            const __VLS_44 = __VLS_43({
                variant: "warning",
                ...{ class: "password-badge" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_43));
            /** @type {__VLS_StyleScopedClasses['password-badge']} */ ;
            const { default: __VLS_47 } = __VLS_45.slots;
            (__VLS_ctx.createdUser.temp_password);
            // @ts-ignore
            [createdUser, createdUser,];
            var __VLS_45;
            let __VLS_48;
            /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
            BaseButton;
            // @ts-ignore
            const __VLS_49 = __VLS_asFunctionalComponent1(__VLS_48, new __VLS_48({
                ...{ 'onClick': {} },
                size: "sm",
                variant: (__VLS_ctx.copied ? 'primary' : 'secondary'),
            }));
            const __VLS_50 = __VLS_49({
                ...{ 'onClick': {} },
                size: "sm",
                variant: (__VLS_ctx.copied ? 'primary' : 'secondary'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_49));
            let __VLS_53;
            const __VLS_54 = ({ click: {} },
                { onClick: (__VLS_ctx.copyPassword) });
            const { default: __VLS_55 } = __VLS_51.slots;
            (__VLS_ctx.copied ? '✓ Copied' : '📋 Copy');
            // @ts-ignore
            [copied, copied, copyPassword,];
            var __VLS_51;
            var __VLS_52;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "reminder-banner" },
            });
            /** @type {__VLS_StyleScopedClasses['reminder-banner']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            let __VLS_56;
            /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
            BaseButton;
            // @ts-ignore
            const __VLS_57 = __VLS_asFunctionalComponent1(__VLS_56, new __VLS_56({
                ...{ 'onClick': {} },
                variant: "secondary",
            }));
            const __VLS_58 = __VLS_57({
                ...{ 'onClick': {} },
                variant: "secondary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_57));
            let __VLS_61;
            const __VLS_62 = ({ click: {} },
                { onClick: (__VLS_ctx.clearForm) });
            const { default: __VLS_63 } = __VLS_59.slots;
            // @ts-ignore
            [clearForm,];
            var __VLS_59;
            var __VLS_60;
            // @ts-ignore
            [];
            var __VLS_21;
        }
        else {
            let __VLS_64;
            /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
            BaseCard;
            // @ts-ignore
            const __VLS_65 = __VLS_asFunctionalComponent1(__VLS_64, new __VLS_64({
                padding: "lg",
            }));
            const __VLS_66 = __VLS_65({
                padding: "lg",
            }, ...__VLS_functionalComponentArgsRest(__VLS_65));
            const { default: __VLS_69 } = __VLS_67.slots;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
                ...{ class: "card-title" },
            });
            /** @type {__VLS_StyleScopedClasses['card-title']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
                ...{ onSubmit: (__VLS_ctx.handleSubmit) },
                ...{ class: "beta-form" },
            });
            /** @type {__VLS_StyleScopedClasses['beta-form']} */ ;
            let __VLS_70;
            /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
            BaseInput;
            // @ts-ignore
            const __VLS_71 = __VLS_asFunctionalComponent1(__VLS_70, new __VLS_70({
                modelValue: (__VLS_ctx.email),
                type: "email",
                label: "Email",
                placeholder: "user@example.com",
                required: true,
            }));
            const __VLS_72 = __VLS_71({
                modelValue: (__VLS_ctx.email),
                type: "email",
                label: "Email",
                placeholder: "user@example.com",
                required: true,
            }, ...__VLS_functionalComponentArgsRest(__VLS_71));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-group" },
            });
            /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
                ...{ class: "ds-input-label" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "ds-input-required" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input-required']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
                value: (__VLS_ctx.role),
                ...{ class: "ds-input" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
            for (const [opt] of __VLS_vFor((__VLS_ctx.roleOptions))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
                    key: (opt.value),
                    value: (opt.value),
                });
                (opt.label);
                // @ts-ignore
                [handleSubmit, email, role, roleOptions,];
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-group" },
            });
            /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
                ...{ class: "ds-input-label" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "ds-input-required" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input-required']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
                value: (__VLS_ctx.plan),
                ...{ class: "ds-input" },
            });
            /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
            for (const [opt] of __VLS_vFor((__VLS_ctx.planOptions))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
                    key: (opt.value),
                    value: (opt.value),
                });
                (opt.label);
                // @ts-ignore
                [plan, planOptions,];
            }
            let __VLS_75;
            /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
            BaseInput;
            // @ts-ignore
            const __VLS_76 = __VLS_asFunctionalComponent1(__VLS_75, new __VLS_75({
                modelValue: (__VLS_ctx.orgId),
                type: "text",
                label: "Organization ID",
                placeholder: "org-uuid (optional)",
                helpText: "Leave empty if not part of an organization",
            }));
            const __VLS_77 = __VLS_76({
                modelValue: (__VLS_ctx.orgId),
                type: "text",
                label: "Organization ID",
                placeholder: "org-uuid (optional)",
                helpText: "Leave empty if not part of an organization",
            }, ...__VLS_functionalComponentArgsRest(__VLS_76));
            let __VLS_80;
            /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
            BaseInput;
            // @ts-ignore
            const __VLS_81 = __VLS_asFunctionalComponent1(__VLS_80, new __VLS_80({
                modelValue: (__VLS_ctx.betaTag),
                type: "text",
                label: "Beta Tag",
                placeholder: "beta_phase1",
            }));
            const __VLS_82 = __VLS_81({
                modelValue: (__VLS_ctx.betaTag),
                type: "text",
                label: "Beta Tag",
                placeholder: "beta_phase1",
            }, ...__VLS_functionalComponentArgsRest(__VLS_81));
            let __VLS_85;
            /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
            BaseInput;
            // @ts-ignore
            const __VLS_86 = __VLS_asFunctionalComponent1(__VLS_85, new __VLS_85({
                modelValue: (__VLS_ctx.password),
                type: "password",
                label: "Password (optional)",
                placeholder: "Leave empty to auto-generate",
                helpText: "If empty, a secure 16-character password will be generated",
            }));
            const __VLS_87 = __VLS_86({
                modelValue: (__VLS_ctx.password),
                type: "password",
                label: "Password (optional)",
                placeholder: "Leave empty to auto-generate",
                helpText: "If empty, a secure 16-character password will be generated",
            }, ...__VLS_functionalComponentArgsRest(__VLS_86));
            if (__VLS_ctx.error) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "error-message" },
                });
                /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
                (__VLS_ctx.error);
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-actions" },
            });
            /** @type {__VLS_StyleScopedClasses['form-actions']} */ ;
            let __VLS_90;
            /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
            BaseButton;
            // @ts-ignore
            const __VLS_91 = __VLS_asFunctionalComponent1(__VLS_90, new __VLS_90({
                type: "submit",
                variant: "primary",
                disabled: (__VLS_ctx.loading),
            }));
            const __VLS_92 = __VLS_91({
                type: "submit",
                variant: "primary",
                disabled: (__VLS_ctx.loading),
            }, ...__VLS_functionalComponentArgsRest(__VLS_91));
            const { default: __VLS_95 } = __VLS_93.slots;
            (__VLS_ctx.loading ? 'Creating...' : 'Create User');
            // @ts-ignore
            [orgId, betaTag, password, error, error, loading, loading,];
            var __VLS_93;
            // @ts-ignore
            [];
            var __VLS_67;
        }
    }
    if (__VLS_ctx.tab === 'manage') {
        let __VLS_96;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_97 = __VLS_asFunctionalComponent1(__VLS_96, new __VLS_96({
            padding: "lg",
        }));
        const __VLS_98 = __VLS_97({
            padding: "lg",
        }, ...__VLS_functionalComponentArgsRest(__VLS_97));
        const { default: __VLS_101 } = __VLS_99.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "card-title" },
        });
        /** @type {__VLS_StyleScopedClasses['card-title']} */ ;
        if (__VLS_ctx.userError) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "error-message" },
            });
            /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
            (__VLS_ctx.userError);
        }
        if (__VLS_ctx.loadingUsers) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "loading-state" },
            });
            /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
        }
        else if (__VLS_ctx.userList.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "empty-state" },
            });
            /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "users-table-wrapper" },
            });
            /** @type {__VLS_StyleScopedClasses['users-table-wrapper']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
                ...{ class: "users-table" },
            });
            /** @type {__VLS_StyleScopedClasses['users-table']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
            for (const [user] of __VLS_vFor((__VLS_ctx.userList))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                    key: (user.id),
                    ...{ class: ({ inactive: !user.is_active }) },
                });
                /** @type {__VLS_StyleScopedClasses['inactive']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                    ...{ class: "email-cell" },
                });
                /** @type {__VLS_StyleScopedClasses['email-cell']} */ ;
                (user.email);
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                let __VLS_102;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_103 = __VLS_asFunctionalComponent1(__VLS_102, new __VLS_102({
                    variant: "primary",
                }));
                const __VLS_104 = __VLS_103({
                    variant: "primary",
                }, ...__VLS_functionalComponentArgsRest(__VLS_103));
                const { default: __VLS_107 } = __VLS_105.slots;
                (user.role);
                // @ts-ignore
                [tab, userError, userError, loadingUsers, userList, userList,];
                var __VLS_105;
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                let __VLS_108;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_109 = __VLS_asFunctionalComponent1(__VLS_108, new __VLS_108({
                    variant: (user.is_active ? 'success' : 'warning'),
                }));
                const __VLS_110 = __VLS_109({
                    variant: (user.is_active ? 'success' : 'warning'),
                }, ...__VLS_functionalComponentArgsRest(__VLS_109));
                const { default: __VLS_113 } = __VLS_111.slots;
                (user.is_active ? 'Active' : 'Inactive');
                // @ts-ignore
                [];
                var __VLS_111;
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                    ...{ class: "date-cell" },
                });
                /** @type {__VLS_StyleScopedClasses['date-cell']} */ ;
                (user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "actions-cell" },
                });
                /** @type {__VLS_StyleScopedClasses['actions-cell']} */ ;
                if (__VLS_ctx.selectedUser !== user.id) {
                    let __VLS_114;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                    BaseButton;
                    // @ts-ignore
                    const __VLS_115 = __VLS_asFunctionalComponent1(__VLS_114, new __VLS_114({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "secondary",
                    }));
                    const __VLS_116 = __VLS_115({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "secondary",
                    }, ...__VLS_functionalComponentArgsRest(__VLS_115));
                    let __VLS_119;
                    const __VLS_120 = ({ click: {} },
                        { onClick: (...[$event]) => {
                                if (!!(!__VLS_ctx.isSuperAdmin))
                                    return;
                                if (!(__VLS_ctx.tab === 'manage'))
                                    return;
                                if (!!(__VLS_ctx.loadingUsers))
                                    return;
                                if (!!(__VLS_ctx.userList.length === 0))
                                    return;
                                if (!(__VLS_ctx.selectedUser !== user.id))
                                    return;
                                __VLS_ctx.selectedUser = user.id;
                                // @ts-ignore
                                [selectedUser, selectedUser,];
                            } });
                    const { default: __VLS_121 } = __VLS_117.slots;
                    // @ts-ignore
                    [];
                    var __VLS_117;
                    var __VLS_118;
                }
                else {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "reset-form" },
                    });
                    /** @type {__VLS_StyleScopedClasses['reset-form']} */ ;
                    let __VLS_122;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
                    BaseInput;
                    // @ts-ignore
                    const __VLS_123 = __VLS_asFunctionalComponent1(__VLS_122, new __VLS_122({
                        modelValue: (__VLS_ctx.resetPasswordCustom),
                        type: "text",
                        placeholder: "Optional: custom password",
                        size: "sm",
                    }));
                    const __VLS_124 = __VLS_123({
                        modelValue: (__VLS_ctx.resetPasswordCustom),
                        type: "text",
                        placeholder: "Optional: custom password",
                        size: "sm",
                    }, ...__VLS_functionalComponentArgsRest(__VLS_123));
                    let __VLS_127;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                    BaseButton;
                    // @ts-ignore
                    const __VLS_128 = __VLS_asFunctionalComponent1(__VLS_127, new __VLS_127({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "primary",
                        disabled: (__VLS_ctx.resetPasswordLoading),
                    }));
                    const __VLS_129 = __VLS_128({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "primary",
                        disabled: (__VLS_ctx.resetPasswordLoading),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_128));
                    let __VLS_132;
                    const __VLS_133 = ({ click: {} },
                        { onClick: (...[$event]) => {
                                if (!!(!__VLS_ctx.isSuperAdmin))
                                    return;
                                if (!(__VLS_ctx.tab === 'manage'))
                                    return;
                                if (!!(__VLS_ctx.loadingUsers))
                                    return;
                                if (!!(__VLS_ctx.userList.length === 0))
                                    return;
                                if (!!(__VLS_ctx.selectedUser !== user.id))
                                    return;
                                __VLS_ctx.handleResetPassword(user.id);
                                // @ts-ignore
                                [resetPasswordCustom, resetPasswordLoading, handleResetPassword,];
                            } });
                    const { default: __VLS_134 } = __VLS_130.slots;
                    (__VLS_ctx.resetPasswordLoading ? 'Resetting...' : 'Confirm');
                    // @ts-ignore
                    [resetPasswordLoading,];
                    var __VLS_130;
                    var __VLS_131;
                    let __VLS_135;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                    BaseButton;
                    // @ts-ignore
                    const __VLS_136 = __VLS_asFunctionalComponent1(__VLS_135, new __VLS_135({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "ghost",
                    }));
                    const __VLS_137 = __VLS_136({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "ghost",
                    }, ...__VLS_functionalComponentArgsRest(__VLS_136));
                    let __VLS_140;
                    const __VLS_141 = ({ click: {} },
                        { onClick: (...[$event]) => {
                                if (!!(!__VLS_ctx.isSuperAdmin))
                                    return;
                                if (!(__VLS_ctx.tab === 'manage'))
                                    return;
                                if (!!(__VLS_ctx.loadingUsers))
                                    return;
                                if (!!(__VLS_ctx.userList.length === 0))
                                    return;
                                if (!!(__VLS_ctx.selectedUser !== user.id))
                                    return;
                                __VLS_ctx.selectedUser = null;
                                // @ts-ignore
                                [selectedUser,];
                            } });
                    const { default: __VLS_142 } = __VLS_138.slots;
                    // @ts-ignore
                    [];
                    var __VLS_138;
                    var __VLS_139;
                }
                if (user.is_active) {
                    let __VLS_143;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                    BaseButton;
                    // @ts-ignore
                    const __VLS_144 = __VLS_asFunctionalComponent1(__VLS_143, new __VLS_143({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "danger",
                        disabled: (__VLS_ctx.deactivatingUser === user.id),
                    }));
                    const __VLS_145 = __VLS_144({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "danger",
                        disabled: (__VLS_ctx.deactivatingUser === user.id),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_144));
                    let __VLS_148;
                    const __VLS_149 = ({ click: {} },
                        { onClick: (...[$event]) => {
                                if (!!(!__VLS_ctx.isSuperAdmin))
                                    return;
                                if (!(__VLS_ctx.tab === 'manage'))
                                    return;
                                if (!!(__VLS_ctx.loadingUsers))
                                    return;
                                if (!!(__VLS_ctx.userList.length === 0))
                                    return;
                                if (!(user.is_active))
                                    return;
                                __VLS_ctx.handleDeactivateUser(user.id);
                                // @ts-ignore
                                [deactivatingUser, handleDeactivateUser,];
                            } });
                    const { default: __VLS_150 } = __VLS_146.slots;
                    (__VLS_ctx.deactivatingUser === user.id ? 'Deactivating...' : 'Deactivate');
                    // @ts-ignore
                    [deactivatingUser,];
                    var __VLS_146;
                    var __VLS_147;
                }
                else {
                    let __VLS_151;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                    BaseButton;
                    // @ts-ignore
                    const __VLS_152 = __VLS_asFunctionalComponent1(__VLS_151, new __VLS_151({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "primary",
                        disabled: (__VLS_ctx.deactivatingUser === user.id),
                    }));
                    const __VLS_153 = __VLS_152({
                        ...{ 'onClick': {} },
                        size: "sm",
                        variant: "primary",
                        disabled: (__VLS_ctx.deactivatingUser === user.id),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_152));
                    let __VLS_156;
                    const __VLS_157 = ({ click: {} },
                        { onClick: (...[$event]) => {
                                if (!!(!__VLS_ctx.isSuperAdmin))
                                    return;
                                if (!(__VLS_ctx.tab === 'manage'))
                                    return;
                                if (!!(__VLS_ctx.loadingUsers))
                                    return;
                                if (!!(__VLS_ctx.userList.length === 0))
                                    return;
                                if (!!(user.is_active))
                                    return;
                                __VLS_ctx.handleReactivateUser(user.id);
                                // @ts-ignore
                                [deactivatingUser, handleReactivateUser,];
                            } });
                    const { default: __VLS_158 } = __VLS_154.slots;
                    (__VLS_ctx.deactivatingUser === user.id ? 'Reactivating...' : 'Reactivate');
                    // @ts-ignore
                    [deactivatingUser,];
                    var __VLS_154;
                    var __VLS_155;
                }
                // @ts-ignore
                [];
            }
        }
        // @ts-ignore
        [];
        var __VLS_99;
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
