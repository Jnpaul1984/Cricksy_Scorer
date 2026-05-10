/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from "vue";
const props = withDefaults(defineProps(), {
    width: 120,
    height: 32,
    strokeWidth: 2,
    smooth: false,
    highlightLast: false,
    variant: "default",
    showFill: false,
});
// ViewBox constants
const VIEW_WIDTH = 100;
const VIEW_HEIGHT = 30;
const PADDING_X = 4;
const PADDING_Y = 3;
const normalizedPoints = computed(() => {
    if (props.points.length === 0)
        return [];
    const pts = props.points;
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min;
    const usableWidth = VIEW_WIDTH - 2 * PADDING_X;
    const usableHeight = VIEW_HEIGHT - 2 * PADDING_Y;
    return pts.map((val, index) => {
        // X coordinate: spread points evenly across width
        const x = pts.length === 1
            ? VIEW_WIDTH / 2
            : PADDING_X + (index / (pts.length - 1)) * usableWidth;
        // Y coordinate: normalize value to height (invert because SVG y=0 is top)
        let normalizedY;
        if (range === 0) {
            // Flat line in the middle
            normalizedY = usableHeight / 2;
        }
        else {
            normalizedY = ((val - min) / range) * usableHeight;
        }
        // Invert for SVG coordinate system and add padding
        const y = VIEW_HEIGHT - PADDING_Y - normalizedY;
        return { x, y };
    });
});
const polylinePoints = computed(() => {
    return normalizedPoints.value.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
});
// Area path for fill (closes polygon to bottom)
const areaPath = computed(() => {
    if (normalizedPoints.value.length === 0)
        return "";
    const pts = normalizedPoints.value;
    const bottom = VIEW_HEIGHT - PADDING_Y + 2;
    const first = pts[0];
    const last = pts[pts.length - 1];
    const linePoints = pts.map((p) => `L${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
    return `M${first.x.toFixed(2)},${bottom} ${linePoints} L${last.x.toFixed(2)},${bottom} Z`;
});
const lastPoint = computed(() => {
    const pts = normalizedPoints.value;
    return pts.length > 0 ? pts[pts.length - 1] : null;
});
const __VLS_defaults = {
    width: 120,
    height: 32,
    strokeWidth: 2,
    smooth: false,
    highlightLast: false,
    variant: "default",
    showFill: false,
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
/** @type {__VLS_StyleScopedClasses['mini-sparkline__area']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__area']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__area']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__area']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__line']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__line']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__line']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__line']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__dot']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__dot']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__dot']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-sparkline__dot']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "mini-sparkline" },
});
/** @type {__VLS_StyleScopedClasses['mini-sparkline']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
    width: (__VLS_ctx.width),
    height: (__VLS_ctx.height),
    viewBox: (`0 0 ${__VLS_ctx.VIEW_WIDTH} ${__VLS_ctx.VIEW_HEIGHT}`),
    preserveAspectRatio: "none",
    role: "img",
    'aria-hidden': "true",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "0",
    y1: "28",
    x2: "100",
    y2: "28",
    ...{ class: "mini-sparkline__baseline" },
});
/** @type {__VLS_StyleScopedClasses['mini-sparkline__baseline']} */ ;
if (__VLS_ctx.normalizedPoints.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        x1: "10",
        y1: "15",
        x2: "90",
        y2: "15",
        ...{ class: "mini-sparkline__nodata" },
    });
    /** @type {__VLS_StyleScopedClasses['mini-sparkline__nodata']} */ ;
}
else if (__VLS_ctx.showFill) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.path)({
        d: (__VLS_ctx.areaPath),
        ...{ class: "mini-sparkline__area" },
        'data-variant': (__VLS_ctx.variant),
    });
    /** @type {__VLS_StyleScopedClasses['mini-sparkline__area']} */ ;
}
if (__VLS_ctx.normalizedPoints.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.polyline)({
        points: (__VLS_ctx.polylinePoints),
        ...{ class: "mini-sparkline__line" },
        'data-variant': (__VLS_ctx.variant),
    });
    /** @type {__VLS_StyleScopedClasses['mini-sparkline__line']} */ ;
}
if (__VLS_ctx.highlightLast && __VLS_ctx.lastPoint) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
        cx: (__VLS_ctx.lastPoint.x),
        cy: (__VLS_ctx.lastPoint.y),
        r: "1.6",
        ...{ class: "mini-sparkline__dot" },
        'data-variant': (__VLS_ctx.variant),
    });
    /** @type {__VLS_StyleScopedClasses['mini-sparkline__dot']} */ ;
}
// @ts-ignore
[width, height, VIEW_WIDTH, VIEW_HEIGHT, normalizedPoints, normalizedPoints, showFill, areaPath, variant, variant, variant, polylinePoints, highlightLast, lastPoint, lastPoint, lastPoint,];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
