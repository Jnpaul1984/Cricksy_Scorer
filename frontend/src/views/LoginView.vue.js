/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getErrorMessage } from '@/services/api';
import { login } from '@/services/auth';
import { useAuthStore } from '@/stores/authStore';
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const email = ref('');
const password = ref('');
const loading = ref(false);
const successMessage = ref('');
const errorMessage = ref('');
async function handleSubmit() {
    errorMessage.value = '';
    successMessage.value = '';
    loading.value = true;
    try {
        const result = await login(email.value.trim(), password.value);
        // Update the auth store so the router guard knows we're logged in
        authStore.token = result.token;
        authStore.user = result.user;
        // If the router sent us here with a redirect query (saved destination), honor it.
        // Default to /setup (create game page) instead of / which loops back to login.
        const redirectTo = route.query.redirect || '/setup';
        await router.push(redirectTo);
    }
    catch (err) {
        errorMessage.value = getErrorMessage(err);
    }
    finally {
        loading.value = false;
    }
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "login-view" },
});
/** @type {__VLS_StyleScopedClasses['login-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
    ...{ onSubmit: (__VLS_ctx.handleSubmit) },
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "email",
    autocomplete: "email",
    required: true,
    placeholder: "you@example.com",
});
(__VLS_ctx.email);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "password",
    autocomplete: "current-password",
    required: true,
    placeholder: "********",
});
(__VLS_ctx.password);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    type: "submit",
    disabled: (__VLS_ctx.loading),
});
(__VLS_ctx.loading ? 'Signing in...' : 'Sign In');
if (__VLS_ctx.successMessage) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "success" },
    });
    /** @type {__VLS_StyleScopedClasses['success']} */ ;
    (__VLS_ctx.successMessage);
}
if (__VLS_ctx.errorMessage) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.errorMessage);
}
// @ts-ignore
[handleSubmit, email, password, loading, loading, successMessage, successMessage, errorMessage, errorMessage,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
