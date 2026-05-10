/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    size: 'medium',
    color: '#3498db',
    message: '',
    overlay: false,
});
// Computed
const sizeClass = computed(() => ({
    'size-small': props.size === 'small',
    'size-medium': props.size === 'medium',
    'size-large': props.size === 'large',
    'with-overlay': props.overlay,
}));
const spinnerStyle = computed(() => ({
    '--spinner-color': props.color,
}));
const __VLS_defaults = {
    size: 'medium',
    color: '#3498db',
    message: '',
    overlay: false,
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
/** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
/** @type {__VLS_StyleScopedClasses['spinner-circle']} */ ;
/** @type {__VLS_StyleScopedClasses['spinner-circle']} */ ;
/** @type {__VLS_StyleScopedClasses['spinner-circle']} */ ;
/** @type {__VLS_StyleScopedClasses['size-small']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-message']} */ ;
/** @type {__VLS_StyleScopedClasses['size-large']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-message']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "loading-spinner" },
    ...{ class: (__VLS_ctx.sizeClass) },
});
/** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "spinner" },
    ...{ style: (__VLS_ctx.spinnerStyle) },
});
/** @type {__VLS_StyleScopedClasses['spinner']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "spinner-circle" },
});
/** @type {__VLS_StyleScopedClasses['spinner-circle']} */ ;
if (__VLS_ctx.message) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-message" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-message']} */ ;
    (__VLS_ctx.message);
}
// @ts-ignore
[sizeClass, spinnerStyle, message, message,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
