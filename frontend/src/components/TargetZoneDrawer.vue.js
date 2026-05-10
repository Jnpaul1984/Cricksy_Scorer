/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted } from 'vue';
const props = defineProps();
const pitchPoints = ref([]);
const zones = ref([]);
const zoneReports = ref({});
const selectedZoneId = ref(null);
const drawMode = ref(false);
const drawStart = ref(null);
const currentMouse = ref(null);
const showCreateDialog = ref(false);
const newZoneName = ref('');
const pendingZone = ref(null);
const pitchSvg = ref(null);
function toggleDrawMode() {
    drawMode.value = !drawMode.value;
    if (!drawMode.value) {
        drawStart.value = null;
        currentMouse.value = null;
    }
}
function getSVGCoordinates(event) {
    if (!pitchSvg.value)
        return null;
    const svg = pitchSvg.value;
    const rect = svg.getBoundingClientRect();
    // Convert mouse position to SVG coordinates (0-100 scale)
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    return { x, y };
}
function startDrawing(event) {
    if (!drawMode.value)
        return;
    const coords = getSVGCoordinates(event);
    if (coords) {
        drawStart.value = coords;
        currentMouse.value = coords;
    }
}
function updateDrawing(event) {
    if (!drawMode.value || !drawStart.value)
        return;
    const coords = getSVGCoordinates(event);
    if (coords) {
        currentMouse.value = coords;
    }
}
function finishDrawing(event) {
    if (!drawMode.value || !drawStart.value)
        return;
    const coords = getSVGCoordinates(event);
    if (!coords)
        return;
    const x = Math.min(drawStart.value.x, coords.x);
    const y = Math.min(drawStart.value.y, coords.y);
    const width = Math.abs(coords.x - drawStart.value.x);
    const height = Math.abs(coords.y - drawStart.value.y);
    // Minimum zone size
    if (width < 5 || height < 5) {
        drawStart.value = null;
        currentMouse.value = null;
        return;
    }
    pendingZone.value = { x, y, width, height };
    showCreateDialog.value = true;
    drawMode.value = false;
    drawStart.value = null;
    currentMouse.value = null;
}
async function saveNewZone() {
    if (!newZoneName.value.trim() || !pendingZone.value)
        return;
    try {
        const response = await fetch('/api/coaches/plus/target-zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: props.sessionId,
                name: newZoneName.value.trim(),
                shape: 'rect',
                definition_json: pendingZone.value
            })
        });
        if (!response.ok) {
            throw new Error('Failed to create zone');
        }
        const zone = await response.json();
        zones.value.push(zone);
        // Load report for new zone
        await loadZoneReport(zone.id);
        showCreateDialog.value = false;
        newZoneName.value = '';
        pendingZone.value = null;
    }
    catch (err) {
        console.error('Failed to create zone:', err);
    }
}
function cancelCreate() {
    showCreateDialog.value = false;
    newZoneName.value = '';
    pendingZone.value = null;
}
function selectZone(zoneId) {
    selectedZoneId.value = selectedZoneId.value === zoneId ? null : zoneId;
}
async function deleteZone(zoneId) {
    if (!confirm('Delete this target zone?'))
        return;
    // TODO: Implement delete endpoint
    zones.value = zones.value.filter(z => z.id !== zoneId);
    delete zoneReports.value[zoneId];
    if (selectedZoneId.value === zoneId) {
        selectedZoneId.value = null;
    }
}
function getZoneName(zoneId) {
    return zones.value.find(z => z.id === zoneId)?.name || 'Unknown Zone';
}
function getZoneFill(zoneId) {
    return selectedZoneId.value === zoneId ? '#3b82f6' : '#10b981';
}
function getZoneStroke(zoneId) {
    return selectedZoneId.value === zoneId ? '#2563eb' : '#059669';
}
async function loadPitchMap() {
    try {
        const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/pitch-map`);
        const data = await response.json();
        pitchPoints.value = data.points || [];
    }
    catch (err) {
        console.error('Failed to load pitch map:', err);
    }
}
async function loadZones() {
    try {
        const response = await fetch(`/api/coaches/plus/target-zones?session_id=${props.sessionId}`);
        const data = await response.json();
        zones.value = data || [];
        // Load reports for all zones
        for (const zone of zones.value) {
            await loadZoneReport(zone.id);
        }
    }
    catch (err) {
        console.error('Failed to load zones:', err);
    }
}
async function loadZoneReport(zoneId) {
    try {
        const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/zone-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                zone_id: zoneId,
                tolerance: 2.0
            })
        });
        const report = await response.json();
        zoneReports.value[zoneId] = report;
    }
    catch (err) {
        console.error('Failed to load zone report:', err);
    }
}
onMounted(() => {
    loadPitchMap();
    loadZones();
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
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['draw-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['draw-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['zone-item']} */ ;
/** @type {__VLS_StyleScopedClasses['zone-item']} */ ;
/** @type {__VLS_StyleScopedClasses['delete-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['zone-details']} */ ;
/** @type {__VLS_StyleScopedClasses['miss-breakdown']} */ ;
/** @type {__VLS_StyleScopedClasses['miss-breakdown']} */ ;
/** @type {__VLS_StyleScopedClasses['dialog']} */ ;
/** @type {__VLS_StyleScopedClasses['zone-name-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "target-zone-panel" },
});
/** @type {__VLS_StyleScopedClasses['target-zone-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-header" },
});
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.toggleDrawMode) },
    ...{ class: ({ active: __VLS_ctx.drawMode }) },
    ...{ class: "draw-toggle" },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['draw-toggle']} */ ;
(__VLS_ctx.drawMode ? '✓ Drawing' : '+ Draw Zone');
if (__VLS_ctx.zones.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "zone-list" },
    });
    /** @type {__VLS_StyleScopedClasses['zone-list']} */ ;
    for (const [zone] of __VLS_vFor((__VLS_ctx.zones))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.zones.length > 0))
                        return;
                    __VLS_ctx.selectZone(zone.id);
                    // @ts-ignore
                    [toggleDrawMode, drawMode, drawMode, zones, zones, selectZone,];
                } },
            key: (zone.id),
            ...{ class: ({ selected: __VLS_ctx.selectedZoneId === zone.id }) },
            ...{ class: "zone-item" },
        });
        /** @type {__VLS_StyleScopedClasses['selected']} */ ;
        /** @type {__VLS_StyleScopedClasses['zone-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "zone-info" },
        });
        /** @type {__VLS_StyleScopedClasses['zone-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "zone-name" },
        });
        /** @type {__VLS_StyleScopedClasses['zone-name']} */ ;
        (zone.name);
        if (__VLS_ctx.zoneReports[zone.id]) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "zone-stats" },
            });
            /** @type {__VLS_StyleScopedClasses['zone-stats']} */ ;
            (__VLS_ctx.zoneReports[zone.id].hit_rate.toFixed(1));
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.zones.length > 0))
                        return;
                    __VLS_ctx.deleteZone(zone.id);
                    // @ts-ignore
                    [selectedZoneId, zoneReports, zoneReports, deleteZone,];
                } },
            ...{ class: "delete-btn" },
        });
        /** @type {__VLS_StyleScopedClasses['delete-btn']} */ ;
        // @ts-ignore
        [];
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pitch-container" },
});
/** @type {__VLS_StyleScopedClasses['pitch-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
    ...{ onMousedown: (__VLS_ctx.startDrawing) },
    ...{ onMousemove: (__VLS_ctx.updateDrawing) },
    ...{ onMouseup: (__VLS_ctx.finishDrawing) },
    ref: "pitchSvg",
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
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "0",
    y1: "50",
    x2: "100",
    y2: "50",
    stroke: "white",
    'stroke-width': "0.3",
    opacity: "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "50",
    y1: "0",
    x2: "50",
    y2: "100",
    stroke: "white",
    'stroke-width': "0.3",
    opacity: "0.3",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
    cx: "50",
    cy: "5",
    r: "0.8",
    fill: "yellow",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
    cx: "50",
    cy: "95",
    r: "0.8",
    fill: "yellow",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "20",
    y1: "10",
    x2: "80",
    y2: "10",
    stroke: "white",
    'stroke-width': "0.2",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.line)({
    x1: "20",
    y1: "90",
    x2: "80",
    y2: "90",
    stroke: "white",
    'stroke-width': "0.2",
});
for (const [point, idx] of __VLS_vFor((__VLS_ctx.pitchPoints))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
        key: (`point-${idx}`),
        cx: (point.x_coordinate),
        cy: (point.y_coordinate),
        r: "1.5",
        fill: "rgba(255, 255, 0, 0.7)",
        stroke: "rgba(255, 200, 0, 0.9)",
        'stroke-width': "0.3",
    });
    // @ts-ignore
    [startDrawing, updateDrawing, finishDrawing, pitchPoints,];
}
for (const [zone] of __VLS_vFor((__VLS_ctx.zones))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.g, __VLS_intrinsics.g)({
        key: (`zone-${zone.id}`),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
        x: (zone.definition_json.x),
        y: (zone.definition_json.y),
        width: (zone.definition_json.width),
        height: (zone.definition_json.height),
        fill: (__VLS_ctx.getZoneFill(zone.id)),
        stroke: (__VLS_ctx.getZoneStroke(zone.id)),
        'stroke-width': "0.5",
        opacity: (__VLS_ctx.selectedZoneId === zone.id ? 0.5 : 0.3),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
        x: (zone.definition_json.x + 2),
        y: (zone.definition_json.y + 4),
        'font-size': "3",
        fill: "white",
        'font-weight': "bold",
    });
    (zone.name);
    // @ts-ignore
    [zones, selectedZoneId, getZoneFill, getZoneStroke,];
}
if (__VLS_ctx.drawMode && __VLS_ctx.drawStart && __VLS_ctx.currentMouse) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.rect)({
        x: (Math.min(__VLS_ctx.drawStart.x, __VLS_ctx.currentMouse.x)),
        y: (Math.min(__VLS_ctx.drawStart.y, __VLS_ctx.currentMouse.y)),
        width: (Math.abs(__VLS_ctx.currentMouse.x - __VLS_ctx.drawStart.x)),
        height: (Math.abs(__VLS_ctx.currentMouse.y - __VLS_ctx.drawStart.y)),
        fill: "rgba(59, 130, 246, 0.3)",
        stroke: "#3b82f6",
        'stroke-width': "0.5",
        'stroke-dasharray': "1,1",
    });
}
if (__VLS_ctx.selectedZoneId && __VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId]) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "zone-details" },
    });
    /** @type {__VLS_StyleScopedClasses['zone-details']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    (__VLS_ctx.getZoneName(__VLS_ctx.selectedZoneId));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].hit_rate.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].hits);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].misses);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat" },
    });
    /** @type {__VLS_StyleScopedClasses['stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].total_deliveries);
    if (__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].misses > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "miss-breakdown" },
        });
        /** @type {__VLS_StyleScopedClasses['miss-breakdown']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h5, __VLS_intrinsics.h5)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
        for (const [count, direction] of __VLS_vFor((__VLS_ctx.zoneReports[__VLS_ctx.selectedZoneId].miss_breakdown))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (direction),
            });
            (direction);
            (count);
            // @ts-ignore
            [drawMode, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, selectedZoneId, zoneReports, zoneReports, zoneReports, zoneReports, zoneReports, zoneReports, zoneReports, drawStart, drawStart, drawStart, drawStart, drawStart, currentMouse, currentMouse, currentMouse, currentMouse, currentMouse, getZoneName,];
        }
    }
}
if (__VLS_ctx.showCreateDialog) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.cancelCreate) },
        ...{ class: "dialog-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['dialog-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "dialog" },
    });
    /** @type {__VLS_StyleScopedClasses['dialog']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        ...{ onKeyup: (__VLS_ctx.saveNewZone) },
        value: (__VLS_ctx.newZoneName),
        type: "text",
        placeholder: "e.g., Yorker Line, Off Stump Channel",
        ...{ class: "zone-name-input" },
    });
    /** @type {__VLS_StyleScopedClasses['zone-name-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dialog-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['dialog-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.cancelCreate) },
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.saveNewZone) },
        disabled: (!__VLS_ctx.newZoneName.trim()),
        ...{ class: "btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
}
// @ts-ignore
[showCreateDialog, cancelCreate, cancelCreate, saveNewZone, saveNewZone, newZoneName, newZoneName,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
