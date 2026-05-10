/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    type: 'text',
    label: undefined,
    id: undefined,
    placeholder: undefined,
    disabled: false,
    error: null,
    helpText: null,
    required: false,
});
const emit = defineEmits();
// Generate unique IDs for accessibility
// Use counter instead of Math.random() for deterministic IDs
let idCounter = 0;
const inputId = computed(() => props.id ?? `input-${++idCounter}`);
const errorId = computed(() => `${inputId.value}-error`);
const helpId = computed(() => `${inputId.value}-help`);
const describedBy = computed(() => {
    if (props.error)
        return errorId.value;
    if (props.helpText)
        return helpId.value;
    return undefined;
});
const inputClasses = computed(() => ({
    'ds-input': true,
    'ds-input--error': !!props.error,
}));
const onInput = (event) => {
    const target = event.target;
    const value = props.type === 'number' ? (target.value === '' ? null : Number(target.value)) : target.value;
    emit('update:modelValue', value);
};
const __VLS_defaults = {
    type: 'text',
    label: undefined,
    id: undefined,
    placeholder: undefined,
    disabled: false,
    error: null,
    helpText: null,
    required: false,
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
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-input-group" },
});
/** @type {__VLS_StyleScopedClasses['ds-input-group']} */ ;
if (__VLS_ctx.label) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: (__VLS_ctx.inputId),
        ...{ class: "ds-input-label" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input-label']} */ ;
    (__VLS_ctx.label);
    if (__VLS_ctx.required) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "ds-input-required" },
            'aria-hidden': "true",
        });
        /** @type {__VLS_StyleScopedClasses['ds-input-required']} */ ;
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    ...{ onInput: (__VLS_ctx.onInput) },
    id: (__VLS_ctx.inputId),
    type: (__VLS_ctx.type),
    value: (__VLS_ctx.modelValue),
    placeholder: (__VLS_ctx.placeholder),
    disabled: (__VLS_ctx.disabled),
    required: (__VLS_ctx.required),
    ...{ class: (__VLS_ctx.inputClasses) },
    'aria-invalid': (!!__VLS_ctx.error),
    'aria-describedby': (__VLS_ctx.describedBy),
});
(__VLS_ctx.$attrs);
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        id: (__VLS_ctx.errorId),
        ...{ class: "ds-input-error" },
        role: "alert",
    });
    /** @type {__VLS_StyleScopedClasses['ds-input-error']} */ ;
    (__VLS_ctx.error);
}
else if (__VLS_ctx.helpText) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        id: (__VLS_ctx.helpId),
        ...{ class: "ds-input-help" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input-help']} */ ;
    (__VLS_ctx.helpText);
}
// @ts-ignore
[label, label, inputId, inputId, required, required, onInput, type, modelValue, placeholder, disabled, inputClasses, error, error, error, describedBy, $attrs, errorId, helpText, helpText, helpId,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
