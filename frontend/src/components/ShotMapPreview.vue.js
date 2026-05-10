/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = defineProps();
const sizePx = computed(() => `${(props.size ?? 72)}px`);
const safeSrc = computed(() => {
    const raw = props.value;
    if (!raw)
        return null;
    const trimmed = raw.trim();
    if (trimmed.startsWith('data:image/svg+xml')) {
        return trimmed;
    }
    if (trimmed.startsWith('<svg')) {
        const encoded = encodeURIComponent(trimmed);
        return `data:image/svg+xml,${encoded}`;
    }
    return null;
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['shot-map-preview']} */ ;
if (__VLS_ctx.safeSrc) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "shot-map-preview" },
    });
    /** @type {__VLS_StyleScopedClasses['shot-map-preview']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        src: (__VLS_ctx.safeSrc),
        ...{ style: ({ width: __VLS_ctx.sizePx, height: __VLS_ctx.sizePx }) },
        alt: "Shot map sketch",
    });
}
// @ts-ignore
[safeSrc, safeSrc, sizePx, sizePx,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
