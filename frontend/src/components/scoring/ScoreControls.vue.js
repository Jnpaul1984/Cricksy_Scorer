/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, ref } from 'vue';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const emit = defineEmits();
const gameStore = useGameStore();
const submitting = ref(false);
const showWicketModal = ref(false);
const canScore = computed(() => props.canScore && !submitting.value);
async function doScoreRuns(runs) {
    if (!canScore.value)
        return;
    submitting.value = true;
    try {
        await gameStore.scoreRuns(props.gameId, runs, null);
        emit('scored');
    }
    catch (e) {
        emit('error', e?.message || 'Failed to score');
    }
    finally {
        submitting.value = false;
    }
}
async function doScoreExtra(code, runs = 1) {
    if (!canScore.value)
        return;
    submitting.value = true;
    try {
        await gameStore.scoreExtra(props.gameId, code, runs, null);
        emit('scored');
    }
    catch (e) {
        emit('error', e?.message || 'Failed to score extra');
    }
    finally {
        submitting.value = false;
    }
}
function openWicket() { showWicketModal.value = true; }
function closeWicket() { showWicketModal.value = false; }
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
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "score-controls" },
});
/** @type {__VLS_StyleScopedClasses['score-controls']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "runs" },
});
/** @type {__VLS_StyleScopedClasses['runs']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "runs-grid" },
});
/** @type {__VLS_StyleScopedClasses['runs-grid']} */ ;
for (const [r] of __VLS_vFor(([0, 1, 2, 3, 4, 5, 6]))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.doScoreRuns(r);
                // @ts-ignore
                [doScoreRuns,];
            } },
        key: (r),
        disabled: (!__VLS_ctx.canScore),
        'data-testid': (`run-${r}`),
    });
    (r);
    // @ts-ignore
    [canScore,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras" },
});
/** @type {__VLS_StyleScopedClasses['extras']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-grid" },
});
/** @type {__VLS_StyleScopedClasses['extras-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doScoreExtra('wd', 1);
            // @ts-ignore
            [doScoreExtra,];
        } },
    disabled: (!__VLS_ctx.canScore),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doScoreExtra('nb', 0);
            // @ts-ignore
            [canScore, doScoreExtra,];
        } },
    disabled: (!__VLS_ctx.canScore),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doScoreExtra('b', 1);
            // @ts-ignore
            [canScore, doScoreExtra,];
        } },
    disabled: (!__VLS_ctx.canScore),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doScoreExtra('lb', 1);
            // @ts-ignore
            [canScore, doScoreExtra,];
        } },
    disabled: (!__VLS_ctx.canScore),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "wicket-row" },
});
/** @type {__VLS_StyleScopedClasses['wicket-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.openWicket) },
    ...{ class: "wicket-btn" },
    disabled: (!__VLS_ctx.canScore),
});
/** @type {__VLS_StyleScopedClasses['wicket-btn']} */ ;
var __VLS_0 = {
    visible: (__VLS_ctx.showWicketModal),
    close: (__VLS_ctx.closeWicket),
};
// @ts-ignore
var __VLS_1 = __VLS_0;
// @ts-ignore
[canScore, canScore, openWicket, showWicketModal, closeWicket,];
const __VLS_base = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
const __VLS_export = {};
export default {};
