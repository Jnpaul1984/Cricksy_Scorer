/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
const props = defineProps();
function undo() {
    // TODO: Implement when backend API exists
    // await apiService.undoLastDelivery(props.gameId)
    alert(`Undo last delivery for game ${props.gameId} is not available yet. Backend endpoint pending.`);
}
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['undo']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.undo) },
    ...{ class: "undo" },
    disabled: (__VLS_ctx.disabled),
    title: "Backend endpoint pending",
});
/** @type {__VLS_StyleScopedClasses['undo']} */ ;
// @ts-ignore
[undo, disabled,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
