/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useGameStore } from '@/stores/gameStore';
const router = useRouter();
const gameStore = useGameStore();
// Form data
const gameForm = ref({
    team_a_name: '',
    team_b_name: '',
    players_a: ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5', 'Player 6'],
    players_b: ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5', 'Player 6'],
    match_type: 'limited',
    overs_limit: null,
    days_limit: null,
    overs_per_day: null,
    dls_enabled: false,
    interruptions: [],
    toss_winner_team: '',
    decision: ''
});
// Computed properties
const canCreateGame = computed(() => {
    return gameForm.value.team_a_name.trim() !== '' &&
        gameForm.value.team_b_name.trim() !== '' &&
        gameForm.value.toss_winner_team !== '' &&
        gameForm.value.decision !== '' &&
        !gameStore.isLoading;
});
// Create new game
const createNewGame = async () => {
    if (!canCreateGame.value)
        return;
    try {
        const payload = {
            ...gameForm.value,
            decision: gameForm.value.decision,
        };
        console.log('Creating new game with data:', payload);
        await gameStore.createNewGame(payload);
        if (gameStore.currentGame) {
            console.log('✅ Game created successfully:', gameStore.currentGame.id);
            router.push(`/game/${gameStore.currentGame.id}`);
        }
    }
    catch (error) {
        console.error('❌ Failed to create game:', error);
    }
};
console.log('🏠 HomeView component loaded');
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['team-input']} */ ;
/** @type {__VLS_StyleScopedClasses['team-input']} */ ;
/** @type {__VLS_StyleScopedClasses['toss-select']} */ ;
/** @type {__VLS_StyleScopedClasses['decision-select']} */ ;
/** @type {__VLS_StyleScopedClasses['cta-button']} */ ;
/** @type {__VLS_StyleScopedClasses['cta-button']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-title']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-content']} */ ;
/** @type {__VLS_StyleScopedClasses['form-row']} */ ;
/** @type {__VLS_StyleScopedClasses['features-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "home-view" },
});
/** @type {__VLS_StyleScopedClasses['home-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "container" },
});
/** @type {__VLS_StyleScopedClasses['container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "hero-section" },
});
/** @type {__VLS_StyleScopedClasses['hero-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-content" },
});
/** @type {__VLS_StyleScopedClasses['hero-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({
    ...{ class: "hero-title" },
});
/** @type {__VLS_StyleScopedClasses['hero-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "hero-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['hero-subtitle']} */ ;
if (!__VLS_ctx.gameStore.isLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "game-form" },
    });
    /** @type {__VLS_StyleScopedClasses['game-form']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-row" },
    });
    /** @type {__VLS_StyleScopedClasses['form-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "Team A Name (e.g., Lions)",
        ...{ class: "team-input" },
    });
    (__VLS_ctx.gameForm.team_a_name);
    /** @type {__VLS_StyleScopedClasses['team-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "Team B Name (e.g., Tigers)",
        ...{ class: "team-input" },
    });
    (__VLS_ctx.gameForm.team_b_name);
    /** @type {__VLS_StyleScopedClasses['team-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "toss-section" },
    });
    /** @type {__VLS_StyleScopedClasses['toss-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "toss-label" },
    });
    /** @type {__VLS_StyleScopedClasses['toss-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.gameForm.toss_winner_team),
        ...{ class: "toss-select" },
    });
    /** @type {__VLS_StyleScopedClasses['toss-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    if (__VLS_ctx.gameForm.team_a_name) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: (__VLS_ctx.gameForm.team_a_name),
        });
        (__VLS_ctx.gameForm.team_a_name);
    }
    if (__VLS_ctx.gameForm.team_b_name) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            value: (__VLS_ctx.gameForm.team_b_name),
        });
        (__VLS_ctx.gameForm.team_b_name);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.gameForm.decision),
        ...{ class: "decision-select" },
    });
    /** @type {__VLS_StyleScopedClasses['decision-select']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bat",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bowl",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.createNewGame) },
        disabled: (!__VLS_ctx.canCreateGame),
        ...{ class: "cta-button" },
        ...{ class: ({ 'disabled': !__VLS_ctx.canCreateGame }) },
    });
    /** @type {__VLS_StyleScopedClasses['cta-button']} */ ;
    /** @type {__VLS_StyleScopedClasses['disabled']} */ ;
}
if (__VLS_ctx.gameStore.isLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
if (__VLS_ctx.gameStore.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error-state" },
    });
    /** @type {__VLS_StyleScopedClasses['error-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.gameStore.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.gameStore.clearError) },
        ...{ class: "retry-button" },
    });
    /** @type {__VLS_StyleScopedClasses['retry-button']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "features-section" },
});
/** @type {__VLS_StyleScopedClasses['features-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "features-grid" },
});
/** @type {__VLS_StyleScopedClasses['features-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-card" },
});
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-icon" },
});
/** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-card" },
});
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-icon" },
});
/** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-card" },
});
/** @type {__VLS_StyleScopedClasses['feature-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feature-icon" },
});
/** @type {__VLS_StyleScopedClasses['feature-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[gameStore, gameStore, gameStore, gameStore, gameStore, gameForm, gameForm, gameForm, gameForm, gameForm, gameForm, gameForm, gameForm, gameForm, gameForm, createNewGame, canCreateGame, canCreateGame,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
