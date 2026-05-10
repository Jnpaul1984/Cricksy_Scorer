/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
/* eslint-disable */
/*
 * QA CHECKLIST (beta/fix-extras-recentballs-correction-theme):
 * ✅ Recent Balls: Extras (WD/NB) should persist in last 6 even after next legal ball
 * ✅ Extras Tab: Totals should match backend snapshot (prefer liveSnapshot.extras_totals)
 * ✅ Field Map: Tap marker dot should NOT appear on zone clicks
 * ✅ Dark Theme: Scoring UI should use CSS variables, no hardcoded white/light colors
 * ✅ Zone Selection: recordZone() should still work for shot tracking
 * ✅ Ball Number: Clamped to 0-5 range to prevent invalid over states
 * ✅ Sorting: Timestamp comparison uses Date.parse() for ISO date strings
 */
/* --- Vue & Router --- */
/* --- Stores --- */
import { storeToRefs } from 'pinia';
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
/* --- UI Components --- */
import { BaseButton, BaseCard, BaseInput } from '@/components';
import BattingCard from '@/components/BattingCard.vue';
import BowlingCard from '@/components/BowlingCard.vue';
import DeliveryTable from '@/components/DeliveryTable.vue';
import DeliveryCorrectionModal from '@/components/DeliveryCorrectionModal.vue';
import EventLogTab from '@/components/EventLogTab.vue';
import WinProbabilityChart from '@/components/WinProbabilityChart.vue';
import InningsGradeWidget from '@/components/InningsGradeWidget.vue';
import PressureMapWidget from '@/components/PressureMapWidget.vue';
import PhaseTimelineWidget from '@/components/PhaseTimelineWidget.vue';
import { useRoleBadge } from '@/composables/useRoleBadge';
import { useInningsGrade } from '@/composables/useInningsGrade';
import { usePressureAnalytics } from '@/composables/usePressureAnalytics';
import { usePhaseAnalytics } from '@/composables/usePhaseAnalytics';
import { apiService } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
import legacyApiService, { API_BASE, apiRequest } from '@/utils/api';
const isDev = import.meta.env.DEV;
const normId = (v) => String(v ?? '').trim();
const extra = ref('none');
const offBat = ref(0);
const extraRuns = ref(1);
const isWicket = ref(false);
const dismissal = ref(null);
const dismissedName = ref(null);
const shotMap = ref(null);
const recordedZone = ref(null);
const recordZone = (zone) => {
    recordedZone.value = zone;
};
if (import.meta.env?.DEV) {
    console.info('GameScoringView setup refs', { isWicket, extra });
}
// ================== Event Log state ==================
// Events managed in Pinia store via gameStore
// --- Fielder (XI + subs) for wicket events ---
const selectedFielderId = ref('');
const inningsStartIso = ref(null);
// Does this dismissal type require a fielder?
const needsFielder = computed(() => {
    const t = (dismissal.value || '').toLowerCase();
    return t === 'caught' || t === 'run_out' || t === 'stumped';
});
// Mark which ids belong to the XI so we can label subs in the dropdown
const bowlingXIIds = computed(() => new Set(bowlingRosterXI.value.map(p => p.id)));
// Reset fielder when wicket toggled off / dismissal changes to a non-fielder type
watch(isWicket, (on) => {
    if (!on) {
        dismissal.value = null;
        selectedFielderId.value = '';
    }
});
watch(dismissal, (t) => {
    if (!needsFielder.value)
        selectedFielderId.value = '';
});
watch(extra, (t) => {
    if (t === 'wd') {
        extraRuns.value = 1;
        offBat.value = 0;
    }
    else if (t === 'b' || t === 'lb') {
        extraRuns.value = 0;
        offBat.value = 0;
    }
    else if (t === 'none') {
        offBat.value = 0;
    }
    if (t !== 'none' && t !== 'nb') {
        shotMap.value = null;
    }
});
// [REMOVED tapMarker and handleMapClick - field tap feedback not needed]
const route = useRoute();
const router = useRouter();
const gameStore = useGameStore();
const authStore = useAuthStore();
const { grade: currentInningsGrade, fetchCurrentGrade: fetchCurrentInningsGrade } = useInningsGrade();
const { pressureData, fetchPressureMap, loading: pressureLoading } = usePressureAnalytics();
const { phaseData, predictions, fetchPhaseMap, fetchPredictions, loading: phaseLoading } = usePhaseAnalytics();
// Captain/Keeper badge composable
const currentGame = computed(() => gameStore.currentGame);
const teamAName = computed(() => String(currentGame.value?.team_a?.name ?? ''));
// Derive batting team name from liveSnapshot (updates on innings change)
const battingTeamName = computed(() => {
    const g = currentGame.value;
    if (!g)
        return '';
    // Use liveSnapshot's batting_team_name if available, otherwise fall back to game's
    const snap = liveSnapshot.value;
    return snap?.batting_team_name ?? g.batting_team_name ?? '';
});
const isBattingTeamA = computed(() => battingTeamName.value === teamAName.value);
const { roleBadge, bowlerRoleBadge } = useRoleBadge({ currentGame, isBattingTeamA });
// Reactive refs from the stores
const { liveSnapshot } = storeToRefs(gameStore);
const { needsNewBatter, needsNewOver } = storeToRefs(gameStore);
const { extrasBreakdown } = storeToRefs(gameStore);
const { dlsKind } = storeToRefs(gameStore);
const { runsRequired, targetSafe, requiredRunRate, ballsBowledTotal } = storeToRefs(gameStore);
const { canScore: roleCanScore, isFreeUser, isPlayerPro, role: authRole, } = storeToRefs(authStore);
const storeCanScore = computed(() => {
    if ('canScore' in gameStore) {
        // @ts-ignore  using store getter
        return gameStore.canScore;
    }
    if ('canScoreDelivery' in gameStore) {
        // @ts-ignore  using store getter
        return gameStore.canScoreDelivery;
    }
    return true;
});
const canScore = computed(() => Boolean(storeCanScore.value && roleCanScore.value));
// Header score display: prefer liveSnapshot, fall back to store score (helps tests and early UI)
const headerRuns = computed(() => {
    const snap = liveSnapshot.value;
    const storeScore = gameStore?.score;
    return snap?.total_runs ?? snap?.batting_team_score ?? storeScore?.runs ?? 0;
});
const headerWickets = computed(() => {
    const snap = liveSnapshot.value;
    const storeScore = gameStore?.score;
    return snap?.total_wickets ?? snap?.batting_team_wickets ?? storeScore?.wickets ?? 0;
});
const headerOvers = computed(() => {
    const snap = liveSnapshot.value;
    const storeScore = gameStore?.score;
    // Format overs as "X.Y" from overs_completed and balls_this_over
    const overs = snap?.overs_completed ?? 0;
    const balls = snap?.balls_this_over ?? 0;
    const oversDisplay = `${overs}.${balls}`;
    return snap?.batting_team_overs ?? oversDisplay ?? storeScore?.overs ?? '0.0';
});
const proTooltip = 'Requires Coach Pro or Organization Pro';
const showScoringUpsell = computed(() => !roleCanScore.value && (!authRole.value || isFreeUser.value || isPlayerPro.value));
const showAnalystReadOnly = computed(() => !roleCanScore.value && authRole.value === 'analyst_pro');
// Allow a manual start even if the server gate didn't flip yet
const canForceStartInnings = computed(() => Boolean(gameId.value) &&
    !isStartingInnings.value &&
    pendingCount.value === 0);
function forceStartInnings() {
    if (!roleCanScore.value)
        return;
    if (!canForceStartInnings.value)
        return;
    // If the normal conditions aren't met, warn before proceeding
    const safeToStart = needsNewInningsLive.value || allOut.value || oversExhausted.value;
    if (!safeToStart) {
        const ok = window.confirm('It looks like the current innings may not be finished yet.\n\nStart the next innings anyway?');
        if (!ok)
            return;
    }
    // Reuse the same picker modal for openers & (optional) opening bowler
    openStartInnings();
}
// Current gameId (param or ?id=)
const gameId = computed(() => route.params.gameId || route.query.id || '');
// Watch for gameId changes and fetch innings grade, pressure map, & phase data
watch(gameId, async (id) => {
    if (id) {
        try {
            // Get current inning number from game state (default to 1)
            const currentInning = currentGame.value?.current_inning || 1;
            await fetchCurrentInningsGrade(id); // Function only accepts gameId
            await fetchPressureMap(id, currentInning);
            await fetchPhaseMap(id, currentInning);
            await fetchPredictions(id);
            // Manually fetch win probability prediction to populate initial state
            // (predictions are normally only emitted via Socket.IO after deliveries)
            try {
                const predictionResponse = await fetch(`http://localhost:8000/games/${id}/snapshot`);
                const snapshotData = await predictionResponse.json();
                // Update liveSnapshot so CRR and other stats display correctly
                gameStore.liveSnapshot = snapshotData;
                if (snapshotData.prediction) {
                    gameStore.currentPrediction = snapshotData.prediction;
                }
            }
            catch {
                // Silently ignore - predictions will come via Socket.IO after next delivery
            }
        }
        catch (err) {
            // Silently handle - analytics features may not be fully implemented yet
        }
    }
}, { immediate: true });
// --- UI State for UX Improvements ---
const isSubmitting = ref(false);
// [REMOVED tapMarker] Field tap feedback not needed - zone selection still works via recordZone()
// --- Delivery Correction State ---
const showCorrectionModal = ref(false);
const correctionDelivery = ref(null);
function openCorrectionModal(delivery) {
    correctionDelivery.value = delivery;
    showCorrectionModal.value = true;
}
function closeCorrectionModal() {
    showCorrectionModal.value = false;
    correctionDelivery.value = null;
}
async function submitCorrection({ deliveryId, correction }) {
    if (!gameId.value)
        return;
    try {
        const snapshot = await apiService.correctDelivery(gameId.value, deliveryId, correction);
        // Update store with corrected snapshot
        if (snapshot) {
            gameStore.liveSnapshot = snapshot;
        }
        closeCorrectionModal();
    }
    catch (err) {
        console.error('Failed to correct delivery:', err);
        alert(err?.message || 'Failed to correct delivery');
    }
}
function getBallClass(b) {
    if (b.is_wicket)
        return 'is-wicket';
    if (b.runs_scored === 6)
        return 'is-6';
    if (b.runs_scored === 4)
        return 'is-4';
    if (b.extra)
        return 'is-extra';
    if (b.runs_scored === 0)
        return 'is-dot';
    return 'is-run';
}
function getBallLabel(b) {
    if (b.is_wicket)
        return 'W';
    if (b.extra === 'wd')
        return 'WD';
    if (b.extra === 'nb')
        return 'NB';
    if (b.extra === 'b')
        return 'B';
    if (b.extra === 'lb')
        return 'LB';
    return b.runs_scored;
}
const canSubmitSimple = computed(() => {
    if (!canScore.value)
        return false;
    const firstBall = Number(currentOverBalls.value || 0) === 0;
    if (!gameId.value || needsNewBatterLive.value)
        return false;
    // Allow submit if it's the first ball and a bowler is chosen
    if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value))
        return false;
    if (!selectedStriker.value || !selectedNonStriker.value || !selectedBowler.value)
        return false;
    if (needsNewInningsLive.value)
        return false;
    if (isStartingInnings.value)
        return false;
    // If it's a wicket that needs a fielder, require one
    if (isWicket.value && needsFielder.value && !selectedFielderId.value)
        return false;
    if (extra.value === 'nb')
        return offBat.value >= 0;
    if (extra.value === 'wd')
        return extraRuns.value >= 1;
    if (extra.value === 'b' || extra.value === 'lb')
        return extraRuns.value >= 0;
    return offBat.value >= 0; // legal
});
async function submitSimple() {
    if (isSubmitting.value)
        return;
    if (!canScore.value)
        return;
    const firstBall = Number(currentOverBalls.value || 0) === 0;
    if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) {
        openStartOver();
        onError('Start the next over first');
        return;
    }
    if (needsNewBatterLive.value) {
        openSelectBatter();
        onError('Select the next batter first');
        return;
    }
    isSubmitting.value = true;
    try {
        const anyStore = gameStore;
        const unifiedPossible = typeof anyStore.scoreDelivery === 'function';
        if (unifiedPossible) {
            const payload = {};
            if (extra.value === 'wd') {
                payload.extra_type = 'wd';
                payload.extra_runs = extraRuns.value;
            }
            else if (extra.value === 'nb') {
                payload.extra_type = 'nb';
                payload.runs_off_bat = offBat.value;
            }
            else if (extra.value === 'b' || extra.value === 'lb') {
                payload.extra_type = extra.value;
                payload.extra_runs = extraRuns.value;
            }
            else {
                payload.runs_off_bat = offBat.value;
            }
            payload.shot_map = (extra.value === 'none' || extra.value === 'nb') ? (shotMap.value ?? null) : null;
            if (isWicket.value) {
                payload.is_wicket = true;
                payload.dismissal_type = (dismissal.value || 'bowled');
                payload.dismissed_player_name = (dismissedName.value || null);
                payload.fielder_id = needsFielder.value ? (selectedFielderId.value || null) : null;
            }
            await anyStore.scoreDelivery(gameId.value, payload);
        }
        else {
            if (isWicket.value && extra.value === 'none') {
                await gameStore.scoreWicket(gameId.value, (dismissal.value || 'bowled'), undefined, undefined, (needsFielder.value ? (selectedFielderId.value || undefined) : undefined));
            }
            else if (!isWicket.value && extra.value === 'nb') {
                await gameStore.scoreExtra(gameId.value, 'nb', offBat.value, shotMap.value ?? null);
            }
            else if (!isWicket.value && extra.value === 'wd') {
                await gameStore.scoreExtra(gameId.value, 'wd', extraRuns.value);
            }
            else if (!isWicket.value && (extra.value === 'b' || extra.value === 'lb')) {
                await gameStore.scoreExtra(gameId.value, extra.value, extraRuns.value);
            }
            else if (!isWicket.value && extra.value === 'none') {
                await gameStore.scoreRuns(gameId.value, offBat.value, shotMap.value ?? null);
            }
            else {
                const payload = {
                    extra_type: extra.value !== 'none' ? extra.value : null,
                    extra_runs: extra.value === 'wd'
                        ? extraRuns.value
                        : (extra.value === 'b' || extra.value === 'lb')
                            ? extraRuns.value
                            : undefined,
                    runs_off_bat: extra.value === 'nb'
                        ? offBat.value
                        : extra.value === 'none'
                            ? offBat.value
                            : undefined,
                    is_wicket: true,
                    dismissal_type: (dismissal.value || 'bowled'),
                    dismissed_player_name: (dismissedName.value || null),
                    shot_map: (extra.value === 'none' || extra.value === 'nb') ? (shotMap.value ?? null) : null,
                    fielder_id: needsFielder.value ? (selectedFielderId.value || null) : null,
                };
                await apiRequest(`/games/${encodeURIComponent(gameId.value)}/deliveries`, {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
            }
        }
        extra.value = 'none';
        offBat.value = 0;
        extraRuns.value = 1;
        isWicket.value = false;
        dismissal.value = null;
        dismissedName.value = null;
        selectedFielderId.value = '';
        shotMap.value = null;
        onScored();
        await nextTick();
        maybeRotateFromLastDelivery();
    }
    catch (e) {
        onError(e?.message || 'Scoring failed');
    }
    finally {
        setTimeout(() => { isSubmitting.value = false; }, 400);
    }
}
// --- Delete last delivery ------------------------------
const deletingLast = ref(false);
const lastDelivery = computed(() => {
    // FIX B7: Use backend last_delivery from liveSnapshot (primary source)
    // Backend provides correct over/ball numbers, no local calculation needed
    return gameStore.liveSnapshot?.last_delivery ?? null;
});
// Block when: there is no ball yet, an innings gate is up, or you still have queued actions
const canDeleteLast = computed(() => Boolean(lastDelivery.value) &&
    !needsNewInningsLive.value &&
    !isStartingInnings.value && // â† add this guard
    pendingCount.value === 0);
async function deleteLastDelivery() {
    const id = gameId.value;
    if (!id || !canDeleteLast.value || deletingLast.value)
        return;
    deletingLast.value = true;
    try {
        const anyStore = gameStore;
        if (typeof anyStore.deleteLastDelivery === 'function') {
            await anyStore.deleteLastDelivery(id);
        }
        else if (typeof anyStore.undoLastDelivery === 'function') {
            await anyStore.undoLastDelivery(id);
        }
        else {
            await legacyApiService.undoLast(id);
        }
        showToast('Last delivery deleted', 'success');
        // Ensure local UI refreshes even if the socket message arrives slowly
        await gameStore.loadGame(id);
    }
    catch (e) {
        onError(e?.message || 'Failed to delete last delivery');
    }
    finally {
        deletingLast.value = false;
    }
}
// --- DLS panel state ---
const G50 = ref(245);
const dls = computed(() => gameStore.dlsPreview);
const canShowDls = computed(() => Boolean(gameId.value) && !!gameStore.currentGame?.dls_enabled);
const loadingDls = ref(false);
const applyingDls = ref(false);
async function refreshDls() {
    if (!gameId.value)
        return;
    loadingDls.value = true;
    try {
        await gameStore.fetchDlsPreview(gameId.value, G50.value);
    }
    catch (e) {
        onError(e?.message || 'DLS preview failed');
    }
    finally {
        loadingDls.value = false;
    }
}
async function applyDls() {
    if (!gameId.value)
        return;
    applyingDls.value = true;
    try {
        await gameStore.applyDls(gameId.value, G50.value);
        onScored();
    }
    catch (e) {
        onError(e?.message || 'Apply DLS failed');
    }
    finally {
        applyingDls.value = false;
    }
}
// --- Reduce Overs & Live Par ---
const oversLimit = computed(() => Number(gameStore.currentGame?.overs_limit ?? 0));
const currentInnings = computed(() => Number(gameStore.currentGame?.current_inning ?? 1));
// Balls & overs remaining in the chase (defensive if not a chase or no limit)
const ballsRemaining = computed(() => {
    // FIX B4: Use backend-calculated balls_remaining from snapshot
    // NO local calculation - backend handles extras/illegal balls correctly
    return gameStore.liveSnapshot?.balls_remaining ?? 0;
});
const oversRemainingDisplay = computed(() => {
    const balls = ballsRemaining.value;
    const ov = Math.floor(balls / 6);
    const rem = balls % 6;
    return `${ov}.${rem}`;
});
const reduceScope = ref('match');
const reduceInnings = ref(currentInnings.value);
const oversNew = ref(null);
const reducingOvers = ref(false);
const computingPar = ref(false);
// --- Optional "Fielding subs" management card ---
const showSubsCard = ref(false);
const SUBS_CARD_KEY = 'cricksy.ui.showSubsCard';
onMounted(() => {
    try {
        const saved = localStorage.getItem(SUBS_CARD_KEY);
        if (saved != null)
            showSubsCard.value = saved === '1';
    }
    catch { }
});
watch(showSubsCard, (v) => {
    try {
        localStorage.setItem(SUBS_CARD_KEY, v ? '1' : '0');
    }
    catch { }
});
const canReduce = computed(() => oversNew.value != null && oversNew.value > 0);
async function doReduceOvers() {
    if (!gameId.value || !canReduce.value)
        return;
    reducingOvers.value = true;
    try {
        if (reduceScope.value === 'innings') {
            await gameStore.reduceOversForInnings(gameId.value, reduceInnings.value, oversNew.value);
        }
        else {
            await gameStore.reduceOvers(gameId.value, oversNew.value);
        }
        showToast('Overs limit updated', 'success');
        try {
            await refreshDls();
        }
        catch { }
    }
    catch (e) {
        onError(e?.message || 'Failed to reduce overs');
    }
    finally {
        reducingOvers.value = false;
    }
}
async function updateParNow() {
    if (!gameId.value)
        return;
    computingPar.value = true;
    try {
        await gameStore.dlsParNow(gameId.value, dlsKind.value, currentInnings.value);
        showToast('Par updated', 'success');
    }
    catch (e) {
        onError(e?.message || 'Par calc failed');
    }
    finally {
        computingPar.value = false;
    }
}
// prime input with current limit when game loads
watch(() => oversLimit.value, (v) => { if (v && !oversNew.value)
    oversNew.value = v; });
// --- Match controls: Weather + Reduce Overs quick actions ---
const weatherDlgOpen = ref(false);
const weatherNote = ref('');
function openWeather() { weatherDlgOpen.value = true; }
function closeWeather() { weatherDlgOpen.value = false; }
const apiBase = (API_BASE || (typeof window !== 'undefined' ? window.location.origin : '')).replace(/\/$/, '');
// Store is the single writer; no manual refresh calls here.
async function startWeatherDelay() {
    const id = gameId.value;
    if (!id)
        return;
    if (!roleCanScore.value)
        return;
    try {
        await gameStore.startInterruption('weather', weatherNote.value || undefined);
        showToast('Weather delay started', 'success');
        closeWeather();
        await nextTick();
    }
    catch (e) {
        onError(e?.message || 'Failed to start interruption');
    }
}
async function resumeAfterWeather() {
    const id = gameId.value;
    if (!id)
        return;
    if (!roleCanScore.value)
        return;
    try {
        await gameStore.stopInterruption('weather');
        showToast('Play resumed', 'success');
        closeWeather();
        await nextTick();
    }
    catch (e) {
        onError(e?.message || 'Failed to resume');
    }
}
// Smooth jump to the existing "Reduce Overs" card
const reduceOversCardRef = ref(null);
function jumpToReduceOvers() {
    reduceOversCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
const XI_KEY = (id) => `cricksy.xi.${id}`;
const xiA = ref(null);
const xiB = ref(null);
const xiLoaded = ref(false);
function loadXIForGame(id) {
    xiA.value = xiB.value = null;
    xiLoaded.value = false;
    try {
        const raw = localStorage.getItem(XI_KEY(id));
        if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed.team_a_xi))
                xiA.value = new Set(parsed.team_a_xi);
            if (Array.isArray(parsed.team_b_xi))
                xiB.value = new Set(parsed.team_b_xi);
        }
    }
    catch { /* ignore */ }
    xiLoaded.value = true;
}
// ================== SELECTION STATE ==================
const selectedStriker = computed({
    get: () => (gameStore.uiState.selectedStrikerId || ''),
    set: (v) => gameStore.setSelectedStriker(normId(v) || null),
});
const selectedNonStriker = computed({
    get: () => (gameStore.uiState.selectedNonStrikerId || ''),
    set: (v) => gameStore.setSelectedNonStriker(normId(v) || null),
});
const selectedBowler = computed({
    get: () => (gameStore.uiState.selectedBowlerId || ''),
    set: (v) => gameStore.setSelectedBowler(normId(v) || null),
});
// Last 6 balls for the center strip
const last6Balls = computed(() => {
    // deliveriesThisInnings is sorted by over/ball ascending (oldest -> newest)
    // We want the last 6, but displayed left-to-right as oldest-of-the-6 -> newest
    const all = deliveriesThisInnings.value || [];
    return all.slice(-6);
});
const recentBallSlots = computed(() => {
    const filled = last6Balls.value;
    const emptyCount = 6 - filled.length;
    const empty = new Array(Math.max(0, emptyCount)).fill(null);
    return [...filled, ...empty];
});
// ================== CONNECTION / OFFLINE QUEUE ==================
const liveReady = computed(() => gameStore.connectionStatus === 'connected');
const pendingForThisGame = computed(() => gameStore.offlineQueue.filter(q => q.gameId === gameId.value && q.status !== 'flushing'));
const pendingCount = computed(() => pendingForThisGame.value.length);
// ================== ROSTERS (FILTERED BY XI) ==================
// Names for status text
const selectedStrikerName = computed(() => battingPlayers.value.find((p) => p.id === selectedStriker.value)?.name || '');
const selectedNonStrikerName = computed(() => battingPlayers.value.find((p) => p.id === selectedNonStriker.value)?.name || '');
const selectedBowlerName = computed(() => bowlingPlayers.value.find((p) => p.id === selectedBowler.value)?.name || '');
// Dismissed dropdown: limit to current batters to avoid ambiguity
const dismissedOptions = computed(() => {
    const list = battingPlayers.value;
    const s = list.find(p => p.id === selectedStriker.value);
    const ns = list.find(p => p.id === selectedNonStriker.value);
    const out = [];
    if (s)
        out.push(s);
    if (ns && (!s || ns.id !== s.id))
        out.push(ns);
    return out;
});
watch([isWicket, selectedStriker, selectedNonStriker], () => {
    if (isWicket.value && !dismissedName.value && dismissedOptions.value.length > 0) {
        dismissedName.value = dismissedOptions.value[0].name;
    }
});
const { battingRosterXI, bowlingRosterXI, battingRowsXI, // NEW: stat rows for current batting XI
bowlingRowsXI, // NEW: stat rows for current bowling XI
fieldingSubs, fielderRosterAll, } = storeToRefs(gameStore);
// selectors:
const battingPlayers = computed(() => battingRosterXI.value);
const bowlingPlayers = computed(() => bowlingRosterXI.value);
const fielderOptions = computed(() => [
    ...bowlingRosterXI.value, // XI
    ...fieldingSubs.value, // subs
]);
const nextBattingXI = computed(() => {
    if (needsNewInningsLive.value) {
        const isInnings1Break = currentInnings.value === 1 && ballsBowledTotal.value > 0;
        return isInnings1Break ? bowlingRosterXI.value : battingRosterXI.value;
    }
    return battingRosterXI.value;
});
const nextBowlingXI = computed(() => {
    if (needsNewInningsLive.value) {
        const isInnings1Break = currentInnings.value === 1 && ballsBowledTotal.value > 0;
        return isInnings1Break ? battingRosterXI.value : bowlingRosterXI.value;
    }
    return bowlingRosterXI.value;
});
// ================== SCORECARDS (from store) ==================
// Preferred order from the store if available
const storeBattingOrderIds = computed(() => {
    const ids = stateAny.value?.batting_order_ids ||
        gameStore.currentGame?.batting_order_ids;
    return Array.isArray(ids) ? ids.map(normId) : null;
});
// Fallback: infer order from first appearance **in this innings** only
const battingAppearanceOrder = computed(() => {
    if (storeBattingOrderIds.value && storeBattingOrderIds.value.length)
        return storeBattingOrderIds.value;
    const seen = new Set();
    const order = [];
    for (const d of deliveriesThisInnings.value) {
        for (const id of [d.striker_id, d.non_striker_id]) {
            const nid = normId(id);
            if (nid && !seen.has(nid)) {
                seen.add(nid);
                order.push(nid);
            }
        }
    }
    return order;
});
const battingEntries = computed(() => {
    const rows = (battingRowsXI.value || []).map((r) => ({
        player_id: r.id,
        player_name: String(r.name),
        runs: Number(r.runs),
        balls_faced: Number(r.balls),
        fours: Number(r.fours),
        sixes: Number(r.sixes),
        strike_rate: Number(r.sr),
        how_out: r.howOut,
        is_out: Boolean(r.isOut),
        // optional: if your row has a batting position/index, keep it for tie-breaks
        _pos: typeof r.pos === 'number' ? r.pos : undefined
    }));
    const order = battingAppearanceOrder.value;
    const rank = new Map(order.map((id, i) => [id, i]));
    rows.sort((a, b) => {
        const ra = rank.get(normId(a.player_id)) ?? 9999;
        const rb = rank.get(normId(b.player_id)) ?? 9999;
        if (ra !== rb)
            return ra - rb;
        // tie-breaker: explicit position if present
        if (a._pos != null && b._pos != null)
            return a._pos - b._pos;
        return String(a.player_name).localeCompare(String(b.player_name));
    });
    return rows;
});
const bowlingEntries = computed(() => (bowlingRowsXI.value || []).map((r) => {
    const pid = String(r.id);
    const derived = bowlingDerivedByPlayer.value[pid];
    const balls = derived ? derived.balls : 0;
    const runsToBowler = derived ? derived.runs : Number(r.runs ?? r.runs_conceded ?? 0);
    const maidens = derived ? derived.maidens : Number(r.maidens ?? 0);
    const oversTxt = balls ? oversDisplayFromBalls(balls) : String(r.overs ?? r.overs_bowled ?? '0.0');
    const econTxt = balls ? econ(runsToBowler, balls) : (typeof r.econ === 'number' ? r.econ.toFixed(2) : (Number(r.econ || 0)).toFixed(2));
    return {
        player_id: pid,
        player_name: String(r.name),
        overs_bowled: oversTxt,
        maidens,
        runs_conceded: runsToBowler,
        wickets_taken: Number(r.wkts ?? r.wickets_taken ?? 0),
        economy: Number(econTxt),
    };
}));
// ================== Deliveries (CHRONOLOGICAL - NO DEDUP) ==================
// ✅ FIX: Treat deliveries as event stream - extras are separate events
// ✅ Order by backend delivery ID (if present), else timestamp, else array order
// ✅ Do NOT deduplicate by over:ball - wide at 3.0 and legal at 3.1 are DIFFERENT
function parseOverBall(overLike, ballLike) {
    // ✅ HARDENED: Clamp ball to 0-5 for all formats to prevent invalid ball numbers
    if (typeof ballLike === 'number') {
        return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: Math.max(0, Math.min(5, ballLike)) };
    }
    if (typeof overLike === 'string') {
        const [o, b] = overLike.split('.');
        return { over: Number(o) || 0, ball: Math.max(0, Math.min(5, Number(b) || 0)) };
    }
    if (typeof overLike === 'number') {
        const over = Math.floor(overLike);
        const ball = Math.max(0, Math.min(5, Math.round((overLike - over) * 10)));
        return { over, ball };
    }
    return { over: 0, ball: 0 };
}
const rawDeliveries = computed(() => {
    const g = gameStore.currentGame;
    return Array.isArray(g?.deliveries) ? g.deliveries : [];
});
// ðŸ”§ NEW: helpers to scope deliveries to the current innings
function inningsOf(d) {
    const v = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number);
    return Number.isFinite(v) ? v : null;
}
const deliveriesThisInningsRaw = computed(() => {
    const cur = currentInnings.value;
    const arr = rawDeliveries.value;
    const hasInnings = arr.some(d => inningsOf(d) != null);
    if (hasInnings)
        return arr.filter(d => inningsOf(d) === cur);
    // Fallback only if absolutely no innings markers exist (old data)
    if (cur === 1)
        return arr;
    if (inningsStartIso.value) {
        // strict: only include items with a timestamp after start
        return arr.filter(d => d.at_utc && String(d.at_utc) >= inningsStartIso.value);
    }
    return []; // no markers, no timestamps â€” donâ€™t risk mixing innings
});
const deliveriesThisInnings = computed(() => {
    // ✅ NO deduplication - keep ALL delivery events in chronological order
    // Sort by: 1) delivery.id (backend PK), 2) at_utc timestamp, 3) over/ball
    const raw = deliveriesThisInningsRaw.value;
    const mapped = raw.map((d, index) => {
        const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball);
        return {
            _delivery_id: d.id ?? d.delivery_id ?? null,
            _timestamp: d.at_utc ?? d.created_at ?? null,
            _index: index,
            over_number: over,
            ball_number: ball,
            runs_scored: Number(d.runs_scored ?? d.runs) || 0,
            striker_id: normId(d.striker_id),
            non_striker_id: normId(d.non_striker_id),
            bowler_id: normId(d.bowler_id),
            extra: (d.extra ?? d.extra_type ?? undefined),
            extra_runs: Number(d.extra_runs ?? 0),
            runs_off_bat: Number(d.runs_off_bat ?? d.runs ?? 0),
            is_wicket: Boolean(d.is_wicket),
            commentary: d.commentary,
            dismissed_player_id: (d.dismissed_player_id ? normId(d.dismissed_player_id) : null),
            at_utc: d.at_utc,
            shot_map: typeof d.shot_map === 'string' ? d.shot_map : null,
        };
    });
    // Sort by delivery ID > timestamp > over/ball > insertion order
    mapped.sort((a, b) => {
        if (a._delivery_id != null && b._delivery_id != null) {
            return a._delivery_id - b._delivery_id;
        }
        if (a._timestamp && b._timestamp) {
            // ✅ HARDENED: Use Date.parse for valid ISO timestamps, fallback to string compare
            const aTime = Date.parse(a._timestamp);
            const bTime = Date.parse(b._timestamp);
            if (!isNaN(aTime) && !isNaN(bTime)) {
                return aTime - bTime;
            }
            return a._timestamp < b._timestamp ? -1 : a._timestamp > b._timestamp ? 1 : 0;
        }
        const overDiff = a.over_number - b.over_number;
        if (overDiff !== 0)
            return overDiff;
        const ballDiff = a.ball_number - b.ball_number;
        if (ballDiff !== 0)
            return ballDiff;
        return a._index - b._index;
    });
    return mapped;
});
// == Derived bowling figures from deliveries in *this innings* ==
const bowlingDerivedByPlayer = computed(() => {
    const out = {};
    // group per over for maiden detection
    const overRuns = {};
    const add = (pid) => (out[pid] ||= { balls: 0, runs: 0, maidens: 0 });
    for (const d of deliveriesThisInnings.value) {
        const pid = String(d.bowler_id || '');
        if (!pid)
            continue;
        const rec = add(pid);
        // Runs conceded to bowler
        if (d.extra === 'wd') {
            rec.runs += Number(d.extra_runs || 0); // wides: all wides to bowler
        }
        else if (d.extra === 'nb') {
            rec.runs += 1 + Number(d.runs_off_bat || 0); // no-ball: 1 penalty + off-bat
            // ball does NOT count
        }
        else if (d.extra === 'b' || d.extra === 'lb') {
            // byes/leg-byes: NO runs to bowler, but DO consume a ball
            rec.balls += 1;
        }
        else {
            // legal: off-bat runs to bowler, consumes a ball
            rec.runs += Number(d.runs_off_bat ?? d.runs_scored ?? 0);
            rec.balls += 1;
        }
        // Track runs in the *over* to compute maidens later (legal extras still count to over total)
        const overKey = `${d.bowler_id}:${d.over_number}`;
        let totalThisBall = 0;
        if (d.extra === 'wd')
            totalThisBall = Number(d.extra_runs || 0);
        else if (d.extra === 'nb')
            totalThisBall = 1 + Number(d.runs_off_bat || 0);
        else if (d.extra === 'b' || d.extra === 'lb')
            totalThisBall = Number(d.runs_scored || d.extra_runs || 0);
        else
            totalThisBall = Number(d.runs_off_bat ?? d.runs_scored ?? 0);
        overRuns[overKey] = (overRuns[overKey] || 0) + totalThisBall;
    }
    // Maidens: any completed over with 0 runs
    for (const key of Object.keys(overRuns)) {
        const [pid, overStr] = key.split(':');
        const over = Number(overStr);
        // count legal balls in that over
        const legalBallsInOver = deliveriesThisInnings.value.filter(d => String(d.bowler_id) === pid &&
            d.over_number === over &&
            (d.extra !== 'wd' && d.extra !== 'nb')).length;
        if (legalBallsInOver === 6 && overRuns[key] === 0) {
            add(pid).maidens += 1;
        }
    }
    return out;
});
// === Current bowler figures (match the scorecardâ€™s logic) ====================
const currentBowlerDerived = computed(() => {
    const id = currentBowlerId.value;
    if (!id)
        return null;
    // Derived balls/runs/maidens for this innings
    const base = bowlingDerivedByPlayer.value[id];
    // Get wickets from the live XI rows (authoritative wicket tally)
    const r = (bowlingRowsXI.value || []).find((p) => String(p.id) === String(id));
    const wkts = Number(r?.wkts ?? r?.wickets_taken ?? 0);
    const balls = Number(base?.balls || 0);
    const runs = Number(base?.runs || 0);
    return {
        wkts,
        runs,
        balls,
        oversText: oversDisplayFromBalls(balls),
        econText: econ(runs, balls),
    };
});
// Name lookup for DeliveryTable
function playerNameById(id) {
    const nid = normId(id);
    if (!nid)
        return '';
    const g = gameStore.currentGame;
    if (!g)
        return '';
    return (g.team_a.players.find(p => normId(p.id) === nid)?.name ??
        g.team_b.players.find(p => normId(p.id) === nid)?.name ??
        '');
}
// ================== Helpers: SR and Economy (local) ==================
function oversDisplayFromBalls(balls) {
    const ov = Math.floor(balls / 6);
    const rem = balls % 6;
    return `${ov}.${rem}`;
}
function econ(runsConceded, ballsBowled) {
    if (!ballsBowled)
        return 'â€”';
    const overs = ballsBowled / 6;
    return (runsConceded / overs).toFixed(2);
}
const cantScoreReasons = computed(() => {
    const rs = [];
    if (!roleCanScore.value)
        rs.push(proTooltip);
    const firstBall = Number(currentOverBalls.value || 0) === 0;
    if (!gameStore.currentGame)
        rs.push('No game loaded');
    else {
        const status = String(gameStore.currentGame.status || '').toLowerCase();
        if (!['in_progress', 'live', 'started'].includes(status)) {
            rs.push(`Game is ${gameStore.currentGame.status}`);
        }
    }
    if (!selectedStriker.value)
        rs.push('Select striker');
    if (!selectedNonStriker.value)
        rs.push('Select non-striker');
    if (selectedStriker.value && selectedStriker.value === selectedNonStriker.value)
        rs.push('Striker and non-striker cannot be the same');
    if (!currentBowlerId.value && !(needsNewOverLive.value && firstBall && !!selectedBowler.value)) {
        rs.push('Start next over / choose bowler');
    }
    if (!selectedBowler.value)
        rs.push('Choose bowler');
    if (needsNewOver.value && !(firstBall && !!selectedBowler.value))
        rs.push('Start next over');
    if (needsNewBatter.value)
        rs.push('Select next batter');
    if (needsNewInningsLive.value)
        rs.push('Start next innings');
    return rs;
});
function clearQueuedDeliveriesForThisGame() {
    const id = gameId.value;
    if (!id)
        return;
    gameStore.offlineQueue = gameStore.offlineQueue.filter((q) => q.gameId !== id);
    console.info('Cleared offlineQueue for game', id);
}
// ================== Live strip data (current bowler / over) ==================
// ================== Live strip data (current bowler / over) ==================
const stateAny = computed(() => gameStore.state);
const isStartingInnings = ref(false);
// First-innings summary captured locally when we flip to innings 2
const firstInnings = ref(null);
// ðŸ”§ NEW: if backend publishes an innings start, adopt it
watch(() => stateAny.value?.innings_start_at, (t) => {
    if (t)
        inningsStartIso.value = String(t);
}, { immediate: true });
// Count legal balls in *this* innings (wides/no-balls don't consume a ball)
const legalBallsBowled = computed(() => deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length);
// NEW: wickets directly from deliveries (robust even before store catches up)
const wicketsFromDeliveries = computed(() => {
    const battingIds = new Set(battingPlayers.value.map(p => normId(p.id)));
    const dismissed = new Set();
    for (const d of deliveriesThisInnings.value) {
        const did = normId(d.dismissed_player_id);
        if (d.is_wicket && did && battingIds.has(did))
            dismissed.add(did);
    }
    return dismissed.size;
});
// All-out fallback (use XI size if available; cricket all-out threshold is 10)
const allOut = computed(() => {
    const xiSize = battingPlayers.value?.length || 11;
    const maxOut = Math.max(10, xiSize - 1);
    const wicketsFromScore = Number(gameStore.score?.wickets ?? 0);
    const wicketsFromRows = battingEntries.value.filter(b => b.is_out).length;
    const wickets = Math.max(wicketsFromScore, wicketsFromRows, wicketsFromDeliveries.value);
    return wickets >= maxOut;
});
// Overs exhausted fallback â€” IMPORTANT: use current_over_balls (your storeâ€™s field)
const ballsThisOver = computed(() => Number(stateAny.value?.current_over_balls ?? 0));
const ballsPerInningsLimit = computed(() => (oversLimit.value ? oversLimit.value * 6 : Infinity));
const oversExhausted = computed(() => legalBallsBowled.value >= ballsPerInningsLimit.value && ballsThisOver.value === 0);
// Track last time the innings number changed
const inningsFlipAt = ref(0);
watch(() => gameStore.currentGame?.current_inning, () => {
    inningsFlipAt.value = Date.now();
});
// Small suppression window after flip (ms)
const SUPPRESS_DERIVED_MS = 10000;
const needsNewInningsLive = computed(() => {
    const statusRaw = String(gameStore.currentGame?.status || '');
    const status = statusRaw.toLowerCase();
    const serverGate = Boolean(stateAny.value?.needs_new_innings) ||
        status === 'innings_break';
    // If server says the gate is up, respect it.
    if (serverGate)
        return true;
    // While server says we're in progress, don't re-raise the gate locally.
    if (status === 'in_progress')
        return false;
    // Right after an innings flip, ignore local "allOut/oversExhausted" noise.
    if (Date.now() - inningsFlipAt.value < SUPPRESS_DERIVED_MS)
        return false;
    // Otherwise, the local fallbacks can raise the gate.
    return allOut.value || oversExhausted.value;
});
const needsNewOverLive = computed(() => Boolean(stateAny.value?.needs_new_over));
const needsNewBatterLive = computed(() => Boolean(stateAny.value?.needs_new_batter));
const currentBowlerId = computed(() => (stateAny.value?.current_bowler_id ?? null));
const lastBallBowlerId = computed(() => (stateAny.value?.last_ball_bowler_id ?? null));
const currentOverBalls = computed(() => Number(stateAny.value?.current_over_balls ?? 0));
const midOverChangeUsed = computed(() => Boolean(stateAny.value?.mid_over_change_used));
const currentBowler = computed(() => {
    const id = currentBowlerId.value;
    if (!id)
        return null;
    return bowlingPlayers.value.find(p => p.id === id) || null;
});
const currentBowlerStats = computed(() => {
    const id = currentBowlerId.value;
    if (!id)
        return { runs: 0, balls: 0 };
    // Prefer precomputed store stats if available
    const sAny = gameStore.bowlingStatsByPlayer;
    const s = sAny?.[id];
    if (s)
        return { runs: Number(s.runsConceded), balls: Number(s.balls) };
    // Fallback: derive from deliveries (per your backend semantics)
    const filtered = deliveriesThisInnings.value.filter(d => d.bowler_id === id);
    const addRuns = (d) => {
        if (d.extra === 'wd')
            return Number(d.extra_runs || 0); // all wides to bowler
        if (d.extra === 'nb')
            return 1 + Number(d.runs_off_bat || 0); // penalty + off bat
        if (d.extra === 'b' || d.extra === 'lb')
            return 0; // byes: none to bowler
        return Number(d.runs_off_bat ?? d.runs_scored ?? 0); // legal: off bat
    };
    const runs = filtered.reduce((sum, d) => sum + addRuns(d), 0);
    // Legal balls: byes/leg-byes DO consume a ball; wides/nb do not
    const isLegal = (d) => !d.extra || d.extra === 'b' || d.extra === 'lb';
    const balls = filtered.filter(isLegal).length;
    return { runs, balls };
});
function parseOversNotation(s) {
    if (s == null)
        return { oc: 0, ob: 0 };
    const str = String(s);
    const [o, b] = str.split('.');
    const oc = Number(o) || 0;
    let ob = Number(b) || 0;
    if (ob < 0)
        ob = 0;
    if (ob > 5)
        ob = 5;
    return { oc, ob };
}
const oversDisplay = computed(() => {
    const legal = deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length;
    const ov = Math.floor(legal / 6);
    const rem = legal % 6;
    return `${ov}.${rem}`;
});
// For next over: exclude the bowler from the last delivery (cannot bowl consecutive overs)
const eligibleNextOverBowlers = computed(() => {
    const lastBowler = lastBallBowlerId.value;
    // Only filter if we have a valid lastBallBowlerId
    return lastBowler
        ? bowlingPlayers.value.filter(p => p.id !== lastBowler)
        : bowlingPlayers.value;
});
// For correction at START of over: allow ALL available bowlers (no restrictions at over start)
const eligibleCorrectionBowlers = computed(() => bowlingPlayers.value);
const replacementOptions = computed(() => bowlingPlayers.value.filter(p => p.id !== currentBowlerId.value));
const canUseMidOverChange = computed(() => currentOverBalls.value < 6 && !midOverChangeUsed.value);
const overInProgress = computed(() => Number((stateAny.value?.balls_this_over ?? 0)) > 0);
// NEW: Derive legal balls in current over to allow correction even if wides were bowled
const legalBallsInCurrentOver = computed(() => {
    // Use deliveries as the source of truth to avoid store sync delays
    const currentOverIndex = Math.floor(Number(stateAny.value?.overs_completed ?? 0));
    const arr = deliveriesThisInnings.value;
    const ballsInThisOver = arr.filter(d => d.over_number === currentOverIndex &&
        (d.extra !== 'wd' && d.extra !== 'nb'));
    return ballsInThisOver.length;
});
const canCorrectBowler = computed(() => {
    // Allow correction at ANY point during the over (not just at start)
    // As long as there's a bowler selected and the over isn't finished (< 6 legal balls)
    const balls = legalBallsInCurrentOver.value;
    const overNotFinished = balls < 6;
    if (import.meta.env.DEV) {
        console.log('[canCorrectBowler] balls:', balls, 'overNotFinished:', overNotFinished, 'currentBowlerId:', currentBowlerId.value);
    }
    // Available during the over when a bowler has been selected
    return overNotFinished && !!currentBowlerId.value;
});
const inningsScore = computed(() => ({
    runs: Number(gameStore.score?.runs ?? 0),
    wickets: Number(gameStore.score?.wickets ?? 0),
}));
// Target shown during the chase (if server provided)
const target = computed(() => {
    const t = gameStore.currentGame?.target;
    return typeof t === 'number' ? t : null;
});
// Legal balls in the *current* (latest) over
const legalBallsThisOver = computed(() => {
    const arr = deliveriesThisInnings.value;
    if (!arr.length)
        return 0;
    const lastOver = Math.max(...arr.map(d => d.over_number));
    return arr.filter(d => d.over_number === lastOver && (d.extra !== 'wd' && d.extra !== 'nb')).length;
});
// Local fallback: if weâ€™ve bowled 6 legal balls and no innings gate is up, prompt next over.
const needsNewOverDerived = computed(() => legalBallsThisOver.value === 6 && !needsNewInningsLive.value);
// ---- Start Next Innings ----
const startInningsDlgOpen = ref(false);
const nextStrikerId = ref('');
const nextNonStrikerId = ref('');
const openingBowlerId = ref('');
function openStartInnings() {
    if (!roleCanScore.value)
        return;
    // sensible defaults
    const bat = nextBattingXI.value;
    const bowl = nextBowlingXI.value;
    nextStrikerId.value = (bat[0]?.id ?? '');
    nextNonStrikerId.value = (bat[1]?.id ?? '');
    openingBowlerId.value = (bowl[0]?.id ?? '');
    startInningsDlgOpen.value = true;
}
function closeStartInnings() { startInningsDlgOpen.value = false; }
async function confirmStartInnings() {
    if (!roleCanScore.value)
        return;
    console.log('[confirmStartInnings] clicked');
    const id = gameId.value;
    if (!id)
        return;
    try {
        inningsStartIso.value = new Date().toISOString();
        isStartingInnings.value = true;
        // Cache the first-innings summary locally (runs/wkts/overs) before we flip
        try {
            firstInnings.value = {
                runs: inningsScore.value.runs,
                wickets: inningsScore.value.wickets,
                overs: oversDisplay.value,
            };
        }
        catch { /* noop */ }
        const strikerId = normId(nextStrikerId.value);
        const nonStrikerId = normId(nextNonStrikerId.value);
        const openingBowler = normId(openingBowlerId.value);
        // Guard: we never want to send null/empty IDs to the API
        if (!strikerId || !nonStrikerId || !openingBowler) {
            console.warn('[confirmStartInnings] missing opener selection', {
                strikerId,
                nonStrikerId,
                openingBowler,
            });
            isStartingInnings.value = false;
            return;
        }
        const payload = {
            striker_id: strikerId,
            non_striker_id: nonStrikerId,
            opening_bowler_id: openingBowler,
        };
        await apiService.setOpeners(id, {
            striker_id: payload.striker_id,
            non_striker_id: payload.non_striker_id,
        });
        const anyStore = gameStore;
        if (typeof anyStore.startNextInnings === 'function') {
            await anyStore.startNextInnings(id, payload);
        }
        else {
            await legacyApiService.startNextInnings(id, payload);
            await gameStore.loadGame(id);
        }
        // ðŸ”§ Optimistic local clear so the dialog actually goes away now
        // (server snapshot will arrive and confirm shortly)
        gameStore.mergeGamePatch({ status: 'in_progress' });
        inningsFlipAt.value = Date.now();
        if (liveSnapshot.value) {
            liveSnapshot.value = {
                ...liveSnapshot.value,
                needs_new_innings: false,
                current_bowler_id: openingBowler,
                current_striker_id: strikerId,
                current_non_striker_id: nonStrikerId
            };
        }
        // Optimistic selections
        selectedStriker.value = normId(nextStrikerId.value);
        selectedNonStriker.value = normId(nextNonStrikerId.value);
        if (openingBowlerId.value)
            selectedBowler.value = normId(openingBowlerId.value);
        isStartingInnings.value = false;
        showToast('Next innings started', 'success');
        closeStartInnings();
    }
    catch (e) {
        isStartingInnings.value = false;
        onError(e?.message || 'Failed to start next innings');
        // (Optional) console for quick visibility:
        console.error('startNextInnings error:', e);
    }
}
// ================== EMBED / SHARE PANEL ==================
const theme = ref('dark');
const title = ref('Live Scoreboard');
const logo = ref('');
const height = ref(180);
// script setup
const sponsorsUrl = ref(`${apiBase}/sponsors/cricksy/sponsors.json`);
const embedUrl = computed(() => {
    const routerMode = import.meta.env?.VITE_ROUTER_MODE ?? 'history';
    const useHash = routerMode === 'hash';
    const base = window.location.origin + (useHash ? '/#' : '');
    const path = `/embed/${encodeURIComponent(gameId.value)}`;
    const qs = new URLSearchParams();
    if (theme.value && theme.value !== 'auto')
        qs.set('theme', theme.value);
    if (title.value)
        qs.set('title', title.value);
    if (logo.value)
        qs.set('logo', logo.value);
    if (sponsorsUrl.value)
        qs.set('sponsorsUrl', sponsorsUrl.value);
    const q = qs.toString();
    return q ? `${base}${path}?${q}` : `${base}${path}`;
});
const iframeCode = computed(() => `<iframe src="${embedUrl.value}" width="100%" height="${height.value}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`);
const shareOpen = ref(false);
const copied = ref(false);
const codeRef = ref(null);
function closeShare() { shareOpen.value = false; copied.value = false; }
async function copyEmbed() {
    const txt = iframeCode.value;
    try {
        await navigator.clipboard.writeText(txt);
        copied.value = true;
    }
    catch {
        const el = codeRef.value;
        if (el) {
            el.focus();
            el.select();
            try {
                document.execCommand('copy');
            }
            catch { /* ignore */ }
            copied.value = true;
        }
    }
    window.setTimeout(() => (copied.value = false), 1600);
}
watch(shareOpen, (o) => { if (o)
    setTimeout(() => codeRef.value?.select(), 75); });
const toast = ref(null);
let toastTimer = null;
function showToast(message, type = 'success', ms = 1800) {
    toast.value = { message, type };
    if (toastTimer)
        window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => (toast.value = null), ms);
}
function onScored() { showToast(pendingCount.value > 0 ? 'Saved (queued) âœ“' : 'Saved âœ“', 'success'); }
function onError(message) { showToast(message || 'Something went wrong', 'error', 3000); }
// ================== Lifecycle ==================
onMounted(async () => {
    const id = gameId.value;
    if (!id) {
        void router.replace('/');
        return;
    }
    try {
        await gameStore.loadGame(id);
        loadXIForGame(id);
        gameStore.initLive(id);
        clearQueuedDeliveriesForThisGame();
        // Gate prompts after initial load
        if (liveSnapshot.value)
            syncBattersFromSnapshot(liveSnapshot.value);
        if (currentBowlerId.value)
            selectedBowler.value = currentBowlerId.value;
        if (roleCanScore.value && needsNewBatterLive.value)
            openSelectBatter();
        if (roleCanScore.value && needsNewOverLive.value)
            openStartOver();
    }
    catch (e) {
        showToast('Failed to load or connect', 'error', 3000);
        console.error('load/init failed:', e);
    }
});
onUnmounted(() => {
    if (toastTimer)
        window.clearTimeout(toastTimer);
    gameStore.stopLive();
});
// --- Client fallback: derive striker/non-striker from the last delivery when snapshot is odd ---
function maybeRotateFromLastDelivery() {
    const last = liveSnapshot.value?.last_delivery ??
        gameStore.currentGame?.last_delivery;
    if (!last)
        return;
    const prevS = normId(selectedStriker.value);
    const prevNS = normId(selectedNonStriker.value);
    if (!prevS || !prevNS)
        return;
    const x = last.extra_type || null;
    const legal = !x || x === 'b' || x === 'lb';
    let swap = false;
    if (legal) {
        // On legal balls, parity of off-the-bat runs decides strike
        const offBat = Number(last.runs_off_bat ?? last.runs_scored ?? 0);
        swap = (offBat % 2) === 1;
    }
    else if (x === 'wd') {
        // wides: total includes automatic 1; only the *run(s) actually run* flip strike
        const totalWides = Math.max(1, Number(last.extra_runs ?? 1));
        const runsRun = totalWides - 1;
        swap = (runsRun % 2) === 1;
    }
    else if (x === 'nb') {
        // no-balls: penalty 1 plus *additional* runs (off bat or nb-byes if you add them later)
        const offBat = Number(last.runs_off_bat ?? 0);
        const extraBeyondPenalty = Math.max(0, Number(last.extra_runs ?? 1) - 1);
        swap = ((offBat + extraBeyondPenalty) % 2) === 1;
    }
    if (swap) {
        const s = selectedStriker.value;
        selectedStriker.value = selectedNonStriker.value;
        selectedNonStriker.value = s;
    }
}
// Keep UI batters in lockstep with server, but fix snapshot oddities locally.
function syncBattersFromSnapshot(snap) {
    if (!snap)
        return;
    const sId = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '');
    const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '');
    if (sId)
        selectedStriker.value = sId;
    if (nsId)
        selectedNonStriker.value = nsId;
    // Guard: snapshot sometimes sends SAME id for both ends; fix using last delivery parity.
    if (sId && nsId && sId === nsId) {
        maybeRotateFromLastDelivery();
    }
}
watch(liveSnapshot, (snap) => syncBattersFromSnapshot(snap));
// Keep selections valid when innings flips or XI loads
watch(currentBowlerId, (id) => { selectedBowler.value = id ? id : ''; });
watch([bowlingPlayers, xiLoaded, currentBowlerId], () => {
    const id = selectedBowler.value;
    if (id && !bowlingPlayers.value.some(p => p.id === id) && id !== currentBowlerId.value)
        selectedBowler.value = '';
});
watch(needsNewInningsLive, (v) => {
    if (!roleCanScore.value)
        return;
    if (!v)
        return;
    if (isStartingInnings.value)
        return; // don't pop while we're starting
    if (startInningsDlgOpen.value)
        return; // already open
    if (v) {
        selectedBowler.value = ''; // force explicit choice for the new innings
    }
    startOverDlgOpen.value = false;
    selectBatterDlgOpen.value = false;
    nextTick().then(() => openStartInnings());
});
watch(() => stateAny.value?.needs_new_innings, (v) => {
    if (!v)
        isStartingInnings.value = false;
});
// Only open these gates if an innings is NOT required
watch(needsNewBatterLive, (v) => {
    if (!roleCanScore.value)
        return;
    if (v && !needsNewInningsLive.value)
        openSelectBatter();
});
watch([needsNewOverLive, needsNewOverDerived], ([serverGate, localGate]) => {
    if (!roleCanScore.value)
        return;
    if ((serverGate || localGate) && !needsNewInningsLive.value) {
        // Keep any user-chosen next bowler; just nudge the dialog if you want.
        if (!selectedBowler.value) {
            selectedBowler.value = (eligibleNextOverBowlers.value[0]?.id || '');
        }
        selectedNextOverBowlerId.value = selectedBowler.value;
        openStartOver();
    }
});
watch([battingPlayers, needsNewInningsLive], ([list]) => {
    const ids = new Set(list.map(p => p.id));
    if (selectedStriker.value && !ids.has(selectedStriker.value)) {
        selectedStriker.value = '';
    }
    if (selectedNonStriker.value && !ids.has(selectedNonStriker.value)) {
        selectedNonStriker.value = '';
    }
});
watch([bowlingPlayers, needsNewInningsLive], ([list]) => {
    const ids = new Set(list.map(p => p.id));
    if (selectedBowler.value && !ids.has(selectedBowler.value)) {
        selectedBowler.value = '';
    }
});
// Reconnect + flush controls
function reconnect() {
    const id = gameId.value;
    if (!id)
        return;
    try {
        gameStore.initLive(id);
        showToast('Reconnectingâ€¦', 'info');
    }
    catch {
        showToast('Reconnect failed', 'error', 2500);
    }
}
function flushNow() {
    const id = gameId.value;
    if (!id)
        return;
    gameStore.flushQueue(id);
    showToast('Flushing queueâ€¦', 'info');
}
// ================== Start Over & Mid-over Change ==================
const startOverDlgOpen = ref(false);
const changeBowlerDlgOpen = ref(false);
const isBowlerCorrection = ref(false);
const selectedNextOverBowlerId = ref('');
const selectedReplacementBowlerId = ref('');
const selectBatterDlgOpen = ref(false);
const selectedNextBatterId = ref('');
const activeTab = ref('recent');
const canStartOverNow = computed(() => needsNewOverLive.value || !currentBowlerId.value);
const candidateBatters = computed(() => {
    const anyStore = gameStore;
    if (Array.isArray(anyStore.availableBatsmen) && anyStore.availableBatsmen.length) {
        return anyStore.availableBatsmen;
    }
    const outSet = new Set(battingEntries.value.filter(b => b.is_out).map(b => b.player_id));
    return battingPlayers.value.filter(p => !outSet.has(p.id));
});
function openSelectBatter() {
    if (!roleCanScore.value)
        return;
    selectedNextBatterId.value = '';
    selectBatterDlgOpen.value = true;
}
function closeSelectBatter() { selectBatterDlgOpen.value = false; }
async function confirmSelectBatter() {
    if (!roleCanScore.value)
        return;
    const batter = normId(selectedNextBatterId.value);
    if (!batter)
        return;
    await gameStore.replaceBatter(batter);
    // Prefer authoritative IDs from the latest snapshot / state
    const snap = liveSnapshot.value ?? gameStore.state ?? {};
    const sId = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '');
    const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '');
    if (sId || nsId) {
        if (sId)
            selectedStriker.value = sId;
        if (nsId)
            selectedNonStriker.value = nsId;
    }
    else {
        // Fallback: use last deliveryâ€™s dismissed id to decide end
        const last = liveSnapshot.value?.last_delivery ??
            gameStore.currentGame?.deliveries?.slice(-1)?.[0];
        const dismissed = normId(last?.dismissed_player_id || '');
        if (dismissed && normId(selectedStriker.value) === dismissed)
            selectedStriker.value = batter;
        else if (dismissed && normId(selectedNonStriker.value) === dismissed)
            selectedNonStriker.value = batter;
        else if (!selectedStriker.value)
            selectedStriker.value = batter;
        else if (!selectedNonStriker.value)
            selectedNonStriker.value = batter;
    }
    showToast('Next batter set', 'success');
    closeSelectBatter();
}
function openStartOver() {
    if (!roleCanScore.value)
        return;
    const first = eligibleNextOverBowlers.value[0]?.id ?? '';
    selectedNextOverBowlerId.value = first;
    startOverDlgOpen.value = true;
}
function closeStartOver() { startOverDlgOpen.value = false; }
// Store only
async function confirmStartOver() {
    if (!roleCanScore.value)
        return;
    const id = gameId.value;
    const bowler = selectedNextOverBowlerId.value;
    if (!id || !bowler)
        return;
    try {
        await gameStore.startNewOver(bowler);
        selectedBowler.value = bowler;
        selectedNextOverBowlerId.value = '';
        showToast('Over started', 'success');
        closeStartOver();
    }
    catch (err) {
        const msg = err?.message || 'Failed to start over';
        showToast(msg, 'error');
        console.error('confirmStartOver error:', err);
    }
}
function openCorrectionBowler() {
    if (!roleCanScore.value)
        return;
    if (!canCorrectBowler.value) {
        showToast('Cannot correct bowler after legal balls bowled', 'error');
        return;
    }
    isBowlerCorrection.value = true;
    // Auto-select first available bowler for correction
    const firstBowler = eligibleCorrectionBowlers.value[0]?.id ?? '';
    selectedReplacementBowlerId.value = firstBowler;
    changeBowlerDlgOpen.value = true;
    if (import.meta.env.DEV) {
        console.log('[openCorrectionBowler] Eligible bowlers:', eligibleCorrectionBowlers.value.length, 'Selected:', firstBowler);
    }
}
function openChangeBowler() {
    if (!roleCanScore.value)
        return;
    isBowlerCorrection.value = false;
    selectedReplacementBowlerId.value = '';
    changeBowlerDlgOpen.value = true;
}
function closeChangeBowler() { changeBowlerDlgOpen.value = false; }
async function confirmChangeBowler() {
    const id = gameId.value;
    const repl = selectedReplacementBowlerId.value;
    if (!id || !repl)
        return;
    if (isBowlerCorrection.value) {
        try {
            await gameStore.startNewOver(repl);
            selectedBowler.value = repl;
            showToast('Bowler corrected', 'success');
        }
        catch (e) {
            onError(e?.message || 'Failed to correct bowler');
        }
        finally {
            selectedReplacementBowlerId.value = '';
            closeChangeBowler();
        }
        return;
    }
    try {
        await gameStore.changeBowlerMidOver(id, repl, 'injury');
        if (currentBowlerId.value)
            selectedBowler.value = currentBowlerId.value;
        showToast('Bowler changed', 'success');
    }
    catch (e) {
        await gameStore.loadGame(id);
        selectedBowler.value = (currentBowlerId.value || '');
        onError(e?.message || 'Failed to change bowler');
    }
    finally {
        selectedReplacementBowlerId.value = '';
        closeChangeBowler();
    }
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['header-left']} */ ;
/** @type {__VLS_StyleScopedClasses['header-left']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-share']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-action-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-action-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-select-full']} */ ;
/** @type {__VLS_StyleScopedClasses['scoring-grid-inputs']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['val-4']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['val-6']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['wicket-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['wicket-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-undo']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-ghost-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['sel']} */ ;
/** @type {__VLS_StyleScopedClasses['sel']} */ ;
/** @type {__VLS_StyleScopedClasses['sel']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score-4']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-score-6']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-wd']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-nb']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-b']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-lb']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics-widget-section']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics-widgets']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "broadcast-layout" },
});
/** @type {__VLS_StyleScopedClasses['broadcast-layout']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "broadcast-header" },
});
/** @type {__VLS_StyleScopedClasses['broadcast-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-left" },
});
/** @type {__VLS_StyleScopedClasses['header-left']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "brand" },
});
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
if (__VLS_ctx.gameId) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "game-meta" },
    });
    /** @type {__VLS_StyleScopedClasses['game-meta']} */ ;
    (__VLS_ctx.gameId.slice(0, 6));
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-center dense-stats" },
});
/** @type {__VLS_StyleScopedClasses['header-center']} */ ;
/** @type {__VLS_StyleScopedClasses['dense-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-group main-score" },
});
/** @type {__VLS_StyleScopedClasses['stat-group']} */ ;
/** @type {__VLS_StyleScopedClasses['main-score']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "team-name" },
});
/** @type {__VLS_StyleScopedClasses['team-name']} */ ;
(__VLS_ctx.battingTeamName || 'Team');
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "score-display" },
});
/** @type {__VLS_StyleScopedClasses['score-display']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    'data-testid': "scoreboard-runs",
});
(__VLS_ctx.headerRuns);
(__VLS_ctx.headerWickets);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "overs-display" },
});
/** @type {__VLS_StyleScopedClasses['overs-display']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    'data-testid': "scoreboard-overs",
});
(__VLS_ctx.headerOvers);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-divider" },
});
/** @type {__VLS_StyleScopedClasses['stat-divider']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stat-group rates" },
});
/** @type {__VLS_StyleScopedClasses['stat-group']} */ ;
/** @type {__VLS_StyleScopedClasses['rates']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "rate-item" },
});
/** @type {__VLS_StyleScopedClasses['rate-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
((__VLS_ctx.liveSnapshot?.current_run_rate ?? __VLS_ctx.liveSnapshot?.crr ?? 0).toFixed(2));
if (__VLS_ctx.targetSafe) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "rate-item" },
    });
    /** @type {__VLS_StyleScopedClasses['rate-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.targetSafe);
}
if (__VLS_ctx.targetSafe) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "rate-item" },
    });
    /** @type {__VLS_StyleScopedClasses['rate-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    ((__VLS_ctx.requiredRunRate ?? 0).toFixed(2));
}
if (__VLS_ctx.targetSafe) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "rate-item need-txt" },
    });
    /** @type {__VLS_StyleScopedClasses['rate-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['need-txt']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.runsRequired);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-right" },
});
/** @type {__VLS_StyleScopedClasses['header-right']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.shareOpen = true;
            // @ts-ignore
            [gameId, gameId, battingTeamName, headerRuns, headerWickets, headerOvers, liveSnapshot, liveSnapshot, targetSafe, targetSafe, targetSafe, targetSafe, requiredRunRate, runsRequired, shareOpen,];
        } },
    ...{ class: "btn-ghost-sm" },
});
/** @type {__VLS_StyleScopedClasses['btn-ghost-sm']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "player-bar" },
});
/** @type {__VLS_StyleScopedClasses['player-bar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-box striker-box" },
});
/** @type {__VLS_StyleScopedClasses['player-box']} */ ;
/** @type {__VLS_StyleScopedClasses['striker-box']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pb-label" },
});
/** @type {__VLS_StyleScopedClasses['pb-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.selectedStriker),
    ...{ class: "pb-select-full" },
});
/** @type {__VLS_StyleScopedClasses['pb-select-full']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    disabled: true,
    value: "",
});
for (const [p] of __VLS_vFor((__VLS_ctx.battingPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (p.id),
        value: (p.id),
        disabled: (p.id === __VLS_ctx.selectedNonStriker),
    });
    (p.name);
    (__VLS_ctx.roleBadge(p.id));
    // @ts-ignore
    [selectedStriker, battingPlayers, selectedNonStriker, roleBadge,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-box non-striker-box" },
});
/** @type {__VLS_StyleScopedClasses['player-box']} */ ;
/** @type {__VLS_StyleScopedClasses['non-striker-box']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pb-label" },
});
/** @type {__VLS_StyleScopedClasses['pb-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.selectedNonStriker),
    ...{ class: "pb-select-full" },
});
/** @type {__VLS_StyleScopedClasses['pb-select-full']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    disabled: true,
    value: "",
});
for (const [p] of __VLS_vFor((__VLS_ctx.battingPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (p.id),
        value: (p.id),
        disabled: (p.id === __VLS_ctx.selectedStriker),
    });
    (p.name);
    (__VLS_ctx.roleBadge(p.id));
    // @ts-ignore
    [selectedStriker, battingPlayers, selectedNonStriker, roleBadge,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-box bowler-box" },
});
/** @type {__VLS_StyleScopedClasses['player-box']} */ ;
/** @type {__VLS_StyleScopedClasses['bowler-box']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pb-label" },
});
/** @type {__VLS_StyleScopedClasses['pb-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
if (__VLS_ctx.roleCanScore) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bowler-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['bowler-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.openStartOver) },
        ...{ class: "btn-action-xs" },
        disabled: (!__VLS_ctx.canStartOverNow),
        title: "Start new over / Change bowler",
    });
    /** @type {__VLS_StyleScopedClasses['btn-action-xs']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.openChangeBowler) },
        ...{ class: "btn-action-xs" },
        disabled: (!__VLS_ctx.canUseMidOverChange),
        title: "Mid-over replacement (injury/suspension)",
    });
    /** @type {__VLS_StyleScopedClasses['btn-action-xs']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.openCorrectionBowler) },
        ...{ class: "btn-action-xs" },
        disabled: (!__VLS_ctx.canCorrectBowler),
        title: (!__VLS_ctx.canCorrectBowler ? 'Correction only available at the start of an over' : 'Correct wrong bowler selection'),
    });
    /** @type {__VLS_StyleScopedClasses['btn-action-xs']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.selectedBowler),
    ...{ class: "pb-select-full" },
});
/** @type {__VLS_StyleScopedClasses['pb-select-full']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    disabled: true,
    value: "",
});
for (const [p] of __VLS_vFor((__VLS_ctx.bowlingPlayers))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (p.id),
        value: (p.id),
    });
    (p.name);
    (__VLS_ctx.bowlerRoleBadge(p.id));
    // @ts-ignore
    [roleCanScore, openStartOver, canStartOverNow, openChangeBowler, canUseMidOverChange, openCorrectionBowler, canCorrectBowler, canCorrectBowler, selectedBowler, bowlingPlayers, bowlerRoleBadge,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "broadcast-main" },
});
/** @type {__VLS_StyleScopedClasses['broadcast-main']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel scoring-panel" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['scoring-panel']} */ ;
if (__VLS_ctx.needsNewBatterLive || __VLS_ctx.needsNewOverLive || __VLS_ctx.needsNewInningsLive) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "gate-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['gate-overlay']} */ ;
    if (__VLS_ctx.needsNewInningsLive) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.roleCanScore) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (__VLS_ctx.openStartInnings) },
                ...{ class: "btn-gate" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-gate']} */ ;
        }
    }
    else if (__VLS_ctx.needsNewBatterLive) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.roleCanScore) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (__VLS_ctx.openSelectBatter) },
                ...{ class: "btn-gate" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-gate']} */ ;
        }
    }
    else if (__VLS_ctx.needsNewOverLive) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.roleCanScore) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (__VLS_ctx.openStartOver) },
                ...{ class: "btn-gate" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-gate']} */ ;
        }
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "scoring-grid-inputs" },
    ...{ class: ({ disabled: !__VLS_ctx.canScore }) },
});
/** @type {__VLS_StyleScopedClasses['scoring-grid-inputs']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "input-row extras-row" },
});
/** @type {__VLS_StyleScopedClasses['input-row']} */ ;
/** @type {__VLS_StyleScopedClasses['extras-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.extra = 'none';
            // @ts-ignore
            [roleCanScore, roleCanScore, roleCanScore, openStartOver, needsNewBatterLive, needsNewBatterLive, needsNewOverLive, needsNewOverLive, needsNewInningsLive, needsNewInningsLive, openStartInnings, openSelectBatter, canScore, extra,];
        } },
    ...{ class: "btn-input btn-extra-legal" },
    ...{ class: ({ active: __VLS_ctx.extra === 'none' }) },
});
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-legal']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.extra = 'wd';
            // @ts-ignore
            [extra, extra,];
        } },
    ...{ class: "btn-input btn-extra-wd" },
    ...{ class: ({ active: __VLS_ctx.extra === 'wd' }) },
});
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-wd']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.extra = 'nb';
            // @ts-ignore
            [extra, extra,];
        } },
    ...{ class: "btn-input btn-extra-nb" },
    ...{ class: ({ active: __VLS_ctx.extra === 'nb' }) },
});
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-nb']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.extra = 'b';
            // @ts-ignore
            [extra, extra,];
        } },
    ...{ class: "btn-input btn-extra-b" },
    ...{ class: ({ active: __VLS_ctx.extra === 'b' }) },
});
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-b']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.extra = 'lb';
            // @ts-ignore
            [extra, extra,];
        } },
    ...{ class: "btn-input btn-extra-lb" },
    ...{ class: ({ active: __VLS_ctx.extra === 'lb' }) },
});
/** @type {__VLS_StyleScopedClasses['btn-input']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-extra-lb']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "input-matrix" },
});
/** @type {__VLS_StyleScopedClasses['input-matrix']} */ ;
for (const [r] of __VLS_vFor(([0, 1, 2, 3, 4, 6, 5]))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.extra === 'none' || __VLS_ctx.extra === 'nb' ? __VLS_ctx.offBat = r : __VLS_ctx.extraRuns = r;
                // @ts-ignore
                [extra, extra, extra, offBat, extraRuns,];
            } },
        key: (r),
        'data-testid': (`delivery-run-${r}`),
        ...{ class: "btn-score" },
        ...{ class: ([
                `btn-score-${r}`,
                { active: (__VLS_ctx.extra === 'none' || __VLS_ctx.extra === 'nb' ? __VLS_ctx.offBat : __VLS_ctx.extraRuns) === r }
            ]) },
    });
    /** @type {__VLS_StyleScopedClasses['btn-score']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    (r);
    // @ts-ignore
    [extra, extra, offBat, extraRuns,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "input-row action-row" },
});
/** @type {__VLS_StyleScopedClasses['input-row']} */ ;
/** @type {__VLS_StyleScopedClasses['action-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "wicket-toggle" },
    ...{ class: ({ checked: __VLS_ctx.isWicket }) },
});
/** @type {__VLS_StyleScopedClasses['wicket-toggle']} */ ;
/** @type {__VLS_StyleScopedClasses['checked']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.isWicket);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.submitSimple) },
    'data-testid': "submit-delivery",
    ...{ class: "btn-submit" },
    disabled: (!__VLS_ctx.canSubmitSimple || __VLS_ctx.isSubmitting),
});
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
(__VLS_ctx.isSubmitting ? '...' : 'SUBMIT');
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Teleport | typeof __VLS_components.Teleport} */
Teleport;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "body",
}));
const __VLS_2 = __VLS_1({
    to: "body",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
if (__VLS_ctx.isWicket) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "wicket-details-floating" },
    });
    /** @type {__VLS_StyleScopedClasses['wicket-details-floating']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "wd-label" },
    });
    /** @type {__VLS_StyleScopedClasses['wd-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "wd-row" },
    });
    /** @type {__VLS_StyleScopedClasses['wd-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.dismissal),
        ...{ class: "sel-sm" },
    });
    /** @type {__VLS_StyleScopedClasses['sel-sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bowled",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "caught",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "lbw",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "run_out",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "stumped",
    });
    if (__VLS_ctx.needsFielder) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
            value: (__VLS_ctx.selectedFielderId),
            ...{ class: "sel-sm" },
        });
        /** @type {__VLS_StyleScopedClasses['sel-sm']} */ ;
        for (const [p] of __VLS_vFor((__VLS_ctx.fielderOptions))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
                key: (p.id),
                value: (p.id),
            });
            (p.name);
            // @ts-ignore
            [isWicket, isWicket, isWicket, submitSimple, canSubmitSimple, isSubmitting, isSubmitting, dismissal, needsFielder, selectedFielderId, fielderOptions,];
        }
    }
}
// @ts-ignore
[];
var __VLS_3;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "undo-row" },
});
/** @type {__VLS_StyleScopedClasses['undo-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.deleteLastDelivery) },
    ...{ class: "btn-undo" },
    disabled: (!__VLS_ctx.canDeleteLast),
});
/** @type {__VLS_StyleScopedClasses['btn-undo']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel map-panel" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['map-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "recent-strip" },
});
/** @type {__VLS_StyleScopedClasses['recent-strip']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "recent-label" },
});
/** @type {__VLS_StyleScopedClasses['recent-label']} */ ;
if (__VLS_ctx.overInProgress) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "active-ball-text" },
    });
    /** @type {__VLS_StyleScopedClasses['active-ball-text']} */ ;
    (__VLS_ctx.oversDisplay);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "recent-balls" },
});
/** @type {__VLS_StyleScopedClasses['recent-balls']} */ ;
for (const [b, i] of __VLS_vFor((__VLS_ctx.recentBallSlots))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                b ? __VLS_ctx.openCorrectionModal(b) : null;
                // @ts-ignore
                [deleteLastDelivery, canDeleteLast, overInProgress, oversDisplay, recentBallSlots, openCorrectionModal,];
            } },
        key: (i),
        ...{ class: "ball-badge" },
        ...{ class: (b ? __VLS_ctx.getBallClass(b) : 'empty') },
        title: (b ? 'Click to correct this delivery' : ''),
        ...{ style: (b ? 'cursor: pointer;' : '') },
    });
    /** @type {__VLS_StyleScopedClasses['ball-badge']} */ ;
    (b ? __VLS_ctx.getBallLabel(b) : '•');
    // @ts-ignore
    [getBallClass, getBallLabel,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "map-container" },
});
/** @type {__VLS_StyleScopedClasses['map-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "wagon-wheel-placeholder" },
});
/** @type {__VLS_StyleScopedClasses['wagon-wheel-placeholder']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "field-oval" },
});
/** @type {__VLS_StyleScopedClasses['field-oval']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pitch-rect" },
});
/** @type {__VLS_StyleScopedClasses['pitch-rect']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "zone-overlay" },
});
/** @type {__VLS_StyleScopedClasses['zone-overlay']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(1);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z1" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z1']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(2);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z2" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z2']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(3);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z3" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z3']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(4);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z4" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z4']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(5);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z5" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z5']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(6);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z6" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z6']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(7);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z7" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z7']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.recordZone(8);
            // @ts-ignore
            [recordZone,];
        } },
    ...{ class: "zone z8" },
});
/** @type {__VLS_StyleScopedClasses['zone']} */ ;
/** @type {__VLS_StyleScopedClasses['z8']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "map-label" },
});
/** @type {__VLS_StyleScopedClasses['map-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
    ...{ class: "broadcast-footer" },
});
/** @type {__VLS_StyleScopedClasses['broadcast-footer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tabs-nav" },
});
/** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'recent';
            // @ts-ignore
            [activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'recent' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'batting';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'batting' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'bowling';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'bowling' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'events';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'events' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'analytics';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'analytics' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'extras';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'extras' }) },
});
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-content" },
});
/** @type {__VLS_StyleScopedClasses['tab-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'recent') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
const __VLS_6 = DeliveryTable;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    deliveries: (__VLS_ctx.deliveriesThisInnings),
    playerNameById: (__VLS_ctx.playerNameById),
}));
const __VLS_8 = __VLS_7({
    deliveries: (__VLS_ctx.deliveriesThisInnings),
    playerNameById: (__VLS_ctx.playerNameById),
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'batting') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
const __VLS_11 = BattingCard;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent1(__VLS_11, new __VLS_11({
    entries: (__VLS_ctx.battingEntries),
}));
const __VLS_13 = __VLS_12({
    entries: (__VLS_ctx.battingEntries),
}, ...__VLS_functionalComponentArgsRest(__VLS_12));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'bowling') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
const __VLS_16 = BowlingCard;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    entries: (__VLS_ctx.bowlingEntries),
}));
const __VLS_18 = __VLS_17({
    entries: (__VLS_ctx.bowlingEntries),
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'events') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
const __VLS_21 = EventLogTab;
// @ts-ignore
const __VLS_22 = __VLS_asFunctionalComponent1(__VLS_21, new __VLS_21({
    gameId: (__VLS_ctx.gameId),
}));
const __VLS_23 = __VLS_22({
    gameId: (__VLS_ctx.gameId),
}, ...__VLS_functionalComponentArgsRest(__VLS_22));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane analytics-container" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'analytics') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-widgets" },
});
/** @type {__VLS_StyleScopedClasses['analytics-widgets']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-widget-section" },
});
/** @type {__VLS_StyleScopedClasses['analytics-widget-section']} */ ;
const __VLS_26 = PhaseTimelineWidget;
// @ts-ignore
const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
    phaseData: (__VLS_ctx.phaseData),
    predictions: (__VLS_ctx.predictions),
    loading: (__VLS_ctx.phaseLoading),
    onRefresh: (() => __VLS_ctx.fetchPhaseMap(__VLS_ctx.gameId)),
}));
const __VLS_28 = __VLS_27({
    phaseData: (__VLS_ctx.phaseData),
    predictions: (__VLS_ctx.predictions),
    loading: (__VLS_ctx.phaseLoading),
    onRefresh: (() => __VLS_ctx.fetchPhaseMap(__VLS_ctx.gameId)),
}, ...__VLS_functionalComponentArgsRest(__VLS_27));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-widget-section" },
});
/** @type {__VLS_StyleScopedClasses['analytics-widget-section']} */ ;
const __VLS_31 = PressureMapWidget;
// @ts-ignore
const __VLS_32 = __VLS_asFunctionalComponent1(__VLS_31, new __VLS_31({
    pressureData: (__VLS_ctx.pressureData),
    loading: (__VLS_ctx.pressureLoading),
}));
const __VLS_33 = __VLS_32({
    pressureData: (__VLS_ctx.pressureData),
    loading: (__VLS_ctx.pressureLoading),
}, ...__VLS_functionalComponentArgsRest(__VLS_32));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-widget-section" },
});
/** @type {__VLS_StyleScopedClasses['analytics-widget-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
const __VLS_36 = InningsGradeWidget;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
    gradeData: (__VLS_ctx.currentInningsGrade),
    battingTeam: (__VLS_ctx.battingTeamName),
    bowlingTeam: ((__VLS_ctx.currentGame?.bowling_team_name ?? '')),
    theme: "dark",
}));
const __VLS_38 = __VLS_37({
    gradeData: (__VLS_ctx.currentInningsGrade),
    battingTeam: (__VLS_ctx.battingTeamName),
    bowlingTeam: ((__VLS_ctx.currentGame?.bowling_team_name ?? '')),
    theme: "dark",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analytics-widget-section" },
});
/** @type {__VLS_StyleScopedClasses['analytics-widget-section']} */ ;
const __VLS_41 = WinProbabilityChart;
// @ts-ignore
const __VLS_42 = __VLS_asFunctionalComponent1(__VLS_41, new __VLS_41({
    showChart: (true),
}));
const __VLS_43 = __VLS_42({
    showChart: (true),
}, ...__VLS_functionalComponentArgsRest(__VLS_42));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-pane" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.activeTab === 'extras') }, null, null);
/** @type {__VLS_StyleScopedClasses['tab-pane']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "extras-grid" },
});
/** @type {__VLS_StyleScopedClasses['extras-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.extrasBreakdown.wides);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.extrasBreakdown.no_balls);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.extrasBreakdown.byes);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.extrasBreakdown.leg_byes);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
(__VLS_ctx.extrasBreakdown.total);
if (__VLS_ctx.canShowDls) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dls-mini" },
    });
    /** @type {__VLS_StyleScopedClasses['dls-mini']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    if (__VLS_ctx.dls) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        (__VLS_ctx.dls.target);
        (__VLS_ctx.dls.team2_resources.toFixed(1));
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.refreshDls) },
        ...{ class: "btn-sm" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-sm']} */ ;
}
if (__VLS_ctx.shareOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeShare) },
        ...{ onKeydown: (__VLS_ctx.closeShare) },
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
        'aria-labelledby': "share-title",
        tabindex: "0",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_46;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_47 = __VLS_asFunctionalComponent1(__VLS_46, new __VLS_46({
        padding: "lg",
        ...{ class: "modal-card modal-card--wide" },
    }));
    const __VLS_48 = __VLS_47({
        padding: "lg",
        ...{ class: "modal-card modal-card--wide" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_47));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['modal-card--wide']} */ ;
    const { default: __VLS_51 } = __VLS_49.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "modal-header" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        id: "share-title",
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    let __VLS_52;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent1(__VLS_52, new __VLS_52({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        'aria-label': "Close modal",
    }));
    const __VLS_54 = __VLS_53({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        'aria-label': "Close modal",
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    let __VLS_57;
    const __VLS_58 = ({ click: {} },
        { onClick: (__VLS_ctx.closeShare) });
    const { default: __VLS_59 } = __VLS_55.slots;
    // @ts-ignore
    [gameId, gameId, battingTeamName, shareOpen, activeTab, activeTab, activeTab, activeTab, activeTab, activeTab, activeTab, deliveriesThisInnings, playerNameById, battingEntries, bowlingEntries, phaseData, predictions, phaseLoading, fetchPhaseMap, pressureData, pressureLoading, currentInningsGrade, currentGame, extrasBreakdown, extrasBreakdown, extrasBreakdown, extrasBreakdown, extrasBreakdown, canShowDls, dls, dls, dls, refreshDls, closeShare, closeShare, closeShare,];
    var __VLS_55;
    var __VLS_56;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "code-wrap" },
    });
    /** @type {__VLS_StyleScopedClasses['code-wrap']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        ref: "codeRef",
        ...{ class: "code" },
        readonly: true,
        value: (__VLS_ctx.iframeCode),
        'aria-label': "Embed iframe HTML",
    });
    /** @type {__VLS_StyleScopedClasses['code']} */ ;
    let __VLS_60;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent1(__VLS_60, new __VLS_60({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        ...{ class: "copy" },
    }));
    const __VLS_62 = __VLS_61({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        ...{ class: "copy" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    let __VLS_65;
    const __VLS_66 = ({ click: {} },
        { onClick: (__VLS_ctx.copyEmbed) });
    /** @type {__VLS_StyleScopedClasses['copy']} */ ;
    const { default: __VLS_67 } = __VLS_63.slots;
    (__VLS_ctx.copied ? 'Copied!' : 'Copy');
    // @ts-ignore
    [iframeCode, copyEmbed, copied,];
    var __VLS_63;
    var __VLS_64;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-row" },
    });
    /** @type {__VLS_StyleScopedClasses['form-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    let __VLS_68;
    /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
    BaseInput;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent1(__VLS_68, new __VLS_68({
        ...{ 'onFocus': {} },
        modelValue: (__VLS_ctx.embedUrl),
        label: "Preview URL",
        readonly: true,
    }));
    const __VLS_70 = __VLS_69({
        ...{ 'onFocus': {} },
        modelValue: (__VLS_ctx.embedUrl),
        label: "Preview URL",
        readonly: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    let __VLS_73;
    const __VLS_74 = ({ focus: {} },
        { onFocus: ((e) => e.target?.select()) });
    var __VLS_71;
    var __VLS_72;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "align-end" },
    });
    /** @type {__VLS_StyleScopedClasses['align-end']} */ ;
    let __VLS_75;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent1(__VLS_75, new __VLS_75({
        variant: "ghost",
        as: "a",
        href: (__VLS_ctx.embedUrl),
        target: "_blank",
        rel: "noopener",
    }));
    const __VLS_77 = __VLS_76({
        variant: "ghost",
        as: "a",
        href: (__VLS_ctx.embedUrl),
        target: "_blank",
        rel: "noopener",
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    const { default: __VLS_80 } = __VLS_78.slots;
    // @ts-ignore
    [embedUrl, embedUrl,];
    var __VLS_78;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "note" },
    });
    /** @type {__VLS_StyleScopedClasses['note']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.em, __VLS_intrinsics.em)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.b, __VLS_intrinsics.b)({});
    (__VLS_ctx.height);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    let __VLS_81;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_82 = __VLS_asFunctionalComponent1(__VLS_81, new __VLS_81({
        ...{ 'onClick': {} },
        variant: "ghost",
    }));
    const __VLS_83 = __VLS_82({
        ...{ 'onClick': {} },
        variant: "ghost",
    }, ...__VLS_functionalComponentArgsRest(__VLS_82));
    let __VLS_86;
    const __VLS_87 = ({ click: {} },
        { onClick: (__VLS_ctx.closeShare) });
    const { default: __VLS_88 } = __VLS_84.slots;
    // @ts-ignore
    [closeShare, height,];
    var __VLS_84;
    var __VLS_85;
    let __VLS_89;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_90 = __VLS_asFunctionalComponent1(__VLS_89, new __VLS_89({
        ...{ 'onClick': {} },
        variant: "primary",
    }));
    const __VLS_91 = __VLS_90({
        ...{ 'onClick': {} },
        variant: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_90));
    let __VLS_94;
    const __VLS_95 = ({ click: {} },
        { onClick: (__VLS_ctx.copyEmbed) });
    const { default: __VLS_96 } = __VLS_92.slots;
    (__VLS_ctx.copied ? 'Copied!' : 'Copy embed');
    // @ts-ignore
    [copyEmbed, copied,];
    var __VLS_92;
    var __VLS_93;
    // @ts-ignore
    [];
    var __VLS_49;
}
if (__VLS_ctx.roleCanScore && __VLS_ctx.startOverDlgOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
        'data-testid': "modal-start-over",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_97;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_98 = __VLS_asFunctionalComponent1(__VLS_97, new __VLS_97({
        padding: "lg",
        ...{ class: "modal-card" },
    }));
    const __VLS_99 = __VLS_98({
        padding: "lg",
        ...{ class: "modal-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_98));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    const { default: __VLS_102 } = __VLS_100.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-body-text" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedNextOverBowlerId),
        ...{ class: "sel" },
        'data-testid': "select-next-over-bowler",
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.eligibleNextOverBowlers))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        (__VLS_ctx.bowlerRoleBadge(p.id));
        // @ts-ignore
        [roleCanScore, bowlerRoleBadge, startOverDlgOpen, selectedNextOverBowlerId, eligibleNextOverBowlers,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    let __VLS_103;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_104 = __VLS_asFunctionalComponent1(__VLS_103, new __VLS_103({
        ...{ 'onClick': {} },
        variant: "ghost",
    }));
    const __VLS_105 = __VLS_104({
        ...{ 'onClick': {} },
        variant: "ghost",
    }, ...__VLS_functionalComponentArgsRest(__VLS_104));
    let __VLS_108;
    const __VLS_109 = ({ click: {} },
        { onClick: (__VLS_ctx.closeStartOver) });
    const { default: __VLS_110 } = __VLS_106.slots;
    // @ts-ignore
    [closeStartOver,];
    var __VLS_106;
    var __VLS_107;
    let __VLS_111;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_112 = __VLS_asFunctionalComponent1(__VLS_111, new __VLS_111({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedNextOverBowlerId),
        dataTestid: "confirm-start-over",
    }));
    const __VLS_113 = __VLS_112({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedNextOverBowlerId),
        dataTestid: "confirm-start-over",
    }, ...__VLS_functionalComponentArgsRest(__VLS_112));
    let __VLS_116;
    const __VLS_117 = ({ click: {} },
        { onClick: (__VLS_ctx.confirmStartOver) });
    const { default: __VLS_118 } = __VLS_114.slots;
    // @ts-ignore
    [selectedNextOverBowlerId, confirmStartOver,];
    var __VLS_114;
    var __VLS_115;
    // @ts-ignore
    [];
    var __VLS_100;
}
if (__VLS_ctx.roleCanScore && __VLS_ctx.startInningsDlgOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
        'data-testid': "modal-start-innings",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_119;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_120 = __VLS_asFunctionalComponent1(__VLS_119, new __VLS_119({
        padding: "lg",
        ...{ class: "modal-card" },
    }));
    const __VLS_121 = __VLS_120({
        padding: "lg",
        ...{ class: "modal-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_120));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    const { default: __VLS_124 } = __VLS_122.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-body-text" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.nextStrikerId),
        ...{ class: "sel" },
        'data-testid': "select-next-striker",
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.nextBattingXI))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        (__VLS_ctx.roleBadge(p.id));
        // @ts-ignore
        [roleBadge, roleCanScore, startInningsDlgOpen, nextStrikerId, nextBattingXI,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.nextNonStrikerId),
        ...{ class: "sel" },
        'data-testid': "select-next-nonstriker",
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.nextBattingXI))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
            disabled: (p.id === __VLS_ctx.nextStrikerId),
        });
        (p.name);
        (__VLS_ctx.roleBadge(p.id));
        // @ts-ignore
        [roleBadge, nextStrikerId, nextBattingXI, nextNonStrikerId,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.openingBowlerId),
        ...{ class: "sel" },
        'data-testid': "select-opening-bowler",
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.nextBowlingXI))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        (__VLS_ctx.bowlerRoleBadge(p.id));
        // @ts-ignore
        [bowlerRoleBadge, openingBowlerId, nextBowlingXI,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    let __VLS_125;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_126 = __VLS_asFunctionalComponent1(__VLS_125, new __VLS_125({
        ...{ 'onClick': {} },
        variant: "ghost",
    }));
    const __VLS_127 = __VLS_126({
        ...{ 'onClick': {} },
        variant: "ghost",
    }, ...__VLS_functionalComponentArgsRest(__VLS_126));
    let __VLS_130;
    const __VLS_131 = ({ click: {} },
        { onClick: (__VLS_ctx.closeStartInnings) });
    const { default: __VLS_132 } = __VLS_128.slots;
    // @ts-ignore
    [closeStartInnings,];
    var __VLS_128;
    var __VLS_129;
    let __VLS_133;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_134 = __VLS_asFunctionalComponent1(__VLS_133, new __VLS_133({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.nextStrikerId || !__VLS_ctx.nextNonStrikerId || __VLS_ctx.nextStrikerId === __VLS_ctx.nextNonStrikerId),
        dataTestid: "confirm-start-innings",
    }));
    const __VLS_135 = __VLS_134({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.nextStrikerId || !__VLS_ctx.nextNonStrikerId || __VLS_ctx.nextStrikerId === __VLS_ctx.nextNonStrikerId),
        dataTestid: "confirm-start-innings",
    }, ...__VLS_functionalComponentArgsRest(__VLS_134));
    let __VLS_138;
    const __VLS_139 = ({ click: {} },
        { onClick: (__VLS_ctx.confirmStartInnings) });
    const { default: __VLS_140 } = __VLS_136.slots;
    // @ts-ignore
    [nextStrikerId, nextStrikerId, nextNonStrikerId, nextNonStrikerId, confirmStartInnings,];
    var __VLS_136;
    var __VLS_137;
    // @ts-ignore
    [];
    var __VLS_122;
}
if (__VLS_ctx.roleCanScore && __VLS_ctx.selectBatterDlgOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
        'data-testid': "modal-select-batter",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_141;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_142 = __VLS_asFunctionalComponent1(__VLS_141, new __VLS_141({
        padding: "lg",
        ...{ class: "modal-card" },
    }));
    const __VLS_143 = __VLS_142({
        padding: "lg",
        ...{ class: "modal-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_142));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    const { default: __VLS_146 } = __VLS_144.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-body-text" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedNextBatterId),
        ...{ class: "sel" },
        'data-testid': "select-next-batter",
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    for (const [p] of __VLS_vFor((__VLS_ctx.candidateBatters))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        (__VLS_ctx.roleBadge(p.id));
        // @ts-ignore
        [roleBadge, roleCanScore, selectBatterDlgOpen, selectedNextBatterId, candidateBatters,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    let __VLS_147;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_148 = __VLS_asFunctionalComponent1(__VLS_147, new __VLS_147({
        ...{ 'onClick': {} },
        variant: "ghost",
    }));
    const __VLS_149 = __VLS_148({
        ...{ 'onClick': {} },
        variant: "ghost",
    }, ...__VLS_functionalComponentArgsRest(__VLS_148));
    let __VLS_152;
    const __VLS_153 = ({ click: {} },
        { onClick: (__VLS_ctx.closeSelectBatter) });
    const { default: __VLS_154 } = __VLS_150.slots;
    // @ts-ignore
    [closeSelectBatter,];
    var __VLS_150;
    var __VLS_151;
    let __VLS_155;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_156 = __VLS_asFunctionalComponent1(__VLS_155, new __VLS_155({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedNextBatterId),
        dataTestid: "confirm-select-batter",
    }));
    const __VLS_157 = __VLS_156({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedNextBatterId),
        dataTestid: "confirm-select-batter",
    }, ...__VLS_functionalComponentArgsRest(__VLS_156));
    let __VLS_160;
    const __VLS_161 = ({ click: {} },
        { onClick: (__VLS_ctx.confirmSelectBatter) });
    const { default: __VLS_162 } = __VLS_158.slots;
    // @ts-ignore
    [selectedNextBatterId, confirmSelectBatter,];
    var __VLS_158;
    var __VLS_159;
    // @ts-ignore
    [];
    var __VLS_144;
}
if (__VLS_ctx.weatherDlgOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_163;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_164 = __VLS_asFunctionalComponent1(__VLS_163, new __VLS_163({
        padding: "lg",
        ...{ class: "modal-card" },
    }));
    const __VLS_165 = __VLS_164({
        padding: "lg",
        ...{ class: "modal-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_164));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    const { default: __VLS_168 } = __VLS_166.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-body-text" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    let __VLS_169;
    /** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
    BaseInput;
    // @ts-ignore
    const __VLS_170 = __VLS_asFunctionalComponent1(__VLS_169, new __VLS_169({
        modelValue: (__VLS_ctx.weatherNote),
        label: "Note",
        placeholder: "Note (optional)",
        dataTestid: "input-weather-note",
    }));
    const __VLS_171 = __VLS_170({
        modelValue: (__VLS_ctx.weatherNote),
        label: "Note",
        placeholder: "Note (optional)",
        dataTestid: "input-weather-note",
    }, ...__VLS_functionalComponentArgsRest(__VLS_170));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions modal-actions--wrap" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    /** @type {__VLS_StyleScopedClasses['modal-actions--wrap']} */ ;
    let __VLS_174;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_175 = __VLS_asFunctionalComponent1(__VLS_174, new __VLS_174({
        ...{ 'onClick': {} },
        variant: "ghost",
        dataTestid: "btn-weather-close",
    }));
    const __VLS_176 = __VLS_175({
        ...{ 'onClick': {} },
        variant: "ghost",
        dataTestid: "btn-weather-close",
    }, ...__VLS_functionalComponentArgsRest(__VLS_175));
    let __VLS_179;
    const __VLS_180 = ({ click: {} },
        { onClick: (__VLS_ctx.closeWeather) });
    const { default: __VLS_181 } = __VLS_177.slots;
    // @ts-ignore
    [weatherDlgOpen, weatherNote, closeWeather,];
    var __VLS_177;
    var __VLS_178;
    let __VLS_182;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_183 = __VLS_asFunctionalComponent1(__VLS_182, new __VLS_182({
        ...{ 'onClick': {} },
        variant: "secondary",
        dataTestid: "btn-weather-resume",
    }));
    const __VLS_184 = __VLS_183({
        ...{ 'onClick': {} },
        variant: "secondary",
        dataTestid: "btn-weather-resume",
    }, ...__VLS_functionalComponentArgsRest(__VLS_183));
    let __VLS_187;
    const __VLS_188 = ({ click: {} },
        { onClick: (__VLS_ctx.resumeAfterWeather) });
    const { default: __VLS_189 } = __VLS_185.slots;
    // @ts-ignore
    [resumeAfterWeather,];
    var __VLS_185;
    var __VLS_186;
    let __VLS_190;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_191 = __VLS_asFunctionalComponent1(__VLS_190, new __VLS_190({
        ...{ 'onClick': {} },
        variant: "primary",
        dataTestid: "btn-weather-start",
    }));
    const __VLS_192 = __VLS_191({
        ...{ 'onClick': {} },
        variant: "primary",
        dataTestid: "btn-weather-start",
    }, ...__VLS_functionalComponentArgsRest(__VLS_191));
    let __VLS_195;
    const __VLS_196 = ({ click: {} },
        { onClick: (__VLS_ctx.startWeatherDelay) });
    const { default: __VLS_197 } = __VLS_193.slots;
    // @ts-ignore
    [startWeatherDelay,];
    var __VLS_193;
    var __VLS_194;
    if (__VLS_ctx.roleCanScore) {
        let __VLS_198;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_199 = __VLS_asFunctionalComponent1(__VLS_198, new __VLS_198({
            ...{ 'onClick': {} },
            variant: "secondary",
            disabled: (__VLS_ctx.needsNewInningsLive || !__VLS_ctx.canStartOverNow),
            title: (!__VLS_ctx.roleCanScore ? __VLS_ctx.proTooltip : undefined),
            dataTestid: "btn-weather-start-over",
        }));
        const __VLS_200 = __VLS_199({
            ...{ 'onClick': {} },
            variant: "secondary",
            disabled: (__VLS_ctx.needsNewInningsLive || !__VLS_ctx.canStartOverNow),
            title: (!__VLS_ctx.roleCanScore ? __VLS_ctx.proTooltip : undefined),
            dataTestid: "btn-weather-start-over",
        }, ...__VLS_functionalComponentArgsRest(__VLS_199));
        let __VLS_203;
        const __VLS_204 = ({ click: {} },
            { onClick: (__VLS_ctx.openStartOver) });
        const { default: __VLS_205 } = __VLS_201.slots;
        // @ts-ignore
        [roleCanScore, roleCanScore, openStartOver, canStartOverNow, needsNewInningsLive, proTooltip,];
        var __VLS_201;
        var __VLS_202;
    }
    // @ts-ignore
    [];
    var __VLS_166;
}
if (__VLS_ctx.changeBowlerDlgOpen) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-backdrop" },
        role: "dialog",
        'aria-modal': "true",
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    let __VLS_206;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_207 = __VLS_asFunctionalComponent1(__VLS_206, new __VLS_206({
        padding: "lg",
        ...{ class: "modal-card" },
    }));
    const __VLS_208 = __VLS_207({
        padding: "lg",
        ...{ class: "modal-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_207));
    /** @type {__VLS_StyleScopedClasses['modal-card']} */ ;
    const { default: __VLS_211 } = __VLS_209.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    (__VLS_ctx.isBowlerCorrection ? 'Correct Bowler' : 'Mid-over change (injury)');
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-body-text" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body-text']} */ ;
    (__VLS_ctx.isBowlerCorrection ? 'Select the correct bowler for this over.' : 'Pick a replacement to finish this over. You can do this only once per over.');
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedReplacementBowlerId),
        ...{ class: "sel" },
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        disabled: true,
        value: "",
    });
    (__VLS_ctx.isBowlerCorrection ? 'Choose correct bowler…' : 'Choose replacement…');
    for (const [p] of __VLS_vFor(((__VLS_ctx.isBowlerCorrection ? __VLS_ctx.eligibleCorrectionBowlers : __VLS_ctx.replacementOptions)))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (p.id),
            value: (p.id),
        });
        (p.name);
        (__VLS_ctx.bowlerRoleBadge(p.id));
        // @ts-ignore
        [bowlerRoleBadge, changeBowlerDlgOpen, isBowlerCorrection, isBowlerCorrection, isBowlerCorrection, isBowlerCorrection, selectedReplacementBowlerId, eligibleCorrectionBowlers, replacementOptions,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    let __VLS_212;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_213 = __VLS_asFunctionalComponent1(__VLS_212, new __VLS_212({
        ...{ 'onClick': {} },
        variant: "ghost",
    }));
    const __VLS_214 = __VLS_213({
        ...{ 'onClick': {} },
        variant: "ghost",
    }, ...__VLS_functionalComponentArgsRest(__VLS_213));
    let __VLS_217;
    const __VLS_218 = ({ click: {} },
        { onClick: (__VLS_ctx.closeChangeBowler) });
    const { default: __VLS_219 } = __VLS_215.slots;
    // @ts-ignore
    [closeChangeBowler,];
    var __VLS_215;
    var __VLS_216;
    let __VLS_220;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_221 = __VLS_asFunctionalComponent1(__VLS_220, new __VLS_220({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedReplacementBowlerId),
    }));
    const __VLS_222 = __VLS_221({
        ...{ 'onClick': {} },
        variant: "primary",
        disabled: (!__VLS_ctx.selectedReplacementBowlerId),
    }, ...__VLS_functionalComponentArgsRest(__VLS_221));
    let __VLS_225;
    const __VLS_226 = ({ click: {} },
        { onClick: (__VLS_ctx.confirmChangeBowler) });
    const { default: __VLS_227 } = __VLS_223.slots;
    (__VLS_ctx.isBowlerCorrection ? 'Correct' : 'Change');
    // @ts-ignore
    [isBowlerCorrection, selectedReplacementBowlerId, confirmChangeBowler,];
    var __VLS_223;
    var __VLS_224;
    // @ts-ignore
    [];
    var __VLS_209;
}
const __VLS_228 = DeliveryCorrectionModal;
// @ts-ignore
const __VLS_229 = __VLS_asFunctionalComponent1(__VLS_228, new __VLS_228({
    ...{ 'onClose': {} },
    ...{ 'onSubmit': {} },
    show: (__VLS_ctx.showCorrectionModal),
    delivery: (__VLS_ctx.correctionDelivery),
    bowlerName: (__VLS_ctx.correctionDelivery ? __VLS_ctx.playerNameById(__VLS_ctx.correctionDelivery.bowler_id) : undefined),
    batterName: (__VLS_ctx.correctionDelivery ? __VLS_ctx.playerNameById(__VLS_ctx.correctionDelivery.striker_id) : undefined),
}));
const __VLS_230 = __VLS_229({
    ...{ 'onClose': {} },
    ...{ 'onSubmit': {} },
    show: (__VLS_ctx.showCorrectionModal),
    delivery: (__VLS_ctx.correctionDelivery),
    bowlerName: (__VLS_ctx.correctionDelivery ? __VLS_ctx.playerNameById(__VLS_ctx.correctionDelivery.bowler_id) : undefined),
    batterName: (__VLS_ctx.correctionDelivery ? __VLS_ctx.playerNameById(__VLS_ctx.correctionDelivery.striker_id) : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_229));
let __VLS_233;
const __VLS_234 = ({ close: {} },
    { onClose: (__VLS_ctx.closeCorrectionModal) });
const __VLS_235 = ({ submit: {} },
    { onSubmit: (__VLS_ctx.submitCorrection) });
var __VLS_231;
var __VLS_232;
// @ts-ignore
[playerNameById, playerNameById, showCorrectionModal, correctionDelivery, correctionDelivery, correctionDelivery, correctionDelivery, correctionDelivery, closeCorrectionModal, submitCorrection,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
