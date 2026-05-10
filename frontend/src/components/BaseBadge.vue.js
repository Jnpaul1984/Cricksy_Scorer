/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    variant: 'neutral',
    uppercase: true,
    pill: true,
    condensed: false,
});
const badgeClasses = computed(() => {
    const classes = ['ds-badge', `ds-badge--${props.variant}`];
    if (!props.uppercase) {
        classes.push('ds-badge--lowercase');
    }
    if (!props.pill) {
        classes.push('ds-badge--square');
    }
    if (props.condensed) {
        classes.push('ds-badge--condensed');
    }
    return classes;
});
const __VLS_defaults = {
    variant: 'neutral',
    uppercase: true,
    pill: true,
    condensed: false,
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
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: (__VLS_ctx.badgeClasses) },
});
(__VLS_ctx.$attrs);
var __VLS_0 = {};
// @ts-ignore
var __VLS_1 = __VLS_0;
// @ts-ignore
[badgeClasses, $attrs,];
const __VLS_base = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
const __VLS_export = {};
export default {};
