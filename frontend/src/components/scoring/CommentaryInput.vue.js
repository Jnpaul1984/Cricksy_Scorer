/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { toRefs } from 'vue';
const props = withDefaults(defineProps(), {
    placeholder: '',
});
const { modelValue, placeholder } = toRefs(props);
const emit = defineEmits();
function onInput(e) {
    const v = e.target.value;
    emit('update:modelValue', v);
}
const __VLS_defaults = {
    placeholder: '',
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
    ...{ class: "commentary" },
});
/** @type {__VLS_StyleScopedClasses['commentary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    ...{ onInput: (__VLS_ctx.onInput) },
    value: (__VLS_ctx.modelValue),
    rows: "2",
    placeholder: (__VLS_ctx.placeholder || 'Optional note for this delivery…'),
});
// @ts-ignore
[onInput, modelValue, placeholder,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
