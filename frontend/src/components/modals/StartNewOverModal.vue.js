/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, toRefs } from 'vue';
const props = withDefaults(defineProps(), {
    busy: false,
});
const { open, busy, bowlers } = toRefs(props);
const emit = defineEmits();
const selectedId = ref('');
function submit() {
    if (!selectedId.value)
        return;
    emit('confirm', selectedId.value);
}
const __VLS_defaults = {
    busy: false,
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
if (__VLS_ctx.open) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.dialog, __VLS_intrinsics.dialog)({
        ...{ class: "modal" },
    });
    /** @type {__VLS_StyleScopedClasses['modal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedId),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.bowlers))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        // @ts-ignore
        [open, selectedId, bowlers,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.open))
                    return;
                __VLS_ctx.$emit('close');
                // @ts-ignore
                [$emit,];
            } },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.submit) },
        disabled: (!__VLS_ctx.selectedId || __VLS_ctx.busy),
    });
}
// @ts-ignore
[selectedId, submit, busy,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
