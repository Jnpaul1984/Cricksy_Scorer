/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, ref, onMounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { BaseCard, BaseButton, BaseBadge, ImpactBar, MiniSparkline, AiCalloutsPanel } from '@/components';
import { getMatchCaseStudy, getMatchAiSummary } from '@/services/api';
const route = useRoute();
const router = useRouter();
const matchId = computed(() => route.params.matchId);
// Reactive state for API data
const loading = ref(true);
const error = ref(null);
const caseStudy = ref(null);
// AI Summary state (dedicated endpoint)
const aiSummary = ref(null);
const aiSummaryLoading = ref(false);
const aiSummaryError = ref(null);
// Derived view-model bindings from caseStudy
const match = computed(() => caseStudy.value?.match ?? null);
const momentumSummary = computed(() => caseStudy.value?.momentum_summary ?? null);
const keyPhase = computed(() => caseStudy.value?.key_phase ?? null);
const phaseBreakdown = computed(() => {
    return (caseStudy.value?.phases ?? []);
});
const keyPlayers = computed(() => caseStudy.value?.key_players ?? []);
// FIX A7: Use real ai_summary from backend, show "unavailable" if missing
const aiSummaryData = computed(() => {
    const cs = caseStudy.value;
    if (!cs)
        return null;
    // Check if backend provides ai_summary structure
    const backendAiSummary = cs.ai?.match_summary;
    if (backendAiSummary && typeof backendAiSummary === 'object') {
        // Backend provides full AI summary structure - use it directly
        return backendAiSummary;
    }
    // If only text summary available, wrap it
    if (backendAiSummary && typeof backendAiSummary === 'string') {
        return {
            overview: backendAiSummary,
            key_moments: [],
            tactical_themes: [],
            innings_summaries: [],
            player_highlights: []
        };
    }
    // No AI summary available - return null to show "unavailable" UI state
    return null;
});
// Computed helpers for AI summary template - prefer dedicated endpoint, fallback to derived
const hasAISummary = computed(() => !!aiSummary.value || !!aiSummaryData.value);
const aiOverallSummary = computed(() => aiSummary.value?.overall_summary ?? '');
const aiOverview = computed(() => aiSummary.value?.overall_summary || aiSummary.value?.headline || aiSummaryData.value?.overview || '');
const aiKeyThemes = computed(() => aiSummary.value?.key_themes ?? []);
const aiTacticalThemes = computed(() => aiSummary.value?.tactical_themes ?? aiSummary.value?.key_themes ?? aiSummaryData.value?.tactical_themes ?? []);
const aiInningsSummaries = computed(() => aiSummaryData.value?.innings_summaries ?? []);
const aiDecisivePhases = computed(() => aiSummary.value?.decisive_phases ?? []);
const aiMomentumShifts = computed(() => aiSummary.value?.momentum_shifts ?? []);
const aiTeams = computed(() => aiSummary.value?.teams ?? []);
const aiPlayerHighlightsRich = computed(() => aiSummary.value?.player_highlights ?? []);
const aiTags = computed(() => aiSummary.value?.tags ?? []);
// Per-match AI callouts derived from case study data
const matchAiLoading = computed(() => loading.value);
const matchAiCallouts = computed(() => {
    const cs = caseStudy.value;
    if (!cs)
        return [];
    const callouts = [];
    const phases = (cs.phases ?? []);
    const players = cs.key_players ?? [];
    // Find noteworthy phases by type
    const powerplayPhases = phases.filter((p) => p.id === 'powerplay');
    const deathPhases = phases.filter((p) => p.id === 'death');
    const middlePhases = phases.filter((p) => p.id === 'middle');
    // Powerplay dominance
    const strongPowerplay = powerplayPhases.find((p) => p.net_swing_vs_par >= 10);
    if (strongPowerplay) {
        const teamName = strongPowerplay.team ?? 'The batting side';
        const inningsIdx = strongPowerplay.innings_index ?? 0;
        callouts.push({
            id: 'powerplay-domination',
            title: 'Powerplay domination',
            body: `${teamName} finished the powerplay about ${Math.round(strongPowerplay.net_swing_vs_par)} runs ahead of par, setting up the innings.`,
            category: 'Batting',
            severity: 'positive',
            scope: `Powerplay`,
            targetDomId: `phase-${inningsIdx}-powerplay`,
            targetGroupId: inningsIdx,
        });
    }
    // Powerplay struggle
    const weakPowerplay = powerplayPhases.find((p) => p.net_swing_vs_par <= -10);
    if (weakPowerplay) {
        const teamName = weakPowerplay.team ?? 'The batting side';
        const inningsIdx = weakPowerplay.innings_index ?? 0;
        callouts.push({
            id: 'powerplay-struggle',
            title: 'Powerplay struggle',
            body: `${teamName} fell ${Math.abs(Math.round(weakPowerplay.net_swing_vs_par))} runs below par in the powerplay.`,
            category: 'Batting',
            severity: 'warning',
            scope: `Powerplay`,
            targetDomId: `phase-${inningsIdx}-powerplay`,
            targetGroupId: inningsIdx,
        });
    }
    // Death overs collapse
    const badDeathPhase = deathPhases.find((p) => p.net_swing_vs_par <= -8 || p.wickets >= 3);
    if (badDeathPhase) {
        const teamName = badDeathPhase.team ?? 'The batting side';
        const inningsIdx = badDeathPhase.innings_index ?? 0;
        callouts.push({
            id: 'death-overs-collapse',
            title: 'Death overs collapse',
            body: `${teamName} struggled at the death, with ${badDeathPhase.wickets} wickets and ${Math.abs(Math.round(badDeathPhase.net_swing_vs_par))} runs below par.`,
            category: 'Batting',
            severity: 'warning',
            scope: `Death overs`,
            targetDomId: `phase-${inningsIdx}-death`,
            targetGroupId: inningsIdx,
        });
    }
    // Death overs surge
    const goodDeathPhase = deathPhases.find((p) => p.net_swing_vs_par >= 10);
    if (goodDeathPhase) {
        const teamName = goodDeathPhase.team ?? 'The batting side';
        const inningsIdx = goodDeathPhase.innings_index ?? 0;
        callouts.push({
            id: 'death-overs-surge',
            title: 'Death overs surge',
            body: `${teamName} accelerated brilliantly at the death, finishing ${Math.round(goodDeathPhase.net_swing_vs_par)} runs ahead of par.`,
            category: 'Batting',
            severity: 'positive',
            scope: `Death overs`,
            targetDomId: `phase-${inningsIdx}-death`,
            targetGroupId: inningsIdx,
        });
    }
    // Middle overs squeeze
    const middleSqueeze = middlePhases.find((p) => p.net_swing_vs_par <= -8);
    if (middleSqueeze) {
        const inningsIdx = middleSqueeze.innings_index ?? 0;
        callouts.push({
            id: 'middle-overs-choke',
            title: 'Middle overs choke',
            body: `Scoring slowed significantly in the middle overs, with the run rate dipping ${Math.abs(Math.round(middleSqueeze.net_swing_vs_par))} below par.`,
            category: 'Bowling',
            severity: 'info',
            scope: `Middle overs`,
            targetDomId: `phase-${inningsIdx}-middle`,
            targetGroupId: inningsIdx,
        });
    }
    // High-impact player
    const impactPlayer = players.find((p) => p.impact === 'high');
    if (impactPlayer) {
        let contribution = '';
        if (impactPlayer.batting && impactPlayer.batting.runs >= 30) {
            contribution = `scored ${impactPlayer.batting.runs} runs`;
        }
        if (impactPlayer.bowling && impactPlayer.bowling.wickets >= 2) {
            contribution += contribution ? ' and ' : '';
            contribution += `took ${impactPlayer.bowling.wickets} wickets`;
        }
        if (contribution) {
            callouts.push({
                id: 'impact-player',
                title: 'Match-defining performance',
                body: `${impactPlayer.name} ${contribution}, producing a match-winning contribution.`,
                category: 'Players',
                severity: 'positive',
                scope: impactPlayer.name,
            });
        }
    }
    // Key tactical theme from AI summary
    const aiData = aiSummaryData.value;
    if (aiData?.tactical_themes?.length) {
        callouts.push({
            id: 'tactical-theme',
            title: 'Key tactical theme',
            body: aiData.tactical_themes[0],
            category: 'Tactics',
            severity: 'info',
            scope: 'Full match',
        });
    }
    // --- Callouts from AI Summary endpoint (decisive phases) ---
    const aiSummaryVal = aiSummary.value;
    if (aiSummaryVal?.decisive_phases?.length) {
        // Death overs collapse from AI summary
        const deathCollapsePhase = aiSummaryVal.decisive_phases.find((p) => p.label.toLowerCase().includes('death') && p.impact_score < -20);
        if (deathCollapsePhase) {
            callouts.push({
                id: 'ai-death-collapse',
                title: 'Death overs collapse',
                body: deathCollapsePhase.narrative,
                category: 'Batting',
                severity: 'warning',
                scope: deathCollapsePhase.label,
                targetDomId: `mc-phase-${deathCollapsePhase.phase_id}`,
            });
        }
        // Powerplay dominance from AI summary
        const powerplayDominancePhase = aiSummaryVal.decisive_phases.find((p) => p.label.toLowerCase().includes('powerplay') && p.impact_score > 20);
        if (powerplayDominancePhase) {
            callouts.push({
                id: 'ai-powerplay-dominance',
                title: 'Powerplay dominance',
                body: powerplayDominancePhase.narrative,
                category: 'Batting',
                severity: 'positive',
                scope: powerplayDominancePhase.label,
                targetDomId: `mc-phase-${powerplayDominancePhase.phase_id}`,
            });
        }
        // Middle overs control from AI summary
        const middleControlPhase = aiSummaryVal.decisive_phases.find((p) => p.label.toLowerCase().includes('middle') && Math.abs(p.impact_score) > 15);
        if (middleControlPhase) {
            const isPositive = middleControlPhase.impact_score > 0;
            callouts.push({
                id: 'ai-middle-control',
                title: isPositive ? 'Middle overs control' : 'Middle overs squeeze',
                body: middleControlPhase.narrative,
                category: isPositive ? 'Batting' : 'Bowling',
                severity: isPositive ? 'positive' : 'warning',
                scope: middleControlPhase.label,
                targetDomId: `mc-phase-${middleControlPhase.phase_id}`,
            });
        }
    }
    // --- Callouts from momentum shifts ---
    if (aiSummaryVal?.momentum_shifts?.length) {
        // Multiple momentum swings
        if (aiSummaryVal.momentum_shifts.length >= 3) {
            callouts.push({
                id: 'ai-momentum-swings',
                title: 'Multiple momentum swings',
                body: `This match saw ${aiSummaryVal.momentum_shifts.length} key momentum shifts, making it a closely contested affair.`,
                category: 'Match Flow',
                severity: 'info',
                scope: 'Full match',
            });
        }
        // Biggest momentum shift
        const biggestShift = aiSummaryVal.momentum_shifts.reduce((max, s) => Math.abs(s.impact_delta) > Math.abs(max.impact_delta) ? s : max, aiSummaryVal.momentum_shifts[0]);
        if (biggestShift && Math.abs(biggestShift.impact_delta) >= 15) {
            callouts.push({
                id: 'ai-big-momentum-shift',
                title: 'Critical turning point',
                body: `Over ${biggestShift.over}: ${biggestShift.description}`,
                category: 'Match Flow',
                severity: biggestShift.impact_delta > 0 ? 'positive' : 'warning',
                scope: `Over ${biggestShift.over}`,
            });
        }
    }
    return callouts;
});
// Filter state for phases
const selectedInningsIndex = ref(0);
const selectedImpactFilter = ref('all');
// Derive innings options from match.innings
const inningsOptions = computed(() => {
    const m = match.value;
    if (!m || !m.innings || m.innings.length === 0) {
        return [];
    }
    return m.innings.map((inn, index) => {
        const labelParts = [];
        if (inn.team)
            labelParts.push(inn.team);
        labelParts.push(`Innings ${index + 1}`);
        return {
            index,
            label: labelParts.join(' • ')
        };
    });
});
// Compute filtered phases based on selected innings and impact filter
const filteredPhases = computed(() => {
    const phases = phaseBreakdown.value;
    if (!phases.length)
        return [];
    const inningsIndex = selectedInningsIndex.value;
    // Filter by innings if any phase has innings_index
    let result = phases;
    const anyHasInningsIndex = phases.some((p) => typeof p.innings_index === 'number');
    if (anyHasInningsIndex) {
        result = result.filter((p) => (p.innings_index ?? 0) === inningsIndex);
    }
    // Filter by impact
    const impactFilter = selectedImpactFilter.value;
    if (impactFilter !== 'all') {
        result = result.filter((p) => p.impact === impactFilter);
    }
    return result;
});
// Reset selectedInningsIndex if it goes out of range when innings options change
watch(inningsOptions, (newOptions) => {
    if (newOptions.length > 0 && selectedInningsIndex.value >= newOptions.length) {
        selectedInningsIndex.value = 0;
    }
});
// Fetch case study data from API
async function loadCaseStudy() {
    if (!matchId.value)
        return;
    loading.value = true;
    error.value = null;
    try {
        const data = await getMatchCaseStudy(matchId.value);
        caseStudy.value = data;
    }
    catch (e) {
        console.error('Failed to load case study:', e);
        error.value = e?.message || 'Could not load match case study.';
    }
    finally {
        loading.value = false;
    }
}
// Fetch AI summary from dedicated endpoint
async function loadAiSummary() {
    if (!matchId.value)
        return;
    aiSummaryLoading.value = true;
    aiSummaryError.value = null;
    try {
        aiSummary.value = await getMatchAiSummary(matchId.value);
    }
    catch (e) {
        console.error('Failed to load AI summary:', e);
        aiSummaryError.value = 'AI summary not available yet.';
        aiSummary.value = null;
    }
    finally {
        aiSummaryLoading.value = false;
    }
}
// Load on mount and when matchId changes
onMounted(() => {
    loadCaseStudy();
    loadAiSummary();
});
watch(matchId, () => {
    loadCaseStudy();
    loadAiSummary();
});
// Actions
function goBack() {
    if (window.history.length > 1) {
        router.back();
    }
    else {
        router.push({ name: 'AnalystWorkspace' });
    }
}
function goToPlayerProfile(playerId) {
    if (!playerId)
        return;
    router.push({
        name: 'PlayerProfile',
        params: { playerId },
    });
}
function regenerateSummary() {
    // Reload the AI summary from the backend
    loadAiSummary();
}
// Helper functions for phase display
function deriveImpactLabel(phase) {
    const impact = phase.net_swing_vs_par ?? 0;
    if (impact > 1)
        return 'Above par';
    if (impact < -1)
        return 'Below par';
    return 'Around par';
}
function formatSigned(value) {
    if (value == null)
        return '—';
    const rounded = Math.round(value * 10) / 10;
    return (rounded > 0 ? '+' : '') + rounded.toString();
}
function formatSignedPercent(value) {
    if (value == null)
        return '—';
    const pct = Math.round(value * 10) / 10;
    return (pct > 0 ? '+' : '') + pct.toString() + '%';
}
function getSparklineVariant(phase) {
    if (phase.impact === 'positive')
        return 'positive';
    if (phase.impact === 'negative')
        return 'negative';
    return 'default';
}
/**
 * Generate a stable DOM id for a phase card based on phase id and innings.
 * This allows the AI Callouts panel to scroll to the relevant phase card.
 */
function getPhaseCardDomId(phase) {
    const inningsIdx = phase.innings_index ?? 0;
    const phaseKey = phase.id.toLowerCase().replace(/\s+/g, '-');
    return `phase-${inningsIdx}-${phaseKey}`;
}
/**
 * Handle AI callout selection - scroll to the relevant phase card and flash the ImpactBar.
 * 1) Switch to correct innings tab if targetGroupId is provided
 * 2) Wait for DOM update with nextTick
 * 3) Scroll to the phase card
 * 4) Flash the ImpactBar or highlight the card
 */
function handleCalloutSelect(callout) {
    // Switch innings tab first if targetGroupId (innings index) is provided
    if (typeof callout.targetGroupId === 'number') {
        selectedInningsIndex.value = callout.targetGroupId;
    }
    const domId = callout.targetDomId;
    if (!domId)
        return;
    // Use nextTick to ensure DOM is updated after switching innings tab
    nextTick(() => {
        const el = document.getElementById(domId);
        if (!el)
            return;
        // Scroll smoothly into view
        el.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
        });
        // Highlight the whole phase card
        el.classList.add('mc-phase--highlight');
        // Also flash the ImpactBar inside, if present
        const impactBarWrapper = el.querySelector('.impact-bar-wrapper');
        if (impactBarWrapper) {
            impactBarWrapper.classList.add('mc-phase-impact--flash');
            window.setTimeout(() => {
                impactBarWrapper.classList.remove('mc-phase-impact--flash');
            }, 1200);
        }
        // Check if it's an AI summary phase item (different styling)
        if (el.classList.contains('cs-ai-phase-item')) {
            el.classList.add('cs-ai-phase-item--highlight');
            window.setTimeout(() => {
                el.classList.remove('cs-ai-phase-item--highlight');
            }, 1400);
        }
        // Remove highlight after animation
        window.setTimeout(() => {
            el.classList.remove('mc-phase--highlight');
        }, 1400);
    });
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-title-block']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-not-found-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-not-found-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phase-moments']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phase-moments']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-player-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-player-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-player-pill--static']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-empty']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-innings-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-innings-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-highlight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-highlight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-main']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-ai-layout']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phases-header']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phases-filters']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phases-innings-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phases-impact-filters']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phase-metrics']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-phase-metrics-trend']} */ ;
/** @type {__VLS_StyleScopedClasses['case-study']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-header']} */ ;
/** @type {__VLS_StyleScopedClasses['cs-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "case-study" },
});
/** @type {__VLS_StyleScopedClasses['case-study']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "cs-header" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-header-left" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header-left']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        ...{ class: "cs-skeleton-card cs-skeleton-card--inline" },
        padding: "sm",
    }));
    const __VLS_2 = __VLS_1({
        ...{ class: "cs-skeleton-card cs-skeleton-card--inline" },
        padding: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card--inline']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    // @ts-ignore
    [loading,];
    var __VLS_3;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-title-block" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-title-block']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-header-right" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header-right']} */ ;
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        ...{ class: "cs-skeleton-card cs-skeleton-card--badge" },
        padding: "sm",
    }));
    const __VLS_8 = __VLS_7({
        ...{ class: "cs-skeleton-card cs-skeleton-card--badge" },
        padding: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card--badge']} */ ;
    const { default: __VLS_11 } = __VLS_9.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    // @ts-ignore
    [];
    var __VLS_9;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "cs-summary" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-summary']} */ ;
    let __VLS_12;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }));
    const __VLS_14 = __VLS_13({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_17 } = __VLS_15.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    // @ts-ignore
    [];
    var __VLS_15;
    let __VLS_18;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }));
    const __VLS_20 = __VLS_19({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_23 } = __VLS_21.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    // @ts-ignore
    [];
    var __VLS_21;
    let __VLS_24;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }));
    const __VLS_26 = __VLS_25({
        ...{ class: "cs-skeleton-card" },
        padding: "md",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_29 } = __VLS_27.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    // @ts-ignore
    [];
    var __VLS_27;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "cs-main" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-main']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-main-left" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-main-left']} */ ;
    let __VLS_30;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }));
    const __VLS_32 = __VLS_31({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_31));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_35 } = __VLS_33.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-phase-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-phase-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-phase-card" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-phase-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-phase-card" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-phase-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-phase-card" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-phase-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    // @ts-ignore
    [];
    var __VLS_33;
    let __VLS_36;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }));
    const __VLS_38 = __VLS_37({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_41 } = __VLS_39.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-table" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-table']} */ ;
    for (const [i] of __VLS_vFor((4))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (i),
            ...{ class: "cs-skeleton-row" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-skeleton-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
        /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
        // @ts-ignore
        [];
    }
    // @ts-ignore
    [];
    var __VLS_39;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-main-right" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-main-right']} */ ;
    let __VLS_42;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }));
    const __VLS_44 = __VLS_43({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_43));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_47 } = __VLS_45.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--sm" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--sm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-ai-block" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-ai-block']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--full" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--full']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--full" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--full']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    // @ts-ignore
    [];
    var __VLS_45;
    let __VLS_48;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent1(__VLS_48, new __VLS_48({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }));
    const __VLS_50 = __VLS_49({
        ...{ class: "cs-skeleton-card" },
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-card']} */ ;
    const { default: __VLS_53 } = __VLS_51.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-dismissal" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-dismissal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "cs-skeleton-line cs-skeleton-line--full" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--full']} */ ;
    // @ts-ignore
    [];
    var __VLS_51;
}
else if (__VLS_ctx.error) {
    let __VLS_54;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_55 = __VLS_asFunctionalComponent1(__VLS_54, new __VLS_54({
        padding: "lg",
        ...{ class: "cs-error" },
    }));
    const __VLS_56 = __VLS_55({
        padding: "lg",
        ...{ class: "cs-error" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_55));
    /** @type {__VLS_StyleScopedClasses['cs-error']} */ ;
    const { default: __VLS_59 } = __VLS_57.slots;
    (__VLS_ctx.error);
    // @ts-ignore
    [error, error,];
    var __VLS_57;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "cs-header" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-header-left" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header-left']} */ ;
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
        { onClick: (__VLS_ctx.goBack) });
    const { default: __VLS_67 } = __VLS_63.slots;
    // @ts-ignore
    [goBack,];
    var __VLS_63;
    var __VLS_64;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-title-block" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-title-block']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "cs-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "cs-header-right" },
    });
    /** @type {__VLS_StyleScopedClasses['cs-header-right']} */ ;
    let __VLS_68;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent1(__VLS_68, new __VLS_68({
        variant: "neutral",
        uppercase: (false),
    }));
    const __VLS_70 = __VLS_69({
        variant: "neutral",
        uppercase: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    const { default: __VLS_73 } = __VLS_71.slots;
    (__VLS_ctx.matchId);
    // @ts-ignore
    [matchId,];
    var __VLS_71;
    if (__VLS_ctx.match) {
        let __VLS_74;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_75 = __VLS_asFunctionalComponent1(__VLS_74, new __VLS_74({
            variant: "primary",
            uppercase: (false),
        }));
        const __VLS_76 = __VLS_75({
            variant: "primary",
            uppercase: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_75));
        const { default: __VLS_79 } = __VLS_77.slots;
        (__VLS_ctx.match.teams_label);
        // @ts-ignore
        [match, match,];
        var __VLS_77;
    }
    if (__VLS_ctx.match) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "cs-summary" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-summary']} */ ;
        let __VLS_80;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_81 = __VLS_asFunctionalComponent1(__VLS_80, new __VLS_80({
            padding: "md",
            ...{ class: "cs-summary-card" },
        }));
        const __VLS_82 = __VLS_81({
            padding: "md",
            ...{ class: "cs-summary-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_81));
        /** @type {__VLS_StyleScopedClasses['cs-summary-card']} */ ;
        const { default: __VLS_85 } = __VLS_83.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-label" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-value" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-value']} */ ;
        (__VLS_ctx.match.result);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-footnote" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-footnote']} */ ;
        (__VLS_ctx.match.date);
        (__VLS_ctx.match.format);
        // @ts-ignore
        [match, match, match, match,];
        var __VLS_83;
        if (__VLS_ctx.momentumSummary) {
            let __VLS_86;
            /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
            BaseCard;
            // @ts-ignore
            const __VLS_87 = __VLS_asFunctionalComponent1(__VLS_86, new __VLS_86({
                padding: "md",
                ...{ class: "cs-summary-card" },
            }));
            const __VLS_88 = __VLS_87({
                padding: "md",
                ...{ class: "cs-summary-card" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_87));
            /** @type {__VLS_StyleScopedClasses['cs-summary-card']} */ ;
            const { default: __VLS_91 } = __VLS_89.slots;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-label" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-value" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-value']} */ ;
            (__VLS_ctx.momentumSummary.title);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-footnote" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-footnote']} */ ;
            (__VLS_ctx.momentumSummary.subtitle);
            // @ts-ignore
            [momentumSummary, momentumSummary, momentumSummary,];
            var __VLS_89;
        }
        if (__VLS_ctx.keyPhase) {
            let __VLS_92;
            /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
            BaseCard;
            // @ts-ignore
            const __VLS_93 = __VLS_asFunctionalComponent1(__VLS_92, new __VLS_92({
                padding: "md",
                ...{ class: "cs-summary-card" },
            }));
            const __VLS_94 = __VLS_93({
                padding: "md",
                ...{ class: "cs-summary-card" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_93));
            /** @type {__VLS_StyleScopedClasses['cs-summary-card']} */ ;
            const { default: __VLS_97 } = __VLS_95.slots;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-label" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-value" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-value']} */ ;
            (__VLS_ctx.keyPhase.title);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-footnote" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-footnote']} */ ;
            (__VLS_ctx.keyPhase.detail);
            // @ts-ignore
            [keyPhase, keyPhase, keyPhase,];
            var __VLS_95;
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "cs-not-found" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-not-found']} */ ;
        let __VLS_98;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_99 = __VLS_asFunctionalComponent1(__VLS_98, new __VLS_98({
            padding: "lg",
            ...{ class: "cs-not-found-card" },
        }));
        const __VLS_100 = __VLS_99({
            padding: "lg",
            ...{ class: "cs-not-found-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_99));
        /** @type {__VLS_StyleScopedClasses['cs-not-found-card']} */ ;
        const { default: __VLS_103 } = __VLS_101.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (__VLS_ctx.matchId);
        let __VLS_104;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_105 = __VLS_asFunctionalComponent1(__VLS_104, new __VLS_104({
            ...{ 'onClick': {} },
            variant: "primary",
            size: "sm",
        }));
        const __VLS_106 = __VLS_105({
            ...{ 'onClick': {} },
            variant: "primary",
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_105));
        let __VLS_109;
        const __VLS_110 = ({ click: {} },
            { onClick: (__VLS_ctx.goBack) });
        const { default: __VLS_111 } = __VLS_107.slots;
        // @ts-ignore
        [goBack, matchId,];
        var __VLS_107;
        var __VLS_108;
        // @ts-ignore
        [];
        var __VLS_101;
    }
    if (__VLS_ctx.match) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "cs-main" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-main']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-main-left" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-main-left']} */ ;
        let __VLS_112;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_113 = __VLS_asFunctionalComponent1(__VLS_112, new __VLS_112({
            padding: "lg",
            ...{ class: "cs-panel" },
        }));
        const __VLS_114 = __VLS_113({
            padding: "lg",
            ...{ class: "cs-panel" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_113));
        /** @type {__VLS_StyleScopedClasses['cs-panel']} */ ;
        const { default: __VLS_117 } = __VLS_115.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-phases-header" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-phases-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "cs-panel-title" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-panel-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-subtitle']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-phases-filters" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-phases-filters']} */ ;
        if (__VLS_ctx.inningsOptions.length > 1) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-phases-innings-tabs" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-phases-innings-tabs']} */ ;
            for (const [opt] of __VLS_vFor((__VLS_ctx.inningsOptions))) {
                let __VLS_118;
                /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
                BaseButton;
                // @ts-ignore
                const __VLS_119 = __VLS_asFunctionalComponent1(__VLS_118, new __VLS_118({
                    ...{ 'onClick': {} },
                    key: (opt.index),
                    size: "sm",
                    variant: (opt.index === __VLS_ctx.selectedInningsIndex ? 'primary' : 'ghost'),
                }));
                const __VLS_120 = __VLS_119({
                    ...{ 'onClick': {} },
                    key: (opt.index),
                    size: "sm",
                    variant: (opt.index === __VLS_ctx.selectedInningsIndex ? 'primary' : 'ghost'),
                }, ...__VLS_functionalComponentArgsRest(__VLS_119));
                let __VLS_123;
                const __VLS_124 = ({ click: {} },
                    { onClick: (...[$event]) => {
                            if (!!(__VLS_ctx.loading))
                                return;
                            if (!!(__VLS_ctx.error))
                                return;
                            if (!(__VLS_ctx.match))
                                return;
                            if (!(__VLS_ctx.inningsOptions.length > 1))
                                return;
                            __VLS_ctx.selectedInningsIndex = opt.index;
                            // @ts-ignore
                            [match, inningsOptions, inningsOptions, selectedInningsIndex, selectedInningsIndex,];
                        } });
                const { default: __VLS_125 } = __VLS_121.slots;
                (opt.label);
                // @ts-ignore
                [];
                var __VLS_121;
                var __VLS_122;
                // @ts-ignore
                [];
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-phases-impact-filters" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-phases-impact-filters']} */ ;
        let __VLS_126;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_127 = __VLS_asFunctionalComponent1(__VLS_126, new __VLS_126({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'all' ? 'secondary' : 'ghost'),
        }));
        const __VLS_128 = __VLS_127({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'all' ? 'secondary' : 'ghost'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_127));
        let __VLS_131;
        const __VLS_132 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    if (!(__VLS_ctx.match))
                        return;
                    __VLS_ctx.selectedImpactFilter = 'all';
                    // @ts-ignore
                    [selectedImpactFilter, selectedImpactFilter,];
                } });
        const { default: __VLS_133 } = __VLS_129.slots;
        // @ts-ignore
        [];
        var __VLS_129;
        var __VLS_130;
        let __VLS_134;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_135 = __VLS_asFunctionalComponent1(__VLS_134, new __VLS_134({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'positive' ? 'secondary' : 'ghost'),
        }));
        const __VLS_136 = __VLS_135({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'positive' ? 'secondary' : 'ghost'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_135));
        let __VLS_139;
        const __VLS_140 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    if (!(__VLS_ctx.match))
                        return;
                    __VLS_ctx.selectedImpactFilter = 'positive';
                    // @ts-ignore
                    [selectedImpactFilter, selectedImpactFilter,];
                } });
        const { default: __VLS_141 } = __VLS_137.slots;
        // @ts-ignore
        [];
        var __VLS_137;
        var __VLS_138;
        let __VLS_142;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_143 = __VLS_asFunctionalComponent1(__VLS_142, new __VLS_142({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'negative' ? 'secondary' : 'ghost'),
        }));
        const __VLS_144 = __VLS_143({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'negative' ? 'secondary' : 'ghost'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_143));
        let __VLS_147;
        const __VLS_148 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    if (!(__VLS_ctx.match))
                        return;
                    __VLS_ctx.selectedImpactFilter = 'negative';
                    // @ts-ignore
                    [selectedImpactFilter, selectedImpactFilter,];
                } });
        const { default: __VLS_149 } = __VLS_145.slots;
        // @ts-ignore
        [];
        var __VLS_145;
        var __VLS_146;
        let __VLS_150;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_151 = __VLS_asFunctionalComponent1(__VLS_150, new __VLS_150({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'neutral' ? 'secondary' : 'ghost'),
        }));
        const __VLS_152 = __VLS_151({
            ...{ 'onClick': {} },
            size: "sm",
            variant: (__VLS_ctx.selectedImpactFilter === 'neutral' ? 'secondary' : 'ghost'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_151));
        let __VLS_155;
        const __VLS_156 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    if (!(__VLS_ctx.match))
                        return;
                    __VLS_ctx.selectedImpactFilter = 'neutral';
                    // @ts-ignore
                    [selectedImpactFilter, selectedImpactFilter,];
                } });
        const { default: __VLS_157 } = __VLS_153.slots;
        // @ts-ignore
        [];
        var __VLS_153;
        var __VLS_154;
        if (__VLS_ctx.phaseBreakdown.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-empty-state" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-state']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-empty-hint" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-hint']} */ ;
        }
        else if (__VLS_ctx.filteredPhases.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-empty-state" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-state']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-empty-hint" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-hint']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-phase-grid" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-phase-grid']} */ ;
            for (const [phase] of __VLS_vFor((__VLS_ctx.filteredPhases))) {
                let __VLS_158;
                /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
                BaseCard;
                // @ts-ignore
                const __VLS_159 = __VLS_asFunctionalComponent1(__VLS_158, new __VLS_158({
                    id: (__VLS_ctx.getPhaseCardDomId(phase)),
                    key: (`${phase.id}-${phase.start_over}-${phase.end_over}`),
                    ...{ class: "cs-phase-card" },
                    padding: "md",
                    dataPhase: (phase.id),
                    dataInnings: (phase.innings_index),
                }));
                const __VLS_160 = __VLS_159({
                    id: (__VLS_ctx.getPhaseCardDomId(phase)),
                    key: (`${phase.id}-${phase.start_over}-${phase.end_over}`),
                    ...{ class: "cs-phase-card" },
                    padding: "md",
                    dataPhase: (phase.id),
                    dataInnings: (phase.innings_index),
                }, ...__VLS_functionalComponentArgsRest(__VLS_159));
                /** @type {__VLS_StyleScopedClasses['cs-phase-card']} */ ;
                const { default: __VLS_163 } = __VLS_161.slots;
                __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
                    ...{ class: "cs-phase-header" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-header']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-phase-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-title']} */ ;
                (phase.label);
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "cs-phase-meta" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-meta']} */ ;
                (phase.start_over);
                (phase.end_over);
                (phase.runs);
                (phase.wickets);
                let __VLS_164;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_165 = __VLS_asFunctionalComponent1(__VLS_164, new __VLS_164({
                    variant: (phase.impact === 'positive'
                        ? 'success'
                        : phase.impact === 'negative'
                            ? 'danger'
                            : 'neutral'),
                    uppercase: (true),
                }));
                const __VLS_166 = __VLS_165({
                    variant: (phase.impact === 'positive'
                        ? 'success'
                        : phase.impact === 'negative'
                            ? 'danger'
                            : 'neutral'),
                    uppercase: (true),
                }, ...__VLS_functionalComponentArgsRest(__VLS_165));
                const { default: __VLS_169 } = __VLS_167.slots;
                (phase.id.toUpperCase());
                // @ts-ignore
                [phaseBreakdown, filteredPhases, filteredPhases, getPhaseCardDomId,];
                var __VLS_167;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-phase-metrics" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-metrics']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-phase-metrics-main impact-bar-wrapper" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-metrics-main']} */ ;
                /** @type {__VLS_StyleScopedClasses['impact-bar-wrapper']} */ ;
                let __VLS_170;
                /** @ts-ignore @type { | typeof __VLS_components.ImpactBar} */
                ImpactBar;
                // @ts-ignore
                const __VLS_171 = __VLS_asFunctionalComponent1(__VLS_170, new __VLS_170({
                    value: (phase.net_swing_vs_par),
                    min: (-20),
                    max: (20),
                    size: "sm",
                    label: (phase.impact_label || __VLS_ctx.deriveImpactLabel(phase)),
                    positiveLabel: ('Batting in control'),
                    negativeLabel: ('Bowling pressure'),
                }));
                const __VLS_172 = __VLS_171({
                    value: (phase.net_swing_vs_par),
                    min: (-20),
                    max: (20),
                    size: "sm",
                    label: (phase.impact_label || __VLS_ctx.deriveImpactLabel(phase)),
                    positiveLabel: ('Batting in control'),
                    negativeLabel: ('Bowling pressure'),
                }, ...__VLS_functionalComponentArgsRest(__VLS_171));
                if (phase.run_rate_series?.length) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-phase-metrics-trend" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-metrics-trend']} */ ;
                    let __VLS_175;
                    /** @ts-ignore @type { | typeof __VLS_components.MiniSparkline} */
                    MiniSparkline;
                    // @ts-ignore
                    const __VLS_176 = __VLS_asFunctionalComponent1(__VLS_175, new __VLS_175({
                        points: (phase.run_rate_series),
                        highlightLast: (true),
                        variant: (__VLS_ctx.getSparklineVariant(phase)),
                    }));
                    const __VLS_177 = __VLS_176({
                        points: (phase.run_rate_series),
                        highlightLast: (true),
                        variant: (__VLS_ctx.getSparklineVariant(phase)),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_176));
                    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                        ...{ class: "cs-phase-trend-label" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-trend-label']} */ ;
                }
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-phase-numbers" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-numbers']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-phase-number" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "cs-phase-number-label" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number-label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "cs-phase-number-value" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number-value']} */ ;
                (phase.run_rate.toFixed(2));
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-phase-number" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "cs-phase-number-label" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number-label']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "cs-phase-number-value" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-phase-number-value']} */ ;
                (__VLS_ctx.formatSigned(phase.net_swing_vs_par));
                if (phase.win_prob_delta != null) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-phase-number" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-number']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-phase-number-label" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-number-label']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-phase-number-value" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-number-value']} */ ;
                    (__VLS_ctx.formatSignedPercent(phase.win_prob_delta));
                }
                if (phase.key_moments?.length) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-phase-moments" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-moments']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
                    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
                    for (const [moment, idx] of __VLS_vFor((phase.key_moments))) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                            key: (idx),
                        });
                        (moment);
                        // @ts-ignore
                        [deriveImpactLabel, getSparklineVariant, formatSigned, formatSignedPercent,];
                    }
                }
                if (phase.tags?.length) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-phase-tags" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-phase-tags']} */ ;
                    for (const [tag] of __VLS_vFor((phase.tags))) {
                        let __VLS_180;
                        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                        BaseBadge;
                        // @ts-ignore
                        const __VLS_181 = __VLS_asFunctionalComponent1(__VLS_180, new __VLS_180({
                            key: (tag),
                            variant: "neutral",
                        }));
                        const __VLS_182 = __VLS_181({
                            key: (tag),
                            variant: "neutral",
                        }, ...__VLS_functionalComponentArgsRest(__VLS_181));
                        const { default: __VLS_185 } = __VLS_183.slots;
                        (tag);
                        // @ts-ignore
                        [];
                        var __VLS_183;
                        // @ts-ignore
                        [];
                    }
                }
                // @ts-ignore
                [];
                var __VLS_161;
                // @ts-ignore
                [];
            }
        }
        // @ts-ignore
        [];
        var __VLS_115;
        let __VLS_186;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_187 = __VLS_asFunctionalComponent1(__VLS_186, new __VLS_186({
            padding: "lg",
            ...{ class: "cs-panel" },
        }));
        const __VLS_188 = __VLS_187({
            padding: "lg",
            ...{ class: "cs-panel" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_187));
        /** @type {__VLS_StyleScopedClasses['cs-panel']} */ ;
        const { default: __VLS_191 } = __VLS_189.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "cs-panel-title" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-panel-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-subtitle']} */ ;
        if (__VLS_ctx.keyPlayers.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-empty-state" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-state']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-empty-hint" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-empty-hint']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-table-scroll" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-table-scroll']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
                ...{ class: "cs-table" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-table']} */ ;
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
            for (const [p] of __VLS_vFor((__VLS_ctx.keyPlayers))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                    key: (p.id),
                });
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                if (p.id) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                        ...{ onClick: (...[$event]) => {
                                if (!!(__VLS_ctx.loading))
                                    return;
                                if (!!(__VLS_ctx.error))
                                    return;
                                if (!(__VLS_ctx.match))
                                    return;
                                if (!!(__VLS_ctx.keyPlayers.length === 0))
                                    return;
                                if (!(p.id))
                                    return;
                                __VLS_ctx.goToPlayerProfile(p.id);
                                // @ts-ignore
                                [keyPlayers, keyPlayers, goToPlayerProfile,];
                            } },
                        ...{ class: "cs-player-pill" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-player-pill']} */ ;
                    (p.name);
                }
                else {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-player-pill cs-player-pill--static" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-player-pill']} */ ;
                    /** @type {__VLS_StyleScopedClasses['cs-player-pill--static']} */ ;
                    (p.name);
                }
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (p.role);
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (p.batting?.runs ?? '—');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (p.batting?.strike_rate?.toFixed(1) ?? '—');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (p.bowling?.wickets ?? '—');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (p.bowling?.economy?.toFixed(1) ?? '—');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                let __VLS_192;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_193 = __VLS_asFunctionalComponent1(__VLS_192, new __VLS_192({
                    variant: (p.impact === 'high'
                        ? 'success'
                        : p.impact === 'medium'
                            ? 'primary'
                            : 'neutral'),
                    uppercase: (false),
                }));
                const __VLS_194 = __VLS_193({
                    variant: (p.impact === 'high'
                        ? 'success'
                        : p.impact === 'medium'
                            ? 'primary'
                            : 'neutral'),
                    uppercase: (false),
                }, ...__VLS_functionalComponentArgsRest(__VLS_193));
                const { default: __VLS_197 } = __VLS_195.slots;
                (p.impact_label);
                // @ts-ignore
                [];
                var __VLS_195;
                // @ts-ignore
                [];
            }
        }
        // @ts-ignore
        [];
        var __VLS_189;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-main-right" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-main-right']} */ ;
        let __VLS_198;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_199 = __VLS_asFunctionalComponent1(__VLS_198, new __VLS_198({
            padding: "lg",
            ...{ class: "cs-panel cs-panel--ai" },
        }));
        const __VLS_200 = __VLS_199({
            padding: "lg",
            ...{ class: "cs-panel cs-panel--ai" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_199));
        /** @type {__VLS_StyleScopedClasses['cs-panel']} */ ;
        /** @type {__VLS_StyleScopedClasses['cs-panel--ai']} */ ;
        const { default: __VLS_203 } = __VLS_201.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
            ...{ class: "cs-ai-header" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-ai-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "cs-panel-title" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-panel-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-subtitle']} */ ;
        if (__VLS_ctx.aiSummary?.created_at) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
                ...{ class: "cs-ai-timestamp" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-timestamp']} */ ;
            (new Date(__VLS_ctx.aiSummary.created_at).toLocaleString());
        }
        let __VLS_204;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_205 = __VLS_asFunctionalComponent1(__VLS_204, new __VLS_204({
            variant: "neutral",
            uppercase: (false),
            ...{ class: "cs-ai-badge" },
        }));
        const __VLS_206 = __VLS_205({
            variant: "neutral",
            uppercase: (false),
            ...{ class: "cs-ai-badge" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_205));
        /** @type {__VLS_StyleScopedClasses['cs-ai-badge']} */ ;
        const { default: __VLS_209 } = __VLS_207.slots;
        // @ts-ignore
        [aiSummary, aiSummary,];
        var __VLS_207;
        if (__VLS_ctx.aiSummaryLoading) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-ai-loading" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-loading']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                ...{ class: "cs-skeleton-line cs-skeleton-line--lg" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--lg']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                ...{ class: "cs-skeleton-line cs-skeleton-line--full" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--full']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                ...{ class: "cs-skeleton-line cs-skeleton-line--full" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--full']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                ...{ class: "cs-skeleton-line cs-skeleton-line--md" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line']} */ ;
            /** @type {__VLS_StyleScopedClasses['cs-skeleton-line--md']} */ ;
        }
        else if (__VLS_ctx.aiSummaryError) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-ai-error-text" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-error-text']} */ ;
            (__VLS_ctx.aiSummaryError);
        }
        else if (!__VLS_ctx.hasAISummary) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-ai-empty" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-empty']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "cs-ai-empty-hint" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-empty-hint']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-ai-body" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-body']} */ ;
            if (__VLS_ctx.aiOverallSummary || __VLS_ctx.aiOverview) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "cs-ai-overall" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-overall']} */ ;
                (__VLS_ctx.aiOverallSummary || __VLS_ctx.aiOverview);
            }
            if (__VLS_ctx.aiKeyThemes.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                    ...{ class: "cs-ai-theme-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-theme-list']} */ ;
                for (const [theme, idx] of __VLS_vFor((__VLS_ctx.aiKeyThemes))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                        key: (idx),
                    });
                    (theme);
                    // @ts-ignore
                    [aiSummaryLoading, aiSummaryError, aiSummaryError, hasAISummary, aiOverallSummary, aiOverallSummary, aiOverview, aiOverview, aiKeyThemes, aiKeyThemes,];
                }
            }
            if (__VLS_ctx.aiDecisivePhases.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-ai-phases-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-phases-list']} */ ;
                for (const [phase] of __VLS_vFor((__VLS_ctx.aiDecisivePhases))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        id: (`mc-phase-${phase.phase_id}`),
                        key: (phase.phase_id),
                        ...{ class: "cs-ai-phase-item" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-item']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-ai-phase-header" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-header']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-phase-label" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-label']} */ ;
                    (phase.label);
                    let __VLS_210;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                    BaseBadge;
                    // @ts-ignore
                    const __VLS_211 = __VLS_asFunctionalComponent1(__VLS_210, new __VLS_210({
                        variant: (phase.impact_score > 0 ? 'success' : phase.impact_score < 0 ? 'danger' : 'neutral'),
                        uppercase: (false),
                        ...{ class: "cs-ai-phase-badge" },
                    }));
                    const __VLS_212 = __VLS_211({
                        variant: (phase.impact_score > 0 ? 'success' : phase.impact_score < 0 ? 'danger' : 'neutral'),
                        uppercase: (false),
                        ...{ class: "cs-ai-phase-badge" },
                    }, ...__VLS_functionalComponentArgsRest(__VLS_211));
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-badge']} */ ;
                    const { default: __VLS_215 } = __VLS_213.slots;
                    (phase.impact_score > 0 ? '+' : '');
                    (phase.impact_score);
                    // @ts-ignore
                    [aiDecisivePhases, aiDecisivePhases,];
                    var __VLS_213;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-phase-overs" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-overs']} */ ;
                    (phase.over_range[0]);
                    (phase.over_range[1]);
                    (phase.innings);
                    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                        ...{ class: "cs-ai-phase-narrative" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-phase-narrative']} */ ;
                    (phase.narrative);
                    // @ts-ignore
                    [];
                }
            }
            if (__VLS_ctx.aiPlayerHighlightsRich.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                    ...{ class: "cs-ai-player-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-player-list']} */ ;
                for (const [ph] of __VLS_vFor((__VLS_ctx.aiPlayerHighlightsRich))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                        key: (ph.player_id ?? ph.player_name),
                        ...{ class: "cs-ai-player-item" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-player-item']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-player-name" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-player-name']} */ ;
                    (ph.player_name);
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-player-role" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-player-role']} */ ;
                    (ph.role);
                    (ph.highlight_type);
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-player-summary" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-player-summary']} */ ;
                    (ph.summary);
                    // @ts-ignore
                    [aiPlayerHighlightsRich, aiPlayerHighlightsRich,];
                }
            }
            if (__VLS_ctx.aiMomentumShifts.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                    ...{ class: "cs-ai-momentum-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-momentum-list']} */ ;
                for (const [shift] of __VLS_vFor((__VLS_ctx.aiMomentumShifts))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                        key: (shift.shift_id),
                        ...{ class: "cs-ai-momentum-item" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-momentum-item']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-momentum-over" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-momentum-over']} */ ;
                    (shift.over);
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-momentum-desc" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-momentum-desc']} */ ;
                    (shift.description);
                    let __VLS_216;
                    /** @ts-ignore @type { | typeof __VLS_components.ImpactBar} */
                    ImpactBar;
                    // @ts-ignore
                    const __VLS_217 = __VLS_asFunctionalComponent1(__VLS_216, new __VLS_216({
                        value: (shift.impact_delta),
                        min: (-20),
                        max: (20),
                        size: "sm",
                        ...{ class: "cs-ai-momentum-bar" },
                    }));
                    const __VLS_218 = __VLS_217({
                        value: (shift.impact_delta),
                        min: (-20),
                        max: (20),
                        size: "sm",
                        ...{ class: "cs-ai-momentum-bar" },
                    }, ...__VLS_functionalComponentArgsRest(__VLS_217));
                    /** @type {__VLS_StyleScopedClasses['cs-ai-momentum-bar']} */ ;
                    // @ts-ignore
                    [aiMomentumShifts, aiMomentumShifts,];
                }
            }
            if (__VLS_ctx.aiTeams.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-ai-teams-grid" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-teams-grid']} */ ;
                for (const [team] of __VLS_vFor((__VLS_ctx.aiTeams))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        key: (team.team_id),
                        ...{ class: "cs-ai-team-card" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-team-card']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-ai-team-header" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-team-header']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-team-name" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-team-name']} */ ;
                    (team.team_name);
                    let __VLS_221;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                    BaseBadge;
                    // @ts-ignore
                    const __VLS_222 = __VLS_asFunctionalComponent1(__VLS_221, new __VLS_221({
                        variant: (team.result === 'won' ? 'success' : team.result === 'lost' ? 'danger' : 'neutral'),
                        uppercase: (false),
                    }));
                    const __VLS_223 = __VLS_222({
                        variant: (team.result === 'won' ? 'success' : team.result === 'lost' ? 'danger' : 'neutral'),
                        uppercase: (false),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_222));
                    const { default: __VLS_226 } = __VLS_224.slots;
                    (team.result.replace('_', ' '));
                    // @ts-ignore
                    [aiTeams, aiTeams,];
                    var __VLS_224;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                        ...{ class: "cs-ai-team-score" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-team-score']} */ ;
                    (team.total_runs);
                    (team.wickets_lost);
                    (team.overs_faced);
                    if (team.key_stats.length) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                            ...{ class: "cs-ai-team-stats" },
                        });
                        /** @type {__VLS_StyleScopedClasses['cs-ai-team-stats']} */ ;
                        for (const [stat, idx] of __VLS_vFor((team.key_stats))) {
                            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                                key: (idx),
                            });
                            (stat);
                            // @ts-ignore
                            [];
                        }
                    }
                    // @ts-ignore
                    [];
                }
            }
            if (!__VLS_ctx.aiKeyThemes.length && __VLS_ctx.aiTacticalThemes.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                    ...{ class: "cs-ai-theme-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-theme-list']} */ ;
                for (const [theme, idx] of __VLS_vFor((__VLS_ctx.aiTacticalThemes))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                        key: (idx),
                    });
                    (theme);
                    // @ts-ignore
                    [aiKeyThemes, aiTacticalThemes, aiTacticalThemes,];
                }
            }
            if (!__VLS_ctx.aiTeams.length && __VLS_ctx.aiInningsSummaries.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
                    ...{ class: "cs-ai-section-title" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section-title']} */ ;
                for (const [innings] of __VLS_vFor((__VLS_ctx.aiInningsSummaries))) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        key: (innings.innings),
                        ...{ class: "cs-ai-innings-card" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-innings-card']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "cs-ai-innings-meta" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-innings-meta']} */ ;
                    let __VLS_227;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                    BaseBadge;
                    // @ts-ignore
                    const __VLS_228 = __VLS_asFunctionalComponent1(__VLS_227, new __VLS_227({
                        variant: "neutral",
                        uppercase: (false),
                    }));
                    const __VLS_229 = __VLS_228({
                        variant: "neutral",
                        uppercase: (false),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_228));
                    const { default: __VLS_232 } = __VLS_230.slots;
                    (innings.innings);
                    // @ts-ignore
                    [aiTeams, aiInningsSummaries, aiInningsSummaries,];
                    var __VLS_230;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "cs-ai-innings-team" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-innings-team']} */ ;
                    (innings.team_name);
                    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                        ...{ class: "cs-ai-innings-summary" },
                    });
                    /** @type {__VLS_StyleScopedClasses['cs-ai-innings-summary']} */ ;
                    (innings.summary);
                    // @ts-ignore
                    [];
                }
            }
            if (__VLS_ctx.aiTags.length) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                    ...{ class: "cs-ai-section cs-ai-tags-section" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-section']} */ ;
                /** @type {__VLS_StyleScopedClasses['cs-ai-tags-section']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "cs-ai-tag-list" },
                });
                /** @type {__VLS_StyleScopedClasses['cs-ai-tag-list']} */ ;
                for (const [tag] of __VLS_vFor((__VLS_ctx.aiTags))) {
                    let __VLS_233;
                    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                    BaseBadge;
                    // @ts-ignore
                    const __VLS_234 = __VLS_asFunctionalComponent1(__VLS_233, new __VLS_233({
                        key: (tag),
                        variant: "neutral",
                        ...{ class: "cs-ai-tag" },
                    }));
                    const __VLS_235 = __VLS_234({
                        key: (tag),
                        variant: "neutral",
                        ...{ class: "cs-ai-tag" },
                    }, ...__VLS_functionalComponentArgsRest(__VLS_234));
                    /** @type {__VLS_StyleScopedClasses['cs-ai-tag']} */ ;
                    const { default: __VLS_238 } = __VLS_236.slots;
                    (tag.replace(/_/g, ' '));
                    // @ts-ignore
                    [aiTags, aiTags,];
                    var __VLS_236;
                    // @ts-ignore
                    [];
                }
            }
        }
        if (__VLS_ctx.hasAISummary) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "cs-ai-actions" },
            });
            /** @type {__VLS_StyleScopedClasses['cs-ai-actions']} */ ;
            let __VLS_239;
            /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
            BaseButton;
            // @ts-ignore
            const __VLS_240 = __VLS_asFunctionalComponent1(__VLS_239, new __VLS_239({
                ...{ 'onClick': {} },
                variant: "ghost",
                size: "sm",
                disabled: (__VLS_ctx.aiSummaryLoading),
            }));
            const __VLS_241 = __VLS_240({
                ...{ 'onClick': {} },
                variant: "ghost",
                size: "sm",
                disabled: (__VLS_ctx.aiSummaryLoading),
            }, ...__VLS_functionalComponentArgsRest(__VLS_240));
            let __VLS_244;
            const __VLS_245 = ({ click: {} },
                { onClick: (__VLS_ctx.regenerateSummary) });
            const { default: __VLS_246 } = __VLS_242.slots;
            if (__VLS_ctx.aiSummaryLoading) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            }
            else {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            }
            // @ts-ignore
            [aiSummaryLoading, aiSummaryLoading, hasAISummary, regenerateSummary,];
            var __VLS_242;
            var __VLS_243;
        }
        // @ts-ignore
        [];
        var __VLS_201;
        let __VLS_247;
        /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
        BaseCard;
        // @ts-ignore
        const __VLS_248 = __VLS_asFunctionalComponent1(__VLS_247, new __VLS_247({
            padding: "lg",
            ...{ class: "cs-panel" },
        }));
        const __VLS_249 = __VLS_248({
            padding: "lg",
            ...{ class: "cs-panel" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_248));
        /** @type {__VLS_StyleScopedClasses['cs-panel']} */ ;
        const { default: __VLS_252 } = __VLS_250.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
            ...{ class: "cs-panel-title" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-panel-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-panel-subtitle']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "cs-dismissal-placeholder" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-dismissal-placeholder']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "cs-empty" },
        });
        /** @type {__VLS_StyleScopedClasses['cs-empty']} */ ;
        // @ts-ignore
        [];
        var __VLS_250;
        let __VLS_253;
        /** @ts-ignore @type { | typeof __VLS_components.AiCalloutsPanel} */
        AiCalloutsPanel;
        // @ts-ignore
        const __VLS_254 = __VLS_asFunctionalComponent1(__VLS_253, new __VLS_253({
            ...{ 'onSelect': {} },
            callouts: (__VLS_ctx.matchAiCallouts),
            loading: (__VLS_ctx.matchAiLoading),
            maxItems: (5),
            dense: true,
            title: "AI Callouts",
            description: "Per-match insights Cricksy AI has flagged as important.",
        }));
        const __VLS_255 = __VLS_254({
            ...{ 'onSelect': {} },
            callouts: (__VLS_ctx.matchAiCallouts),
            loading: (__VLS_ctx.matchAiLoading),
            maxItems: (5),
            dense: true,
            title: "AI Callouts",
            description: "Per-match insights Cricksy AI has flagged as important.",
        }, ...__VLS_functionalComponentArgsRest(__VLS_254));
        let __VLS_258;
        const __VLS_259 = ({ select: {} },
            { onSelect: (__VLS_ctx.handleCalloutSelect) });
        var __VLS_256;
        var __VLS_257;
    }
}
// @ts-ignore
[matchAiCallouts, matchAiLoading, handleCalloutSelect,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
