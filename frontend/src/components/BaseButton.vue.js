/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    variant: 'primary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
    fullWidth: false,
    ariaLabel: undefined,
});
const buttonClasses = computed(() => {
    const classes = ['ds-btn', `ds-btn--${props.variant}`];
    // Only add size modifier for non-default sizes
    if (props.size !== 'md') {
        classes.push(`ds-btn--${props.size}`);
    }
    if (props.fullWidth) {
        classes.push('ds-btn--full-width');
    }
    if (props.loading) {
        classes.push('ds-btn--loading');
    }
    return classes;
});
const __VLS_defaults = {
    variant: 'primary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
    fullWidth: false,
    ariaLabel: undefined,
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
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    type: (__VLS_ctx.type),
    ...{ class: (__VLS_ctx.buttonClasses) },
    disabled: (__VLS_ctx.disabled || __VLS_ctx.loading),
    'aria-label': (__VLS_ctx.ariaLabel),
    'aria-busy': (__VLS_ctx.loading),
});
(__VLS_ctx.$attrs);
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "ds-btn__spinner" },
        'aria-hidden': "true",
    });
    /** @type {__VLS_StyleScopedClasses['ds-btn__spinner']} */ ;
}
else {
    var __VLS_0 = {};
}
// @ts-ignore
var __VLS_1 = __VLS_0;
// @ts-ignore
[type, buttonClasses, disabled, loading, loading, loading, ariaLabel, $attrs,];
const __VLS_base = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
const __VLS_export = {};
export default {};
