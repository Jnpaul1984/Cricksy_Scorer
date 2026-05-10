/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { storeToRefs } from 'pinia';
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { BaseButton } from '@/components';
import { useGameStore } from '@/stores/gameStore';
const props = withDefaults(defineProps(), {
    canAction: true,
});
/* ============================================================================
   Store & Router
   ============================================================================ */
const router = useRouter();
const gameStore = useGameStore();
const { currentGame, state, battingRowsXI, bowlingRowsXI, liveSnapshot, currentPrediction, } = storeToRefs(gameStore);
/* ============================================================================
   Dialog State
   ============================================================================ */
const noteDialogOpen = ref(false);
const noteText = ref('');
/* ============================================================================
   Computed: Match Snapshot (Layer 1)
   ============================================================================ */
const isLive = computed(() => {
    const status = String(currentGame.value?.status || '').toUpperCase();
    return status === 'IN_PROGRESS' || status === 'LIVE';
});
const battingTeam = computed(() => currentGame.value?.batting_team_name || 'BAT');
const bowlingTeam = computed(() => currentGame.value?.bowling_team_name || 'BOWL');
const totalRuns = computed(() => currentGame.value?.total_runs ?? 0);
const totalWickets = computed(() => currentGame.value?.total_wickets ?? 0);
const oversDisplay = computed(() => {
    const oc = currentGame.value?.overs_completed ?? 0;
    const bto = currentGame.value?.balls_this_over ?? 0;
    return `${oc}.${bto}`;
});
const currentRunRate = computed(() => {
    const runs = totalRuns.value;
    const overs = Number(oversDisplay.value) || 0;
    if (overs === 0)
        return '—';
    const crr = (runs / overs).toFixed(2);
    return crr;
});
const target = computed(() => currentGame.value?.target ?? null);
/* ============================================================================
   Computed: Current Matchups (Layer 2)
   ============================================================================ */
const strikerBatting = computed(() => {
    const id = currentGame.value?.current_striker_id;
    if (!id || !currentGame.value?.batting_scorecard)
        return null;
    return currentGame.value.batting_scorecard[id];
});
const strikerName = computed(() => strikerBatting.value?.player_name || 'Striker');
const strikerRuns = computed(() => strikerBatting.value?.runs ?? 0);
const strikerBalls = computed(() => strikerBatting.value?.balls_faced ?? 0);
const strikerSR = computed(() => {
    const balls = strikerBalls.value;
    if (balls === 0)
        return '—';
    const sr = ((strikerRuns.value / balls) * 100).toFixed(1);
    return sr;
});
const nonStrikerBatting = computed(() => {
    const id = currentGame.value?.current_non_striker_id;
    if (!id || !currentGame.value?.batting_scorecard)
        return null;
    return currentGame.value.batting_scorecard[id];
});
const nonStrikerName = computed(() => nonStrikerBatting.value?.player_name || 'Non-Striker');
const nonStrikerRuns = computed(() => nonStrikerBatting.value?.runs ?? 0);
const nonStrikerBalls = computed(() => nonStrikerBatting.value?.balls_faced ?? 0);
const nonStrikerSR = computed(() => {
    const balls = nonStrikerBalls.value;
    if (balls === 0)
        return '—';
    const sr = ((nonStrikerRuns.value / balls) * 100).toFixed(1);
    return sr;
});
const bowlerBowling = computed(() => {
    const id = state.value?.current_bowler_id;
    if (!id || !currentGame.value?.bowling_scorecard)
        return null;
    return currentGame.value.bowling_scorecard[id];
});
const bowlerName = computed(() => bowlerBowling.value?.player_name || 'Bowler');
const bowlerOvers = computed(() => {
    const val = bowlerBowling.value?.overs_bowled ?? 0;
    const whole = Math.floor(val);
    const frac = Math.round((val - whole) * 10);
    return whole;
});
const bowlerRuns = computed(() => bowlerBowling.value?.runs_conceded ?? 0);
const bowlerWkts = computed(() => bowlerBowling.value?.wickets_taken ?? 0);
const bowlerEcon = computed(() => {
    // FIX B6: Use backend-calculated economy from bowling_scorecard
    // NO local calculation - backend handles overs→balls conversion correctly
    const bowlerId = state.value?.current_bowler_id;
    const bowler = gameStore.liveSnapshot?.bowling_scorecard?.[bowlerId];
    return bowler?.economy?.toFixed(2) ?? '—';
});
/* ============================================================================
   Computed: Momentum & Signals (Layer 3)
   ============================================================================ */
const lastSixBalls = computed(() => {
    // FIX A3: Use actual deliveries from liveSnapshot
    const deliveries = gameStore.liveSnapshot?.deliveries ?? [];
    const lastSix = deliveries.slice(-6);
    return lastSix.map((d) => {
        if (d.is_wicket)
            return 'W';
        if (d.runs_off_bat === 4)
            return '4';
        if (d.runs_off_bat === 6)
            return '6';
        if (!d.extra_type && d.runs_scored === 0)
            return '0';
        return String(d.runs_scored);
    });
});
const ballClass = (ball) => {
    if (!ball)
        return 'empty';
    if (ball === 'W')
        return 'wicket';
    if (ball === '4')
        return 'four';
    if (ball === '6')
        return 'six';
    if (ball === '0')
        return 'dot';
    return 'run';
};
const wicketsInHand = computed(() => {
    const max = 10;
    const out = totalWickets.value;
    return max - out;
});
const parRunRate = computed(() => {
    // FIX B5: Use liveSnapshot for real-time DLS par value
    const dls = gameStore.liveSnapshot?.dls;
    if (!dls || !dls.par)
        return null;
    return dls.par;
});
const parVsCRR = computed(() => {
    // FIX B5: Calculate par vs CRR using snapshot values only
    const snapshot = gameStore.liveSnapshot;
    if (!snapshot?.dls?.par || !snapshot?.current_run_rate)
        return null;
    const diff = snapshot.current_run_rate - snapshot.dls.par;
    return diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2);
});
const parComparison = computed(() => {
    if (!parVsCRR.value)
        return '';
    const diff = Number(parVsCRR.value);
    if (diff >= 0.5)
        return 'ahead';
    if (diff <= -0.5)
        return 'behind';
    return 'neutral';
});
const bowlerStatus = computed(() => {
    const econ = Number(bowlerEcon.value) || 0;
    // Simple heuristic: econ > 8 = under pressure, < 5 = good
    if (econ > 8)
        return 'under-pressure';
    if (econ < 5)
        return 'good';
    return 'neutral';
});
const bowlerStatusLabel = computed(() => {
    switch (bowlerStatus.value) {
        case 'good':
            return '✓ Good';
        case 'under-pressure':
            return '⚠ Pressure';
        default:
            return '○ Neutral';
    }
});
/* ============================================================================
   Actions
   ============================================================================ */
function openNoteDialog() {
    noteText.value = '';
    noteDialogOpen.value = true;
}
function saveNote() {
    console.log('[Coach] Note saved:', noteText.value);
    // TODO: Persist to backend or local storage
    noteDialogOpen.value = false;
    noteText.value = '';
}
function flagPlayer() {
    console.log('[Coach] TODO: Flag player for analysis');
    // TODO: Implement flag player workflow
}
function openAnalyst() {
    router.push({ name: 'AnalystWorkspace', params: { gameId: props.gameId } });
}
/* ============================================================================
   Lifecycle
   ============================================================================ */
onMounted(async () => {
    try {
        if (!currentGame.value || currentGame.value.id !== props.gameId) {
            await gameStore.loadGame(props.gameId);
        }
    }
    catch (err) {
        console.error('[LiveMatchCardCoach] Failed to load game:', err);
    }
});
const __VLS_defaults = {
    canAction: true,
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
/** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['par-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['par-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['par-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['neutral']} */ ;
/** @type {__VLS_StyleScopedClasses['layer-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['note-dialog']} */ ;
/** @type {__VLS_StyleScopedClasses['note-textarea']} */ ;
/** @type {__VLS_StyleScopedClasses['dialog-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coach-match-card" },
});
/** @type {__VLS_StyleScopedClasses['coach-match-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "layer-snapshot" },
});
/** @type {__VLS_StyleScopedClasses['layer-snapshot']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "snapshot-row" },
});
/** @type {__VLS_StyleScopedClasses['snapshot-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "teams-section" },
});
/** @type {__VLS_StyleScopedClasses['teams-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "team-name" },
});
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
(__VLS_ctx.battingTeam);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "vs-badge" },
});
/** @type {__VLS_StyleScopedClasses['vs-badge']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "team-name" },
});
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
(__VLS_ctx.bowlingTeam);
if (__VLS_ctx.isLive) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "live-badge" },
    });
    /** @type {__VLS_StyleScopedClasses['live-badge']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "snapshot-stats" },
});
/** @type {__VLS_StyleScopedClasses['snapshot-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-pill" },
});
/** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label" },
});
/** @type {__VLS_StyleScopedClasses['label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "value" },
});
/** @type {__VLS_StyleScopedClasses['value']} */ ;
(__VLS_ctx.totalRuns);
(__VLS_ctx.totalWickets);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-pill" },
});
/** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label" },
});
/** @type {__VLS_StyleScopedClasses['label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "value" },
});
/** @type {__VLS_StyleScopedClasses['value']} */ ;
(__VLS_ctx.oversDisplay);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-pill" },
});
/** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label" },
});
/** @type {__VLS_StyleScopedClasses['label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "value" },
});
/** @type {__VLS_StyleScopedClasses['value']} */ ;
(__VLS_ctx.currentRunRate);
if (__VLS_ctx.target) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-pill target-pill" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-pill']} */ ;
    /** @type {__VLS_StyleScopedClasses['target-pill']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "value" },
    });
    /** @type {__VLS_StyleScopedClasses['value']} */ ;
    (__VLS_ctx.target);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "layer-matchups" },
});
/** @type {__VLS_StyleScopedClasses['layer-matchups']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-box striker" },
});
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['striker']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-role" },
});
/** @type {__VLS_StyleScopedClasses['matchup-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-name" },
});
/** @type {__VLS_StyleScopedClasses['matchup-name']} */ ;
(__VLS_ctx.strikerName);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-stats" },
});
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
(__VLS_ctx.strikerRuns);
(__VLS_ctx.strikerBalls);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat sr" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['sr']} */ ;
(__VLS_ctx.strikerSR);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-box non-striker" },
});
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['non-striker']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-role" },
});
/** @type {__VLS_StyleScopedClasses['matchup-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-name" },
});
/** @type {__VLS_StyleScopedClasses['matchup-name']} */ ;
(__VLS_ctx.nonStrikerName);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-stats" },
});
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
(__VLS_ctx.nonStrikerRuns);
(__VLS_ctx.nonStrikerBalls);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat sr" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['sr']} */ ;
(__VLS_ctx.nonStrikerSR);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-box bowler" },
});
/** @type {__VLS_StyleScopedClasses['matchup-box']} */ ;
/** @type {__VLS_StyleScopedClasses['bowler']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-role" },
});
/** @type {__VLS_StyleScopedClasses['matchup-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-name" },
});
/** @type {__VLS_StyleScopedClasses['matchup-name']} */ ;
(__VLS_ctx.bowlerName);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "matchup-stats" },
});
/** @type {__VLS_StyleScopedClasses['matchup-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
(__VLS_ctx.bowlerOvers);
(__VLS_ctx.bowlerRuns);
(__VLS_ctx.bowlerWkts);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat econ" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['econ']} */ ;
(__VLS_ctx.bowlerEcon);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "layer-momentum" },
});
/** @type {__VLS_StyleScopedClasses['layer-momentum']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "momentum-row" },
});
/** @type {__VLS_StyleScopedClasses['momentum-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "momentum-section" },
});
/** @type {__VLS_StyleScopedClasses['momentum-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "section-label" },
});
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "balls-strip" },
});
/** @type {__VLS_StyleScopedClasses['balls-strip']} */ ;
for (const [ball, idx] of __VLS_vFor((__VLS_ctx.lastSixBalls))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (idx),
        ...{ class: (['ball-pill', __VLS_ctx.ballClass(ball)]) },
    });
    /** @type {__VLS_StyleScopedClasses['ball-pill']} */ ;
    (ball || '-');
    // @ts-ignore
    [battingTeam, bowlingTeam, isLive, totalRuns, totalWickets, oversDisplay, currentRunRate, target, target, strikerName, strikerRuns, strikerBalls, strikerSR, nonStrikerName, nonStrikerRuns, nonStrikerBalls, nonStrikerSR, bowlerName, bowlerOvers, bowlerRuns, bowlerWkts, bowlerEcon, lastSixBalls, ballClass,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "momentum-section" },
});
/** @type {__VLS_StyleScopedClasses['momentum-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "section-label" },
});
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "wkts-value" },
});
/** @type {__VLS_StyleScopedClasses['wkts-value']} */ ;
(__VLS_ctx.wicketsInHand);
if (__VLS_ctx.parRunRate) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "momentum-section" },
    });
    /** @type {__VLS_StyleScopedClasses['momentum-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "section-label" },
    });
    /** @type {__VLS_StyleScopedClasses['section-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: (['par-badge', __VLS_ctx.parComparison]) },
    });
    /** @type {__VLS_StyleScopedClasses['par-badge']} */ ;
    (__VLS_ctx.parVsCRR);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "momentum-section" },
});
/** @type {__VLS_StyleScopedClasses['momentum-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "section-label" },
});
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: (['status-badge', __VLS_ctx.bowlerStatus]) },
});
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
(__VLS_ctx.bowlerStatusLabel);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "layer-actions" },
});
/** @type {__VLS_StyleScopedClasses['layer-actions']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Add a tactical note about this moment",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Add a tactical note about this moment",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ click: {} },
    { onClick: (__VLS_ctx.openNoteDialog) });
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[wicketsInHand, parRunRate, parComparison, parVsCRR, bowlerStatus, bowlerStatusLabel, openNoteDialog,];
var __VLS_3;
var __VLS_4;
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Flag a player for analysis",
}));
const __VLS_10 = __VLS_9({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Flag a player for analysis",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ click: {} },
    { onClick: (__VLS_ctx.flagPlayer) });
const { default: __VLS_15 } = __VLS_11.slots;
// @ts-ignore
[flagPlayer,];
var __VLS_11;
var __VLS_12;
let __VLS_16;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Open detailed analyst view",
}));
const __VLS_18 = __VLS_17({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    title: "Open detailed analyst view",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_21;
const __VLS_22 = ({ click: {} },
    { onClick: (__VLS_ctx.openAnalyst) });
const { default: __VLS_23 } = __VLS_19.slots;
// @ts-ignore
[openAnalyst,];
var __VLS_19;
var __VLS_20;
if (__VLS_ctx.noteDialogOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.noteDialogOpen))
                    return;
                __VLS_ctx.noteDialogOpen = false;
                // @ts-ignore
                [noteDialogOpen, noteDialogOpen,];
            } },
        ...{ class: "note-dialog-backdrop" },
    });
    /** @type {__VLS_StyleScopedClasses['note-dialog-backdrop']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "note-dialog" },
    });
    /** @type {__VLS_StyleScopedClasses['note-dialog']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
        value: (__VLS_ctx.noteText),
        placeholder: "Jot down observations, tactics, or player notes...",
        ...{ class: "note-textarea" },
        rows: "4",
    });
    /** @type {__VLS_StyleScopedClasses['note-textarea']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dialog-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['dialog-actions']} */ ;
    let __VLS_24;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }));
    const __VLS_26 = __VLS_25({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    let __VLS_29;
    const __VLS_30 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!(__VLS_ctx.noteDialogOpen))
                    return;
                __VLS_ctx.noteDialogOpen = false;
                // @ts-ignore
                [noteDialogOpen, noteText,];
            } });
    const { default: __VLS_31 } = __VLS_27.slots;
    // @ts-ignore
    [];
    var __VLS_27;
    var __VLS_28;
    let __VLS_32;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent1(__VLS_32, new __VLS_32({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
    }));
    const __VLS_34 = __VLS_33({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    let __VLS_37;
    const __VLS_38 = ({ click: {} },
        { onClick: (__VLS_ctx.saveNote) });
    const { default: __VLS_39 } = __VLS_35.slots;
    // @ts-ignore
    [saveNote,];
    var __VLS_35;
    var __VLS_36;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
