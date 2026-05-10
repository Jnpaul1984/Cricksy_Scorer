/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { storeToRefs } from 'pinia';
import { ref, computed } from 'vue';
import ShotMapPreview from '@/components/ShotMapPreview.vue';
import ChartBar from '@/components/analytics/ChartBar.vue';
import ChartLine from '@/components/analytics/ChartLine.vue';
import PartnershipHeatmap from '@/components/analytics/PartnershipHeatmap.vue';
import PhaseSplits from '@/components/analytics/PhaseSplits.vue';
import RunRateComparison from '@/components/analytics/RunRateComparison.vue';
import WagonWheel from '@/components/analytics/WagonWheel.vue';
import { useAuthStore } from '@/stores/authStore';
const qTeamA = ref('');
const qTeamB = ref('');
const loading = ref(false);
const error = ref(null);
const results = ref([]);
const selectedId = ref('');
const snapshot = ref(null);
const deliveries = ref([]);
const auth = useAuthStore();
const { role, isOrgPro, isAnalystPro, isSuperuser, } = storeToRefs(auth);
const hasAnalyticsAccess = computed(() => Boolean(isOrgPro.value || isAnalystPro.value || isSuperuser.value));
/* Read ?apiBase=... so Cypress can point this view at the backend */
function apiBase() {
    try {
        const u = new URL(window.location.href);
        const v = u.searchParams.get('apiBase') || '';
        return v ? v.replace(/\/+$/, '') : '';
    }
    catch {
        return '';
    }
}
async function search() {
    loading.value = true;
    error.value = null;
    try {
        const base = apiBase();
        const qp = new URLSearchParams();
        if (qTeamA.value.trim())
            qp.set('team_a', qTeamA.value.trim());
        if (qTeamB.value.trim())
            qp.set('team_b', qTeamB.value.trim());
        const qs = qp.toString();
        const path = `/games/search${qs ? `?${qs}` : ''}`;
        const url = base ? `${base}${path}` : path;
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok)
            throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        results.value = Array.isArray(data) ? data : [];
    }
    catch (e) {
        error.value = e?.message || 'Search failed';
    }
    finally {
        loading.value = false;
    }
}
async function loadGame(id) {
    selectedId.value = id;
    loading.value = true;
    error.value = null;
    try {
        const base = apiBase();
        // GET /games/{id}
        {
            const path = `/games/${encodeURIComponent(id)}`;
            const url = base ? `${base}${path}` : path;
            const res = await fetch(url, { cache: 'no-store' });
            if (!res.ok)
                throw new Error(`${res.status} ${res.statusText}`);
            snapshot.value = await res.json();
        }
        // GET /games/{id}/deliveries?order=asc
        {
            const path = `/games/${encodeURIComponent(id)}/deliveries?order=asc`;
            const url = base ? `${base}${path}` : path;
            const res = await fetch(url, { cache: 'no-store' });
            if (!res.ok)
                throw new Error(`${res.status} ${res.statusText}`);
            const j = await res.json();
            deliveries.value = (j?.deliveries || []);
        }
    }
    catch (e) {
        error.value = e?.message || 'Load failed';
    }
    finally {
        loading.value = false;
    }
}
const innings = computed(() => {
    const out = { 1: [], 2: [] };
    for (const d of deliveries.value) {
        const inn = Number(d?.inning ?? 1);
        if (!out[inn])
            out[inn] = [];
        out[inn].push(d);
    }
    return out;
});
function runsPerOver(dl) {
    const tally = {};
    for (const d of dl) {
        const ov = Number(d?.over_number ?? 0);
        const rs = Number(d.runs_scored ?? d?.runs ?? 0);
        tally[ov] = (tally[ov] || 0) + rs;
    }
    const overs = Object.keys(tally).map(n => Number(n)).sort((a, b) => a - b);
    return overs.map(o => tally[o]);
}
const manhattan = computed(() => ({
    1: runsPerOver(innings.value[1] || []),
    2: runsPerOver(innings.value[2] || []),
}));
const worm = computed(() => {
    const mk = (arr) => {
        const out = [];
        let total = 0;
        for (let i = 0; i < arr.length; i += 1) {
            total += arr[i];
            out.push(total);
        }
        return out;
    };
    return {
        1: mk(manhattan.value[1]),
        2: mk(manhattan.value[2]),
    };
});
function padSeries(arr, len) {
    return Array.from({ length: len }, (_, i) => arr[i] ?? null);
}
const manhattanChart = computed(() => {
    const len = Math.max(manhattan.value[1].length, manhattan.value[2].length);
    if (!len) {
        return {
            labels: [],
            series: [],
        };
    }
    const labels = Array.from({ length: len }, (_, i) => `Over ${i + 1}`);
    return {
        labels,
        series: [
            { label: 'Innings 1', data: padSeries(manhattan.value[1], len) },
            { label: 'Innings 2', data: padSeries(manhattan.value[2], len) },
        ],
    };
});
const wormChart = computed(() => {
    const len = Math.max(worm.value[1].length, worm.value[2].length);
    if (!len) {
        return {
            labels: [],
            series: [],
        };
    }
    const labels = Array.from({ length: len }, (_, i) => `Over ${i + 1}`);
    return {
        labels,
        series: [
            { label: 'Innings 1', data: padSeries(worm.value[1], len) },
            { label: 'Innings 2', data: padSeries(worm.value[2], len) },
        ],
    };
});
function isLegalBall(d) {
    const x = (d.extra_type || '').toString().toLowerCase();
    return !(x === 'wd' || x === 'nb');
}
const dotBoundary = computed(() => {
    let legal = 0;
    let dots = 0;
    let boundaries = 0;
    for (const d of deliveries.value) {
        if (!isLegalBall(d))
            continue;
        legal += 1;
        const rs = Number(d.runs_scored ?? 0);
        if (rs === 0)
            dots += 1;
        if (rs === 4 || rs === 6)
            boundaries += 1;
    }
    return {
        legal,
        dots,
        boundaries,
        dotPct: legal ? (dots / legal) * 100 : 0,
        boundaryPct: legal ? (boundaries / legal) * 100 : 0,
    };
});
const currRuns = computed(() => Number(snapshot.value?.total_runs ?? 0));
const ballsBowled = computed(() => Number(snapshot.value?.overs_completed ?? 0) * 6 +
    Number(snapshot.value?.balls_this_over ?? 0));
const crr = computed(() => {
    // FIX B2: Use backend-calculated current_run_rate ONLY
    // NO local calculation allowed - backend handles this
    return snapshot.value?.current_run_rate ?? 0;
});
const req = computed(() => {
    // FIX B3: Use backend-calculated required_run_rate and balls_remaining
    const s = snapshot.value;
    if (!s?.target) {
        return {
            rrr: null,
            remainingOvers: null,
            remainingRuns: null,
        };
    }
    // Use backend values - no local calculation
    const rrr = s.required_run_rate ?? null;
    const remainingRuns = s.target - (s.total_runs ?? 0);
    const remainingOvers = (s.balls_remaining ?? 0) / 6;
    return { rrr, remainingOvers, remainingRuns };
});
const extrasTotals = computed(() => snapshot.value?.extras_totals || {});
const fallOfWickets = computed(() => (snapshot.value?.fall_of_wickets || []));
const dlsPanel = computed(() => snapshot.value?.dls || {});
const battingRows = computed(() => {
    const card = snapshot.value?.batting_scorecard || {};
    return Object.values(card).map((e) => {
        const balls = Number(e?.balls_faced ?? 0);
        const runs = Number(e?.runs ?? 0);
        const sr = balls > 0 ? (runs * 100) / balls : 0;
        return {
            name: e?.player_name || '',
            runs,
            balls,
            sr,
            fours: Number(e?.fours ?? 0),
            sixes: Number(e?.sixes ?? 0),
            how_out: (e?.how_out || '').toString(),
        };
    });
});
const bowlingRows = computed(() => {
    const card = snapshot.value?.bowling_scorecard || {};
    return Object.values(card).map((e) => {
        const overs = Number(e?.overs_bowled ?? 0);
        const econ = overs > 0 ? Number(e?.runs_conceded ?? 0) / overs : 0;
        return {
            name: e?.player_name || '',
            overs,
            maidens: Number(e?.maidens ?? 0),
            runs: Number(e?.runs_conceded ?? 0),
            wickets: Number(e?.wickets_taken ?? 0),
            econ,
        };
    });
});
const pairKey = (a, b) => {
    const A = String(a || '');
    const B = String(b || '');
    return A < B ? `${A}|${B}` : `${B}|${A}`;
};
const partnerships = computed(() => {
    const map = new Map();
    const appeared = new Set();
    for (const d of deliveries.value) {
        const s = String(d.striker_id || '');
        const n = String(d.non_striker_id || '');
        if (s)
            appeared.add(s);
        if (n)
            appeared.add(n);
        if (s && n && s !== n) {
            const key = pairKey(s, n);
            const add = Number(d.runs_scored ?? d?.runs ?? 0);
            map.set(key, (map.get(key) || 0) + add);
        }
    }
    const players = [];
    const nameMap = new Map();
    const pushList = (list) => {
        for (const p of list ?? []) {
            const id = String(p?.id ?? '');
            if (!id)
                continue;
            const name = String(p?.name ?? '');
            if (!nameMap.has(id))
                nameMap.set(id, name);
        }
    };
    pushList(snapshot.value?.team_a?.players);
    pushList(snapshot.value?.team_b?.players);
    const card = snapshot.value?.batting_scorecard || {};
    for (const [id, row] of Object.entries(card)) {
        if (!nameMap.has(id))
            nameMap.set(id, String(row?.player_name ?? ''));
    }
    for (const id of appeared) {
        players.push({ id, name: nameMap.get(id) || id });
    }
    players.sort((a, b) => a.name.localeCompare(b.name));
    const matrix = players.map(() => players.map(() => 0));
    const index = new Map();
    players.forEach((p, i) => index.set(p.id, i));
    for (const [key, value] of map.entries()) {
        const [a, b] = key.split('|');
        if (!index.has(a) || !index.has(b))
            continue;
        const ia = index.get(a);
        const ib = index.get(b);
        matrix[ia][ib] = matrix[ib][ia] = value;
    }
    return { players, matrix };
});
function phaseBuckets(oversLimit) {
    if (oversLimit >= 45)
        return [
            { name: 'Powerplay', start: 1, end: 10 },
            { name: 'Middle', start: 11, end: oversLimit - 10 },
            { name: 'Death', start: oversLimit - 9, end: oversLimit },
        ];
    const death = Math.min(5, Math.floor(oversLimit / 4) || 1);
    const powerplay = Math.min(6, Math.max(1, Math.floor(oversLimit / 3) || 1));
    const middleEnd = Math.max(powerplay + 1, oversLimit - death);
    return [
        { name: 'Powerplay', start: 1, end: powerplay },
        { name: 'Middle', start: powerplay + 1, end: middleEnd },
        { name: 'Death', start: middleEnd + 1, end: oversLimit },
    ];
}
const phaseSplits = computed(() => {
    const oversLimit = Number(snapshot.value?.overs_limit ?? 0);
    if (!oversLimit)
        return [];
    const buckets = phaseBuckets(oversLimit);
    const acc = {};
    for (const bucket of buckets)
        acc[bucket.name] = { runs: 0, balls: 0, wkts: 0 };
    for (const d of deliveries.value) {
        const over = Number(d.over_number ?? 0) + 1;
        const bucket = buckets.find(b => over >= b.start && over <= b.end);
        if (!bucket)
            continue;
        const entry = acc[bucket.name];
        entry.runs += Number(d.runs_scored ?? d?.runs ?? 0);
        if (isLegalBall(d))
            entry.balls += 1;
        if (d.is_wicket)
            entry.wkts += 1;
    }
    return buckets.map(bucket => ({
        name: bucket.name,
        runs: acc[bucket.name].runs,
        overs: acc[bucket.name].balls / 6,
        wkts: acc[bucket.name].wkts,
    }));
});
const wagonStrokes = computed(() => {
    const out = [];
    for (const d of deliveries.value) {
        const angle = d?.shot_angle_deg;
        if (angle == null || Number.isNaN(Number(angle)))
            continue;
        const runs = Number(d.runs_scored ?? 0);
        const kind = runs === 6 ? '6' : runs === 4 ? '4' : 'other';
        out.push({ angleDeg: Number(angle), runs, kind });
    }
    return out;
});
const shotMapDeliveries = computed(() => {
    const withMap = deliveries.value.filter((d) => {
        const value = d?.shot_map;
        return typeof value === 'string' && value.length > 0;
    });
    return withMap.reverse();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['analytics']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics']} */ ;
/** @type {__VLS_StyleScopedClasses['analytics']} */ ;
/** @type {__VLS_StyleScopedClasses['access-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['access-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['shot-map-list']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['tbl']} */ ;
/** @type {__VLS_StyleScopedClasses['tbl']} */ ;
if (__VLS_ctx.hasAnalyticsAccess) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
        ...{ class: "container analytics" },
    });
    /** @type {__VLS_StyleScopedClasses['container']} */ ;
    /** @type {__VLS_StyleScopedClasses['analytics']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "analytics-header" },
    });
    /** @type {__VLS_StyleScopedClasses['analytics-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "access-chip" },
    });
    /** @type {__VLS_StyleScopedClasses['access-chip']} */ ;
    (__VLS_ctx.role || 'analyst_pro');
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "card" },
    });
    /** @type {__VLS_StyleScopedClasses['card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "Team A name",
        ...{ class: "inp" },
    });
    (__VLS_ctx.qTeamA);
    /** @type {__VLS_StyleScopedClasses['inp']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "Team B name",
        ...{ class: "inp" },
    });
    (__VLS_ctx.qTeamB);
    /** @type {__VLS_StyleScopedClasses['inp']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.search) },
        ...{ class: "btn" },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['btn']} */ ;
    if (__VLS_ctx.error) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "error" },
        });
        /** @type {__VLS_StyleScopedClasses['error']} */ ;
        (__VLS_ctx.error);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "result-list" },
    });
    /** @type {__VLS_StyleScopedClasses['result-list']} */ ;
    for (const [g] of __VLS_vFor((__VLS_ctx.results))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (g.id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.hasAnalyticsAccess))
                        return;
                    __VLS_ctx.loadGame(g.id);
                    // @ts-ignore
                    [hasAnalyticsAccess, role, qTeamA, qTeamB, search, loading, error, error, results, loadGame,];
                } },
            ...{ class: "link" },
        });
        /** @type {__VLS_StyleScopedClasses['link']} */ ;
        (g.team_a_name);
        (g.team_b_name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({});
        (g.status);
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.selectedId && __VLS_ctx.snapshot) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "grid" },
        });
        /** @type {__VLS_StyleScopedClasses['grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card wide" },
            'data-testid': "analytics-runrate-card",
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        /** @type {__VLS_StyleScopedClasses['wide']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        const __VLS_0 = RunRateComparison;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
            currentRunRate: (__VLS_ctx.crr),
            requiredRunRate: (__VLS_ctx.req.rrr),
            currentScore: (__VLS_ctx.currRuns),
            ballsBowled: (__VLS_ctx.ballsBowled),
            oversLimit: (Number(__VLS_ctx.snapshot?.overs_limit ?? 0)),
            targetScore: (__VLS_ctx.snapshot?.target ?? null),
        }));
        const __VLS_2 = __VLS_1({
            currentRunRate: (__VLS_ctx.crr),
            requiredRunRate: (__VLS_ctx.req.rrr),
            currentScore: (__VLS_ctx.currRuns),
            ballsBowled: (__VLS_ctx.ballsBowled),
            oversLimit: (Number(__VLS_ctx.snapshot?.overs_limit ?? 0)),
            targetScore: (__VLS_ctx.snapshot?.target ?? null),
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        if (__VLS_ctx.manhattanChart.labels.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "card" },
                'data-testid': "analytics-manhattan-card",
            });
            /** @type {__VLS_StyleScopedClasses['card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            const __VLS_5 = ChartBar;
            // @ts-ignore
            const __VLS_6 = __VLS_asFunctionalComponent1(__VLS_5, new __VLS_5({
                labels: (__VLS_ctx.manhattanChart.labels),
                series: (__VLS_ctx.manhattanChart.series),
            }));
            const __VLS_7 = __VLS_6({
                labels: (__VLS_ctx.manhattanChart.labels),
                series: (__VLS_ctx.manhattanChart.series),
            }, ...__VLS_functionalComponentArgsRest(__VLS_6));
        }
        if (__VLS_ctx.wormChart.labels.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "card" },
                'data-testid': "analytics-worm-card",
            });
            /** @type {__VLS_StyleScopedClasses['card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            const __VLS_10 = ChartLine;
            // @ts-ignore
            const __VLS_11 = __VLS_asFunctionalComponent1(__VLS_10, new __VLS_10({
                labels: (__VLS_ctx.wormChart.labels),
                series: (__VLS_ctx.wormChart.series),
            }));
            const __VLS_12 = __VLS_11({
                labels: (__VLS_ctx.wormChart.labels),
                series: (__VLS_ctx.wormChart.series),
            }, ...__VLS_functionalComponentArgsRest(__VLS_11));
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card" },
            'data-testid': "analytics-extras-card",
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "extras-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['extras-grid']} */ ;
        for (const [value, key] of __VLS_vFor((__VLS_ctx.extrasTotals))) {
            (key);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            (key);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "value" },
            });
            /** @type {__VLS_StyleScopedClasses['value']} */ ;
            (value);
            // @ts-ignore
            [selectedId, snapshot, snapshot, snapshot, crr, req, currRuns, ballsBowled, manhattanChart, manhattanChart, manhattanChart, wormChart, wormChart, wormChart, extrasTotals,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "summary" },
        });
        /** @type {__VLS_StyleScopedClasses['summary']} */ ;
        (__VLS_ctx.dotBoundary.legal);
        (__VLS_ctx.dotBoundary.dots);
        (__VLS_ctx.dotBoundary.dotPct.toFixed(1));
        (__VLS_ctx.dotBoundary.boundaries);
        (__VLS_ctx.dotBoundary.boundaryPct.toFixed(1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card wide" },
            'data-testid': "analytics-batting-card",
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        /** @type {__VLS_StyleScopedClasses['wide']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "tbl" },
        });
        /** @type {__VLS_StyleScopedClasses['tbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [r] of __VLS_vFor((__VLS_ctx.battingRows))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (r.name),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.runs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.balls);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.sr.toFixed(1));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.fours);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.sixes);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.how_out);
            // @ts-ignore
            [dotBoundary, dotBoundary, dotBoundary, dotBoundary, dotBoundary, battingRows,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card wide" },
            'data-testid': "analytics-bowling-card",
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        /** @type {__VLS_StyleScopedClasses['wide']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "tbl" },
        });
        /** @type {__VLS_StyleScopedClasses['tbl']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [r] of __VLS_vFor((__VLS_ctx.bowlingRows))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (r.name),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.overs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.maidens);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.runs);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.wickets);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (r.econ.toFixed(2));
            // @ts-ignore
            [bowlingRows,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card wide" },
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        /** @type {__VLS_StyleScopedClasses['wide']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.partnerships.players.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            const __VLS_15 = PartnershipHeatmap;
            // @ts-ignore
            const __VLS_16 = __VLS_asFunctionalComponent1(__VLS_15, new __VLS_15({
                players: (__VLS_ctx.partnerships.players),
                matrix: (__VLS_ctx.partnerships.matrix),
            }));
            const __VLS_17 = __VLS_16({
                players: (__VLS_ctx.partnerships.players),
                matrix: (__VLS_ctx.partnerships.matrix),
            }, ...__VLS_functionalComponentArgsRest(__VLS_16));
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "empty" },
            });
            /** @type {__VLS_StyleScopedClasses['empty']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card" },
            'data-testid': "analytics-phase-card",
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        const __VLS_20 = PhaseSplits;
        // @ts-ignore
        const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
            splits: (__VLS_ctx.phaseSplits),
        }));
        const __VLS_22 = __VLS_21({
            splits: (__VLS_ctx.phaseSplits),
        }, ...__VLS_functionalComponentArgsRest(__VLS_21));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card" },
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
        for (const [w, i] of __VLS_vFor((__VLS_ctx.fallOfWickets))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (i),
            });
            (w.score_at_fall);
            (w.over);
            // @ts-ignore
            [partnerships, partnerships, partnerships, phaseSplits, fallOfWickets,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card" },
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.dlsPanel.target != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            (__VLS_ctx.dlsPanel.target);
        }
        if (__VLS_ctx.dlsPanel.par != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            (__VLS_ctx.dlsPanel.par);
        }
        if (__VLS_ctx.dlsPanel.ahead_by != null) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            (__VLS_ctx.dlsPanel.ahead_by);
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card" },
        });
        /** @type {__VLS_StyleScopedClasses['card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        const __VLS_25 = WagonWheel;
        // @ts-ignore
        const __VLS_26 = __VLS_asFunctionalComponent1(__VLS_25, new __VLS_25({
            strokes: (__VLS_ctx.wagonStrokes),
        }));
        const __VLS_27 = __VLS_26({
            strokes: (__VLS_ctx.wagonStrokes),
        }, ...__VLS_functionalComponentArgsRest(__VLS_26));
        if (!__VLS_ctx.wagonStrokes.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
                ...{ class: "hint" },
            });
            /** @type {__VLS_StyleScopedClasses['hint']} */ ;
        }
        if (__VLS_ctx.shotMapDeliveries.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "card wide" },
            });
            /** @type {__VLS_StyleScopedClasses['card']} */ ;
            /** @type {__VLS_StyleScopedClasses['wide']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                ...{ class: "shot-map-list" },
            });
            /** @type {__VLS_StyleScopedClasses['shot-map-list']} */ ;
            for (const [d] of __VLS_vFor((__VLS_ctx.shotMapDeliveries.slice(0, 12)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (`${d.inning ?? 0}-${d.over_number ?? 0}-${d.ball_number ?? 0}`),
                });
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "shot-map-meta" },
                });
                /** @type {__VLS_StyleScopedClasses['shot-map-meta']} */ ;
                (d.inning ?? '?');
                ((d.over_number ?? 0) + 1);
                (d.ball_number ?? 0);
                const __VLS_30 = ShotMapPreview;
                // @ts-ignore
                const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
                    value: (d.shot_map),
                    size: (88),
                }));
                const __VLS_32 = __VLS_31({
                    value: (d.shot_map),
                    size: (88),
                }, ...__VLS_functionalComponentArgsRest(__VLS_31));
                // @ts-ignore
                [dlsPanel, dlsPanel, dlsPanel, dlsPanel, dlsPanel, dlsPanel, wagonStrokes, wagonStrokes, shotMapDeliveries, shotMapDeliveries,];
            }
        }
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "analytics-locked-full" },
    });
    /** @type {__VLS_StyleScopedClasses['analytics-locked-full']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    let __VLS_35;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_36 = __VLS_asFunctionalComponent1(__VLS_35, new __VLS_35({
        to: "/login",
        ...{ class: "login-link" },
    }));
    const __VLS_37 = __VLS_36({
        to: "/login",
        ...{ class: "login-link" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_36));
    /** @type {__VLS_StyleScopedClasses['login-link']} */ ;
    const { default: __VLS_40 } = __VLS_38.slots;
    // @ts-ignore
    [];
    var __VLS_38;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
