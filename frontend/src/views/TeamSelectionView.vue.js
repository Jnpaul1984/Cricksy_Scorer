/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
import { API_BASE } from '@/utils/api';
const KEY = (id) => `cricksy.xi.${id}`;
const route = useRoute();
const router = useRouter();
const game = useGameStore();
const auth = useAuthStore();
const redirectTarget = computed(() => route.fullPath || `/game/${gameId.value}/select-xi`);
async function ensureScorerAccess() {
    if (auth.token && !auth.user && !auth.loading) {
        try {
            await auth.loadUser();
        }
        catch { /* ignore */ }
    }
    if (!auth.requireRole('coach_pro', 'org_pro', 'superuser')) {
        await router.replace({
            path: '/login',
            query: { redirect: redirectTarget.value },
        });
        return false;
    }
    return true;
}
const gameId = computed(() => route.params.gameId || '');
const loading = ref(true);
const saving = ref(false);
const errorMsg = ref(null);
const teamA = computed(() => game.currentGame?.team_a);
const teamB = computed(() => game.currentGame?.team_b);
const teamADisplayName = computed(() => teamA.value?.name && teamA.value.name.trim().length ? teamA.value.name : 'Team A');
const teamBDisplayName = computed(() => teamB.value?.name && teamB.value.name.trim().length ? teamB.value.name : 'Team B');
const selectedA = ref(new Set());
const selectedB = ref(new Set());
// NEW: role selections
const captainA = ref(null);
const keeperA = ref(null);
const captainB = ref(null);
const keeperB = ref(null);
// (optional) require roles to be chosen before continuing
const canContinue = computed(() => selectedA.value.size === 11 &&
    selectedB.value.size === 11 &&
    !!captainA.value && !!keeperA.value &&
    !!captainB.value && !!keeperB.value);
// Flatten sets to arrays (used for payload and dropdowns)
const xiAList = computed(() => Array.from(selectedA.value));
const xiBList = computed(() => Array.from(selectedB.value));
// teamA/teamB already exist as computed(() => game.currentGame?.team_a / team_b)
function nameFromId(id, team) {
    const arr = team?.players ?? [];
    const found = Array.isArray(arr) ? arr.find((p) => p?.id === id) : undefined;
    return found?.name ?? id;
}
// Basic in-UI guard to keep roles within the XI
function validateRoles() {
    if (xiAList.value.length !== 11 || xiBList.value.length !== 11)
        return 'Each XI must be 11 players.';
    const teamAName = teamADisplayName.value;
    const teamBName = teamBDisplayName.value;
    if (captainA.value && !selectedA.value.has(captainA.value))
        return `${teamAName} captain must be in the XI.`;
    if (keeperA.value && !selectedA.value.has(keeperA.value))
        return `${teamAName} wicket-keeper must be in the XI.`;
    if (captainB.value && !selectedB.value.has(captainB.value))
        return `${teamBName} captain must be in the XI.`;
    if (keeperB.value && !selectedB.value.has(keeperB.value))
        return `${teamBName} wicket-keeper must be in the XI.`;
    return null;
}
function loadSavedXI() {
    try {
        const raw = localStorage.getItem(KEY(gameId.value));
        if (!raw)
            return;
        const obj = JSON.parse(raw);
        if (Array.isArray(obj.team_a_xi))
            selectedA.value = new Set(obj.team_a_xi);
        if (Array.isArray(obj.team_b_xi))
            selectedB.value = new Set(obj.team_b_xi);
        if (obj.captain_a)
            captainA.value = obj.captain_a;
        if (obj.keeper_a)
            keeperA.value = obj.keeper_a;
        if (obj.captain_b)
            captainB.value = obj.captain_b;
        if (obj.keeper_b)
            keeperB.value = obj.keeper_b;
    }
    catch {
        // ignore corrupted cached XI data
    }
}
function prefillIfEmpty() {
    if (selectedA.value.size === 0 && teamA.value?.players?.length) {
        teamA.value.players.slice(0, 11).forEach(p => selectedA.value.add(p.id));
    }
    if (selectedB.value.size === 0 && teamB.value?.players?.length) {
        teamB.value.players.slice(0, 11).forEach(p => selectedB.value.add(p.id));
    }
}
function toggleA(id) {
    if (selectedA.value.has(id)) {
        selectedA.value.delete(id);
    }
    else {
        if (selectedA.value.size >= 11)
            return;
        selectedA.value.add(id);
    }
    selectedA.value = new Set(selectedA.value);
}
function toggleB(id) {
    if (selectedB.value.has(id)) {
        selectedB.value.delete(id);
    }
    else {
        if (selectedB.value.size >= 11)
            return;
        selectedB.value.add(id);
    }
    selectedB.value = new Set(selectedB.value);
}
async function persistXIIfSupported() {
    const base = (API_BASE || (typeof window !== 'undefined' ? window.location.origin : '')).replace(/\/+$/, '');
    if (!base)
        return;
    const payload = {
        team_a: xiAList.value,
        team_b: xiBList.value,
        captain_a: captainA.value,
        keeper_a: keeperA.value,
        captain_b: captainB.value,
        keeper_b: keeperB.value,
    };
    const res = await fetch(`${base}/games/${encodeURIComponent(gameId.value)}/playing-xi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(`Failed to set XI: ${res.status} ${JSON.stringify(body)}`);
    }
}
async function continueToScoring() {
    if (!canContinue.value || saving.value)
        return;
    saving.value = true;
    errorMsg.value = null;
    try {
        // NEW: validate roles on the client
        const v = validateRoles();
        if (v)
            throw new Error(v);
        // Save XI locally (your existing code)
        const xi = {
            team_a_xi: xiAList.value,
            team_b_xi: xiBList.value,
            captain_a: captainA.value,
            keeper_a: keeperA.value,
            captain_b: captainB.value,
            keeper_b: keeperB.value,
        };
        localStorage.setItem(KEY(gameId.value), JSON.stringify(xi));
        // NEW: send XI + roles to backend
        await persistXIIfSupported();
        // (Your existing navigation to scoring)
        await game.loadGame(gameId.value); // optional refresh if you want captain/keeper reflected immediately
        router.push({ name: 'GameScoringView', params: { gameId: gameId.value } });
    }
    catch (e) {
        errorMsg.value = e?.message || 'Failed to continue';
    }
    finally {
        saving.value = false;
    }
}
onMounted(async () => {
    const allowed = await ensureScorerAccess();
    if (!allowed)
        return;
    if (!gameId.value)
        return router.replace('/');
    try {
        if (!game.currentGame || gameId.value !== game.currentGame.id) {
            await game.loadGame(gameId.value);
        }
        loadSavedXI();
        prefillIfEmpty();
    }
    catch (e) {
        errorMsg.value = e?.message || 'Failed to load match';
    }
    finally {
        loading.value = false;
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['team']} */ ;
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "wrap" },
});
/** @type {__VLS_StyleScopedClasses['wrap']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "/",
    ...{ class: "back" },
}));
const __VLS_2 = __VLS_1({
    to: "/",
    ...{ class: "back" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['back']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
var __VLS_3;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "spacer" },
});
/** @type {__VLS_StyleScopedClasses['spacer']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading" },
    });
    /** @type {__VLS_StyleScopedClasses['loading']} */ ;
}
else if (!__VLS_ctx.game.currentGame) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "grid" },
    });
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "team" },
        'data-testid': "team-a-section",
    });
    /** @type {__VLS_StyleScopedClasses['team']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.teamADisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "hint" },
    });
    /** @type {__VLS_StyleScopedClasses['hint']} */ ;
    (__VLS_ctx.selectedA.size);
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    for (const [p] of __VLS_vFor((__VLS_ctx.teamA?.players || []))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(!__VLS_ctx.game.currentGame))
                        return;
                    __VLS_ctx.toggleA(p.id);
                    // @ts-ignore
                    [loading, game, teamADisplayName, selectedA, teamA, toggleA,];
                } },
            key: (p.id),
            ...{ class: (['row', { picked: __VLS_ctx.selectedA.has(p.id), full: __VLS_ctx.selectedA.size >= 11 && !__VLS_ctx.selectedA.has(p.id) }]) },
            'data-testid': "team-a-player",
        });
        /** @type {__VLS_StyleScopedClasses['picked']} */ ;
        /** @type {__VLS_StyleScopedClasses['full']} */ ;
        /** @type {__VLS_StyleScopedClasses['row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            ...{ onChange: () => { } },
            type: "checkbox",
            checked: (__VLS_ctx.selectedA.has(p.id)),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (p.name);
        // @ts-ignore
        [selectedA, selectedA, selectedA, selectedA,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "mt-4 grid grid-cols-1 md:grid-cols-2 gap-3" },
    });
    /** @type {__VLS_StyleScopedClasses['mt-4']} */ ;
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    /** @type {__VLS_StyleScopedClasses['grid-cols-1']} */ ;
    /** @type {__VLS_StyleScopedClasses['md:grid-cols-2']} */ ;
    /** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "block text-sm font-medium mb-1" },
    });
    /** @type {__VLS_StyleScopedClasses['block']} */ ;
    /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
    /** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
    /** @type {__VLS_StyleScopedClasses['mb-1']} */ ;
    (__VLS_ctx.teamADisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.captainA),
        ...{ class: "w-full border rounded p-2" },
        disabled: (__VLS_ctx.xiAList.length === 0),
        'data-testid': "select-captain-a",
    });
    /** @type {__VLS_StyleScopedClasses['w-full']} */ ;
    /** @type {__VLS_StyleScopedClasses['border']} */ ;
    /** @type {__VLS_StyleScopedClasses['rounded']} */ ;
    /** @type {__VLS_StyleScopedClasses['p-2']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
        disabled: true,
    });
    for (const [pid] of __VLS_vFor((__VLS_ctx.xiAList))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (pid),
            value: (pid),
        });
        (__VLS_ctx.nameFromId(pid, __VLS_ctx.teamA));
        // @ts-ignore
        [teamADisplayName, teamA, captainA, xiAList, xiAList, nameFromId,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "block text-sm font-medium mb-1" },
    });
    /** @type {__VLS_StyleScopedClasses['block']} */ ;
    /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
    /** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
    /** @type {__VLS_StyleScopedClasses['mb-1']} */ ;
    (__VLS_ctx.teamADisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.keeperA),
        ...{ class: "w-full border rounded p-2" },
        disabled: (__VLS_ctx.xiAList.length === 0),
        'data-testid': "select-keeper-a",
    });
    /** @type {__VLS_StyleScopedClasses['w-full']} */ ;
    /** @type {__VLS_StyleScopedClasses['border']} */ ;
    /** @type {__VLS_StyleScopedClasses['rounded']} */ ;
    /** @type {__VLS_StyleScopedClasses['p-2']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
        disabled: true,
    });
    for (const [pid] of __VLS_vFor((__VLS_ctx.xiAList))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (pid),
            value: (pid),
        });
        (__VLS_ctx.nameFromId(pid, __VLS_ctx.teamA));
        // @ts-ignore
        [teamADisplayName, teamA, xiAList, xiAList, nameFromId, keeperA,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "team" },
        'data-testid': "team-b-section",
    });
    /** @type {__VLS_StyleScopedClasses['team']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.teamBDisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "hint" },
    });
    /** @type {__VLS_StyleScopedClasses['hint']} */ ;
    (__VLS_ctx.selectedB.size);
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
    for (const [p] of __VLS_vFor((__VLS_ctx.teamB?.players || []))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(!__VLS_ctx.game.currentGame))
                        return;
                    __VLS_ctx.toggleB(p.id);
                    // @ts-ignore
                    [teamBDisplayName, selectedB, teamB, toggleB,];
                } },
            key: (p.id),
            ...{ class: (['row', { picked: __VLS_ctx.selectedB.has(p.id), full: __VLS_ctx.selectedB.size >= 11 && !__VLS_ctx.selectedB.has(p.id) }]) },
            'data-testid': "team-b-player",
        });
        /** @type {__VLS_StyleScopedClasses['picked']} */ ;
        /** @type {__VLS_StyleScopedClasses['full']} */ ;
        /** @type {__VLS_StyleScopedClasses['row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            ...{ onChange: () => { } },
            type: "checkbox",
            checked: (__VLS_ctx.selectedB.has(p.id)),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (p.name);
        // @ts-ignore
        [selectedB, selectedB, selectedB, selectedB,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "mt-6 grid grid-cols-1 md:grid-cols-2 gap-3" },
    });
    /** @type {__VLS_StyleScopedClasses['mt-6']} */ ;
    /** @type {__VLS_StyleScopedClasses['grid']} */ ;
    /** @type {__VLS_StyleScopedClasses['grid-cols-1']} */ ;
    /** @type {__VLS_StyleScopedClasses['md:grid-cols-2']} */ ;
    /** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "block text-sm font-medium mb-1" },
    });
    /** @type {__VLS_StyleScopedClasses['block']} */ ;
    /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
    /** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
    /** @type {__VLS_StyleScopedClasses['mb-1']} */ ;
    (__VLS_ctx.teamBDisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.captainB),
        ...{ class: "w-full border rounded p-2" },
        disabled: (__VLS_ctx.xiBList.length === 0),
        'data-testid': "select-captain-b",
    });
    /** @type {__VLS_StyleScopedClasses['w-full']} */ ;
    /** @type {__VLS_StyleScopedClasses['border']} */ ;
    /** @type {__VLS_StyleScopedClasses['rounded']} */ ;
    /** @type {__VLS_StyleScopedClasses['p-2']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
        disabled: true,
    });
    for (const [pid] of __VLS_vFor((__VLS_ctx.xiBList))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (pid),
            value: (pid),
        });
        (__VLS_ctx.nameFromId(pid, __VLS_ctx.teamB));
        // @ts-ignore
        [nameFromId, teamBDisplayName, teamB, captainB, xiBList, xiBList,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "block text-sm font-medium mb-1" },
    });
    /** @type {__VLS_StyleScopedClasses['block']} */ ;
    /** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
    /** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
    /** @type {__VLS_StyleScopedClasses['mb-1']} */ ;
    (__VLS_ctx.teamBDisplayName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.keeperB),
        ...{ class: "w-full border rounded p-2" },
        disabled: (__VLS_ctx.xiBList.length === 0),
        'data-testid': "select-keeper-b",
    });
    /** @type {__VLS_StyleScopedClasses['w-full']} */ ;
    /** @type {__VLS_StyleScopedClasses['border']} */ ;
    /** @type {__VLS_StyleScopedClasses['rounded']} */ ;
    /** @type {__VLS_StyleScopedClasses['p-2']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
        disabled: true,
    });
    for (const [pid] of __VLS_vFor((__VLS_ctx.xiBList))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (pid),
            value: (pid),
        });
        (__VLS_ctx.nameFromId(pid, __VLS_ctx.teamB));
        // @ts-ignore
        [nameFromId, teamBDisplayName, teamB, xiBList, xiBList, keeperB,];
    }
}
if (__VLS_ctx.errorMsg) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.errorMsg);
}
if (__VLS_ctx.game.currentGame) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.game.currentGame))
                    return;
                __VLS_ctx.$router.replace('/');
                // @ts-ignore
                [game, errorMsg, errorMsg, $router,];
            } },
        ...{ class: "secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.continueToScoring) },
        ...{ class: "primary" },
        disabled: (!__VLS_ctx.canContinue || __VLS_ctx.saving),
        'data-testid': "btn-save-xi",
    });
    /** @type {__VLS_StyleScopedClasses['primary']} */ ;
    (__VLS_ctx.saving ? 'Saving…' : 'Save & Continue');
}
// @ts-ignore
[continueToScoring, canContinue, saving, saving,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
