/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
/* eslint-disable */
import { storeToRefs } from 'pinia';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { RouterLink } from 'vue-router';
import { BaseButton, BaseBadge } from '@/components';
import { useHighlights } from '@/composables/useHighlights';
import { useRoleBadge } from '@/composables/useRoleBadge';
import { useGameStore } from '@/stores/gameStore';
import { isValidUUID } from '@/utils';
import { fmtSR, oversDisplayFromBalls, oversDisplayFromAny, deriveBowlerFigures } from '@/utils/cricket';
import WinProbabilityChart from '@/components/WinProbabilityChart.vue';
const props = withDefaults(defineProps(), {
    apiBase: '',
    theme: 'dark',
    title: 'Live Scoreboard',
    interruptionsMode: 'auto',
    pollMs: 5000,
    canControl: false,
});
/* ---------------------------------- */
/* Store: single source of truth      */
/* ---------------------------------- */
const gameStore = useGameStore();
const { currentGame, error: storeError, dlsPanel, interruptions, currentInterruption, state, battingRowsXI, bowlingRowsXI, liveSnapshot, currentBowlerFigures: bowlerRow, isGameOver, resultText, currentPrediction, } = storeToRefs(gameStore);
const { targetSafe, requiredRunRate, runsRequired, ballsBowledTotal } = storeToRefs(gameStore);
/* ---------------------- */
/* Bootstrapping (NEW)    */
/* ---------------------- */
let pollTimer = null;
const ownsLive = ref(false);
async function startFeed() {
    console.log('[ScoreboardWidget] startFeed gameId:', props.gameId);
    // Ensure we have the game model to render names/score even before first event
    try {
        if (!currentGame.value || currentGame.value.id !== props.gameId) {
            await gameStore.loadGame(props.gameId);
        }
    }
    catch { }
    if (props.interruptionsMode === 'off') {
        return;
    }
    // Prefer sockets in 'socket' or 'auto'
    const wantSocket = props.interruptionsMode === 'socket' || props.interruptionsMode === 'auto';
    if (wantSocket) {
        try {
            if (gameStore.liveGameId !== props.gameId) {
                await gameStore.initLive(props.gameId);
                ownsLive.value = true;
            }
        }
        catch {
            // ignore; we’ll fall back to polling below if in 'auto'
        }
    }
    // Always fetch once so the banner can show immediately
    try {
        console.log('[ScoreboardWidget] calling refreshInterruptions');
        await gameStore.refreshInterruptions();
    }
    catch { }
    // Poll if: explicitly 'poll' OR 'auto' but not connected
    const shouldPoll = props.interruptionsMode === 'poll' ||
        (props.interruptionsMode === 'auto' && gameStore.connectionStatus !== 'connected');
    if (shouldPoll) {
        stopPoll();
        pollTimer = window.setInterval(() => { void gameStore.refreshInterruptions(); }, props.pollMs);
    }
}
function stopPoll() {
    if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
    }
}
function teardown() {
    stopPoll();
    // Only stop the socket if *this* widget started it
    if (ownsLive.value) {
        gameStore.stopLive();
        ownsLive.value = false;
    }
}
watch(() => props.gameId, async () => {
    teardown();
    await startFeed();
});
onMounted(() => { void startFeed(); });
onUnmounted(() => teardown());
/* -------------------- */
/* Exposed to parent    */
/* -------------------- */
const __VLS_exposed = {
    refreshInterruptions: () => gameStore.refreshInterruptions(),
};
defineExpose(__VLS_exposed);
const base = computed(() => props.apiBase?.replace(/\/$/, '') || window.location.origin.replace(/\/$/, ''));
const resolvedSponsorsUrl = computed(() => props.sponsorsUrl || `${base.value}/games/${encodeURIComponent(props.gameId)}/sponsors`);
const sponsorsBase = computed(() => {
    try {
        return new URL(resolvedSponsorsUrl.value, window.location.href);
    }
    catch {
        return null;
    }
});
const sponsors = ref([]);
const sponsorsLoading = ref(false);
function toAbsolute(url) {
    if (!url)
        return '';
    if (/^(https?:)?\/\//i.test(url) || /^(data|blob):/i.test(url))
        return url;
    try {
        if (sponsorsBase.value)
            return new URL(url, sponsorsBase.value).toString();
    }
    catch { }
    const originBase = (props.apiBase?.replace(/\/$/, '') || window.location.origin.replace(/\/$/, ''));
    if (url.startsWith('/'))
        return `${originBase}${url}`.replace(/([^:]\/)\/+/g, '$1');
    if (url.startsWith('static/'))
        return `${originBase}/${url}`.replace(/([^:]\/)\/+/g, '$1');
    return url;
}
const logoUrl = computed(() => toAbsolute(props.logo || ''));
const logoOk = ref(true);
function onLogoErr() { logoOk.value = false; }
// --- helpers ---
function sponsorImg(s) {
    const raw = typeof s === 'string' ? s : (s.logoUrl || s.image_url || s.img || '');
    return toAbsolute(raw);
}
function sponsorHref(s) {
    const raw = typeof s === 'string' ? undefined : (s.clickUrl || s.link_url || s.url || undefined);
    return raw ? toAbsolute(raw) : undefined;
}
function sponsorAlt(s) {
    if (typeof s === 'string')
        return 'Sponsor';
    return s.alt || s.name || 'Sponsor';
}
// NEW: read a per-item max size, fallback to the CSS default
function railMaxPx(s, fallback = 72) {
    if (!s || typeof s === 'string')
        return `${fallback}px`;
    const raw = s.maxPx ?? s.size;
    if (raw == null)
        return `${fallback}px`;
    const n = typeof raw === 'string' ? parseInt(raw, 10) : Number(raw);
    return Number.isFinite(n) && n > 0 ? `${n}px` : `${fallback}px`;
}
// --- choose left/right (explicit rail beats index order) ---
const leftSponsor = computed(() => sponsors.value.find(s => typeof s !== 'string' && s.rail === 'left')
    ?? sponsors.value?.[0] ?? null);
const rightSponsor = computed(() => sponsors.value.find(s => typeof s !== 'string' && s.rail === 'right')
    ?? sponsors.value?.[1] ?? null);
const badgeSponsor = computed(() => sponsors.value.find(s => typeof s !== 'string' && s.rail === 'badge')
    ?? sponsors.value?.[2] ?? sponsors.value?.[0] ?? null);
// Accept {items:[]}, {sponsors:[]}, {data:[]}, or [] directly
function normalizeSponsors(raw) {
    const arr = Array.isArray(raw?.items) ? raw.items
        : Array.isArray(raw?.sponsors) ? raw.sponsors
            : Array.isArray(raw?.data) ? raw.data
                : Array.isArray(raw) ? raw
                    : [];
    return arr
        .map((it) => {
        if (typeof it === 'string')
            return it;
        const logo = it.logoUrl || it.image_url || it.img || it.logo || it.path || it.src;
        const link = it.clickUrl || it.link_url || it.url;
        const alt = it.alt || it.name;
        return { logoUrl: logo, clickUrl: link, alt };
    })
        .filter((it) => typeof it === 'string' ? true : Boolean(it.logoUrl));
}
async function loadSponsors() {
    sponsorsLoading.value = true;
    try {
        const apiOrigin = base.value.replace(/\/$/, '');
        const raw = (resolvedSponsorsUrl.value || '').replace(/^\s+|\s+$/g, '');
        // Build candidates: user-provided first, then common mounts
        const candidates = [];
        const absolutize = (p) => /^https?:\/\//i.test(p) || p.startsWith('//')
            ? p
            : p.startsWith('/') ? `${apiOrigin}${p}` : `${apiOrigin}/${p}`;
        if (raw)
            candidates.push(absolutize(raw));
        // helpful fallbacks for your setup
        candidates.push(`${apiOrigin}/sponsors/cricksy/sponsors.json`, `${apiOrigin}/cricksy/sponsors.json`, `${apiOrigin}/static/sponsors/cricksy/sponsors.json`);
        let lastErr = null;
        for (const url of candidates) {
            try {
                console.info('[Sponsors] GET', url);
                const res = await fetch(url, { cache: 'no-store', mode: 'cors', headers: { Accept: 'application/json' } });
                const ct = res.headers.get('content-type') || '';
                if (!res.ok || !ct.includes('application/json')) {
                    const preview = (await res.text()).slice(0, 200);
                    console.warn('[Sponsors] skip', url, res.status, ct, preview);
                    continue;
                }
                const data = await res.json();
                const arr = normalizeSponsors(data);
                sponsors.value = arr;
                console.info('[Sponsors] parsed', arr);
                return;
            }
            catch (e) {
                lastErr = e;
            }
        }
        console.error('[Sponsors] failed all candidates', lastErr);
        sponsors.value = []; // render without sponsors
    }
    finally {
        sponsorsLoading.value = false;
    }
}
const teamA = computed(() => currentGame.value?.team_a || {});
const teamB = computed(() => currentGame.value?.team_b || {});
function bestTeamNameShape(t) {
    return String(t?.name ?? t?.team_name ?? t?.short_name ?? t?.abbr ?? '');
}
const teamAName = computed(() => bestTeamNameShape(teamA.value));
const teamBName = computed(() => bestTeamNameShape(teamB.value));
const teamAId = computed(() => String(teamA.value?.id ?? ''));
const teamBId = computed(() => String(teamB.value?.id ?? ''));
const currentInningNo = computed(() => Number(currentGame.value?.current_inning ?? 1));
const battingTeamId = computed(() => String(currentGame.value?.batting_team_id ?? ''));
const battingTeamName = computed(() => currentGame.value?.batting_team_name
    ?? (battingTeamId.value === teamAId.value ? teamAName.value
        : battingTeamId.value === teamBId.value ? teamBName.value
            : ''));
const bowlingTeamName = computed(() => currentGame.value?.bowlingTeamName
    ?? currentGame.value?.bowling_team_name
    ?? '');
// ✅ Deterministic: who played the FIRST innings?
const innings1TeamName = computed(() => {
    if (currentInningNo.value === 1) {
        // first innings still in progress
        return battingTeamName.value || teamAName.value || teamBName.value || '';
    }
    // second innings -> the other side batted first
    if (battingTeamId.value && teamAId.value && teamBId.value) {
        return battingTeamId.value === teamAId.value ? teamBName.value : teamAName.value;
    }
    const bt = String(currentGame.value?.batting_team_name || '');
    if (bt && bt === teamAName.value)
        return teamBName.value;
    if (bt && bt === teamBName.value)
        return teamAName.value;
    return '';
});
watch(resolvedSponsorsUrl, () => { void loadSponsors(); });
onMounted(() => { void loadSponsors(); });
/* ----------------- */
/* Small UI helpers  */
/* ----------------- */
function elapsedSince(iso) {
    if (!iso)
        return '';
    const start = new Date(iso).getTime();
    const ms = Math.max(0, Date.now() - start);
    const m = Math.floor(ms / 60000);
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return h ? `${h}h ${String(mm).padStart(2, '0')}m` : `${m}m`;
}
/* ----------------------------- */
/* Derived scoreboard from store */
/* ----------------------------- */
const sAny = computed(() => (state.value || {}));
// All deliveries (model or live state), newest last
const allDeliveries = computed(() => {
    const fromState = Array.isArray(state.value?.recent_deliveries)
        ? state.value.recent_deliveries
        : [];
    const fromModel = Array.isArray(currentGame.value?.deliveries)
        ? currentGame.value.deliveries
        : [];
    const combined = fromModel.length ? [...fromModel, ...fromState] : fromState;
    return combined.length ? dedupeByKey(combined) : [];
});
// Prefer server’s total if present; else fall back to derived legal balls; else model counters.
const totalBallsThisInnings = computed(() => deliveriesThisInnings.value.filter(isLegal).length);
const oversText = computed(() => oversDisplayFromBalls(totalBallsThisInnings.value));
// Totals (prefer live state, then snapshot, then model)
const runs = computed(() => Number(sAny.value?.total_runs ?? liveSnapshot.value?.total_runs ?? currentGame.value?.total_runs ?? 0));
const wkts = computed(() => Number(sAny.value?.total_wickets ??
    liveSnapshot.value?.total_wickets ??
    currentGame.value?.total_wickets ?? 0));
// Rates now based on backend calculations (NO local fallback allowed)
const crr = computed(() => {
    // FIX B1: Use backend-calculated current_run_rate ONLY
    // Remove local fallback - if backend doesn't send it, show '—'
    const backendCrr = liveSnapshot.value?.current_run_rate;
    return backendCrr != null ? backendCrr.toFixed(2) : '—';
});
// Show CRR only when backend provides it
const showCrr = computed(() => liveSnapshot.value?.current_run_rate != null);
const parTxt = computed(() => {
    const p = dlsPanel.value;
    return typeof p?.par === 'number' ? String(p.par) : null;
});
const targetDisplay = computed(() => {
    const t = targetSafe?.value;
    if (t == null || Number.isNaN(Number(t)))
        return null;
    return Number(t);
});
function makeKey(d) {
    // innings number (support multiple possible field names)
    const inn = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number ?? 0);
    // normalize over & ball into integers: over=0.., ball=0..5
    const { over, ball } = parseOverBall(d);
    // include distinguishing payload so wides/no-balls don’t collapse into the legal ball
    const ex = String(d.extra ?? d.extra_type ?? ''); // '', 'wd', 'nb', 'b', 'lb', ...
    const rb = Number(d.runs_off_bat ?? d.runs ?? 0); // off-bat runs (for nbs)
    const rs = Number(d.runs_scored ?? d.extra_runs ?? 0); // total/extra runs
    const w = d.is_wicket ? 1 : 0; // wicket flag
    // Only identical re-sends will produce the same key
    return `${inn}:${over}:${ball}:${ex}:${rb}:${rs}:${w}`;
}
// ADD this helper right after makeKey
function dedupeByKey(arr) {
    const byKey = new Map();
    for (const d of arr)
        byKey.set(makeKey(d), d); // last write wins
    return Array.from(byKey.values());
}
const allDeliveriesRaw = computed(() => allDeliveries.value);
// only this innings; if there are no innings markers at all, fall back to everything for innings 1, else empty
// helper: is the ball legal (consumes ball)
const isLegal = (d) => {
    const x = String(d.extra ?? d.extra_type ?? '');
    return x !== 'wd' && x !== 'nb';
};
function parseOversNotation(s) {
    // Accept "13.3" or 13.3; clamp balls 0..5
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
const overStr = computed(() => 
// Prefer canonical "overs" (e.g., "13.3"); fallback to completed+this_over
currentGame.value?.overs ??
    `${currentGame.value?.overs_completed ?? 0}.${currentGame.value?.balls_this_over ?? 0}`);
const ocob = computed(() => parseOversNotation(overStr.value));
const oversC = computed(() => ocob.value.oc);
const ballsO = computed(() => ocob.value.ob);
const ballsBowled = computed(() => totalBallsThisInnings.value);
const legalBallsThisOver = computed(() => {
    if (!deliveriesThisInnings.value.length)
        return 0;
    const lastOver = Math.max(...deliveriesThisInnings.value.map(d => {
        const o = d.over_number ?? d.over;
        return typeof o === 'number' ? Math.floor(o) : Number(String(o).split('.')[0] || 0);
    }));
    return deliveriesThisInnings.value.filter(d => {
        const o = d.over_number ?? d.over;
        const over = typeof o === 'number' ? Math.floor(o) : Number(String(o).split('.')[0] || 0);
        return over === lastOver && isLegal(d);
    }).length % 6;
});
// If the server ever omits "overs", uncomment the next line to force fallback:
// const ballsO = computed(() => overStr.value ? ocob.value.ob : legalBallsThisOver.value)
const oversLimit = computed(() => Number(currentGame.value?.overs_limit ?? 0));
const target = computed(() => (currentGame.value?.target ?? null));
const isSecondInnings = computed(() => Number(currentGame.value?.current_inning ?? 1) === 2);
// Chase mode: second innings with a valid target set
const isChase = computed(() => isSecondInnings.value && targetSafe.value != null && targetSafe.value > 0);
// RRR: prefer store value, fallback to local calculation
const rrr = computed(() => {
    // Use store's requiredRunRate if available
    if (requiredRunRate.value != null && Number.isFinite(requiredRunRate.value)) {
        return requiredRunRate.value.toFixed(2);
    }
    // Fallback to local calculation
    if (!isSecondInnings.value || target.value == null)
        return null;
    const need = Math.max(0, target.value - runs.value);
    if (!oversLimit.value)
        return null;
    const remBalls = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value);
    if (remBalls <= 0)
        return null;
    return (need / (remBalls / 6)).toFixed(2);
});
const oversLeft = computed(() => {
    if (!oversLimit.value)
        return null;
    const rem = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value);
    return rem > 0 ? oversDisplayFromBalls(rem) : null;
});
// --- First-innings summary (derive from deliveries if innings markers exist)
function inningsOf(d) {
    const v = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number);
    return Number.isFinite(v) ? v : null;
}
const currentInningsNo = computed(() => Number(currentGame.value?.current_inning ?? 1));
const deliveriesThisInnings = computed(() => hasInningsMarkers.value
    ? allDeliveries.value.filter(d => Number(inningsOf(d)) === currentInningsNo.value)
    : allDeliveries.value // old data with no innings markers
);
// Derived, per-bowler figures (runs/balls/maidens/overs/econ) for *this innings*
const figuresByBowler = computed(() => {
    const map = {};
    // collect unique bowler ids seen in this innings
    const ids = Array.from(new Set(deliveriesThisInnings.value
        .map(d => String(d.bowler_id ?? ''))
        .filter(Boolean)));
    for (const id of ids) {
        map[id] = deriveBowlerFigures(deliveriesThisInnings.value, id);
    }
    return map;
});
const legalBallsThisInningsDerived = computed(() => deliveriesThisInnings.value.filter(d => {
    const ex = String(d.extra ?? d.extra_type ?? '');
    return ex !== 'wd' && ex !== 'nb';
}).length);
const hasInningsMarkers = computed(() => allDeliveriesRaw.value.some(d => inningsOf(d) != null));
// De-dupe first-innings feed so the last ball isn't double-counted
const innings1Deliveries = computed(() => hasInningsMarkers.value
    ? dedupeByKey(allDeliveriesRaw.value.filter(d => inningsOf(d) === 1))
    : []);
// Total runs for one delivery (robust across legal+extras)
function totalRunsOf(d) {
    const ex = String(d.extra ?? d.extra_type ?? '');
    const rb = Number(d.runs_off_bat ?? d.runs ?? 0); // off the bat
    const rs = Number(d.runs_scored ?? d.extra_runs ?? 0); // backend "total" if present
    if (ex === 'wd')
        return rs || Math.max(1, Number(d.extra_runs ?? 1));
    if (ex === 'nb')
        return (rs || 0) || (1 + rb); // prefer rs if provided
    if (ex === 'b' || ex === 'lb')
        return rs || Number(d.extra_runs ?? 0);
    return rs || rb; // legal: off bat (or total)
}
// Balls = legal only (wides/no-balls don't consume a ball)
const innings1 = computed(() => {
    if (!innings1Deliveries.value.length)
        return null;
    const legal = (d) => {
        const ex = String(d.extra ?? d.extra_type ?? '');
        return ex !== 'wd' && ex !== 'nb';
    };
    const balls = innings1Deliveries.value.filter(legal).length;
    const runs = innings1Deliveries.value.reduce((s, d) => s + totalRunsOf(d), 0);
    const wkts = innings1Deliveries.value.filter(d => Boolean(d.is_wicket)).length;
    return { runs, wkts, balls };
});
const innings1Line = computed(() => {
    const snap = liveSnapshot.value;
    // If we're in innings 2 or later, ALWAYS use the snapshot summary (most reliable)
    if (currentInningsNo.value >= 2) {
        const summary = snap?.first_inning_summary || snap?.first_innings_summary;
        if (summary) {
            const runs = summary.runs ?? 0;
            const wickets = summary.wickets ?? 0;
            const overs = summary.overs ?? 0;
            return `${runs}/${wickets} (${overs} ov)`;
        }
    }
    // For live innings 1, calculate from deliveries
    if (innings1.value) {
        return `${innings1.value.runs}/${innings1.value.wkts} (${oversDisplayFromBalls(innings1.value.balls)} ov)`;
    }
    return null;
});
// === Highlights (FOUR/SIX/WICKET/DUCK/50/100) =========================
const enableHighlights = ref(true); // make a prop later if you want
const highlightMs = ref(1800);
const { current: highlight, // <- 'FOUR' | 'SIX' | 'WICKET' | 'DUCK' | 'FIFTY' | 'HUNDRED' | null
enqueueFromSnapshots, reset: resetHighlights, } = useHighlights(enableHighlights, highlightMs);
const prevHL = ref(null);
// map your Pinia/live snapshot to the useHighlights Snapshot shape
function mapToHL(s) {
    const g = currentGame.value || {};
    const card = (g.batting_scorecard || {});
    const findName = (id) => {
        if (!id)
            return '';
        const tA = g.team_a?.players || [];
        const tB = g.team_b?.players || [];
        return (tA.find((p) => String(p.id) === String(id))?.name ||
            tB.find((p) => String(p.id) === String(id))?.name ||
            card[String(id)]?.player_name ||
            '');
    };
    const mkBatter = (id) => {
        if (!id)
            return undefined;
        const row = card[String(id)] || {};
        return {
            id: String(id),
            name: findName(id),
            runs: Number(row?.runs ?? 0),
            balls: Number(row?.balls_faced ?? row?.balls ?? 0),
            out: Boolean(row?.is_out),
        };
    };
    const ld = s?.last_delivery;
    const runsOffBat = Number(ld?.runs_scored ?? ld?.runs ?? 0);
    const isExtra = Boolean(ld?.is_extra ?? (ld?.extra_type != null));
    const lastBall = ld
        ? {
            runs: runsOffBat,
            // count only off-the-bat 4/6 as boundaries; tweak if you want “wide four” etc.
            isBoundary4: !isExtra && runsOffBat === 4,
            isBoundary6: !isExtra && runsOffBat === 6,
            isWicket: Boolean(ld?.is_wicket),
            dismissedBatterId: ld?.dismissed_player_id ? String(ld.dismissed_player_id) : undefined,
        }
        : undefined;
    return {
        total: {
            runs: Number(s?.total_runs ?? g.total_runs ?? 0),
            wickets: Number(s?.total_wickets ?? g.total_wickets ?? 0),
        },
        striker: mkBatter(s?.current_striker_id ?? g.current_striker_id),
        nonStriker: mkBatter(s?.current_non_striker_id ?? g.current_non_striker_id),
        lastBall,
    };
}
// enqueue on every live snapshot change (skip first paint)
watch(liveSnapshot, (next) => {
    if (!next)
        return;
    const nextHL = mapToHL(next);
    if (prevHL.value)
        enqueueFromSnapshots(prevHL.value, nextHL);
    prevHL.value = nextHL;
}, { deep: true });
onUnmounted(() => { resetHighlights(); });
const battingRows = computed(() => (battingRowsXI.value || []).map((r) => ({
    id: String(r.id),
    name: String(r.name),
    runs: Number(r.runs ?? 0),
    balls: Number(r.balls ?? r.balls_faced ?? 0),
    fours: Number(r.fours ?? 0),
    sixes: Number(r.sixes ?? 0),
    sr: typeof r.sr === 'number' ? r.sr : Number(r.sr ?? 0),
    isOut: Boolean(r.isOut ?? r.is_out),
    howOut: r.howOut ?? r.how_out ?? undefined,
})));
const bowlingRows = computed(() => (bowlingRowsXI.value || []).map((r) => {
    const id = String(r.id);
    const fig = figuresByBowler.value[id];
    return {
        id,
        name: String(r.name),
        overs: fig?.oversText ?? oversDisplayFromAny(r),
        maidens: fig?.maidens ?? Number(r.maidens ?? 0),
        runs: fig?.runs ?? Number(r.runs ?? r.runs_conceded ?? 0),
        wkts: Number(r.wkts ?? r.wickets_taken ?? 0), // keep server wickets
        econ: fig?.econText ?? (typeof r.econ === 'number' ? r.econ : Number(r.econ ?? 0)),
    };
}));
// --- Decide strike swap from the last delivery (handles wd/nb running correctly)
function shouldSwapStrikeFromLast(ld) {
    if (!ld)
        return false;
    const x = String(ld.extra_type ?? ld.extra ?? '');
    if (!x || x === 'b' || x === 'lb') {
        const offBat = Number(ld.runs_off_bat ?? ld.runs_scored ?? ld.runs ?? 0);
        return (offBat % 2) === 1;
    }
    if (x === 'wd') {
        // wides: only *run(s) actually run* flip strike
        const total = Math.max(1, Number(ld.runs_scored ?? ld.extra_runs ?? 1));
        const runsRun = total - 1;
        return (runsRun % 2) === 1;
    }
    if (x === 'nb') {
        // no-ball: penalty 1 + off-bat (and any extra beyond penalty)
        const offBat = Number(ld.runs_off_bat ?? 0);
        const extraBeyondPenalty = Math.max(0, Number(ld.extra_runs ?? 1) - 1);
        return ((offBat + extraBeyondPenalty) % 2) === 1;
    }
    return false;
}
const safeStrikerId = computed(() => {
    const g = currentGame.value || {};
    const st = String(state.value?.current_striker_id ??
        liveSnapshot.value?.current_striker_id ??
        g.current_striker_id ?? '') || null;
    const nst = String(state.value?.current_non_striker_id ??
        liveSnapshot.value?.current_non_striker_id ??
        g.current_non_striker_id ?? '') || null;
    if (st && nst && st === nst) {
        const ld = state.value?.last_delivery ?? g.last_delivery;
        return shouldSwapStrikeFromLast(ld) ? nst : st;
    }
    return st;
});
const safeNonStrikerId = computed(() => {
    const g = currentGame.value || {};
    const st = String(state.value?.current_striker_id ??
        liveSnapshot.value?.current_striker_id ??
        g.current_striker_id ?? '') || null;
    const nst = String(state.value?.current_non_striker_id ??
        liveSnapshot.value?.current_non_striker_id ??
        g.current_non_striker_id ?? '') || null;
    if (st && nst && st === nst) {
        const ld = state.value?.last_delivery ?? g.last_delivery;
        return shouldSwapStrikeFromLast(ld) ? st : nst;
    }
    return nst;
});
// striker/non-striker lookups
const strikerRow = computed(() => safeStrikerId.value
    ? battingRows.value.find(r => String(r.id) === safeStrikerId.value) || null
    : null);
const nonStrikerRow = computed(() => safeNonStrikerId.value
    ? battingRows.value.find(r => String(r.id) === safeNonStrikerId.value) || null
    : null);
/* ---------------------------------- */
/* Captain / Keeper badge helpers     */
/* ---------------------------------- */
const isBattingTeamA = computed(() => battingTeamName.value === teamAName.value);
const { roleBadge } = useRoleBadge({
    currentGame,
    isBattingTeamA,
});
function parseOverBall(d) {
    const overLike = d?.over_number ?? d?.over;
    const ballLike = d?.ball_number ?? d?.ball;
    if (typeof ballLike === 'number' && typeof overLike === 'number')
        return { over: Math.max(0, Math.floor(overLike)), ball: Math.max(0, ballLike) };
    if (typeof overLike === 'string') {
        const [o, b] = overLike.split('.');
        return { over: Number(o) || 0, ball: Number(b) || 0 };
    }
    if (typeof overLike === 'number') {
        const whole = Math.floor(overLike);
        const tenth = Math.round((overLike - whole) * 10);
        return { over: whole, ball: Math.max(0, Math.min(5, tenth)) };
    }
    return { over: 0, ball: 0 };
}
function outcomeTag(d) {
    const ex = (d.extra || '');
    const rb = Number(d.runs_off_bat ?? d.runs_scored ?? 0);
    const re = Number(d.runs_scored ?? 0);
    if (d.is_wicket)
        return 'W';
    if (ex === 'wd')
        return re > 1 ? `Wd+${re - 1}` : 'Wd';
    if (ex === 'nb')
        return rb ? `Nb+${rb}` : 'Nb';
    if (ex === 'b')
        return re ? `B${re}` : 'B';
    if (ex === 'lb')
        return re ? `LB${re}` : 'LB';
    return String(rb || re || 0);
}
function ballLabel(d) {
    const { over, ball } = parseOverBall(d);
    const parts = [`${over}.${ball}`, outcomeTag(d)];
    if (d.commentary)
        parts.push(`— ${d.commentary}`);
    return parts.join(' ');
}
const recentDeliveries = computed(() => deliveriesThisInnings.value.slice(-10) // (de-dup already applied above)
);
// Current bowler (safe id + name + derived figures)
const safeCurrentBowlerId = computed(() => {
    const s = state.value || {};
    const id = s.current_bowler_id ?? s.last_ball_bowler_id ?? currentGame.value?.current_bowler_id;
    return id != null ? String(id) : null;
});
const safeCurrentBowlerName = computed(() => {
    const id = safeCurrentBowlerId.value;
    if (!id)
        return '';
    const row = (bowlingRowsXI.value || []).find((p) => String(p.id) === id);
    if (row?.name)
        return String(row.name);
    // Fallback: look in the team roster
    const g = currentGame.value;
    if (!g)
        return '';
    const p = [...(g.team_a?.players || []), ...(g.team_b?.players || [])].find(p => String(p.id) === id);
    return p?.name || '';
});
const currentBowlerDerived = computed(() => {
    const id = safeCurrentBowlerId.value;
    return id ? figuresByBowler.value[id] : undefined;
});
const currentBowlerWkts = computed(() => {
    const id = safeCurrentBowlerId.value;
    if (!id)
        return 0;
    const r = bowlingRowsXI.value.find((p) => String(p.id) === id);
    return Number((r?.wkts ?? r?.wickets_taken ?? 0));
});
/* ------------------- */
/* Interruption control */
/* ------------------- */
const showInterruptionBanner = computed(() => !!currentInterruption.value);
const interBusy = ref(false);
async function startDelay(kind = 'weather', note) {
    if (interBusy.value)
        return;
    interBusy.value = true;
    try {
        await gameStore.startInterruption(kind, note);
    }
    finally {
        interBusy.value = false;
    }
}
async function resumePlay(kind = 'weather') {
    if (interBusy.value)
        return;
    interBusy.value = true;
    try {
        await gameStore.stopInterruption(kind);
    }
    finally {
        interBusy.value = false;
    }
}
const __VLS_defaults = {
    apiBase: '',
    theme: 'dark',
    title: 'Live Scoreboard',
    interruptionsMode: 'auto',
    pollMs: 5000,
    canControl: false,
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
/** @type {__VLS_StyleScopedClasses['rail-large']} */ ;
/** @type {__VLS_StyleScopedClasses['sponsor-rail']} */ ;
/** @type {__VLS_StyleScopedClasses['board']} */ ;
/** @type {__VLS_StyleScopedClasses['sponsor-rail']} */ ;
/** @type {__VLS_StyleScopedClasses['rail-large']} */ ;
/** @type {__VLS_StyleScopedClasses['rail-large']} */ ;
/** @type {__VLS_StyleScopedClasses['badge-sponsor']} */ ;
/** @type {__VLS_StyleScopedClasses['badge-sponsor']} */ ;
/** @type {__VLS_StyleScopedClasses['badge-sponsor']} */ ;
/** @type {__VLS_StyleScopedClasses['interrupt-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['interrupt-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['interrupt-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['interrupt-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['first-inn']} */ ;
/** @type {__VLS_StyleScopedClasses['first-inn']} */ ;
/** @type {__VLS_StyleScopedClasses['info-strip']} */ ;
/** @type {__VLS_StyleScopedClasses['info-strip']} */ ;
/** @type {__VLS_StyleScopedClasses['lbl']} */ ;
/** @type {__VLS_StyleScopedClasses['info-strip']} */ ;
/** @type {__VLS_StyleScopedClasses['cell']} */ ;
/** @type {__VLS_StyleScopedClasses['info-strip']} */ ;
/** @type {__VLS_StyleScopedClasses['grid-3']} */ ;
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['pane']} */ ;
/** @type {__VLS_StyleScopedClasses['ov']} */ ;
/** @type {__VLS_StyleScopedClasses['teams']} */ ;
/** @type {__VLS_StyleScopedClasses['label']} */ ;
/** @type {__VLS_StyleScopedClasses['batting-table']} */ ;
/** @type {__VLS_StyleScopedClasses['bowling-table']} */ ;
/** @type {__VLS_StyleScopedClasses['ball']} */ ;
/** @type {__VLS_StyleScopedClasses['hl-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['hl-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['player-link']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['pane']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "board" },
    'data-theme': (__VLS_ctx.theme),
});
/** @type {__VLS_StyleScopedClasses['board']} */ ;
if (__VLS_ctx.highlight) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "hl-banner" },
        'aria-live': "polite",
    });
    /** @type {__VLS_StyleScopedClasses['hl-banner']} */ ;
    if (__VLS_ctx.highlight === 'FOUR') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.highlight === 'SIX') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.highlight === 'WICKET') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.highlight === 'DUCK') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.highlight === 'FIFTY') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else if (__VLS_ctx.highlight === 'HUNDRED') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
}
if (__VLS_ctx.leftSponsor) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
        ...{ class: "sponsor-rail rail-left rail-large" },
    });
    /** @type {__VLS_StyleScopedClasses['sponsor-rail']} */ ;
    /** @type {__VLS_StyleScopedClasses['rail-left']} */ ;
    /** @type {__VLS_StyleScopedClasses['rail-large']} */ ;
    const __VLS_0 = (__VLS_ctx.sponsorHref(__VLS_ctx.leftSponsor) ? 'a' : 'div');
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        href: (__VLS_ctx.sponsorHref(__VLS_ctx.leftSponsor)),
        target: "_blank",
        rel: "noopener",
        ...{ class: "rail-link" },
    }));
    const __VLS_2 = __VLS_1({
        href: (__VLS_ctx.sponsorHref(__VLS_ctx.leftSponsor)),
        target: "_blank",
        rel: "noopener",
        ...{ class: "rail-link" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['rail-link']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        src: (__VLS_ctx.sponsorImg(__VLS_ctx.leftSponsor)),
        alt: (__VLS_ctx.sponsorAlt(__VLS_ctx.leftSponsor)),
    });
    // @ts-ignore
    [theme, highlight, highlight, highlight, highlight, highlight, highlight, highlight, leftSponsor, leftSponsor, leftSponsor, leftSponsor, leftSponsor, sponsorHref, sponsorHref, sponsorImg, sponsorAlt,];
    var __VLS_3;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "hdr" },
});
/** @type {__VLS_StyleScopedClasses['hdr']} */ ;
if (__VLS_ctx.logoUrl && __VLS_ctx.logoOk) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        ...{ onError: (__VLS_ctx.onLogoErr) },
        key: (__VLS_ctx.logoUrl),
        ...{ class: "brand" },
        src: (__VLS_ctx.logoUrl),
        alt: "Logo",
    });
    /** @type {__VLS_StyleScopedClasses['brand']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
(__VLS_ctx.title || 'Live Scoreboard');
if (!__VLS_ctx.isGameOver) {
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        variant: "primary",
    }));
    const __VLS_8 = __VLS_7({
        variant: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    const { default: __VLS_11 } = __VLS_9.slots;
    // @ts-ignore
    [logoUrl, logoUrl, logoUrl, logoOk, onLogoErr, title, isGameOver,];
    var __VLS_9;
}
else {
    let __VLS_12;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
        variant: "success",
    }));
    const __VLS_14 = __VLS_13({
        variant: "success",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    const { default: __VLS_17 } = __VLS_15.slots;
    // @ts-ignore
    [];
    var __VLS_15;
}
if (__VLS_ctx.badgeSponsor) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
        ...{ class: "badge-sponsor" },
        href: (__VLS_ctx.sponsorHref(__VLS_ctx.badgeSponsor)),
        target: "_blank",
        rel: "noopener",
        'aria-label': (`Presented by ${__VLS_ctx.sponsorAlt(__VLS_ctx.badgeSponsor)}`),
    });
    /** @type {__VLS_StyleScopedClasses['badge-sponsor']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge-label" },
    });
    /** @type {__VLS_StyleScopedClasses['badge-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
        src: (__VLS_ctx.sponsorImg(__VLS_ctx.badgeSponsor)),
        alt: (__VLS_ctx.sponsorAlt(__VLS_ctx.badgeSponsor)),
    });
}
if (props.canControl && !__VLS_ctx.showInterruptionBanner) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ctrl-row" },
    });
    /** @type {__VLS_StyleScopedClasses['ctrl-row']} */ ;
    let __VLS_18;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        disabled: (__VLS_ctx.interBusy),
    }));
    const __VLS_20 = __VLS_19({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        disabled: (__VLS_ctx.interBusy),
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    let __VLS_23;
    const __VLS_24 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!(props.canControl && !__VLS_ctx.showInterruptionBanner))
                    return;
                __VLS_ctx.startDelay('weather');
                // @ts-ignore
                [sponsorHref, sponsorImg, sponsorAlt, sponsorAlt, badgeSponsor, badgeSponsor, badgeSponsor, badgeSponsor, badgeSponsor, showInterruptionBanner, interBusy, startDelay,];
            } });
    const { default: __VLS_25 } = __VLS_21.slots;
    (__VLS_ctx.interBusy ? 'Starting…' : 'Start delay');
    // @ts-ignore
    [interBusy,];
    var __VLS_21;
    var __VLS_22;
}
if (__VLS_ctx.storeError) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.storeError);
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card" },
    });
    /** @type {__VLS_StyleScopedClasses['card']} */ ;
    if (__VLS_ctx.showInterruptionBanner) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "interrupt-banner" },
            role: "status",
            'aria-live': "polite",
            'data-testid': "interrupt-banner",
        });
        /** @type {__VLS_StyleScopedClasses['interrupt-banner']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "icon" },
        });
        /** @type {__VLS_StyleScopedClasses['icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({
            ...{ class: "kind" },
        });
        /** @type {__VLS_StyleScopedClasses['kind']} */ ;
        ((__VLS_ctx.currentInterruption?.kind || 'weather') === 'weather' ? 'Rain delay' : (__VLS_ctx.currentInterruption?.kind || 'Interruption'));
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "dot" },
        });
        /** @type {__VLS_StyleScopedClasses['dot']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "elapsed" },
        });
        /** @type {__VLS_StyleScopedClasses['elapsed']} */ ;
        (__VLS_ctx.elapsedSince(__VLS_ctx.currentInterruption?.started_at));
        if (__VLS_ctx.currentInterruption?.note) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "note" },
            });
            /** @type {__VLS_StyleScopedClasses['note']} */ ;
            (__VLS_ctx.currentInterruption?.note);
        }
        if (props.canControl) {
            let __VLS_26;
            /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
            BaseButton;
            // @ts-ignore
            const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
                ...{ 'onClick': {} },
                variant: "ghost",
                size: "sm",
                disabled: (__VLS_ctx.interBusy),
                ...{ class: "resume-btn" },
                dataTestid: "btn-resume-interruption",
            }));
            const __VLS_28 = __VLS_27({
                ...{ 'onClick': {} },
                variant: "ghost",
                size: "sm",
                disabled: (__VLS_ctx.interBusy),
                ...{ class: "resume-btn" },
                dataTestid: "btn-resume-interruption",
            }, ...__VLS_functionalComponentArgsRest(__VLS_27));
            let __VLS_31;
            const __VLS_32 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.storeError))
                            return;
                        if (!(__VLS_ctx.showInterruptionBanner))
                            return;
                        if (!(props.canControl))
                            return;
                        __VLS_ctx.resumePlay(__VLS_ctx.currentInterruption?.kind);
                        // @ts-ignore
                        [showInterruptionBanner, interBusy, storeError, storeError, currentInterruption, currentInterruption, currentInterruption, currentInterruption, currentInterruption, currentInterruption, elapsedSince, resumePlay,];
                    } });
            /** @type {__VLS_StyleScopedClasses['resume-btn']} */ ;
            const { default: __VLS_33 } = __VLS_29.slots;
            (__VLS_ctx.interBusy ? 'Resuming…' : 'Resume play');
            // @ts-ignore
            [interBusy,];
            var __VLS_29;
            var __VLS_30;
        }
    }
    if (__VLS_ctx.isGameOver || __VLS_ctx.resultText) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "result-banner" },
            role: "status",
            'aria-live': "polite",
            'data-testid': "scoreboard-result-banner",
        });
        /** @type {__VLS_StyleScopedClasses['result-banner']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.resultText || 'Match completed');
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "topline" },
    });
    /** @type {__VLS_StyleScopedClasses['topline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "teams" },
    });
    /** @type {__VLS_StyleScopedClasses['teams']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.currentGame?.batting_team_name || '');
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.currentGame?.bowling_team_name || '');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "score" },
    });
    /** @type {__VLS_StyleScopedClasses['score']} */ ;
    if (__VLS_ctx.currentInningNo === 2) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "bt" },
        });
        /** @type {__VLS_StyleScopedClasses['bt']} */ ;
        (__VLS_ctx.battingTeamName);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "big" },
        'data-testid': "scoreboard-score",
    });
    /** @type {__VLS_StyleScopedClasses['big']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        'data-testid': "scoreboard-runs",
    });
    (__VLS_ctx.runs);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        'data-testid': "scoreboard-wkts",
    });
    (__VLS_ctx.wkts);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "ov" },
        'data-testid': "scoreboard-overs",
    });
    /** @type {__VLS_StyleScopedClasses['ov']} */ ;
    (__VLS_ctx.oversText);
    if (__VLS_ctx.innings1Line) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "first-inn" },
        });
        /** @type {__VLS_StyleScopedClasses['first-inn']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        (__VLS_ctx.innings1TeamName || '—');
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.innings1Line);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grid grid-3" },
    });
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    /** @type {__VLS_StyleScopedClasses['grid-3']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
        'data-testid': "scoreboard-striker-name",
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    if (__VLS_ctx.strikerRow?.id && __VLS_ctx.isValidUUID(__VLS_ctx.strikerRow.id)) {
        let __VLS_34;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_35 = __VLS_asFunctionalComponent1(__VLS_34, new __VLS_34({
            to: ({ name: 'PlayerProfile', params: { playerId: __VLS_ctx.strikerRow.id } }),
            ...{ class: "player-link" },
            target: "_blank",
            rel: "noopener noreferrer",
        }));
        const __VLS_36 = __VLS_35({
            to: ({ name: 'PlayerProfile', params: { playerId: __VLS_ctx.strikerRow.id } }),
            ...{ class: "player-link" },
            target: "_blank",
            rel: "noopener noreferrer",
        }, ...__VLS_functionalComponentArgsRest(__VLS_35));
        /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
        const { default: __VLS_39 } = __VLS_37.slots;
        (__VLS_ctx.strikerRow.name);
        // @ts-ignore
        [isGameOver, resultText, resultText, currentGame, currentGame, currentInningNo, battingTeamName, runs, wkts, oversText, innings1Line, innings1Line, innings1TeamName, strikerRow, strikerRow, strikerRow, strikerRow, isValidUUID,];
        var __VLS_37;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (__VLS_ctx.strikerRow?.name || '-');
    }
    if (__VLS_ctx.strikerRow?.id) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
        (__VLS_ctx.roleBadge(__VLS_ctx.strikerRow.id));
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.strikerRow?.runs ?? 0);
    (__VLS_ctx.strikerRow?.balls ?? 0);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.fmtSR(__VLS_ctx.strikerRow?.runs ?? 0, __VLS_ctx.strikerRow?.balls ?? 0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
        'data-testid': "scoreboard-nonstriker-name",
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    if (__VLS_ctx.nonStrikerRow?.id && __VLS_ctx.isValidUUID(__VLS_ctx.nonStrikerRow.id)) {
        let __VLS_40;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_41 = __VLS_asFunctionalComponent1(__VLS_40, new __VLS_40({
            to: ({ name: 'PlayerProfile', params: { playerId: __VLS_ctx.nonStrikerRow.id } }),
            ...{ class: "player-link" },
            target: "_blank",
            rel: "noopener noreferrer",
        }));
        const __VLS_42 = __VLS_41({
            to: ({ name: 'PlayerProfile', params: { playerId: __VLS_ctx.nonStrikerRow.id } }),
            ...{ class: "player-link" },
            target: "_blank",
            rel: "noopener noreferrer",
        }, ...__VLS_functionalComponentArgsRest(__VLS_41));
        /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
        const { default: __VLS_45 } = __VLS_43.slots;
        (__VLS_ctx.nonStrikerRow.name);
        // @ts-ignore
        [strikerRow, strikerRow, strikerRow, strikerRow, strikerRow, strikerRow, strikerRow, isValidUUID, roleBadge, fmtSR, nonStrikerRow, nonStrikerRow, nonStrikerRow, nonStrikerRow,];
        var __VLS_43;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (__VLS_ctx.nonStrikerRow?.name || '-');
    }
    if (__VLS_ctx.nonStrikerRow?.id) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
        (__VLS_ctx.roleBadge(__VLS_ctx.nonStrikerRow.id));
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.nonStrikerRow?.runs ?? 0);
    (__VLS_ctx.nonStrikerRow?.balls ?? 0);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.fmtSR(__VLS_ctx.nonStrikerRow?.runs ?? 0, __VLS_ctx.nonStrikerRow?.balls ?? 0));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
        'data-testid': "scoreboard-bowler-name",
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.safeCurrentBowlerName || '-');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.currentBowlerWkts);
    (__VLS_ctx.currentBowlerDerived?.runs ?? 0);
    (__VLS_ctx.currentBowlerDerived?.oversText ?? '0.0');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "label" },
    });
    /** @type {__VLS_StyleScopedClasses['label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "val" },
    });
    /** @type {__VLS_StyleScopedClasses['val']} */ ;
    (__VLS_ctx.currentBowlerDerived?.econText ?? '—');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "info-strip" },
    });
    /** @type {__VLS_StyleScopedClasses['info-strip']} */ ;
    if (__VLS_ctx.showCrr) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cell" },
            'data-testid': "scoreboard-crr",
        });
        /** @type {__VLS_StyleScopedClasses['cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.crr);
    }
    if (__VLS_ctx.isChase && __VLS_ctx.targetDisplay != null) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cell" },
            'data-testid': "scoreboard-target",
        });
        /** @type {__VLS_StyleScopedClasses['cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.targetDisplay);
    }
    if (__VLS_ctx.isChase && __VLS_ctx.rrr) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cell" },
            'data-testid': "scoreboard-rrr",
        });
        /** @type {__VLS_StyleScopedClasses['cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.rrr);
    }
    if (__VLS_ctx.parTxt) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cell" },
            'data-testid': "scoreboard-par",
        });
        /** @type {__VLS_StyleScopedClasses['cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.parTxt);
    }
    if (__VLS_ctx.isChase && __VLS_ctx.oversLeft) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cell" },
            'data-testid': "scoreboard-overs-left",
        });
        /** @type {__VLS_StyleScopedClasses['cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "lbl" },
        });
        /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.oversLeft);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "full-span" },
    });
    /** @type {__VLS_StyleScopedClasses['full-span']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane wide-pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    /** @type {__VLS_StyleScopedClasses['wide-pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "mini batting-table" },
    });
    /** @type {__VLS_StyleScopedClasses['mini']} */ ;
    /** @type {__VLS_StyleScopedClasses['batting-table']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "name" },
    });
    /** @type {__VLS_StyleScopedClasses['name']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [b] of __VLS_vFor((__VLS_ctx.battingRows))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (b.id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "name" },
        });
        /** @type {__VLS_StyleScopedClasses['name']} */ ;
        if (__VLS_ctx.isValidUUID(b.id)) {
            let __VLS_46;
            /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
            RouterLink;
            // @ts-ignore
            const __VLS_47 = __VLS_asFunctionalComponent1(__VLS_46, new __VLS_46({
                to: ({ name: 'PlayerProfile', params: { playerId: b.id } }),
                ...{ class: "player-link" },
                target: "_blank",
                rel: "noopener noreferrer",
            }));
            const __VLS_48 = __VLS_47({
                to: ({ name: 'PlayerProfile', params: { playerId: b.id } }),
                ...{ class: "player-link" },
                target: "_blank",
                rel: "noopener noreferrer",
            }, ...__VLS_functionalComponentArgsRest(__VLS_47));
            /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
            const { default: __VLS_51 } = __VLS_49.slots;
            (b.name);
            // @ts-ignore
            [isValidUUID, roleBadge, fmtSR, nonStrikerRow, nonStrikerRow, nonStrikerRow, nonStrikerRow, nonStrikerRow, nonStrikerRow, nonStrikerRow, safeCurrentBowlerName, currentBowlerWkts, currentBowlerDerived, currentBowlerDerived, currentBowlerDerived, showCrr, crr, isChase, isChase, isChase, targetDisplay, targetDisplay, rrr, rrr, parTxt, parTxt, oversLeft, oversLeft, battingRows,];
            var __VLS_49;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (b.name);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-badge" },
        });
        /** @type {__VLS_StyleScopedClasses['role-badge']} */ ;
        (__VLS_ctx.roleBadge(b.id));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (b.runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (b.balls);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (b.fours);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (b.sixes);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (__VLS_ctx.fmtSR(b.runs, b.balls));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "status" },
        });
        /** @type {__VLS_StyleScopedClasses['status']} */ ;
        (b.isOut ? (b.howOut ? `Out (${b.howOut})` : 'Out') : 'Not out');
        // @ts-ignore
        [roleBadge, fmtSR,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane wide-pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    /** @type {__VLS_StyleScopedClasses['wide-pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "mini bowling-table" },
    });
    /** @type {__VLS_StyleScopedClasses['mini']} */ ;
    /** @type {__VLS_StyleScopedClasses['bowling-table']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "name" },
    });
    /** @type {__VLS_StyleScopedClasses['name']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [bw] of __VLS_vFor((__VLS_ctx.bowlingRows))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (bw.id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "name" },
        });
        /** @type {__VLS_StyleScopedClasses['name']} */ ;
        if (__VLS_ctx.isValidUUID(bw.id)) {
            let __VLS_52;
            /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
            RouterLink;
            // @ts-ignore
            const __VLS_53 = __VLS_asFunctionalComponent1(__VLS_52, new __VLS_52({
                to: ({ name: 'PlayerProfile', params: { playerId: bw.id } }),
                ...{ class: "player-link" },
                target: "_blank",
                rel: "noopener noreferrer",
            }));
            const __VLS_54 = __VLS_53({
                to: ({ name: 'PlayerProfile', params: { playerId: bw.id } }),
                ...{ class: "player-link" },
                target: "_blank",
                rel: "noopener noreferrer",
            }, ...__VLS_functionalComponentArgsRest(__VLS_53));
            /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
            const { default: __VLS_57 } = __VLS_55.slots;
            (bw.name);
            // @ts-ignore
            [isValidUUID, bowlingRows,];
            var __VLS_55;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (bw.name);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (bw.overs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (bw.maidens);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (bw.runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (bw.wkts);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (typeof bw.econ === 'number' ? bw.econ.toFixed(2) : bw.econ);
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane" },
    });
    /** @type {__VLS_StyleScopedClasses['pane']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pane-title" },
    });
    /** @type {__VLS_StyleScopedClasses['pane-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "balls" },
    });
    /** @type {__VLS_StyleScopedClasses['balls']} */ ;
    for (const [d, i] of __VLS_vFor((__VLS_ctx.recentDeliveries))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (i),
            ...{ class: "ball" },
            title: (__VLS_ctx.ballLabel(d)),
        });
        /** @type {__VLS_StyleScopedClasses['ball']} */ ;
        (__VLS_ctx.outcomeTag(d));
        // @ts-ignore
        [recentDeliveries, ballLabel, outcomeTag,];
    }
    if (__VLS_ctx.currentPrediction) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "prediction-section" },
        });
        /** @type {__VLS_StyleScopedClasses['prediction-section']} */ ;
        const __VLS_58 = WinProbabilityChart;
        // @ts-ignore
        const __VLS_59 = __VLS_asFunctionalComponent1(__VLS_58, new __VLS_58({
            showChart: (false),
        }));
        const __VLS_60 = __VLS_59({
            showChart: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_59));
    }
}
// @ts-ignore
[currentPrediction,];
const __VLS_export = (await import('vue')).defineComponent({
    setup: () => __VLS_exposed,
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
