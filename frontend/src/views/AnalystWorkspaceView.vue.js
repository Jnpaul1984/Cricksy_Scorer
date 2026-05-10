/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { BaseCard, BaseButton, BaseBadge, BaseInput, ImpactBar, MiniSparkline, AiCalloutsPanel } from '@/components';
import AnalyticsTablesWidget from '@/components/AnalyticsTablesWidget.vue';
import ExportUI from '@/components/ExportUI.vue';
import { getAnalystMatches, } from '@/services/api';
const router = useRouter();
// State
const activeTab = ref('matches');
const filters = reactive({
    search: '',
    format: 'all',
    phase: 'all',
    perspective: 'all'
});
const formatOptions = [
    { label: 'All', value: 'all' },
    { label: 'T20', value: 't20' },
    { label: 'ODI', value: 'odi' },
    { label: 'Custom', value: 'custom' }
];
const phaseOptions = [
    { label: 'All', value: 'all' },
    { label: 'Powerplay', value: 'powerplay' },
    { label: 'Middle', value: 'middle' },
    { label: 'Death', value: 'death' }
];
const perspectiveOptions = [
    { label: 'All', value: 'all' },
    { label: 'Batting', value: 'batting' },
    { label: 'Bowling', value: 'bowling' }
];
const tabs = [
    { value: 'matches', label: 'Matches' },
    { value: 'players', label: 'Players' },
    { value: 'deliveries', label: 'Deliveries' },
    { value: 'case-studies', label: 'Case studies' },
    { value: 'analytics', label: 'Analytics' }
];
const lastSyncLabel = ref('Just now');
// Summary metrics - NO FAKE DATA
// Required: GET /analyst/summary
const summary = reactive({
    avgRunsPerOver: null,
    wicketsInPhase: null,
    topBowler: null
});
// Matches state - wired to backend
const matches = ref([]);
const matchesLoading = ref(false);
const matchesError = ref(null);
// Players list - NO FAKE DATA
// Required: GET /analyst/players
const players = ref([]);
// Computed
const filteredMatches = computed(() => {
    const term = filters.search.toLowerCase();
    return matches.value.filter((m) => {
        const matchesTerm = !term ||
            m.teams.toLowerCase().includes(term) ||
            m.result.toLowerCase().includes(term);
        const matchesFormat = filters.format === 'all' ||
            (filters.format === 't20' && m.format === 'T20') ||
            (filters.format === 'odi' && m.format === 'ODI');
        return matchesTerm && matchesFormat;
    });
});
const filteredPlayers = computed(() => {
    const term = filters.search.toLowerCase();
    return players.value.filter((p) => {
        const matchesTerm = !term || p.name.toLowerCase().includes(term) || p.role.toLowerCase().includes(term);
        return matchesTerm;
    });
});
const currentPhaseLabel = computed(() => {
    const map = {
        all: 'All phases',
        powerplay: 'Powerplay overs',
        middle: 'Middle overs',
        death: 'Death overs'
    };
    return map[filters.phase] ?? 'All phases';
});
const currentTabLabel = computed(() => {
    const tab = tabs.find((t) => t.value === activeTab.value);
    return tab?.label ?? '';
});
// Workspace-level AI callouts derived from matches
const workspaceCallouts = computed(() => {
    if (!matches.value.length)
        return [];
    const list = [];
    const recent = matches.value.slice(0, 6);
    // Check for death overs collapses
    const deathCollapses = recent.filter(m => m.tags?.includes('death overs collapse'));
    if (deathCollapses.length >= 2) {
        list.push({
            id: 'death-collapse',
            title: 'Death overs collapses',
            body: `Detected collapses in ${deathCollapses.length} of last ${recent.length} matches.`,
            severity: 'warning',
            targetDomId: `aw-match-${deathCollapses[0].id}`,
            category: 'death overs',
        });
    }
    // Check for powerplay dominance
    const strongPowerplay = recent.filter(m => m.tags?.includes('powerplay dominance'));
    if (strongPowerplay.length >= 2) {
        list.push({
            id: 'powerplay-dominance',
            title: 'Powerplay dominance',
            body: `Strong starts in ${strongPowerplay.length} recent matches.`,
            severity: 'positive',
            targetDomId: `aw-match-${strongPowerplay[0].id}`,
            category: 'powerplay',
        });
    }
    // Check for volatile matches
    const volatileMatches = recent.filter(m => m.key_flag === 'volatile');
    if (volatileMatches.length >= 2) {
        list.push({
            id: 'volatility',
            title: 'Inconsistent phases',
            body: `Volatile phase patterns in ${volatileMatches.length} matches.`,
            severity: 'warning',
            targetDomId: `aw-match-${volatileMatches[0].id}`,
            category: 'consistency',
        });
    }
    // Check for dominant performances
    const dominantMatches = recent.filter(m => m.key_flag === 'dominant');
    if (dominantMatches.length >= 2) {
        list.push({
            id: 'dominant-form',
            title: 'Dominant form',
            body: `Strong performances in ${dominantMatches.length} recent matches.`,
            severity: 'positive',
            targetDomId: `aw-match-${dominantMatches[0].id}`,
            category: 'form',
        });
    }
    // Check for pressure situations
    const pressureMatches = recent.filter(m => m.key_flag === 'under_pressure');
    if (pressureMatches.length >= 2) {
        list.push({
            id: 'under-pressure',
            title: 'Under pressure',
            body: `Pressure situations in ${pressureMatches.length} matches require attention.`,
            severity: 'critical',
            targetDomId: `aw-match-${pressureMatches[0].id}`,
            category: 'pressure',
        });
    }
    return list;
});
// Actions
async function loadMatches() {
    matchesLoading.value = true;
    matchesError.value = null;
    try {
        const response = await getAnalystMatches();
        // Map backend schema to frontend AnalystMatch interface
        matches.value = response.items.map((item) => ({
            id: item.id,
            date: item.date,
            format: item.format,
            teams: item.teams,
            result: item.result,
            runRate: item.run_rate,
            phaseSwing: item.phase_swing,
            // These fields are not in the backend yet - derive or leave null
            netImpact: null,
            winProbSeries: null,
            runRateSeries: null,
            tagged: false,
            caseStudyId: null,
            primaryTeam: item.teams.split(' vs ')[0] || null,
        }));
    }
    catch (err) {
        matchesError.value = err instanceof Error ? err.message : 'Failed to load matches';
        console.error('[AnalystWorkspace] Failed to load matches:', err);
    }
    finally {
        matchesLoading.value = false;
        lastSyncLabel.value = 'Just now';
    }
}
async function refreshData() {
    await loadMatches();
}
function resetFilters() {
    filters.search = '';
    filters.format = 'all';
    filters.phase = 'all';
    filters.perspective = 'all';
}
function openMatchCaseStudy(matchId) {
    router.push({
        name: 'MatchCaseStudy',
        params: { matchId }
    });
}
function handleCalloutSelect(callout) {
    if (!callout.targetDomId)
        return;
    const el = document.getElementById(callout.targetDomId);
    if (!el)
        return;
    // Scroll to the element
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // Add highlight effect
    el.classList.add('aw-match--highlight');
    window.setTimeout(() => {
        el.classList.remove('aw-match--highlight');
    }, 1400);
}
// Helper functions for display formatting
function formatImpactLabel(match) {
    const v = match.netImpact ?? 0;
    if (v > 10)
        return 'Strong positive';
    if (v > 3)
        return 'Slightly positive';
    if (v < -10)
        return 'Strong negative';
    if (v < -3)
        return 'Slightly negative';
    return 'Around par';
}
function getSparklineVariant(match) {
    const impact = match.netImpact ?? 0;
    if (impact > 5)
        return 'positive';
    if (impact < -5)
        return 'negative';
    return 'default';
}
// Lifecycle - load data on mount
onMounted(() => {
    loadMatches();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['aw-title-row']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-chip--active']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-tab-btn--active']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-row--clickable']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-empty-large']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-empty-large']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-head']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-row']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-row']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-row']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-main']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-filters']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-head']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-row']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-col--impact']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-matches-col--trend']} */ ;
/** @type {__VLS_StyleScopedClasses['analyst-workspace']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-header']} */ ;
/** @type {__VLS_StyleScopedClasses['aw-tabs-nav']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "analyst-workspace" },
});
/** @type {__VLS_StyleScopedClasses['analyst-workspace']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "aw-header" },
});
/** @type {__VLS_StyleScopedClasses['aw-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-header-text" },
});
/** @type {__VLS_StyleScopedClasses['aw-header-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-title-row" },
});
/** @type {__VLS_StyleScopedClasses['aw-title-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    variant: "primary",
    uppercase: (false),
}));
const __VLS_2 = __VLS_1({
    variant: "primary",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
var __VLS_3;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['aw-subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-header-actions" },
});
/** @type {__VLS_StyleScopedClasses['aw-header-actions']} */ ;
const __VLS_6 = ExportUI;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    data: (__VLS_ctx.filteredMatches),
}));
const __VLS_8 = __VLS_7({
    data: (__VLS_ctx.filteredMatches),
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
let __VLS_11;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent1(__VLS_11, new __VLS_11({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_13 = __VLS_12({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_12));
let __VLS_16;
const __VLS_17 = ({ click: {} },
    { onClick: (__VLS_ctx.refreshData) });
const { default: __VLS_18 } = __VLS_14.slots;
// @ts-ignore
[filteredMatches, refreshData,];
var __VLS_14;
var __VLS_15;
let __VLS_19;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_20 = __VLS_asFunctionalComponent1(__VLS_19, new __VLS_19({
    variant: "neutral",
    uppercase: (false),
}));
const __VLS_21 = __VLS_20({
    variant: "neutral",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_20));
const { default: __VLS_24 } = __VLS_22.slots;
(__VLS_ctx.lastSyncLabel);
// @ts-ignore
[lastSyncLabel,];
var __VLS_22;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "aw-main" },
});
/** @type {__VLS_StyleScopedClasses['aw-main']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
    ...{ class: "aw-filters" },
});
/** @type {__VLS_StyleScopedClasses['aw-filters']} */ ;
let __VLS_25;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_26 = __VLS_asFunctionalComponent1(__VLS_25, new __VLS_25({
    padding: "lg",
    ...{ class: "aw-filters-card" },
}));
const __VLS_27 = __VLS_26({
    padding: "lg",
    ...{ class: "aw-filters-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_26));
/** @type {__VLS_StyleScopedClasses['aw-filters-card']} */ ;
const { default: __VLS_30 } = __VLS_28.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "aw-section-title" },
});
/** @type {__VLS_StyleScopedClasses['aw-section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-filter-group" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-group']} */ ;
let __VLS_31;
/** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
BaseInput;
// @ts-ignore
const __VLS_32 = __VLS_asFunctionalComponent1(__VLS_31, new __VLS_31({
    modelValue: (__VLS_ctx.filters.search),
    label: "Search",
    placeholder: "Player, team, opponent, venue...",
}));
const __VLS_33 = __VLS_32({
    modelValue: (__VLS_ctx.filters.search),
    label: "Search",
    placeholder: "Player, team, opponent, venue...",
}, ...__VLS_functionalComponentArgsRest(__VLS_32));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-filter-group" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-filter-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-chip-row" },
});
/** @type {__VLS_StyleScopedClasses['aw-chip-row']} */ ;
for (const [format] of __VLS_vFor((__VLS_ctx.formatOptions))) {
    let __VLS_36;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
        ...{ 'onClick': {} },
        key: (format.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.format === format.value }) },
    }));
    const __VLS_38 = __VLS_37({
        ...{ 'onClick': {} },
        key: (format.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.format === format.value }) },
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    let __VLS_41;
    const __VLS_42 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.filters.format = format.value;
                // @ts-ignore
                [filters, filters, filters, formatOptions,];
            } });
    /** @type {__VLS_StyleScopedClasses['aw-chip']} */ ;
    /** @type {__VLS_StyleScopedClasses['aw-chip--active']} */ ;
    const { default: __VLS_43 } = __VLS_39.slots;
    (format.label);
    // @ts-ignore
    [];
    var __VLS_39;
    var __VLS_40;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-filter-group" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-filter-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-chip-row" },
});
/** @type {__VLS_StyleScopedClasses['aw-chip-row']} */ ;
for (const [phase] of __VLS_vFor((__VLS_ctx.phaseOptions))) {
    let __VLS_44;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent1(__VLS_44, new __VLS_44({
        ...{ 'onClick': {} },
        key: (phase.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.phase === phase.value }) },
    }));
    const __VLS_46 = __VLS_45({
        ...{ 'onClick': {} },
        key: (phase.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.phase === phase.value }) },
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    let __VLS_49;
    const __VLS_50 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.filters.phase = phase.value;
                // @ts-ignore
                [filters, filters, phaseOptions,];
            } });
    /** @type {__VLS_StyleScopedClasses['aw-chip']} */ ;
    /** @type {__VLS_StyleScopedClasses['aw-chip--active']} */ ;
    const { default: __VLS_51 } = __VLS_47.slots;
    (phase.label);
    // @ts-ignore
    [];
    var __VLS_47;
    var __VLS_48;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-filter-group" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-filter-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-chip-row" },
});
/** @type {__VLS_StyleScopedClasses['aw-chip-row']} */ ;
for (const [perspective] of __VLS_vFor((__VLS_ctx.perspectiveOptions))) {
    let __VLS_52;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent1(__VLS_52, new __VLS_52({
        ...{ 'onClick': {} },
        key: (perspective.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.perspective === perspective.value }) },
    }));
    const __VLS_54 = __VLS_53({
        ...{ 'onClick': {} },
        key: (perspective.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-chip" },
        ...{ class: ({ 'aw-chip--active': __VLS_ctx.filters.perspective === perspective.value }) },
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    let __VLS_57;
    const __VLS_58 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.filters.perspective = perspective.value;
                // @ts-ignore
                [filters, filters, perspectiveOptions,];
            } });
    /** @type {__VLS_StyleScopedClasses['aw-chip']} */ ;
    /** @type {__VLS_StyleScopedClasses['aw-chip--active']} */ ;
    const { default: __VLS_59 } = __VLS_55.slots;
    (perspective.label);
    // @ts-ignore
    [];
    var __VLS_55;
    var __VLS_56;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-filter-footer" },
});
/** @type {__VLS_StyleScopedClasses['aw-filter-footer']} */ ;
let __VLS_60;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent1(__VLS_60, new __VLS_60({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_62 = __VLS_61({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
let __VLS_65;
const __VLS_66 = ({ click: {} },
    { onClick: (__VLS_ctx.resetFilters) });
const { default: __VLS_67 } = __VLS_63.slots;
// @ts-ignore
[resetFilters,];
var __VLS_63;
var __VLS_64;
// @ts-ignore
[];
var __VLS_28;
if (__VLS_ctx.workspaceCallouts.length > 0) {
    let __VLS_68;
    /** @ts-ignore @type { | typeof __VLS_components.AiCalloutsPanel} */
    AiCalloutsPanel;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent1(__VLS_68, new __VLS_68({
        ...{ 'onSelect': {} },
        title: "AI Insights",
        description: "Patterns detected across your matches.",
        callouts: (__VLS_ctx.workspaceCallouts),
        maxItems: (4),
    }));
    const __VLS_70 = __VLS_69({
        ...{ 'onSelect': {} },
        title: "AI Insights",
        description: "Patterns detected across your matches.",
        callouts: (__VLS_ctx.workspaceCallouts),
        maxItems: (4),
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    let __VLS_73;
    const __VLS_74 = ({ select: {} },
        { onSelect: (__VLS_ctx.handleCalloutSelect) });
    var __VLS_71;
    var __VLS_72;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "aw-content" },
});
/** @type {__VLS_StyleScopedClasses['aw-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "aw-summary" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary']} */ ;
let __VLS_75;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_76 = __VLS_asFunctionalComponent1(__VLS_75, new __VLS_75({
    padding: "md",
    ...{ class: "aw-summary-card" },
}));
const __VLS_77 = __VLS_76({
    padding: "md",
    ...{ class: "aw-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_76));
/** @type {__VLS_StyleScopedClasses['aw-summary-card']} */ ;
const { default: __VLS_80 } = __VLS_78.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-value']} */ ;
(__VLS_ctx.summary.avgRunsPerOver);
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-footnote']} */ ;
// @ts-ignore
[workspaceCallouts, workspaceCallouts, handleCalloutSelect, summary,];
var __VLS_78;
let __VLS_81;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_82 = __VLS_asFunctionalComponent1(__VLS_81, new __VLS_81({
    padding: "md",
    ...{ class: "aw-summary-card" },
}));
const __VLS_83 = __VLS_82({
    padding: "md",
    ...{ class: "aw-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_82));
/** @type {__VLS_StyleScopedClasses['aw-summary-card']} */ ;
const { default: __VLS_86 } = __VLS_84.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-value']} */ ;
(__VLS_ctx.summary.wicketsInPhase);
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-footnote']} */ ;
(__VLS_ctx.currentPhaseLabel);
// @ts-ignore
[summary, currentPhaseLabel,];
var __VLS_84;
let __VLS_87;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_88 = __VLS_asFunctionalComponent1(__VLS_87, new __VLS_87({
    padding: "md",
    ...{ class: "aw-summary-card" },
}));
const __VLS_89 = __VLS_88({
    padding: "md",
    ...{ class: "aw-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_88));
/** @type {__VLS_StyleScopedClasses['aw-summary-card']} */ ;
const { default: __VLS_92 } = __VLS_90.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-value']} */ ;
(__VLS_ctx.summary.topBowler || '—');
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "aw-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['aw-summary-footnote']} */ ;
// @ts-ignore
[summary,];
var __VLS_90;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "aw-tabs" },
});
/** @type {__VLS_StyleScopedClasses['aw-tabs']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.nav, __VLS_intrinsics.nav)({
    ...{ class: "aw-tabs-nav" },
});
/** @type {__VLS_StyleScopedClasses['aw-tabs-nav']} */ ;
for (const [tab] of __VLS_vFor((__VLS_ctx.tabs))) {
    let __VLS_93;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_94 = __VLS_asFunctionalComponent1(__VLS_93, new __VLS_93({
        ...{ 'onClick': {} },
        key: (tab.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-tab-btn" },
        ...{ class: ({ 'aw-tab-btn--active': __VLS_ctx.activeTab === tab.value }) },
    }));
    const __VLS_95 = __VLS_94({
        ...{ 'onClick': {} },
        key: (tab.value),
        variant: "ghost",
        size: "sm",
        ...{ class: "aw-tab-btn" },
        ...{ class: ({ 'aw-tab-btn--active': __VLS_ctx.activeTab === tab.value }) },
    }, ...__VLS_functionalComponentArgsRest(__VLS_94));
    let __VLS_98;
    const __VLS_99 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.activeTab = tab.value;
                // @ts-ignore
                [tabs, activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['aw-tab-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['aw-tab-btn--active']} */ ;
    const { default: __VLS_100 } = __VLS_96.slots;
    (tab.label);
    // @ts-ignore
    [];
    var __VLS_96;
    var __VLS_97;
    // @ts-ignore
    [];
}
let __VLS_101;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_102 = __VLS_asFunctionalComponent1(__VLS_101, new __VLS_101({
    padding: "lg",
    ...{ class: "aw-tab-panel" },
}));
const __VLS_103 = __VLS_102({
    padding: "lg",
    ...{ class: "aw-tab-panel" },
}, ...__VLS_functionalComponentArgsRest(__VLS_102));
/** @type {__VLS_StyleScopedClasses['aw-tab-panel']} */ ;
const { default: __VLS_106 } = __VLS_104.slots;
if (__VLS_ctx.activeTab === 'matches') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-header" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "aw-table-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-subtitle']} */ ;
    if (__VLS_ctx.matchesLoading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-loading" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-loading']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    else if (__VLS_ctx.matchesError) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-error" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-error']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (__VLS_ctx.matchesError);
        let __VLS_107;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_108 = __VLS_asFunctionalComponent1(__VLS_107, new __VLS_107({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
        }));
        const __VLS_109 = __VLS_108({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_108));
        let __VLS_112;
        const __VLS_113 = ({ click: {} },
            { onClick: (__VLS_ctx.loadMatches) });
        const { default: __VLS_114 } = __VLS_110.slots;
        // @ts-ignore
        [activeTab, matchesLoading, matchesError, matchesError, loadMatches,];
        var __VLS_110;
        var __VLS_111;
    }
    else if (__VLS_ctx.filteredMatches.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-empty" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-empty']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "aw-matches-empty-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-empty-hint']} */ ;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-list" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-list']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-head" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-head']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-col aw-matches-col--main" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
        /** @type {__VLS_StyleScopedClasses['aw-matches-col--main']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-col aw-matches-col--impact" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
        /** @type {__VLS_StyleScopedClasses['aw-matches-col--impact']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-col aw-matches-col--trend" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
        /** @type {__VLS_StyleScopedClasses['aw-matches-col--trend']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "aw-matches-col aw-matches-col--tags" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
        /** @type {__VLS_StyleScopedClasses['aw-matches-col--tags']} */ ;
        for (const [match] of __VLS_vFor((__VLS_ctx.filteredMatches))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'matches'))
                            return;
                        if (!!(__VLS_ctx.matchesLoading))
                            return;
                        if (!!(__VLS_ctx.matchesError))
                            return;
                        if (!!(__VLS_ctx.filteredMatches.length === 0))
                            return;
                        __VLS_ctx.openMatchCaseStudy(match.id);
                        // @ts-ignore
                        [filteredMatches, filteredMatches, openMatchCaseStudy,];
                    } },
                id: (`aw-match-${match.id}`),
                key: (match.id),
                ...{ class: "aw-matches-row" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-matches-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-matches-col aw-matches-col--main" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
            /** @type {__VLS_StyleScopedClasses['aw-matches-col--main']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-match-title" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-match-title']} */ ;
            (match.teams);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-match-meta" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-match-meta']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (match.format);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (match.date);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (match.result);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-matches-col aw-matches-col--impact" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
            /** @type {__VLS_StyleScopedClasses['aw-matches-col--impact']} */ ;
            let __VLS_115;
            /** @ts-ignore @type { | typeof __VLS_components.ImpactBar} */
            ImpactBar;
            // @ts-ignore
            const __VLS_116 = __VLS_asFunctionalComponent1(__VLS_115, new __VLS_115({
                value: (match.netImpact ?? 0),
                min: (-20),
                max: (20),
                size: "sm",
                label: (__VLS_ctx.formatImpactLabel(match)),
                positiveLabel: ('Favouring ' + (match.primaryTeam || match.teams.split(' vs ')[0])),
                negativeLabel: ('Pressure on ' + (match.primaryTeam || match.teams.split(' vs ')[0])),
            }));
            const __VLS_117 = __VLS_116({
                value: (match.netImpact ?? 0),
                min: (-20),
                max: (20),
                size: "sm",
                label: (__VLS_ctx.formatImpactLabel(match)),
                positiveLabel: ('Favouring ' + (match.primaryTeam || match.teams.split(' vs ')[0])),
                negativeLabel: ('Pressure on ' + (match.primaryTeam || match.teams.split(' vs ')[0])),
            }, ...__VLS_functionalComponentArgsRest(__VLS_116));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-matches-col aw-matches-col--trend" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
            /** @type {__VLS_StyleScopedClasses['aw-matches-col--trend']} */ ;
            if (match.winProbSeries?.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "aw-trend-wrap" },
                });
                /** @type {__VLS_StyleScopedClasses['aw-trend-wrap']} */ ;
                let __VLS_120;
                /** @ts-ignore @type { | typeof __VLS_components.MiniSparkline} */
                MiniSparkline;
                // @ts-ignore
                const __VLS_121 = __VLS_asFunctionalComponent1(__VLS_120, new __VLS_120({
                    points: (match.winProbSeries),
                    highlightLast: (true),
                    variant: (__VLS_ctx.getSparklineVariant(match)),
                }));
                const __VLS_122 = __VLS_121({
                    points: (match.winProbSeries),
                    highlightLast: (true),
                    variant: (__VLS_ctx.getSparklineVariant(match)),
                }, ...__VLS_functionalComponentArgsRest(__VLS_121));
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "aw-trend-label" },
                });
                /** @type {__VLS_StyleScopedClasses['aw-trend-label']} */ ;
            }
            else if (match.runRateSeries?.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "aw-trend-wrap" },
                });
                /** @type {__VLS_StyleScopedClasses['aw-trend-wrap']} */ ;
                let __VLS_125;
                /** @ts-ignore @type { | typeof __VLS_components.MiniSparkline} */
                MiniSparkline;
                // @ts-ignore
                const __VLS_126 = __VLS_asFunctionalComponent1(__VLS_125, new __VLS_125({
                    points: (match.runRateSeries),
                    highlightLast: (true),
                    variant: "neutral",
                }));
                const __VLS_127 = __VLS_126({
                    points: (match.runRateSeries),
                    highlightLast: (true),
                    variant: "neutral",
                }, ...__VLS_functionalComponentArgsRest(__VLS_126));
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "aw-trend-label" },
                });
                /** @type {__VLS_StyleScopedClasses['aw-trend-label']} */ ;
            }
            else {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "aw-trend-none" },
                });
                /** @type {__VLS_StyleScopedClasses['aw-trend-none']} */ ;
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-matches-col aw-matches-col--tags" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-matches-col']} */ ;
            /** @type {__VLS_StyleScopedClasses['aw-matches-col--tags']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-tag-badges" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-tag-badges']} */ ;
            if (match.tagged) {
                let __VLS_130;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_131 = __VLS_asFunctionalComponent1(__VLS_130, new __VLS_130({
                    variant: "primary",
                    uppercase: (false),
                }));
                const __VLS_132 = __VLS_131({
                    variant: "primary",
                    uppercase: (false),
                }, ...__VLS_functionalComponentArgsRest(__VLS_131));
                const { default: __VLS_135 } = __VLS_133.slots;
                // @ts-ignore
                [formatImpactLabel, getSparklineVariant,];
                var __VLS_133;
            }
            if (match.caseStudyId) {
                let __VLS_136;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_137 = __VLS_asFunctionalComponent1(__VLS_136, new __VLS_136({
                    variant: "success",
                    uppercase: (false),
                }));
                const __VLS_138 = __VLS_137({
                    variant: "success",
                    uppercase: (false),
                }, ...__VLS_functionalComponentArgsRest(__VLS_137));
                const { default: __VLS_141 } = __VLS_139.slots;
                // @ts-ignore
                [];
                var __VLS_139;
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "aw-match-analytics" },
            });
            /** @type {__VLS_StyleScopedClasses['aw-match-analytics']} */ ;
            let __VLS_142;
            /** @ts-ignore @type { | typeof __VLS_components.ImpactBar} */
            ImpactBar;
            // @ts-ignore
            const __VLS_143 = __VLS_asFunctionalComponent1(__VLS_142, new __VLS_142({
                ...{ class: "aw-impact" },
                ...{ class: ([
                        match.key_flag === 'dominant' && 'aw-impact--good',
                        match.key_flag === 'under_pressure' && 'aw-impact--bad',
                        match.key_flag === 'volatile' && 'aw-impact--warn',
                    ]) },
                value: (match.impact_score ?? 0),
                label: (match.key_flag ? match.key_flag : 'Impact'),
            }));
            const __VLS_144 = __VLS_143({
                ...{ class: "aw-impact" },
                ...{ class: ([
                        match.key_flag === 'dominant' && 'aw-impact--good',
                        match.key_flag === 'under_pressure' && 'aw-impact--bad',
                        match.key_flag === 'volatile' && 'aw-impact--warn',
                    ]) },
                value: (match.impact_score ?? 0),
                label: (match.key_flag ? match.key_flag : 'Impact'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_143));
            /** @type {__VLS_StyleScopedClasses['aw-impact']} */ ;
            let __VLS_147;
            /** @ts-ignore @type { | typeof __VLS_components.MiniSparkline} */
            MiniSparkline;
            // @ts-ignore
            const __VLS_148 = __VLS_asFunctionalComponent1(__VLS_147, new __VLS_147({
                ...{ class: "aw-trend" },
                points: (match.phase_impact_trend?.length ? match.phase_impact_trend : [0]),
                height: (28),
            }));
            const __VLS_149 = __VLS_148({
                ...{ class: "aw-trend" },
                points: (match.phase_impact_trend?.length ? match.phase_impact_trend : [0]),
                height: (28),
            }, ...__VLS_functionalComponentArgsRest(__VLS_148));
            /** @type {__VLS_StyleScopedClasses['aw-trend']} */ ;
            // @ts-ignore
            [];
        }
    }
}
else if (__VLS_ctx.activeTab === 'players') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-header" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "aw-table-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-scroll" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-scroll']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "aw-table" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table']} */ ;
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
    for (const [player] of __VLS_vFor((__VLS_ctx.filteredPlayers))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (player.id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.role);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.innings);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.strikeRate);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (player.economy);
        // @ts-ignore
        [activeTab, filteredPlayers,];
    }
    if (__VLS_ctx.filteredPlayers.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            colspan: "7",
            ...{ class: "aw-empty" },
        });
        /** @type {__VLS_StyleScopedClasses['aw-empty']} */ ;
    }
}
else if (__VLS_ctx.activeTab === 'case-studies') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-empty-large" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-empty-large']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.currentTabLabel);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.activeTab === 'analytics') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-wrapper']} */ ;
    const __VLS_152 = AnalyticsTablesWidget;
    // @ts-ignore
    const __VLS_153 = __VLS_asFunctionalComponent1(__VLS_152, new __VLS_152({
        profile: (null),
    }));
    const __VLS_154 = __VLS_153({
        profile: (null),
    }, ...__VLS_functionalComponentArgsRest(__VLS_153));
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-table-wrapper" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-table-wrapper']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "aw-empty-large" },
    });
    /** @type {__VLS_StyleScopedClasses['aw-empty-large']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    (__VLS_ctx.currentTabLabel);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
// @ts-ignore
[activeTab, activeTab, filteredPlayers, currentTabLabel, currentTabLabel,];
var __VLS_104;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
