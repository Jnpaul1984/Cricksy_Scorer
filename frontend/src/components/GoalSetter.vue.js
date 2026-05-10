/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { setJobGoals } from '@/services/coachPlusVideoService';
const props = defineProps();
const emit = defineEmits();
// Zone goals state
const zoneGoals = ref([]);
// Metric goals state
const metricGoals = ref([]);
// UI state
const saving = ref(false);
const error = ref(null);
// Available metrics (common across all analysis modes)
const defaultMetrics = [
    { code: 'HEAD_MOVEMENT', title: 'Head Stability' },
    { code: 'FRONT_ELBOW', title: 'Front Elbow Position' },
    { code: 'BACK_ELBOW', title: 'Back Elbow Position' },
    { code: 'FRONT_KNEE', title: 'Front Knee Bend' },
    { code: 'BACK_KNEE', title: 'Back Knee Drive' },
    { code: 'SHOULDER_ROTATION', title: 'Shoulder Rotation' },
    { code: 'HIP_ROTATION', title: 'Hip Rotation' },
    { code: 'BALANCE', title: 'Balance Score' },
    { code: 'FOLLOW_THROUGH', title: 'Follow Through' },
    { code: 'STRIDE_LENGTH', title: 'Stride Length' },
];
const availableMetrics = computed(() => props.availableMetrics || defaultMetrics);
// Computed
const hasValidGoals = computed(() => {
    const validZoneGoals = zoneGoals.value.filter((zg) => zg.zone_id).length > 0;
    const validMetricGoals = metricGoals.value.filter((mg) => mg.code).length > 0;
    return validZoneGoals || validMetricGoals;
});
// Methods
function addZoneGoal() {
    zoneGoals.value.push({ zone_id: '', target_accuracy: 0.8 });
}
function removeZoneGoal(index) {
    zoneGoals.value.splice(index, 1);
}
function addMetricGoal() {
    metricGoals.value.push({ code: '', target_score: 0.7 });
}
function removeMetricGoal(index) {
    metricGoals.value.splice(index, 1);
}
async function saveGoals() {
    saving.value = true;
    error.value = null;
    try {
        // Filter out incomplete goals
        const validZoneGoals = zoneGoals.value.filter((zg) => zg.zone_id);
        const validMetricGoals = metricGoals.value.filter((mg) => mg.code);
        const goals = {
            zones: validZoneGoals,
            metrics: validMetricGoals,
        };
        await setJobGoals(props.jobId, goals);
        emit('goalsSaved', goals);
        emit('close');
    }
    catch (err) {
        error.value = err.message || 'Failed to save goals';
    }
    finally {
        saving.value = false;
    }
}
// Initialize with existing goals
onMounted(() => {
    if (props.existingGoals) {
        zoneGoals.value = [...(props.existingGoals.zones || [])];
        metricGoals.value = [...(props.existingGoals.metrics || [])];
    }
    // Add at least one empty row if no existing goals
    if (zoneGoals.value.length === 0) {
        addZoneGoal();
    }
    if (metricGoals.value.length === 0) {
        addMetricGoal();
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
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['goals-section']} */ ;
/** @type {__VLS_StyleScopedClasses['accuracy-input']} */ ;
/** @type {__VLS_StyleScopedClasses['score-input']} */ ;
/** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['add-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['cancel-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['cancel-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['save-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['save-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['save-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "goal-setter" },
});
/** @type {__VLS_StyleScopedClasses['goal-setter']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "modal-header" },
});
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.$emit('close');
            // @ts-ignore
            [$emit,];
        } },
    ...{ class: "close-btn" },
});
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "modal-body" },
});
/** @type {__VLS_StyleScopedClasses['modal-body']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "goals-section" },
});
/** @type {__VLS_StyleScopedClasses['goals-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-description" },
});
/** @type {__VLS_StyleScopedClasses['section-description']} */ ;
for (const [zoneGoal, index] of __VLS_vFor((__VLS_ctx.zoneGoals))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (index),
        ...{ class: "goal-row" },
    });
    /** @type {__VLS_StyleScopedClasses['goal-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (zoneGoal.zone_id),
        ...{ class: "zone-select" },
    });
    /** @type {__VLS_StyleScopedClasses['zone-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    for (const [zone] of __VLS_vFor((__VLS_ctx.availableZones))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (zone.id),
            value: (zone.id),
        });
        (zone.name);
        // @ts-ignore
        [zoneGoals, availableZones,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "accuracy-input" },
    });
    /** @type {__VLS_StyleScopedClasses['accuracy-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    ((zoneGoal.target_accuracy * 100).toFixed(0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "range",
        min: "0",
        max: "1",
        step: "0.05",
        ...{ class: "accuracy-slider" },
    });
    (zoneGoal.target_accuracy);
    /** @type {__VLS_StyleScopedClasses['accuracy-slider']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.removeZoneGoal(index);
                // @ts-ignore
                [removeZoneGoal,];
            } },
        ...{ class: "remove-btn" },
        title: "Remove",
    });
    /** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.addZoneGoal) },
    ...{ class: "add-btn" },
});
/** @type {__VLS_StyleScopedClasses['add-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "goals-section" },
});
/** @type {__VLS_StyleScopedClasses['goals-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-description" },
});
/** @type {__VLS_StyleScopedClasses['section-description']} */ ;
for (const [metricGoal, index] of __VLS_vFor((__VLS_ctx.metricGoals))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (index),
        ...{ class: "goal-row" },
    });
    /** @type {__VLS_StyleScopedClasses['goal-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (metricGoal.code),
        ...{ class: "metric-select" },
    });
    /** @type {__VLS_StyleScopedClasses['metric-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    for (const [metric] of __VLS_vFor((__VLS_ctx.availableMetrics))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (metric.code),
            value: (metric.code),
        });
        (metric.title);
        // @ts-ignore
        [addZoneGoal, metricGoals, availableMetrics,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score-input" },
    });
    /** @type {__VLS_StyleScopedClasses['score-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    (metricGoal.target_score.toFixed(2));
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "range",
        min: "0",
        max: "1",
        step: "0.05",
        ...{ class: "score-slider" },
    });
    (metricGoal.target_score);
    /** @type {__VLS_StyleScopedClasses['score-slider']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.removeMetricGoal(index);
                // @ts-ignore
                [removeMetricGoal,];
            } },
        ...{ class: "remove-btn" },
        title: "Remove",
    });
    /** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.addMetricGoal) },
    ...{ class: "add-btn" },
});
/** @type {__VLS_StyleScopedClasses['add-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "modal-footer" },
});
/** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.$emit('close');
            // @ts-ignore
            [$emit, addMetricGoal,];
        } },
    ...{ class: "cancel-btn" },
});
/** @type {__VLS_StyleScopedClasses['cancel-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveGoals) },
    ...{ class: "save-btn" },
    disabled: (!__VLS_ctx.hasValidGoals || __VLS_ctx.saving),
});
/** @type {__VLS_StyleScopedClasses['save-btn']} */ ;
(__VLS_ctx.saving ? 'Saving...' : 'Save Goals');
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-message" },
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    (__VLS_ctx.error);
}
// @ts-ignore
[saveGoals, hasValidGoals, saving, saving, error, error,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
