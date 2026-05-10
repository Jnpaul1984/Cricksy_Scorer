/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from "vue";
const props = withDefaults(defineProps(), {
    min: -100,
    max: 100,
    size: "md",
    showLabel: true,
    label: null,
    invert: false,
    positiveLabel: null,
    negativeLabel: null,
    variant: null,
});
const clamped = computed(() => Math.min(Math.max(props.value, props.min), props.max));
const effectiveValue = computed(() => (props.invert ? -clamped.value : clamped.value));
const isPositive = computed(() => effectiveValue.value > 0);
const isNegative = computed(() => effectiveValue.value < 0);
// Variant can be explicitly set or auto-detected from value
const computedVariant = computed(() => {
    // If explicit variant is provided, use it
    if (props.variant)
        return props.variant;
    // Auto-detect from value
    if (effectiveValue.value > 0)
        return "positive";
    if (effectiveValue.value < 0)
        return "negative";
    return "neutral";
});
// Width as percentage of half-track (50% = full half)
const computedWidth = computed(() => {
    const halfRange = (props.max - props.min) / 2;
    if (halfRange === 0)
        return "0%";
    const widthPct = Math.min(Math.abs(clamped.value) / halfRange, 1) * 50;
    return `${widthPct}%`;
});
const fillStyle = computed(() => {
    if (isPositive.value) {
        // Positive: fill grows from center (50%) to the right
        return { left: "50%", width: computedWidth.value };
    }
    else if (isNegative.value) {
        // Negative: fill grows from center (50%) to the left
        return { right: "50%", width: computedWidth.value };
    }
    return { left: "50%", width: "0%" };
});
const formattedValue = computed(() => {
    if (props.label !== null)
        return props.label;
    const val = clamped.value;
    const absVal = Math.abs(val);
    // Format with 1 decimal for small ranges, otherwise integer
    const range = props.max - props.min;
    const formatted = range <= 20 ? absVal.toFixed(1) : Math.round(absVal).toString();
    if (val > 0)
        return `+${formatted}`;
    if (val < 0)
        return `−${formatted}`;
    return formatted;
});
const sideLabel = computed(() => {
    if (effectiveValue.value > 0 && props.positiveLabel) {
        return props.positiveLabel;
    }
    if (effectiveValue.value < 0 && props.negativeLabel) {
        return props.negativeLabel;
    }
    return null;
});
const __VLS_defaults = {
    min: -100,
    max: 100,
    size: "md",
    showLabel: true,
    label: null,
    invert: false,
    positiveLabel: null,
    negativeLabel: null,
    variant: null,
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
/** @type {__VLS_StyleScopedClasses['impact-bar__track']} */ ;
/** @type {__VLS_StyleScopedClasses['impact-bar__track']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "impact-bar" },
    'data-size': (__VLS_ctx.size),
});
/** @type {__VLS_StyleScopedClasses['impact-bar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "impact-bar__track" },
});
/** @type {__VLS_StyleScopedClasses['impact-bar__track']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "impact-bar__zero-marker" },
});
/** @type {__VLS_StyleScopedClasses['impact-bar__zero-marker']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "impact-bar__fill" },
    ...{ class: (['impact-bar__fill--' + __VLS_ctx.computedVariant]) },
    ...{ style: (__VLS_ctx.fillStyle) },
});
/** @type {__VLS_StyleScopedClasses['impact-bar__fill']} */ ;
if (__VLS_ctx.showLabel) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "impact-bar__labels" },
    });
    /** @type {__VLS_StyleScopedClasses['impact-bar__labels']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "impact-bar__value" },
    });
    /** @type {__VLS_StyleScopedClasses['impact-bar__value']} */ ;
    (__VLS_ctx.formattedValue);
    if (__VLS_ctx.sideLabel) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "impact-bar__side-label" },
        });
        /** @type {__VLS_StyleScopedClasses['impact-bar__side-label']} */ ;
        (__VLS_ctx.sideLabel);
    }
}
// @ts-ignore
[size, computedVariant, fillStyle, showLabel, formattedValue, sideLabel, sideLabel,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
