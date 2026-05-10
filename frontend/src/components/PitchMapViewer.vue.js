/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
const props = defineProps();
const pitchPoints = ref([]);
const lengthFilter = ref('');
const lineFilter = ref('');
const hoveredPoint = ref(null);
const filteredPoints = computed(() => {
    return pitchPoints.value.filter(point => {
        if (lengthFilter.value && point.length !== lengthFilter.value)
            return false;
        if (lineFilter.value && point.line !== lineFilter.value)
            return false;
        return true;
    });
});
const averageLength = computed(() => {
    if (filteredPoints.value.length === 0)
        return 0;
    const sum = filteredPoints.value.reduce((acc, p) => acc + p.y_coordinate, 0);
    return sum / filteredPoints.value.length;
});
const averageLine = computed(() => {
    if (filteredPoints.value.length === 0)
        return 0;
    const sum = filteredPoints.value.reduce((acc, p) => acc + p.x_coordinate, 0);
    return sum / filteredPoints.value.length;
});
const lengthDistribution = computed(() => {
    const dist = {
        yorker: 0,
        full: 0,
        good_length: 0,
        short: 0,
        bouncer: 0
    };
    filteredPoints.value.forEach(point => {
        if (point.length in dist) {
            dist[point.length]++;
        }
    });
    return dist;
});
const lineDistribution = computed(() => {
    const dist = {
        wide_leg: 0,
        leg_stump: 0,
        middle: 0,
        off_stump: 0,
        wide_off: 0
    };
    filteredPoints.value.forEach(point => {
        if (point.line in dist) {
            dist[point.line]++;
        }
    });
    return dist;
});
function getPointColor(point) {
    const lengthColors = {
        yorker: '#ff6b6b',
        full: '#feca57',
        good_length: '#48dbfb',
        short: '#1dd1a1',
        bouncer: '#ee5a6f'
    };
    return lengthColors[point.length] || '#ffffff';
}
function getPointStroke(point) {
    const lengthStrokes = {
        yorker: '#d63031',
        full: '#fdcb6e',
        good_length: '#0984e3',
        short: '#00b894',
        bouncer: '#d63031'
    };
    return lengthStrokes[point.length] || '#cccccc';
}
async function loadPitchMap() {
    try {
        const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/pitch-map`);
        if (!response.ok) {
            throw new Error('Failed to load pitch map');
        }
        const data = await response.json();
        pitchPoints.value = data.points || [];
    }
    catch (err) {
        console.error('Failed to load pitch map:', err);
    }
}
onMounted(() => {
    loadPitchMap();
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
/** @type {__VLS_StyleScopedClasses['viewer-header']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-select']} */ ;
/** @type {__VLS_StyleScopedClasses['distribution-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pitch-map-viewer" },
});
/** @type {__VLS_StyleScopedClasses['pitch-map-viewer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "viewer-header" },
});
/** @type {__VLS_StyleScopedClasses['viewer-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "filter-controls" },
});
/** @type {__VLS_StyleScopedClasses['filter-controls']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.lengthFilter),
    ...{ class: "filter-select" },
});
/** @type {__VLS_StyleScopedClasses['filter-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "yorker",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "full",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "good_length",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "short",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "bouncer",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.lineFilter),
    ...{ class: "filter-select" },
});
/** @type {__VLS_StyleScopedClasses['filter-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "wide_leg",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "leg_stump",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "middle",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "off_stump",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "wide_off",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stats-summary" },
});
/** @type {__VLS_StyleScopedClasses['stats-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-card" },
});
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.filteredPoints.length);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-card" },
});
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.averageLength.toFixed(1));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-card" },
});
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-label" },
});
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat-value" },
});
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
(__VLS_ctx.averageLine.toFixed(1));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pitch-container" },
});
/** @type {__VLS_StyleScopedClasses['pitch-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
    ...{ class: "pitch-svg" },
    viewBox: "0 0 100 100",
});
/** @type {__VLS_StyleScopedClasses['pitch-svg']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "0",
    width: "100",
    height: "100",
    fill: "#0d5a2c",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
    opacity: "0.2",
});
for (const [i] of __VLS_vFor((9))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        key: (`h-${i}`),
        x1: (0),
        y1: (i * 10),
        x2: (100),
        y2: (i * 10),
        stroke: "white",
        'stroke-width': "0.1",
    });
    // @ts-ignore
    [lengthFilter, lineFilter, filteredPoints, averageLength, averageLine,];
}
for (const [i] of __VLS_vFor((9))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.line)({
        key: (`v-${i}`),
        x1: (i * 10),
        y1: (0),
        x2: (i * 10),
        y2: (100),
        stroke: "white",
        'stroke-width': "0.1",
    });
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
    opacity: "0.15",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "0",
    width: "100",
    height: "10",
    fill: "#ff6b6b",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
    x: "50",
    y: "6",
    'text-anchor': "middle",
    'font-size': "3",
    fill: "white",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "10",
    width: "100",
    height: "20",
    fill: "#feca57",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
    x: "50",
    y: "21",
    'text-anchor': "middle",
    'font-size': "3",
    fill: "white",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "30",
    width: "100",
    height: "30",
    fill: "#48dbfb",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
    x: "50",
    y: "46",
    'text-anchor': "middle",
    'font-size': "3",
    fill: "white",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "60",
    width: "100",
    height: "25",
    fill: "#1dd1a1",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
    x: "50",
    y: "73",
    'text-anchor': "middle",
    'font-size': "3",
    fill: "white",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
    x: "0",
    y: "85",
    width: "100",
    height: "15",
    fill: "#ee5a6f",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
    x: "50",
    y: "93",
    'text-anchor': "middle",
    'font-size': "3",
    fill: "white",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
    opacity: "0.1",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "25",
    y1: "0",
    x2: "25",
    y2: "100",
    stroke: "white",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "40",
    y1: "0",
    x2: "40",
    y2: "100",
    stroke: "white",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "60",
    y1: "0",
    x2: "60",
    y2: "100",
    stroke: "white",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "75",
    y1: "0",
    x2: "75",
    y2: "100",
    stroke: "white",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
    cx: "50",
    cy: "5",
    r: "1",
    fill: "yellow",
    stroke: "orange",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
    cx: "50",
    cy: "95",
    r: "1",
    fill: "yellow",
    stroke: "orange",
    'stroke-width': "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "20",
    y1: "10",
    x2: "80",
    y2: "10",
    stroke: "white",
    'stroke-width': "0.3",
    opacity: "0.5",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "20",
    y1: "90",
    x2: "80",
    y2: "90",
    stroke: "white",
    'stroke-width': "0.3",
    opacity: "0.5",
});
for (const [point, idx] of __VLS_vFor((__VLS_ctx.filteredPoints))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
        key: (`point-${idx}`),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
        ...{ onMouseenter: (...[$event]) => {
                __VLS_ctx.hoveredPoint = idx;
                // @ts-ignore
                [filteredPoints, hoveredPoint,];
            } },
        ...{ onMouseleave: (...[$event]) => {
                __VLS_ctx.hoveredPoint = null;
                // @ts-ignore
                [hoveredPoint,];
            } },
        cx: (point.x_coordinate),
        cy: (point.y_coordinate),
        r: (__VLS_ctx.hoveredPoint === idx ? 2 : 1.5),
        fill: (__VLS_ctx.getPointColor(point)),
        stroke: (__VLS_ctx.hoveredPoint === idx ? 'white' : __VLS_ctx.getPointStroke(point)),
        'stroke-width': "0.4",
        opacity: (__VLS_ctx.hoveredPoint === idx ? 1 : 0.8),
        ...{ class: "pitch-point" },
    });
    /** @type {__VLS_StyleScopedClasses['pitch-point']} */ ;
    // @ts-ignore
    [hoveredPoint, hoveredPoint, hoveredPoint, getPointColor, getPointStroke,];
}
if (__VLS_ctx.hoveredPoint !== null && __VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint]) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
        x: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].x_coordinate + 3),
        y: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].y_coordinate - 8),
        width: "30",
        height: "15",
        fill: "rgba(0, 0, 0, 0.9)",
        rx: "1",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].x_coordinate + 5),
        y: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].y_coordinate - 3),
        'font-size': "2.5",
        fill: "white",
        'font-weight': "600",
    });
    (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].x_coordinate + 5),
        y: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].y_coordinate + 1),
        'font-size': "2.5",
        fill: "white",
    });
    (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].line);
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].x_coordinate + 5),
        y: (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].y_coordinate + 5),
        'font-size': "2",
        fill: "#aaa",
    });
    (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].x_coordinate.toFixed(1));
    (__VLS_ctx.filteredPoints[__VLS_ctx.hoveredPoint].y_coordinate.toFixed(1));
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "distribution-panel" },
});
/** @type {__VLS_StyleScopedClasses['distribution-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "distribution-bars" },
});
/** @type {__VLS_StyleScopedClasses['distribution-bars']} */ ;
for (const [count, length] of __VLS_vFor((__VLS_ctx.lengthDistribution))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (length),
        ...{ class: "bar-item" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "bar-label" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-label']} */ ;
    (length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-fill" },
        ...{ style: ({ width: `${(count / __VLS_ctx.filteredPoints.length) * 100}%` }) },
    });
    /** @type {__VLS_StyleScopedClasses['bar-fill']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "bar-count" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-count']} */ ;
    (count);
    // @ts-ignore
    [filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, filteredPoints, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, hoveredPoint, lengthDistribution,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "distribution-panel" },
});
/** @type {__VLS_StyleScopedClasses['distribution-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "distribution-bars" },
});
/** @type {__VLS_StyleScopedClasses['distribution-bars']} */ ;
for (const [count, line] of __VLS_vFor((__VLS_ctx.lineDistribution))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (line),
        ...{ class: "bar-item" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "bar-label" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-label']} */ ;
    (line);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-container" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bar-fill" },
        ...{ style: ({ width: `${(count / __VLS_ctx.filteredPoints.length) * 100}%` }) },
    });
    /** @type {__VLS_StyleScopedClasses['bar-fill']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "bar-count" },
    });
    /** @type {__VLS_StyleScopedClasses['bar-count']} */ ;
    (count);
    // @ts-ignore
    [filteredPoints, lineDistribution,];
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
