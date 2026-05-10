/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { BaseButton, BaseCard, BaseBadge } from '@/components';
import CoachNotebookWidget from '@/components/CoachNotebookWidget.vue';
import FormTrackerWidget from '@/components/FormTrackerWidget.vue';
import MentalProfilePanel from '@/components/MentalProfilePanel.vue';
import MiniSparkline from '@/components/MiniSparkline.vue';
import SeasonGraphsWidget from '@/components/SeasonGraphsWidget.vue';
import StrengthWeaknessWidget from '@/components/StrengthWeaknessWidget.vue';
import { apiService, getErrorMessage, getPlayerAIInsights } from '@/services/api';
import { getPlayerProfile } from '@/services/playerApi';
const route = useRoute();
const loading = ref(true);
const error = ref(null);
const profile = ref(null);
const activeTab = ref('overview');
// Fan favorites state
const isFavorite = ref(false);
const favoriteId = ref(null);
const isTogglingFavorite = ref(false);
const favoriteError = ref(null);
// AI Insights state
const aiInsightsLoading = ref(false);
const aiInsightsError = ref(null);
const aiInsights = ref(null);
// Derive player role from stats
const playerRole = computed(() => {
    if (!profile.value)
        return 'Player';
    const { total_wickets, total_runs_scored } = profile.value;
    if (total_wickets > 10 && total_runs_scored > 200)
        return 'All-rounder';
    if (total_wickets >= 10)
        return 'Bowler';
    if (total_runs_scored >= 200)
        return 'Batter';
    return 'Player';
});
// Role badge variant for BaseBadge component
const roleBadgeVariant = computed(() => {
    switch (playerRole.value) {
        case 'All-rounder': return 'success';
        case 'Bowler': return 'warning';
        case 'Batter': return 'primary';
        default: return 'neutral';
    }
});
// Player initials for avatar
const playerInitials = computed(() => {
    if (!profile.value)
        return '?';
    const parts = profile.value.player_name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
});
// Format numeric stats with fallback
const formatStat = (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value))
        return '—';
    return value.toFixed(decimals);
};
// AI Insights computed helpers
const aiSummary = computed(() => aiInsights.value?.summary ?? '');
const aiRecentForm = computed(() => aiInsights.value?.recent_form ?? null);
const aiStrengths = computed(() => aiInsights.value?.strengths ?? []);
const aiWeaknesses = computed(() => aiInsights.value?.weaknesses ?? []);
const aiRoleTags = computed(() => aiInsights.value?.role_tags ?? []);
const aiRecommendations = computed(() => aiInsights.value?.recommendations ?? []);
const loadProfile = async () => {
    loading.value = true;
    error.value = null;
    try {
        const playerId = route.params.playerId;
        if (!playerId) {
            throw new Error('No player ID provided');
        }
        profile.value = await getPlayerProfile(playerId);
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load player profile';
    }
    finally {
        loading.value = false;
    }
};
// Load current user's favorites and check if this player is followed
const loadFavorites = async () => {
    if (!profile.value)
        return;
    try {
        const favorites = await apiService.getFanFavorites();
        const match = favorites.find((f) => f.favorite_type === 'player' && f.player_profile_id === profile.value?.player_id);
        if (match) {
            isFavorite.value = true;
            favoriteId.value = match.id;
        }
        else {
            isFavorite.value = false;
            favoriteId.value = null;
        }
    }
    catch (err) {
        // Silently fail - user may not be logged in
        console.warn('Failed to load favorites:', getErrorMessage(err));
    }
};
// Toggle follow/unfollow for current player
const toggleFavorite = async () => {
    if (!profile.value || isTogglingFavorite.value)
        return;
    isTogglingFavorite.value = true;
    favoriteError.value = null;
    try {
        if (isFavorite.value && favoriteId.value) {
            // Unfollow
            await apiService.deleteFanFavorite(favoriteId.value);
            isFavorite.value = false;
            favoriteId.value = null;
        }
        else {
            // Follow
            const newFavorite = await apiService.createFanFavorite({
                favorite_type: 'player',
                player_profile_id: profile.value.player_id,
            });
            isFavorite.value = true;
            favoriteId.value = newFavorite.id;
        }
    }
    catch (err) {
        favoriteError.value = getErrorMessage(err);
        console.error('Failed to toggle favorite:', err);
    }
    finally {
        isTogglingFavorite.value = false;
    }
};
// Load AI insights for current player
const loadAIInsights = async () => {
    const playerId = route.params.playerId;
    if (!playerId)
        return;
    aiInsightsLoading.value = true;
    aiInsightsError.value = null;
    try {
        aiInsights.value = await getPlayerAIInsights(playerId);
    }
    catch (err) {
        aiInsightsError.value = getErrorMessage(err) || 'Failed to load AI insights';
        console.warn('Failed to load AI insights:', err);
    }
    finally {
        aiInsightsLoading.value = false;
    }
};
onMounted(async () => {
    await loadProfile();
    await loadFavorites();
    await loadAIInsights();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['error-card']} */ ;
/** @type {__VLS_StyleScopedClasses['error-card']} */ ;
/** @type {__VLS_StyleScopedClasses['player-name-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['fielding-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['fielding-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['achievement-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
/** @type {__VLS_StyleScopedClasses['player-header']} */ ;
/** @type {__VLS_StyleScopedClasses['player-name-row']} */ ;
/** @type {__VLS_StyleScopedClasses['player-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['overview-stats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-recommendations']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-header']} */ ;
/** @type {__VLS_StyleScopedClasses['ai-insights-actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-profile-view" },
});
/** @type {__VLS_StyleScopedClasses['player-profile-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "container" },
});
/** @type {__VLS_StyleScopedClasses['container']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-container" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-spinner" },
        'aria-busy': "true",
    });
    /** @type {__VLS_StyleScopedClasses['loading-spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-container" },
    });
    /** @type {__VLS_StyleScopedClasses['error-container']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        ...{ class: "error-card" },
    }));
    const __VLS_2 = __VLS_1({
        ...{ class: "error-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['error-card']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['error-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.error);
    let __VLS_6;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
        ...{ 'onClick': {} },
        variant: "primary",
    }));
    const __VLS_8 = __VLS_7({
        ...{ 'onClick': {} },
        variant: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    let __VLS_11;
    const __VLS_12 = ({ click: {} },
        { onClick: (__VLS_ctx.loadProfile) });
    const { default: __VLS_13 } = __VLS_9.slots;
    // @ts-ignore
    [loading, error, error, loadProfile,];
    var __VLS_9;
    var __VLS_10;
    // @ts-ignore
    [];
    var __VLS_3;
}
else if (__VLS_ctx.profile) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "profile-content" },
    });
    /** @type {__VLS_StyleScopedClasses['profile-content']} */ ;
    let __VLS_14;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
        as: "header",
        ...{ class: "player-header" },
    }));
    const __VLS_16 = __VLS_15({
        as: "header",
        ...{ class: "player-header" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_15));
    /** @type {__VLS_StyleScopedClasses['player-header']} */ ;
    const { default: __VLS_19 } = __VLS_17.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-avatar" },
    });
    /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
    (__VLS_ctx.playerInitials);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-info" },
    });
    /** @type {__VLS_StyleScopedClasses['player-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-name-row" },
    });
    /** @type {__VLS_StyleScopedClasses['player-name-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    (__VLS_ctx.profile.player_name);
    let __VLS_20;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
        variant: (__VLS_ctx.roleBadgeVariant),
    }));
    const __VLS_22 = __VLS_21({
        variant: (__VLS_ctx.roleBadgeVariant),
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    const { default: __VLS_25 } = __VLS_23.slots;
    (__VLS_ctx.playerRole);
    // @ts-ignore
    [profile, profile, playerInitials, roleBadgeVariant, playerRole,];
    var __VLS_23;
    let __VLS_26;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.isFavorite ? 'primary' : 'ghost'),
        size: "sm",
        ...{ class: "follow-btn" },
        ...{ class: ({ following: __VLS_ctx.isFavorite }) },
        loading: (__VLS_ctx.isTogglingFavorite),
        'aria-label': (__VLS_ctx.isFavorite ? 'Unfollow this player' : 'Follow this player'),
    }));
    const __VLS_28 = __VLS_27({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.isFavorite ? 'primary' : 'ghost'),
        size: "sm",
        ...{ class: "follow-btn" },
        ...{ class: ({ following: __VLS_ctx.isFavorite }) },
        loading: (__VLS_ctx.isTogglingFavorite),
        'aria-label': (__VLS_ctx.isFavorite ? 'Unfollow this player' : 'Follow this player'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_27));
    let __VLS_31;
    const __VLS_32 = ({ click: {} },
        { onClick: (__VLS_ctx.toggleFavorite) });
    /** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['following']} */ ;
    const { default: __VLS_33 } = __VLS_29.slots;
    if (__VLS_ctx.isFavorite) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    // @ts-ignore
    [isFavorite, isFavorite, isFavorite, isFavorite, isTogglingFavorite, toggleFavorite,];
    var __VLS_29;
    var __VLS_30;
    if (__VLS_ctx.favoriteError) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "favorite-error" },
        });
        /** @type {__VLS_StyleScopedClasses['favorite-error']} */ ;
        (__VLS_ctx.favoriteError);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-meta" },
    });
    /** @type {__VLS_StyleScopedClasses['player-meta']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "meta-item" },
    });
    /** @type {__VLS_StyleScopedClasses['meta-item']} */ ;
    (__VLS_ctx.profile.total_matches);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "meta-item subdued" },
    });
    /** @type {__VLS_StyleScopedClasses['meta-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['subdued']} */ ;
    (__VLS_ctx.profile.player_id.slice(0, 8));
    // @ts-ignore
    [profile, profile, favoriteError, favoriteError,];
    var __VLS_17;
    let __VLS_34;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_35 = __VLS_asFunctionalComponent1(__VLS_34, new __VLS_34({
        as: "nav",
        padding: "sm",
        ...{ class: "tabs-nav" },
    }));
    const __VLS_36 = __VLS_35({
        as: "nav",
        padding: "sm",
        ...{ class: "tabs-nav" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_35));
    /** @type {__VLS_StyleScopedClasses['tabs-nav']} */ ;
    const { default: __VLS_39 } = __VLS_37.slots;
    let __VLS_40;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent1(__VLS_40, new __VLS_40({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'overview' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "overview",
    }));
    const __VLS_42 = __VLS_41({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'overview' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "overview",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    let __VLS_45;
    const __VLS_46 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'overview';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_47 } = __VLS_43.slots;
    // @ts-ignore
    [];
    var __VLS_43;
    var __VLS_44;
    let __VLS_48;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent1(__VLS_48, new __VLS_48({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'batting' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "batting",
    }));
    const __VLS_50 = __VLS_49({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'batting' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "batting",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    let __VLS_53;
    const __VLS_54 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'batting';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_55 } = __VLS_51.slots;
    // @ts-ignore
    [];
    var __VLS_51;
    var __VLS_52;
    let __VLS_56;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_57 = __VLS_asFunctionalComponent1(__VLS_56, new __VLS_56({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'bowling' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "bowling",
    }));
    const __VLS_58 = __VLS_57({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'bowling' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "bowling",
    }, ...__VLS_functionalComponentArgsRest(__VLS_57));
    let __VLS_61;
    const __VLS_62 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'bowling';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_63 } = __VLS_59.slots;
    // @ts-ignore
    [];
    var __VLS_59;
    var __VLS_60;
    let __VLS_64;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_65 = __VLS_asFunctionalComponent1(__VLS_64, new __VLS_64({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'form' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "form",
    }));
    const __VLS_66 = __VLS_65({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'form' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "form",
    }, ...__VLS_functionalComponentArgsRest(__VLS_65));
    let __VLS_69;
    const __VLS_70 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'form';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_71 } = __VLS_67.slots;
    // @ts-ignore
    [];
    var __VLS_67;
    var __VLS_68;
    let __VLS_72;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent1(__VLS_72, new __VLS_72({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'season' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "season",
    }));
    const __VLS_74 = __VLS_73({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'season' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "season",
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
    let __VLS_77;
    const __VLS_78 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'season';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_79 } = __VLS_75.slots;
    // @ts-ignore
    [];
    var __VLS_75;
    var __VLS_76;
    let __VLS_80;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_81 = __VLS_asFunctionalComponent1(__VLS_80, new __VLS_80({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'profile' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "profile",
    }));
    const __VLS_82 = __VLS_81({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'profile' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "profile",
    }, ...__VLS_functionalComponentArgsRest(__VLS_81));
    let __VLS_85;
    const __VLS_86 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'profile';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_87 } = __VLS_83.slots;
    // @ts-ignore
    [];
    var __VLS_83;
    var __VLS_84;
    let __VLS_88;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_89 = __VLS_asFunctionalComponent1(__VLS_88, new __VLS_88({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'notebook' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "notebook",
    }));
    const __VLS_90 = __VLS_89({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'notebook' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "notebook",
    }, ...__VLS_functionalComponentArgsRest(__VLS_89));
    let __VLS_93;
    const __VLS_94 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'notebook';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_95 } = __VLS_91.slots;
    // @ts-ignore
    [];
    var __VLS_91;
    var __VLS_92;
    let __VLS_96;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_97 = __VLS_asFunctionalComponent1(__VLS_96, new __VLS_96({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'mental' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "mental",
    }));
    const __VLS_98 = __VLS_97({
        ...{ 'onClick': {} },
        variant: (__VLS_ctx.activeTab === 'mental' ? 'primary' : 'ghost'),
        ...{ class: "tab-btn" },
        dataTab: "mental",
    }, ...__VLS_functionalComponentArgsRest(__VLS_97));
    let __VLS_101;
    const __VLS_102 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!!(__VLS_ctx.loading))
                    return;
                if (!!(__VLS_ctx.error))
                    return;
                if (!(__VLS_ctx.profile))
                    return;
                __VLS_ctx.activeTab = 'mental';
                // @ts-ignore
                [activeTab, activeTab,];
            } });
    /** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
    const { default: __VLS_103 } = __VLS_99.slots;
    // @ts-ignore
    [];
    var __VLS_99;
    var __VLS_100;
    // @ts-ignore
    [];
    var __VLS_37;
    let __VLS_104;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_105 = __VLS_asFunctionalComponent1(__VLS_104, new __VLS_104({
        ...{ class: "tab-content" },
    }));
    const __VLS_106 = __VLS_105({
        ...{ class: "tab-content" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_105));
    /** @type {__VLS_StyleScopedClasses['tab-content']} */ ;
    const { default: __VLS_109 } = __VLS_107.slots;
    if (__VLS_ctx.activeTab === 'overview') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "overview-stats-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['overview-stats-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.profile.total_matches);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.profile.total_runs_scored.toLocaleString());
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.profile.total_wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.formatStat(__VLS_ctx.profile.strike_rate));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.formatStat(__VLS_ctx.profile.batting_average));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (__VLS_ctx.formatStat(__VLS_ctx.profile.economy_rate));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "fielding-summary" },
        });
        /** @type {__VLS_StyleScopedClasses['fielding-summary']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "fielding-stats" },
        });
        /** @type {__VLS_StyleScopedClasses['fielding-stats']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.profile.catches);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.profile.stumpings);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.profile.run_outs);
        if (__VLS_ctx.profile.achievements && __VLS_ctx.profile.achievements.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "achievements-section" },
            });
            /** @type {__VLS_StyleScopedClasses['achievements-section']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "achievements-list" },
            });
            /** @type {__VLS_StyleScopedClasses['achievements-list']} */ ;
            for (const [achievement] of __VLS_vFor((__VLS_ctx.profile.achievements))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    key: (achievement.id),
                    ...{ class: "achievement-pill" },
                    title: (achievement.description),
                });
                /** @type {__VLS_StyleScopedClasses['achievement-pill']} */ ;
                (achievement.badge_icon || '🏅');
                (achievement.title);
                // @ts-ignore
                [profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, activeTab, formatStat, formatStat, formatStat,];
            }
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "no-achievements" },
            });
            /** @type {__VLS_StyleScopedClasses['no-achievements']} */ ;
        }
    }
    else if (__VLS_ctx.activeTab === 'batting') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dl, __VLS_intrinsics.dl)({
            ...{ class: "stats-list" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-list']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_innings_batted);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_runs_scored.toLocaleString());
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.formatStat(__VLS_ctx.profile.batting_average));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.formatStat(__VLS_ctx.profile.strike_rate));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.highest_score);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.centuries);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.half_centuries);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_fours);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_sixes);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_balls_faced.toLocaleString());
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.times_out);
    }
    else if (__VLS_ctx.activeTab === 'bowling') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dl, __VLS_intrinsics.dl)({
            ...{ class: "stats-list" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-list']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_innings_bowled);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.formatStat(__VLS_ctx.profile.total_overs_bowled, 1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.formatStat(__VLS_ctx.profile.bowling_average));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.formatStat(__VLS_ctx.profile.economy_rate));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.best_bowling_figures || '—');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.five_wicket_hauls);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.maidens);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stats-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.profile.total_runs_conceded.toLocaleString());
    }
    else if (__VLS_ctx.activeTab === 'form') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        const __VLS_110 = FormTrackerWidget;
        // @ts-ignore
        const __VLS_111 = __VLS_asFunctionalComponent1(__VLS_110, new __VLS_110({
            profile: (__VLS_ctx.profile),
        }));
        const __VLS_112 = __VLS_111({
            profile: (__VLS_ctx.profile),
        }, ...__VLS_functionalComponentArgsRest(__VLS_111));
    }
    else if (__VLS_ctx.activeTab === 'season') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        const __VLS_115 = SeasonGraphsWidget;
        // @ts-ignore
        const __VLS_116 = __VLS_asFunctionalComponent1(__VLS_115, new __VLS_115({
            profile: (__VLS_ctx.profile),
        }));
        const __VLS_117 = __VLS_116({
            profile: (__VLS_ctx.profile),
        }, ...__VLS_functionalComponentArgsRest(__VLS_116));
    }
    else if (__VLS_ctx.activeTab === 'profile') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        const __VLS_120 = StrengthWeaknessWidget;
        // @ts-ignore
        const __VLS_121 = __VLS_asFunctionalComponent1(__VLS_120, new __VLS_120({
            profile: (__VLS_ctx.profile),
            strengths: (__VLS_ctx.aiStrengths),
            weaknesses: (__VLS_ctx.aiWeaknesses),
        }));
        const __VLS_122 = __VLS_121({
            profile: (__VLS_ctx.profile),
            strengths: (__VLS_ctx.aiStrengths),
            weaknesses: (__VLS_ctx.aiWeaknesses),
        }, ...__VLS_functionalComponentArgsRest(__VLS_121));
    }
    else if (__VLS_ctx.activeTab === 'notebook') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        const __VLS_125 = CoachNotebookWidget;
        // @ts-ignore
        const __VLS_126 = __VLS_asFunctionalComponent1(__VLS_125, new __VLS_125({
            profile: (__VLS_ctx.profile),
        }));
        const __VLS_127 = __VLS_126({
            profile: (__VLS_ctx.profile),
        }, ...__VLS_functionalComponentArgsRest(__VLS_126));
    }
    else if (__VLS_ctx.activeTab === 'mental') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tab-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
        const __VLS_130 = MentalProfilePanel;
        // @ts-ignore
        const __VLS_131 = __VLS_asFunctionalComponent1(__VLS_130, new __VLS_130({
            playerId: (__VLS_ctx.profile.player_id),
            playerName: (__VLS_ctx.profile.player_name),
        }));
        const __VLS_132 = __VLS_131({
            playerId: (__VLS_ctx.profile.player_id),
            playerName: (__VLS_ctx.profile.player_name),
        }, ...__VLS_functionalComponentArgsRest(__VLS_131));
    }
    // @ts-ignore
    [profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, profile, activeTab, activeTab, activeTab, activeTab, activeTab, activeTab, activeTab, formatStat, formatStat, formatStat, formatStat, formatStat, aiStrengths, aiWeaknesses,];
    var __VLS_107;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "ai-insights-section" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-insights-section']} */ ;
    let __VLS_135;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_136 = __VLS_asFunctionalComponent1(__VLS_135, new __VLS_135({
        padding: "lg",
        ...{ class: "ai-insights-card" },
    }));
    const __VLS_137 = __VLS_136({
        padding: "lg",
        ...{ class: "ai-insights-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_136));
    /** @type {__VLS_StyleScopedClasses['ai-insights-card']} */ ;
    const { default: __VLS_140 } = __VLS_138.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "ai-insights-header" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-insights-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
        ...{ class: "ai-insights-title" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-insights-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ai-insights-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['ai-insights-actions']} */ ;
    if (__VLS_ctx.aiRecentForm?.label) {
        let __VLS_141;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_142 = __VLS_asFunctionalComponent1(__VLS_141, new __VLS_141({
            variant: "neutral",
            ...{ class: "trend-badge" },
        }));
        const __VLS_143 = __VLS_142({
            variant: "neutral",
            ...{ class: "trend-badge" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_142));
        /** @type {__VLS_StyleScopedClasses['trend-badge']} */ ;
        const { default: __VLS_146 } = __VLS_144.slots;
        (__VLS_ctx.aiRecentForm.label);
        // @ts-ignore
        [aiRecentForm, aiRecentForm,];
        var __VLS_144;
    }
    let __VLS_147;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_148 = __VLS_asFunctionalComponent1(__VLS_147, new __VLS_147({
        ...{ 'onClick': {} },
        size: "sm",
        variant: "ghost",
        disabled: (__VLS_ctx.aiInsightsLoading),
    }));
    const __VLS_149 = __VLS_148({
        ...{ 'onClick': {} },
        size: "sm",
        variant: "ghost",
        disabled: (__VLS_ctx.aiInsightsLoading),
    }, ...__VLS_functionalComponentArgsRest(__VLS_148));
    let __VLS_152;
    const __VLS_153 = ({ click: {} },
        { onClick: (__VLS_ctx.loadAIInsights) });
    const { default: __VLS_154 } = __VLS_150.slots;
    if (__VLS_ctx.aiInsightsLoading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    // @ts-ignore
    [aiInsightsLoading, aiInsightsLoading, loadAIInsights,];
    var __VLS_150;
    var __VLS_151;
    if (__VLS_ctx.aiInsightsLoading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-insights-loading" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-loading']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line short" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
        /** @type {__VLS_StyleScopedClasses['short']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "skeleton-line" },
        });
        /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    }
    else if (__VLS_ctx.aiInsightsError) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "ai-insights-error" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-error']} */ ;
        (__VLS_ctx.aiInsightsError);
    }
    else if (__VLS_ctx.aiInsights) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-insights-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "ai-insights-summary" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-summary']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (__VLS_ctx.aiSummary);
        if (__VLS_ctx.aiRoleTags.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "ai-insights-role-tags" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-role-tags']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "ai-insights-tag-list" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-tag-list']} */ ;
            for (const [tag] of __VLS_vFor((__VLS_ctx.aiRoleTags))) {
                let __VLS_155;
                /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
                BaseBadge;
                // @ts-ignore
                const __VLS_156 = __VLS_asFunctionalComponent1(__VLS_155, new __VLS_155({
                    key: (tag),
                    variant: "primary",
                    ...{ class: "ai-tag" },
                }));
                const __VLS_157 = __VLS_156({
                    key: (tag),
                    variant: "primary",
                    ...{ class: "ai-tag" },
                }, ...__VLS_functionalComponentArgsRest(__VLS_156));
                /** @type {__VLS_StyleScopedClasses['ai-tag']} */ ;
                const { default: __VLS_160 } = __VLS_158.slots;
                (tag.replace(/_/g, ' '));
                // @ts-ignore
                [aiInsightsLoading, aiInsightsError, aiInsightsError, aiInsights, aiSummary, aiRoleTags, aiRoleTags,];
                var __VLS_158;
                // @ts-ignore
                [];
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "ai-insights-strengths" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-strengths']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.aiStrengths.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
            for (const [item, idx] of __VLS_vFor((__VLS_ctx.aiStrengths))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (idx),
                });
                (item);
                // @ts-ignore
                [aiStrengths, aiStrengths,];
            }
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "ai-insights-empty" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-empty']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "ai-insights-weaknesses" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-weaknesses']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.aiWeaknesses.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
            for (const [item, idx] of __VLS_vFor((__VLS_ctx.aiWeaknesses))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (idx),
                });
                (item);
                // @ts-ignore
                [aiWeaknesses, aiWeaknesses,];
            }
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "ai-insights-empty" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-empty']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "ai-insights-form" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-form']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        if (__VLS_ctx.aiRecentForm && __VLS_ctx.aiRecentForm.trend.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-chart" },
            });
            /** @type {__VLS_StyleScopedClasses['form-chart']} */ ;
            const __VLS_161 = MiniSparkline;
            // @ts-ignore
            const __VLS_162 = __VLS_asFunctionalComponent1(__VLS_161, new __VLS_161({
                points: (__VLS_ctx.aiRecentForm.trend),
                width: (160),
                height: (40),
                highlightLast: (true),
                variant: "default",
            }));
            const __VLS_163 = __VLS_162({
                points: (__VLS_ctx.aiRecentForm.trend),
                width: (160),
                height: (40),
                highlightLast: (true),
                variant: "default",
            }, ...__VLS_functionalComponentArgsRest(__VLS_162));
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "form-label" },
            });
            /** @type {__VLS_StyleScopedClasses['form-label']} */ ;
            (__VLS_ctx.aiRecentForm.label);
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "ai-insights-empty" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-empty']} */ ;
        }
        if (__VLS_ctx.aiRecommendations.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "ai-insights-recommendations" },
            });
            /** @type {__VLS_StyleScopedClasses['ai-insights-recommendations']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
            for (const [rec, idx] of __VLS_vFor((__VLS_ctx.aiRecommendations))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (idx),
                });
                (rec);
                // @ts-ignore
                [aiRecentForm, aiRecentForm, aiRecentForm, aiRecentForm, aiRecommendations, aiRecommendations,];
            }
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "ai-insights-empty" },
        });
        /** @type {__VLS_StyleScopedClasses['ai-insights-empty']} */ ;
    }
    // @ts-ignore
    [];
    var __VLS_138;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
