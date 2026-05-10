/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    title: '',
    details: '',
    type: 'error',
    dismissible: true,
    visible: true,
});
const emit = defineEmits();
// Computed
const typeClass = computed(() => ({
    'type-error': props.type === 'error',
    'type-warning': props.type === 'warning',
    'type-info': props.type === 'info',
}));
const errorIcon = computed(() => {
    switch (props.type) {
        case 'error':
            return '❌';
        case 'warning':
            return '⚠️';
        case 'info':
            return 'ℹ️';
        default:
            return '❌';
    }
});
// Methods
const handleDismiss = () => {
    emit('dismiss');
};
const __VLS_defaults = {
    title: '',
    details: '',
    type: 'error',
    dismissible: true,
    visible: true,
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
/** @type {__VLS_StyleScopedClasses['dismiss-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dismiss-button']} */ ;
/** @type {__VLS_StyleScopedClasses['error-message']} */ ;
/** @type {__VLS_StyleScopedClasses['error-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['error-title']} */ ;
/** @type {__VLS_StyleScopedClasses['error-text']} */ ;
if (__VLS_ctx.visible) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-message" },
        ...{ class: (__VLS_ctx.typeClass) },
        role: "alert",
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['error-icon']} */ ;
    (__VLS_ctx.errorIcon);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-content" },
    });
    /** @type {__VLS_StyleScopedClasses['error-content']} */ ;
    if (__VLS_ctx.title) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "error-title" },
        });
        /** @type {__VLS_StyleScopedClasses['error-title']} */ ;
        (__VLS_ctx.title);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-text" },
    });
    /** @type {__VLS_StyleScopedClasses['error-text']} */ ;
    (__VLS_ctx.message);
    if (__VLS_ctx.details) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "error-details" },
        });
        /** @type {__VLS_StyleScopedClasses['error-details']} */ ;
        (__VLS_ctx.details);
    }
    if (__VLS_ctx.dismissible) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.handleDismiss) },
            ...{ class: "dismiss-button" },
            type: "button",
            'aria-label': "Dismiss error",
        });
        /** @type {__VLS_StyleScopedClasses['dismiss-button']} */ ;
    }
}
// @ts-ignore
[visible, typeClass, errorIcon, title, title, message, details, details, dismissible, handleDismiss,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
