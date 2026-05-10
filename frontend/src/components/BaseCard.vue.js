/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    as: 'div',
    interactive: false,
    padding: 'md',
    fullHeight: false,
});
const cardClasses = computed(() => {
    const classes = ['ds-card'];
    if (props.interactive) {
        classes.push('ds-card--interactive');
    }
    return classes;
});
const paddingMap = {
    none: '0',
    sm: 'var(--space-2)',
    md: 'var(--space-4)',
    lg: 'var(--space-6)',
};
const cardStyle = computed(() => {
    const styles = {};
    // Apply padding based on prop
    styles.padding = paddingMap[props.padding];
    // Apply full height if needed
    if (props.fullHeight) {
        styles.height = '100%';
    }
    return styles;
});
const __VLS_defaults = {
    as: 'div',
    interactive: false,
    padding: 'md',
    fullHeight: false,
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
const __VLS_0 = (__VLS_ctx.as);
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ class: (__VLS_ctx.cardClasses) },
    ...{ style: (__VLS_ctx.cardStyle) },
}));
const __VLS_2 = __VLS_1({
    ...{ class: (__VLS_ctx.cardClasses) },
    ...{ style: (__VLS_ctx.cardStyle) },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
(__VLS_ctx.$attrs);
var __VLS_5 = {};
const { default: __VLS_6 } = __VLS_3.slots;
var __VLS_7 = {};
// @ts-ignore
[as, cardClasses, cardStyle, $attrs,];
var __VLS_3;
// @ts-ignore
var __VLS_8 = __VLS_7;
// @ts-ignore
[];
const __VLS_base = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
const __VLS_export = {};
export default {};
