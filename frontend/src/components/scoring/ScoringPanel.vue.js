/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, toRefs } from 'vue';
import CommentaryInput from './CommentaryInput.vue';
import DismissalForm from './DismissalForm.vue';
import ScoreControls from './ScoreControls.vue';
import UndoLastBall from './UndoLastBall.vue';
import WicketModal from './WicketModal.vue';
import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
const props = defineProps();
const { gameId, canScore, strikerId, nonStrikerId, bowlerId, battingPlayers } = toRefs(props);
const authStore = useAuthStore();
const gameStore = useGameStore();
if (import.meta.env.DEV) {
    console.log('[ScoringPanel debug]', {
        role: authStore.role,
        isSuperuser: authStore.isSuperuser,
        authCanScore: authStore.canScore,
        gameCanScore: gameStore.canScore,
        striker: gameStore.currentStriker?.id ?? null,
        nonStriker: gameStore.currentNonStriker?.id ?? null,
        bowler: gameStore.state?.current_bowler_id ?? null,
    });
}
const emit = defineEmits();
const note = ref('');
function onScored() { emit('scored'); }
function onError(m) { emit('error', m); }
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
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "scoring-panel" },
});
/** @type {__VLS_StyleScopedClasses['scoring-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
const __VLS_0 = CommentaryInput;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    modelValue: (__VLS_ctx.note),
    ...{ class: "mb" },
}));
const __VLS_2 = __VLS_1({
    modelValue: (__VLS_ctx.note),
    ...{ class: "mb" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['mb']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
if (__VLS_ctx.canScore) {
    const __VLS_5 = ScoreControls || ScoreControls;
    // @ts-ignore
    const __VLS_6 = __VLS_asFunctionalComponent1(__VLS_5, new __VLS_5({
        ...{ 'onScored': {} },
        ...{ 'onError': {} },
        gameId: (__VLS_ctx.gameId),
        strikerId: (__VLS_ctx.strikerId),
        nonStrikerId: (__VLS_ctx.nonStrikerId),
        bowlerId: (__VLS_ctx.bowlerId),
        canScore: (__VLS_ctx.canScore),
        commentary: (__VLS_ctx.note),
    }));
    const __VLS_7 = __VLS_6({
        ...{ 'onScored': {} },
        ...{ 'onError': {} },
        gameId: (__VLS_ctx.gameId),
        strikerId: (__VLS_ctx.strikerId),
        nonStrikerId: (__VLS_ctx.nonStrikerId),
        bowlerId: (__VLS_ctx.bowlerId),
        canScore: (__VLS_ctx.canScore),
        commentary: (__VLS_ctx.note),
    }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    let __VLS_10;
    const __VLS_11 = ({ scored: {} },
        { onScored: (__VLS_ctx.onScored) });
    const __VLS_12 = ({ error: {} },
        { onError: (__VLS_ctx.onError) });
    const { default: __VLS_13 } = __VLS_8.slots;
    {
        const { 'wicket-modal': __VLS_14 } = __VLS_8.slots;
        const [{ visible, close }] = __VLS_vSlot(__VLS_14);
        const __VLS_15 = WicketModal;
        // @ts-ignore
        const __VLS_16 = __VLS_asFunctionalComponent1(__VLS_15, new __VLS_15({
            ...{ 'onClose': {} },
            ...{ 'onScored': {} },
            ...{ 'onError': {} },
            gameId: (__VLS_ctx.gameId),
            visible: (visible),
            strikerId: (__VLS_ctx.strikerId),
            nonStrikerId: (__VLS_ctx.nonStrikerId),
            bowlerId: (__VLS_ctx.bowlerId),
        }));
        const __VLS_17 = __VLS_16({
            ...{ 'onClose': {} },
            ...{ 'onScored': {} },
            ...{ 'onError': {} },
            gameId: (__VLS_ctx.gameId),
            visible: (visible),
            strikerId: (__VLS_ctx.strikerId),
            nonStrikerId: (__VLS_ctx.nonStrikerId),
            bowlerId: (__VLS_ctx.bowlerId),
        }, ...__VLS_functionalComponentArgsRest(__VLS_16));
        let __VLS_20;
        const __VLS_21 = ({ close: {} },
            { onClose: (close) });
        const __VLS_22 = ({ scored: {} },
            { onScored: (__VLS_ctx.onScored) });
        const __VLS_23 = ({ error: {} },
            { onError: (__VLS_ctx.onError) });
        var __VLS_18;
        var __VLS_19;
        // @ts-ignore
        [note, note, canScore, canScore, gameId, gameId, strikerId, strikerId, nonStrikerId, nonStrikerId, bowlerId, bowlerId, onScored, onScored, onError, onError,];
    }
    // @ts-ignore
    [];
    var __VLS_8;
    var __VLS_9;
}
const __VLS_24 = DismissalForm;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
    ...{ 'onScored': {} },
    ...{ 'onError': {} },
    gameId: (__VLS_ctx.gameId),
    strikerId: (__VLS_ctx.strikerId),
    nonStrikerId: (__VLS_ctx.nonStrikerId),
    bowlerId: (__VLS_ctx.bowlerId),
    canScore: (__VLS_ctx.canScore),
    battingPlayers: (__VLS_ctx.battingPlayers),
}));
const __VLS_26 = __VLS_25({
    ...{ 'onScored': {} },
    ...{ 'onError': {} },
    gameId: (__VLS_ctx.gameId),
    strikerId: (__VLS_ctx.strikerId),
    nonStrikerId: (__VLS_ctx.nonStrikerId),
    bowlerId: (__VLS_ctx.bowlerId),
    canScore: (__VLS_ctx.canScore),
    battingPlayers: (__VLS_ctx.battingPlayers),
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
let __VLS_29;
const __VLS_30 = ({ scored: {} },
    { onScored: (__VLS_ctx.onScored) });
const __VLS_31 = ({ error: {} },
    { onError: (__VLS_ctx.onError) });
var __VLS_27;
var __VLS_28;
if (__VLS_ctx.canScore) {
    const __VLS_32 = UndoLastBall;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent1(__VLS_32, new __VLS_32({
        gameId: (__VLS_ctx.gameId),
        disabled: (true),
        ...{ class: "mt" },
    }));
    const __VLS_34 = __VLS_33({
        gameId: (__VLS_ctx.gameId),
        disabled: (true),
        ...{ class: "mt" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    /** @type {__VLS_StyleScopedClasses['mt']} */ ;
}
if (import.__VLS_ctx.meta.env.DEV) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "debug-panel" },
    });
    /** @type {__VLS_StyleScopedClasses['debug-panel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.authStore.role);
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.authStore.isSuperuser);
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.authStore.canScore);
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.gameStore.canScore);
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.gameStore.currentStriker?.id ?? 'n/a');
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.gameStore.currentNonStriker?.id ?? 'n/a');
    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    (__VLS_ctx.gameStore.state?.current_bowler_id ?? 'n/a');
}
// @ts-ignore
[canScore, canScore, gameId, gameId, strikerId, nonStrikerId, bowlerId, onScored, onError, battingPlayers, meta, authStore, authStore, authStore, gameStore, gameStore, gameStore, gameStore,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
