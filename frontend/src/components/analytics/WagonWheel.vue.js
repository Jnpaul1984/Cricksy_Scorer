/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, ref } from 'vue';
const props = defineProps();
const size = computed(() => props.size ?? 220);
const r = computed(() => (size.value / 2) - 8);
const hoveredStroke = ref(null);
function polar(angleDeg, radius) {
    const a = (angleDeg - 90) * Math.PI / 180;
    return { x: (size.value / 2) + Math.cos(a) * radius, y: (size.value / 2) + Math.sin(a) * radius };
}
function getStrokeColor(kind) {
    return kind === '6' ? '#22c55e' : (kind === '4' ? '#2563eb' : '#94a3b8');
}
function getStrokeWidth(index) {
    return hoveredStroke.value === index ? 3 : 2;
}
const strokeCounts = computed(() => {
    const counts = { sixes: 0, fours: 0, other: 0 };
    props.strokes.forEach(s => {
        if (s.kind === '6')
            counts.sixes++;
        else if (s.kind === '4')
            counts.fours++;
        else
            counts.other++;
    });
    return counts;
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
/** @type {__VLS_StyleScopedClasses['stroke-line']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "wagon-wheel-container" },
});
/** @type {__VLS_StyleScopedClasses['wagon-wheel-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
    width: (__VLS_ctx.size),
    height: (__VLS_ctx.size),
    role: "img",
    'aria-label': "Wagon wheel",
    ...{ class: "wagon-wheel-svg" },
});
/** @type {__VLS_StyleScopedClasses['wagon-wheel-svg']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
    cx: (__VLS_ctx.size / 2),
    cy: (__VLS_ctx.size / 2),
    r: (__VLS_ctx.r),
    fill: "#fafafa",
    stroke: "#e5e7eb",
});
for (const [a] of __VLS_vFor((12))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: (__VLS_ctx.size / 2),
        y1: (__VLS_ctx.size / 2),
        x2: (__VLS_ctx.polar((a - 1) * 30, __VLS_ctx.r).x),
        y2: (__VLS_ctx.polar((a - 1) * 30, __VLS_ctx.r).y),
        stroke: "#eee",
        key: (a),
    });
    // @ts-ignore
    [size, size, size, size, size, size, r, r, r, polar, polar,];
}
for (const [s, i] of __VLS_vFor((__VLS_ctx.strokes))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.line, __VLS_intrinsics.line)({
        ...{ onMouseenter: (...[$event]) => {
                __VLS_ctx.hoveredStroke = i;
                // @ts-ignore
                [strokes, hoveredStroke,];
            } },
        ...{ onMouseleave: (...[$event]) => {
                __VLS_ctx.hoveredStroke = null;
                // @ts-ignore
                [hoveredStroke,];
            } },
        x1: (__VLS_ctx.size / 2),
        y1: (__VLS_ctx.size / 2),
        x2: (__VLS_ctx.polar(s.angleDeg, __VLS_ctx.r).x),
        y2: (__VLS_ctx.polar(s.angleDeg, __VLS_ctx.r).y),
        stroke: (__VLS_ctx.getStrokeColor(s.kind)),
        'stroke-width': (__VLS_ctx.getStrokeWidth(i)),
        ...{ class: "stroke-line" },
        key: (i),
    });
    /** @type {__VLS_StyleScopedClasses['stroke-line']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.title, __VLS_intrinsics.title)({});
    (s.runs);
    (s.runs !== 1 ? 's' : '');
    (s.angleDeg.toFixed(0));
    // @ts-ignore
    [size, size, r, r, polar, polar, getStrokeColor, getStrokeWidth,];
}
if (__VLS_ctx.showLegend !== false) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend" },
    });
    /** @type {__VLS_StyleScopedClasses['legend']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-dot six" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
    /** @type {__VLS_StyleScopedClasses['six']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-text" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-text']} */ ;
    (__VLS_ctx.strokeCounts.sixes);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-dot four" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
    /** @type {__VLS_StyleScopedClasses['four']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-text" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-text']} */ ;
    (__VLS_ctx.strokeCounts.fours);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "legend-item" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-dot other" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
    /** @type {__VLS_StyleScopedClasses['other']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "legend-text" },
    });
    /** @type {__VLS_StyleScopedClasses['legend-text']} */ ;
    (__VLS_ctx.strokeCounts.other);
}
// @ts-ignore
[showLegend, strokeCounts, strokeCounts, strokeCounts,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
