/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { BaseCard, BaseButton, BaseBadge, AiCalloutsPanel } from '@/components';
const router = useRouter();
// Loading state
// FIX A4: Remove ALL mock org data - show unavailable state
const orgLoading = ref(false);
const lastSyncLabel = ref('—');
const backendEndpointsAvailable = ref(false);
const requiredEndpoints = [
    'GET /organizations/{orgId}/stats',
    'GET /organizations/{orgId}/teams',
    'GET /organizations/{orgId}/recent-matches'
];
// NO MOCK DATA - return null when backend unavailable
const orgStats = computed(() => {
    if (!backendEndpointsAvailable.value)
        return null;
    // TODO: Fetch from API when endpoint ready
    // const data = await apiRequest('/organizations/{orgId}/stats')
    return null;
});
// NO MOCK DATA - empty array when backend unavailable
const teams = ref([]);
// NO MOCK DATA - empty array when backend unavailable
const recentMatches = ref([]);
// NO MOCK DATA - callouts derived from real data only
const orgAiCallouts = computed(() => {
    const stats = orgStats.value;
    if (!stats)
        return [];
    const callouts = [];
    // Only generate callouts from REAL data
    if (stats.seasonWinRate >= 65) {
        callouts.push({
            id: 'high-win-rate',
            title: 'Strong season performance',
            body: `Your teams have won around ${Math.round(stats.seasonWinRate)}% of their games this season.`,
            category: 'Org',
            severity: 'positive',
            scope: 'All teams',
        });
    }
    // Powerplay strength
    if (stats.powerplayNetRuns > 0) {
        callouts.push({
            id: 'powerplay-advantage',
            title: 'Powerplay advantage',
            body: `On average, your sides are ${Math.round(stats.powerplayNetRuns)} runs ahead of par during the powerplay.`,
            category: 'Org',
            severity: 'positive',
            scope: 'All teams',
        });
    }
    // All other callouts removed - they were based on mock data
    // When backend provides real stats, add callout logic here
    return callouts;
});
// Actions
function refreshData() {
    // TODO: Hook into real data refresh when backend is ready
    lastSyncLabel.value = 'Just now';
}
function viewAllMatches() {
    router.push({ name: 'AnalystWorkspace' });
}
function handleViewAllInsights() {
    // TODO: Navigate to a dedicated insights page when available
    console.log('View all insights clicked');
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['org-title-row']} */ ;
/** @type {__VLS_StyleScopedClasses['org-empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['org-table']} */ ;
/** @type {__VLS_StyleScopedClasses['org-table']} */ ;
/** @type {__VLS_StyleScopedClasses['org-table']} */ ;
/** @type {__VLS_StyleScopedClasses['org-table']} */ ;
/** @type {__VLS_StyleScopedClasses['org-table']} */ ;
/** @type {__VLS_StyleScopedClasses['org-dashboard-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['org-side-column']} */ ;
/** @type {__VLS_StyleScopedClasses['org-main-column']} */ ;
/** @type {__VLS_StyleScopedClasses['org-dashboard']} */ ;
/** @type {__VLS_StyleScopedClasses['org-header']} */ ;
/** @type {__VLS_StyleScopedClasses['org-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-dashboard" },
});
/** @type {__VLS_StyleScopedClasses['org-dashboard']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "org-header" },
});
/** @type {__VLS_StyleScopedClasses['org-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-header-text" },
});
/** @type {__VLS_StyleScopedClasses['org-header-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-title-row" },
});
/** @type {__VLS_StyleScopedClasses['org-title-row']} */ ;
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
    ...{ class: "org-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['org-subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-header-actions" },
});
/** @type {__VLS_StyleScopedClasses['org-header-actions']} */ ;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_8 = __VLS_7({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
let __VLS_11;
const __VLS_12 = ({ click: {} },
    { onClick: (__VLS_ctx.refreshData) });
const { default: __VLS_13 } = __VLS_9.slots;
// @ts-ignore
[refreshData,];
var __VLS_9;
var __VLS_10;
let __VLS_14;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
    variant: "neutral",
    uppercase: (false),
}));
const __VLS_16 = __VLS_15({
    variant: "neutral",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_15));
const { default: __VLS_19 } = __VLS_17.slots;
(__VLS_ctx.lastSyncLabel);
// @ts-ignore
[lastSyncLabel,];
var __VLS_17;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-dashboard-grid" },
});
/** @type {__VLS_StyleScopedClasses['org-dashboard-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-main-column" },
});
/** @type {__VLS_StyleScopedClasses['org-main-column']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "org-summary" },
});
/** @type {__VLS_StyleScopedClasses['org-summary']} */ ;
let __VLS_20;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
    padding: "md",
    ...{ class: "org-summary-card" },
}));
const __VLS_22 = __VLS_21({
    padding: "md",
    ...{ class: "org-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
/** @type {__VLS_StyleScopedClasses['org-summary-card']} */ ;
const { default: __VLS_25 } = __VLS_23.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-value']} */ ;
(__VLS_ctx.orgStats?.totalTeams ?? '—');
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-footnote']} */ ;
// @ts-ignore
[orgStats,];
var __VLS_23;
let __VLS_26;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
    padding: "md",
    ...{ class: "org-summary-card" },
}));
const __VLS_28 = __VLS_27({
    padding: "md",
    ...{ class: "org-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_27));
/** @type {__VLS_StyleScopedClasses['org-summary-card']} */ ;
const { default: __VLS_31 } = __VLS_29.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-value']} */ ;
(__VLS_ctx.orgStats?.totalMatches ?? '—');
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-footnote']} */ ;
// @ts-ignore
[orgStats,];
var __VLS_29;
let __VLS_32;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent1(__VLS_32, new __VLS_32({
    padding: "md",
    ...{ class: "org-summary-card" },
}));
const __VLS_34 = __VLS_33({
    padding: "md",
    ...{ class: "org-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
/** @type {__VLS_StyleScopedClasses['org-summary-card']} */ ;
const { default: __VLS_37 } = __VLS_35.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-value']} */ ;
(__VLS_ctx.orgStats?.seasonWinRate ?? '—');
(__VLS_ctx.orgStats?.seasonWinRate ? '%' : '');
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-footnote']} */ ;
// @ts-ignore
[orgStats, orgStats,];
var __VLS_35;
let __VLS_38;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_39 = __VLS_asFunctionalComponent1(__VLS_38, new __VLS_38({
    padding: "md",
    ...{ class: "org-summary-card" },
}));
const __VLS_40 = __VLS_39({
    padding: "md",
    ...{ class: "org-summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_39));
/** @type {__VLS_StyleScopedClasses['org-summary-card']} */ ;
const { default: __VLS_43 } = __VLS_41.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-label" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-value" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-value']} */ ;
(__VLS_ctx.orgStats?.avgRunRate ?? '—');
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-summary-footnote" },
});
/** @type {__VLS_StyleScopedClasses['org-summary-footnote']} */ ;
// @ts-ignore
[orgStats,];
var __VLS_41;
let __VLS_44;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_45 = __VLS_asFunctionalComponent1(__VLS_44, new __VLS_44({
    padding: "lg",
    ...{ class: "org-panel" },
}));
const __VLS_46 = __VLS_45({
    padding: "lg",
    ...{ class: "org-panel" },
}, ...__VLS_functionalComponentArgsRest(__VLS_45));
/** @type {__VLS_StyleScopedClasses['org-panel']} */ ;
const { default: __VLS_49 } = __VLS_47.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-panel-header" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "org-panel-title" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-panel-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-subtitle']} */ ;
if (__VLS_ctx.teams.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['org-empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "org-empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['org-empty-hint']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-table-scroll" },
    });
    /** @type {__VLS_StyleScopedClasses['org-table-scroll']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
        ...{ class: "org-table" },
    });
    /** @type {__VLS_StyleScopedClasses['org-table']} */ ;
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
    for (const [team] of __VLS_vFor((__VLS_ctx.teams))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (team.id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.played);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.won);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.lost);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.winPercent);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
        (team.avgScore);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: (team.nrr >= 0 ? 'org-positive' : 'org-negative') },
        });
        (team.nrr >= 0 ? '+' : '');
        (team.nrr.toFixed(2));
        // @ts-ignore
        [teams, teams,];
    }
}
// @ts-ignore
[];
var __VLS_47;
let __VLS_50;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_51 = __VLS_asFunctionalComponent1(__VLS_50, new __VLS_50({
    padding: "lg",
    ...{ class: "org-panel" },
}));
const __VLS_52 = __VLS_51({
    padding: "lg",
    ...{ class: "org-panel" },
}, ...__VLS_functionalComponentArgsRest(__VLS_51));
/** @type {__VLS_StyleScopedClasses['org-panel']} */ ;
const { default: __VLS_55 } = __VLS_53.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-panel-header" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "org-panel-title" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "org-panel-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['org-panel-subtitle']} */ ;
let __VLS_56;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_57 = __VLS_asFunctionalComponent1(__VLS_56, new __VLS_56({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_58 = __VLS_57({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_57));
let __VLS_61;
const __VLS_62 = ({ click: {} },
    { onClick: (__VLS_ctx.viewAllMatches) });
const { default: __VLS_63 } = __VLS_59.slots;
// @ts-ignore
[viewAllMatches,];
var __VLS_59;
var __VLS_60;
if (__VLS_ctx.recentMatches.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['org-empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "org-empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['org-empty-hint']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-matches-list" },
    });
    /** @type {__VLS_StyleScopedClasses['org-matches-list']} */ ;
    for (const [match] of __VLS_vFor((__VLS_ctx.recentMatches))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (match.id),
            ...{ class: "org-match-item" },
        });
        /** @type {__VLS_StyleScopedClasses['org-match-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "org-match-info" },
        });
        /** @type {__VLS_StyleScopedClasses['org-match-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "org-match-teams" },
        });
        /** @type {__VLS_StyleScopedClasses['org-match-teams']} */ ;
        (match.teams);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "org-match-date" },
        });
        /** @type {__VLS_StyleScopedClasses['org-match-date']} */ ;
        (match.date);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "org-match-result" },
        });
        /** @type {__VLS_StyleScopedClasses['org-match-result']} */ ;
        let __VLS_64;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent1(__VLS_64, new __VLS_64({
            variant: (match.won ? 'success' : 'danger'),
            uppercase: (false),
        }));
        const __VLS_66 = __VLS_65({
            variant: (match.won ? 'success' : 'danger'),
            uppercase: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
        const { default: __VLS_69 } = __VLS_67.slots;
        (match.result);
        // @ts-ignore
        [recentMatches, recentMatches,];
        var __VLS_67;
        // @ts-ignore
        [];
    }
}
// @ts-ignore
[];
var __VLS_53;
__VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
    ...{ class: "org-side-column" },
});
/** @type {__VLS_StyleScopedClasses['org-side-column']} */ ;
let __VLS_70;
/** @ts-ignore @type { | typeof __VLS_components.AiCalloutsPanel} */
AiCalloutsPanel;
// @ts-ignore
const __VLS_71 = __VLS_asFunctionalComponent1(__VLS_70, new __VLS_70({
    ...{ 'onViewAll': {} },
    callouts: (__VLS_ctx.orgAiCallouts),
    loading: (__VLS_ctx.orgLoading),
    maxItems: (5),
    dense: true,
    showViewAllButton: true,
    title: "AI Org Callouts",
    description: "High-level patterns and risks across your teams this season.",
}));
const __VLS_72 = __VLS_71({
    ...{ 'onViewAll': {} },
    callouts: (__VLS_ctx.orgAiCallouts),
    loading: (__VLS_ctx.orgLoading),
    maxItems: (5),
    dense: true,
    showViewAllButton: true,
    title: "AI Org Callouts",
    description: "High-level patterns and risks across your teams this season.",
}, ...__VLS_functionalComponentArgsRest(__VLS_71));
let __VLS_75;
const __VLS_76 = ({ viewAll: {} },
    { onViewAll: (__VLS_ctx.handleViewAllInsights) });
var __VLS_73;
var __VLS_74;
if (__VLS_ctx.orgStats) {
    let __VLS_77;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_78 = __VLS_asFunctionalComponent1(__VLS_77, new __VLS_77({
        padding: "md",
        ...{ class: "org-phase-summary" },
    }));
    const __VLS_79 = __VLS_78({
        padding: "md",
        ...{ class: "org-phase-summary" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_78));
    /** @type {__VLS_StyleScopedClasses['org-phase-summary']} */ ;
    const { default: __VLS_82 } = __VLS_80.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "org-phase-title" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "org-phase-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-phase-list" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-list']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-phase-item" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-label" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-value" },
        ...{ class: ((__VLS_ctx.orgStats.powerplayNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative') },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-value']} */ ;
    ((__VLS_ctx.orgStats.powerplayNetRuns ?? 0) >= 0 ? '+' : '');
    (__VLS_ctx.orgStats.powerplayNetRuns ?? 0);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-phase-item" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-label" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-value" },
        ...{ class: ((__VLS_ctx.orgStats.middleNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative') },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-value']} */ ;
    ((__VLS_ctx.orgStats.middleNetRuns ?? 0) >= 0 ? '+' : '');
    (__VLS_ctx.orgStats.middleNetRuns ?? 0);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-phase-item" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-label" },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "org-phase-value" },
        ...{ class: ((__VLS_ctx.orgStats.deathNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative') },
    });
    /** @type {__VLS_StyleScopedClasses['org-phase-value']} */ ;
    ((__VLS_ctx.orgStats.deathNetRuns ?? 0) >= 0 ? '+' : '');
    (__VLS_ctx.orgStats.deathNetRuns ?? 0);
    // @ts-ignore
    [orgStats, orgStats, orgStats, orgStats, orgStats, orgStats, orgStats, orgStats, orgStats, orgStats, orgAiCallouts, orgLoading, handleViewAllInsights,];
    var __VLS_80;
}
if (__VLS_ctx.orgStats?.standoutPlayerName) {
    let __VLS_83;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_84 = __VLS_asFunctionalComponent1(__VLS_83, new __VLS_83({
        padding: "md",
        ...{ class: "org-standout" },
    }));
    const __VLS_85 = __VLS_84({
        padding: "md",
        ...{ class: "org-standout" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_84));
    /** @type {__VLS_StyleScopedClasses['org-standout']} */ ;
    const { default: __VLS_88 } = __VLS_86.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "org-standout-title" },
    });
    /** @type {__VLS_StyleScopedClasses['org-standout-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-standout-player" },
    });
    /** @type {__VLS_StyleScopedClasses['org-standout-player']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "org-standout-name" },
    });
    /** @type {__VLS_StyleScopedClasses['org-standout-name']} */ ;
    (__VLS_ctx.orgStats.standoutPlayerName);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "org-standout-team" },
    });
    /** @type {__VLS_StyleScopedClasses['org-standout-team']} */ ;
    (__VLS_ctx.orgStats.standoutPlayerTeam);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-standout-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['org-standout-stats']} */ ;
    let __VLS_89;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_90 = __VLS_asFunctionalComponent1(__VLS_89, new __VLS_89({
        variant: "success",
        uppercase: (false),
    }));
    const __VLS_91 = __VLS_90({
        variant: "success",
        uppercase: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_90));
    const { default: __VLS_94 } = __VLS_92.slots;
    (__VLS_ctx.orgStats.standoutPlayerImpact);
    // @ts-ignore
    [orgStats, orgStats, orgStats, orgStats,];
    var __VLS_92;
    // @ts-ignore
    [];
    var __VLS_86;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
