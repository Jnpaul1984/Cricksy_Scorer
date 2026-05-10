/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, ref, watch } from 'vue';
import shotMapAvif1024 from '@/assets/optimized/shot-map-field-w1024.avif';
import shotMapWebp1024 from '@/assets/optimized/shot-map-field-w1024.webp';
import shotMapAvif1440 from '@/assets/optimized/shot-map-field-w1440.avif';
import shotMapWebp1440 from '@/assets/optimized/shot-map-field-w1440.webp';
import shotMapAvif480 from '@/assets/optimized/shot-map-field-w480.avif';
import shotMapWebp480 from '@/assets/optimized/shot-map-field-w480.webp';
import shotMapAvif768 from '@/assets/optimized/shot-map-field-w768.avif';
import shotMapWebp768 from '@/assets/optimized/shot-map-field-w768.webp';
const props = defineProps();
const emit = defineEmits();
const canvasRef = ref(null);
const strokes = ref([]);
const currentStroke = ref([]);
const isDrawing = ref(false);
const lastEmitted = ref(null);
const canvasWidth = computed(() => props.width ?? 220);
const canvasHeight = computed(() => props.height ?? 220);
const hasHistory = computed(() => strokes.value.length > 0);
const hasActiveStroke = computed(() => hasHistory.value || currentStroke.value.length > 1);
const surfaceStyle = computed(() => ({
    width: `${canvasWidth.value}px`,
    height: `${canvasHeight.value}px`,
    backgroundColor: props.backgroundImage ? 'transparent' : '#f8fafc',
}));
const shotMapSources = [
    { width: 480, avif: shotMapAvif480, webp: shotMapWebp480 },
    { width: 768, avif: shotMapAvif768, webp: shotMapWebp768 },
    { width: 1024, avif: shotMapAvif1024, webp: shotMapWebp1024 },
    { width: 1440, avif: shotMapAvif1440, webp: shotMapWebp1440 },
];
const shotMapAvifSrcset = shotMapSources.map((src) => `${src.avif} ${src.width}w`).join(', ');
const shotMapWebpSrcset = shotMapSources.map((src) => `${src.webp} ${src.width}w`).join(', ');
const shotMapDefaultSrc = shotMapSources.find((src) => src.width === 1024)?.webp ??
    shotMapSources[shotMapSources.length - 1]?.webp ??
    '';
const shotMapSizes = computed(() => `${canvasWidth.value}px`);
function setupCanvas() {
    const canvas = canvasRef.value;
    if (!canvas)
        return;
    canvas.width = canvasWidth.value;
    canvas.height = canvasHeight.value;
    canvas.style.width = `${canvasWidth.value}px`;
    canvas.style.height = `${canvasHeight.value}px`;
    render();
}
function pointFromEvent(event) {
    const canvas = canvasRef.value;
    if (!canvas)
        return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const x = Math.min(Math.max(event.clientX - rect.left, 0), canvasWidth.value);
    const y = Math.min(Math.max(event.clientY - rect.top, 0), canvasHeight.value);
    return { x, y };
}
function drawStroke(ctx, stroke) {
    if (stroke.length < 2)
        return;
    ctx.beginPath();
    ctx.moveTo(stroke[0].x, stroke[0].y);
    for (let i = 1; i < stroke.length; i += 1) {
        ctx.lineTo(stroke[i].x, stroke[i].y);
    }
    ctx.stroke();
}
function render() {
    const canvas = canvasRef.value;
    if (!canvas)
        return;
    const ctx = canvas.getContext('2d');
    if (!ctx)
        return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#2563eb';
    for (const stroke of strokes.value) {
        drawStroke(ctx, stroke);
    }
    drawStroke(ctx, currentStroke.value);
}
function encodeSvg() {
    if (!strokes.value.length) {
        return null;
    }
    const segments = [];
    for (const stroke of strokes.value) {
        if (!stroke.length)
            continue;
        const path = stroke
            .map((point, idx) => `${idx === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
            .join(' ');
        if (path)
            segments.push(path);
    }
    if (!segments.length)
        return null;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasWidth.value} ${canvasHeight.value}" fill="none"><path d="${segments.join(' ')}" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
function emitValue() {
    const encoded = encodeSvg();
    lastEmitted.value = encoded;
    emit('update:modelValue', encoded);
}
function onPointerDown(event) {
    if (event.button !== 0 && event.pointerType === 'mouse')
        return;
    event.preventDefault();
    isDrawing.value = true;
    const start = pointFromEvent(event);
    currentStroke.value = [start];
    render();
}
function onPointerMove(event) {
    if (!isDrawing.value)
        return;
    event.preventDefault();
    const next = pointFromEvent(event);
    const last = currentStroke.value[currentStroke.value.length - 1];
    if (!last || Math.hypot(next.x - last.x, next.y - last.y) < 1)
        return;
    currentStroke.value = [...currentStroke.value, next];
    render();
}
function finishStroke() {
    if (!isDrawing.value)
        return;
    isDrawing.value = false;
    if (currentStroke.value.length > 1) {
        strokes.value = [...strokes.value, [...currentStroke.value]];
        emitValue();
    }
    currentStroke.value = [];
    render();
}
function undo() {
    if (!strokes.value.length)
        return;
    strokes.value = strokes.value.slice(0, -1);
    render();
    emitValue();
}
function clearAll() {
    if (!hasActiveStroke.value)
        return;
    strokes.value = [];
    currentStroke.value = [];
    render();
    lastEmitted.value = null;
    emit('update:modelValue', null);
}
onMounted(() => {
    setupCanvas();
});
watch([canvasWidth, canvasHeight], () => {
    setupCanvas();
});
watch(() => props.modelValue, (value) => {
    if (value === lastEmitted.value)
        return;
    if (value == null) {
        strokes.value = [];
        currentStroke.value = [];
        render();
    }
});
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
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "shot-map-canvas" },
});
/** @type {__VLS_StyleScopedClasses['shot-map-canvas']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "shot-map-canvas__surface-wrapper" },
    ...{ style: (__VLS_ctx.surfaceStyle) },
});
/** @type {__VLS_StyleScopedClasses['shot-map-canvas__surface-wrapper']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "shot-map-canvas__background" },
});
/** @type {__VLS_StyleScopedClasses['shot-map-canvas__background']} */ ;
if (props.backgroundImage) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        ...{ class: "shot-map-canvas__background-img" },
        src: (props.backgroundImage),
        alt: "Cricket field",
        loading: "lazy",
        decoding: "async",
    });
    /** @type {__VLS_StyleScopedClasses['shot-map-canvas__background-img']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.picture, __VLS_intrinsics.picture)({
        ...{ class: "shot-map-canvas__picture" },
    });
    /** @type {__VLS_StyleScopedClasses['shot-map-canvas__picture']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.source)({
        srcset: (__VLS_ctx.shotMapAvifSrcset),
        sizes: (__VLS_ctx.shotMapSizes),
        type: "image/avif",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.source)({
        srcset: (__VLS_ctx.shotMapWebpSrcset),
        sizes: (__VLS_ctx.shotMapSizes),
        type: "image/webp",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        ...{ class: "shot-map-canvas__background-img" },
        src: (__VLS_ctx.shotMapDefaultSrc),
        sizes: (__VLS_ctx.shotMapSizes),
        alt: "Cricket field",
        loading: "lazy",
        decoding: "async",
    });
    /** @type {__VLS_StyleScopedClasses['shot-map-canvas__background-img']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.canvas)({
    ...{ onPointerdown: (__VLS_ctx.onPointerDown) },
    ...{ onPointermove: (__VLS_ctx.onPointerMove) },
    ...{ onPointerup: (__VLS_ctx.finishStroke) },
    ...{ onPointerleave: (__VLS_ctx.finishStroke) },
    ...{ onPointercancel: (__VLS_ctx.finishStroke) },
    ref: "canvasRef",
    ...{ class: "shot-map-canvas__surface" },
    width: (__VLS_ctx.canvasWidth),
    height: (__VLS_ctx.canvasHeight),
});
/** @type {__VLS_StyleScopedClasses['shot-map-canvas__surface']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "shot-map-canvas__actions" },
});
/** @type {__VLS_StyleScopedClasses['shot-map-canvas__actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.undo) },
    ...{ class: "btn" },
    type: "button",
    disabled: (!__VLS_ctx.hasHistory),
});
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.clearAll) },
    ...{ class: "btn" },
    type: "button",
    disabled: (!__VLS_ctx.hasActiveStroke),
});
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
// @ts-ignore
[surfaceStyle, shotMapAvifSrcset, shotMapSizes, shotMapSizes, shotMapSizes, shotMapWebpSrcset, shotMapDefaultSrc, onPointerDown, onPointerMove, finishStroke, finishStroke, finishStroke, canvasWidth, canvasHeight, undo, hasHistory, clearAll, hasActiveStroke,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
