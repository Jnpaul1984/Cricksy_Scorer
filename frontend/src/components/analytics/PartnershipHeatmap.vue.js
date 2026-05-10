/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = defineProps();
const maxVal = computed(() => {
    const flat = props.matrix.flat();
    return flat.length ? Math.max(...flat, 0) : 0;
});
function cellBackground(value) {
    if (!maxVal.value)
        return '#f8fafc';
    const alpha = Math.min(0.9, value / maxVal.value);
    return `rgba(37, 99, 235, ${alpha})`;
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
/** @type {__VLS_StyleScopedClasses['tbl']} */ ;
/** @type {__VLS_StyleScopedClasses['tbl']} */ ;
/** @type {__VLS_StyleScopedClasses['tbl']} */ ;
if (__VLS_ctx.players.length) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "heatmap" },
    });
    /** @type {__VLS_StyleScopedClasses['heatmap']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "tbl" },
    });
    /** @type {__VLS_StyleScopedClasses['tbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    for (const [p] of __VLS_vFor((__VLS_ctx.players))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
            key: (p.id),
        });
        (p.name);
        // @ts-ignore
        [players, players,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [row, i] of __VLS_vFor((__VLS_ctx.matrix))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (__VLS_ctx.players[i]?.id || i),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        (__VLS_ctx.players[i]?.name);
        for (const [value, j] of __VLS_vFor((row))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                key: (j),
                ...{ style: ({ background: __VLS_ctx.cellBackground(value) }) },
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "cell" },
            });
            /** @type {__VLS_StyleScopedClasses['cell']} */ ;
            (value || '');
            // @ts-ignore
            [players, players, matrix, cellBackground,];
        }
        // @ts-ignore
        [];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty" },
    });
    /** @type {__VLS_StyleScopedClasses['empty']} */ ;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
