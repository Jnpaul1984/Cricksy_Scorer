/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
const route = useRoute();
const sessionId = computed(() => route.params.sessionId);
const loading = ref(false);
const error = ref(null);
const saving = ref(false);
const saveSuccess = ref(false);
const frameUrl = ref(null);
const frameImage = ref(null);
const imageLoaded = ref(false);
const imageWidth = ref(0);
const imageHeight = ref(0);
const corners = ref([]);
const cornerLabels = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right'];
const cornerColors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24'];
async function loadFrame() {
    loading.value = true;
    error.value = null;
    try {
        const response = await fetch(`/api/coaches/plus/sessions/${sessionId.value}/calibration-frame`);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load calibration frame');
        }
        if (!data.frame_url) {
            throw new Error(data.message || 'Calibration frame not available');
        }
        frameUrl.value = data.frame_url;
    }
    catch (err) {
        error.value = err.message || 'Failed to load calibration frame';
    }
    finally {
        loading.value = false;
    }
}
function onImageLoad(event) {
    const img = event.target;
    imageWidth.value = img.naturalWidth;
    imageHeight.value = img.naturalHeight;
    imageLoaded.value = true;
}
function handleImageClick(event) {
    if (corners.value.length >= 4) {
        return;
    }
    const img = frameImage.value;
    if (!img)
        return;
    const rect = img.getBoundingClientRect();
    const scaleX = imageWidth.value / rect.width;
    const scaleY = imageHeight.value / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    corners.value.push({ x, y });
}
function removeCorner(index) {
    corners.value.splice(index, 1);
}
function resetCorners() {
    corners.value = [];
    saveSuccess.value = false;
}
function getCornerLabel(index) {
    return cornerLabels[index] || `Corner ${index + 1}`;
}
function getCornerColor(index) {
    return cornerColors[index] || '#888';
}
function getPolylinePoints() {
    if (corners.value.length < 2)
        return '';
    const points = corners.value.map(c => `${c.x},${c.y}`).join(' ');
    // Close the polygon if we have all 4 corners
    if (corners.value.length === 4) {
        return points + ` ${corners.value[0].x},${corners.value[0].y}`;
    }
    return points;
}
async function saveCalibration() {
    if (corners.value.length !== 4) {
        error.value = 'Please select exactly 4 corners';
        return;
    }
    saving.value = true;
    error.value = null;
    saveSuccess.value = false;
    try {
        const response = await fetch(`/api/coaches/plus/sessions/${sessionId.value}/pitch-calibration`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                corners: corners.value.map(c => ({ x: c.x, y: c.y }))
            })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to save calibration');
        }
        saveSuccess.value = true;
        setTimeout(() => {
            saveSuccess.value = false;
        }, 3000);
    }
    catch (err) {
        error.value = err.message || 'Failed to save calibration';
    }
    finally {
        saving.value = false;
    }
}
onMounted(() => {
    loadFrame();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['calibration-header']} */ ;
/** @type {__VLS_StyleScopedClasses['calibration-header']} */ ;
/** @type {__VLS_StyleScopedClasses['error-state']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['corner-list']} */ ;
/** @type {__VLS_StyleScopedClasses['corner-list']} */ ;
/** @type {__VLS_StyleScopedClasses['corner-list']} */ ;
/** @type {__VLS_StyleScopedClasses['corner-list']} */ ;
/** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['calibration-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pitch-calibration" },
});
/** @type {__VLS_StyleScopedClasses['pitch-calibration']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "calibration-header" },
});
/** @type {__VLS_StyleScopedClasses['calibration-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-state" },
    });
    /** @type {__VLS_StyleScopedClasses['error-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.loadFrame) },
        ...{ class: "retry-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['retry-btn']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "calibration-content" },
    });
    /** @type {__VLS_StyleScopedClasses['calibration-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "image-container" },
    });
    /** @type {__VLS_StyleScopedClasses['image-container']} */ ;
    if (__VLS_ctx.frameUrl) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
            ...{ onClick: (__VLS_ctx.handleImageClick) },
            ...{ onLoad: (__VLS_ctx.onImageLoad) },
            ref: "frameImage",
            src: (__VLS_ctx.frameUrl),
            alt: "Calibration frame",
            ...{ class: "calibration-frame" },
        });
        /** @type {__VLS_StyleScopedClasses['calibration-frame']} */ ;
    }
    if (__VLS_ctx.imageLoaded) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            ...{ onClick: (__VLS_ctx.handleImageClick) },
            ...{ class: "overlay-svg" },
            viewBox: (`0 0 ${__VLS_ctx.imageWidth} ${__VLS_ctx.imageHeight}`),
        });
        /** @type {__VLS_StyleScopedClasses['overlay-svg']} */ ;
        for (const [corner, index] of __VLS_vFor((__VLS_ctx.corners))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
                key: (index),
                cx: (corner.x),
                cy: (corner.y),
                r: "8",
                fill: (__VLS_ctx.getCornerColor(index)),
                stroke: "white",
                'stroke-width': "2",
            });
            // @ts-ignore
            [loading, error, error, loadFrame, frameUrl, frameUrl, handleImageClick, handleImageClick, onImageLoad, imageLoaded, imageWidth, imageHeight, corners, getCornerColor,];
        }
        if (__VLS_ctx.corners.length >= 2) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.polyline)({
                points: (__VLS_ctx.getPolylinePoints()),
                fill: "none",
                stroke: "cyan",
                'stroke-width': "2",
                'stroke-dasharray': "5,5",
            });
        }
        for (const [corner, index] of __VLS_vFor((__VLS_ctx.corners))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
                key: (`label-${index}`),
                x: (corner.x + 15),
                y: (corner.y - 10),
                fill: "white",
                'font-size': "14",
                'font-weight': "bold",
                stroke: "black",
                'stroke-width': "0.5",
            });
            (__VLS_ctx.getCornerLabel(index));
            // @ts-ignore
            [corners, corners, getPolylinePoints, getCornerLabel,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "corner-list" },
    });
    /** @type {__VLS_StyleScopedClasses['corner-list']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.corners.length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    for (const [corner, index] of __VLS_vFor((__VLS_ctx.corners))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (index),
            ...{ class: ({ active: index === __VLS_ctx.corners.length - 1 }) },
        });
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "corner-number" },
            ...{ style: ({ backgroundColor: __VLS_ctx.getCornerColor(index) }) },
        });
        /** @type {__VLS_StyleScopedClasses['corner-number']} */ ;
        (index + 1);
        (__VLS_ctx.getCornerLabel(index));
        (Math.round(corner.x));
        (Math.round(corner.y));
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    __VLS_ctx.removeCorner(index);
                    // @ts-ignore
                    [corners, corners, corners, getCornerColor, getCornerLabel, removeCorner,];
                } },
            ...{ class: "remove-btn" },
        });
        /** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.resetCorners) },
        disabled: (__VLS_ctx.corners.length === 0),
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.saveCalibration) },
        disabled: (__VLS_ctx.corners.length !== 4 || __VLS_ctx.saving),
        ...{ class: "btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    (__VLS_ctx.saving ? 'Saving...' : 'Save Calibration');
    if (__VLS_ctx.saveSuccess) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "success-message" },
        });
        /** @type {__VLS_StyleScopedClasses['success-message']} */ ;
    }
}
// @ts-ignore
[corners, corners, resetCorners, saveCalibration, saving, saving, saveSuccess,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
