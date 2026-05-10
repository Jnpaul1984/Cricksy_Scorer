/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { changePassword } from '@/services/auth';
import { useAuthStore } from '@/stores/authStore';
const router = useRouter();
const auth = useAuthStore();
// User profile state
const userEmail = ref('');
const userName = ref('');
const userId = ref('');
const memberSince = ref('');
// Password change state
const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const showPasswords = ref(false);
const isChangingPassword = ref(false);
const passwordMessage = ref(null);
// Computed properties
const isLoggedIn = computed(() => auth.isLoggedIn);
const passwordsMatch = computed(() => newPassword.value === confirmPassword.value);
const canSubmit = computed(() => currentPassword.value &&
    newPassword.value &&
    confirmPassword.value &&
    passwordsMatch.value &&
    newPassword.value.length >= 6);
// Load user data
async function loadUserData() {
    try {
        userEmail.value = auth.userEmail;
        userName.value = auth.userName;
        userId.value = auth.userId;
        memberSince.value = auth.createdAt || new Date().toISOString();
    }
    catch (error) {
        console.error('Failed to load user data:', error);
    }
}
// Change password handler
async function handleChangePassword() {
    if (!canSubmit.value) {
        return;
    }
    isChangingPassword.value = true;
    passwordMessage.value = null;
    try {
        await changePassword(currentPassword.value, newPassword.value);
        passwordMessage.value = {
            type: 'success',
            text: 'Password changed successfully! Please log in again.',
        };
        // Reset form
        currentPassword.value = '';
        newPassword.value = '';
        confirmPassword.value = '';
        // Redirect to login after 2 seconds
        setTimeout(() => {
            auth.logout();
            router.push('/login');
        }, 2000);
    }
    catch (error) {
        console.error('Failed to change password:', error);
        passwordMessage.value = {
            type: 'error',
            text: error.response?.data?.detail || 'Failed to change password. Please try again.',
        };
    }
    finally {
        isChangingPassword.value = false;
    }
}
// Format date
function formatDate(dateString) {
    if (!dateString)
        return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    }
    catch {
        return dateString;
    }
}
// Initialize
onMounted(() => {
    if (!isLoggedIn.value) {
        router.push('/login');
    }
    else {
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
/** @type {__VLS_StyleScopedClasses['info-item']} */ ;
/** @type {__VLS_StyleScopedClasses['info-item']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['message']} */ ;
/** @type {__VLS_StyleScopedClasses['banner']} */ ;
/** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
/** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['password-hint']} */ ;
/** @type {__VLS_StyleScopedClasses['error-hint']} */ ;
/** @type {__VLS_StyleScopedClasses['success-hint']} */ ;
/** @type {__VLS_StyleScopedClasses['checkbox-group']} */ ;
/** @type {__VLS_StyleScopedClasses['checkbox-group']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['security-tips']} */ ;
/** @type {__VLS_StyleScopedClasses['security-tips']} */ ;
/** @type {__VLS_StyleScopedClasses['security-tips']} */ ;
/** @type {__VLS_StyleScopedClasses['profile-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['info-grid']} */ ;
if (__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "profile-container" },
    });
    /** @type {__VLS_StyleScopedClasses['profile-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "profile-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['profile-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
    transition;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        name: "message",
    }));
    const __VLS_2 = __VLS_1({
        name: "message",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    const { default: __VLS_5 } = __VLS_3.slots;
    if (__VLS_ctx.auth.requiresPasswordChange) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "banner warning" },
        });
        /** @type {__VLS_StyleScopedClasses['banner']} */ ;
        /** @type {__VLS_StyleScopedClasses['warning']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "banner-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['banner-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "banner-content" },
        });
        /** @type {__VLS_StyleScopedClasses['banner-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    // @ts-ignore
    [isLoggedIn, auth,];
    var __VLS_3;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-section" },
    });
    /** @type {__VLS_StyleScopedClasses['info-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['info-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-item" },
    });
    /** @type {__VLS_StyleScopedClasses['info-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.userEmail);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-item" },
    });
    /** @type {__VLS_StyleScopedClasses['info-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "user-id" },
    });
    /** @type {__VLS_StyleScopedClasses['user-id']} */ ;
    (__VLS_ctx.userId);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-item" },
    });
    /** @type {__VLS_StyleScopedClasses['info-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.formatDate(__VLS_ctx.memberSince));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "password-section" },
    });
    /** @type {__VLS_StyleScopedClasses['password-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "section-description" },
    });
    /** @type {__VLS_StyleScopedClasses['section-description']} */ ;
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
    transition;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        name: "message",
    }));
    const __VLS_8 = __VLS_7({
        name: "message",
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    const { default: __VLS_11 } = __VLS_9.slots;
    if (__VLS_ctx.passwordMessage) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: (['message', __VLS_ctx.passwordMessage.type]) },
        });
        /** @type {__VLS_StyleScopedClasses['message']} */ ;
        (__VLS_ctx.passwordMessage.text);
    }
    // @ts-ignore
    [userEmail, userId, formatDate, memberSince, passwordMessage, passwordMessage, passwordMessage,];
    var __VLS_9;
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.handleChangePassword) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "current-password",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "password-input-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['password-input-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "current-password",
        type: (__VLS_ctx.showPasswords ? 'text' : 'password'),
        placeholder: "Enter your current password",
        required: true,
        autocomplete: "current-password",
    });
    (__VLS_ctx.currentPassword);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "new-password",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "password-input-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['password-input-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "new-password",
        type: (__VLS_ctx.showPasswords ? 'text' : 'password'),
        placeholder: "Enter a new password",
        required: true,
        autocomplete: "new-password",
        minlength: "6",
    });
    (__VLS_ctx.newPassword);
    if (__VLS_ctx.newPassword.length < 6) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
            ...{ class: "password-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['password-hint']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "confirm-password",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "password-input-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['password-input-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "confirm-password",
        type: (__VLS_ctx.showPasswords ? 'text' : 'password'),
        placeholder: "Re-enter your new password",
        required: true,
        autocomplete: "new-password",
        minlength: "6",
    });
    (__VLS_ctx.confirmPassword);
    let __VLS_12;
    /** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
    transition;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
        name: "fade",
    }));
    const __VLS_14 = __VLS_13({
        name: "fade",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    const { default: __VLS_17 } = __VLS_15.slots;
    if (__VLS_ctx.confirmPassword && !__VLS_ctx.passwordsMatch) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
            ...{ class: "error-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['error-hint']} */ ;
    }
    else if (__VLS_ctx.confirmPassword && __VLS_ctx.passwordsMatch) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
            ...{ class: "success-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['success-hint']} */ ;
    }
    // @ts-ignore
    [handleChangePassword, showPasswords, showPasswords, showPasswords, currentPassword, newPassword, newPassword, confirmPassword, confirmPassword, confirmPassword, passwordsMatch, passwordsMatch,];
    var __VLS_15;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "checkbox-group" },
    });
    /** @type {__VLS_StyleScopedClasses['checkbox-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "show-passwords",
        type: "checkbox",
    });
    (__VLS_ctx.showPasswords);
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "show-passwords",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        disabled: (!__VLS_ctx.canSubmit || __VLS_ctx.isChangingPassword),
        ...{ class: "btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    if (!__VLS_ctx.isChangingPassword) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "security-tips" },
    });
    /** @type {__VLS_StyleScopedClasses['security-tips']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
}
// @ts-ignore
[showPasswords, canSubmit, isChangingPassword, isChangingPassword,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
