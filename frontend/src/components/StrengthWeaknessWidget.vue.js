/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
const props = defineProps();
// Default strengths and weaknesses based on profile stats
const defaultStrengths = computed(() => {
    const strengths = [];
    if (!props.profile)
        return strengths;
    if (props.profile.strike_rate > 140)
        strengths.push('Aggressive batting with excellent strike rate');
    if (props.profile.batting_average > 40)
        strengths.push('Consistent batting performance');
    if (props.profile.total_fours + props.profile.total_sixes > 20)
        strengths.push('Strong boundary hitting ability');
    if (props.profile.total_wickets > 10)
        strengths.push('Reliable bowling skills');
    if (props.profile.economy_rate < 8)
        strengths.push('Economical bowling');
    if (props.profile.catches > 5)
        strengths.push('Good fielding consistency');
    return strengths.length > 0 ? strengths : ['Developing player with potential'];
});
const defaultWeaknesses = computed(() => {
    const weaknesses = [];
    if (!props.profile)
        return weaknesses;
    if (props.profile.strike_rate < 100)
        weaknesses.push('Strike rate could be improved - work on attacking more');
    if (props.profile.batting_average < 25)
        weaknesses.push('Batting consistency - focus on playing more match situations');
    if (props.profile.times_out > 5)
        weaknesses.push('Dismissal patterns - reduce reckless shots');
    if (props.profile.total_wickets === 0)
        weaknesses.push('Bowling - develop bowling variations');
    if (props.profile.economy_rate > 10)
        weaknesses.push('Economy rate - practice bowling at right pace');
    return weaknesses.length > 0 ? weaknesses : [];
});
const strengths = computed(() => props.strengths || defaultStrengths.value);
const weaknesses = computed(() => props.weaknesses || defaultWeaknesses.value);
// Calculate overall strength score
const strengthScore = computed(() => {
    if (!props.profile)
        return 0;
    let score = 0;
    // Scale: 0-100 based on various metrics
    score += Math.min(props.profile.strike_rate / 150 * 25, 25); // Strike rate (25 points)
    score += Math.min((props.profile.batting_average / 50) * 20, 20); // Average (20 points)
    score += Math.min((props.profile.total_wickets / 20) * 20, 20); // Bowling (20 points)
    score += Math.min((props.profile.catches / 10) * 15, 15); // Fielding (15 points)
    score += Math.min((props.profile.total_matches / 50) * 20, 20); // Experience (20 points)
    return Math.round(Math.min(score, 100));
});
const strengthClass = computed(() => {
    if (strengthScore.value >= 80)
        return 'strength-excellent';
    if (strengthScore.value >= 60)
        return 'strength-good';
    if (strengthScore.value >= 40)
        return 'strength-average';
    return 'strength-developing';
});
const strengthLabel = computed(() => {
    if (strengthScore.value >= 80)
        return 'Excellent';
    if (strengthScore.value >= 60)
        return 'Good';
    if (strengthScore.value >= 40)
        return 'Average';
    return 'Developing';
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['sw-item-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['sw-item-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['sw-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "strength-weakness-widget" },
});
/** @type {__VLS_StyleScopedClasses['strength-weakness-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-container" },
});
/** @type {__VLS_StyleScopedClasses['sw-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-section strengths-section" },
});
/** @type {__VLS_StyleScopedClasses['sw-section']} */ ;
/** @type {__VLS_StyleScopedClasses['strengths-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-header" },
});
/** @type {__VLS_StyleScopedClasses['sw-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "sw-title" },
});
/** @type {__VLS_StyleScopedClasses['sw-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "sw-count" },
});
/** @type {__VLS_StyleScopedClasses['sw-count']} */ ;
(__VLS_ctx.strengths.length);
if (__VLS_ctx.strengths.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sw-list" },
    });
    /** @type {__VLS_StyleScopedClasses['sw-list']} */ ;
    for (const [strength, idx] of __VLS_vFor((__VLS_ctx.strengths))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`strength-${idx}`),
            ...{ class: "sw-item strength-item" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item']} */ ;
        /** @type {__VLS_StyleScopedClasses['strength-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "sw-item-badge good" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-badge']} */ ;
        /** @type {__VLS_StyleScopedClasses['good']} */ ;
        (idx + 1);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "sw-item-content" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "sw-item-text" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-text']} */ ;
        (strength);
        // @ts-ignore
        [strengths, strengths, strengths,];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "sw-empty" },
    });
    /** @type {__VLS_StyleScopedClasses['sw-empty']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-section weaknesses-section" },
});
/** @type {__VLS_StyleScopedClasses['sw-section']} */ ;
/** @type {__VLS_StyleScopedClasses['weaknesses-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-header" },
});
/** @type {__VLS_StyleScopedClasses['sw-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "sw-title" },
});
/** @type {__VLS_StyleScopedClasses['sw-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "sw-count" },
});
/** @type {__VLS_StyleScopedClasses['sw-count']} */ ;
(__VLS_ctx.weaknesses.length);
if (__VLS_ctx.weaknesses.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sw-list" },
    });
    /** @type {__VLS_StyleScopedClasses['sw-list']} */ ;
    for (const [weakness, idx] of __VLS_vFor((__VLS_ctx.weaknesses))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`weakness-${idx}`),
            ...{ class: "sw-item weakness-item" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item']} */ ;
        /** @type {__VLS_StyleScopedClasses['weakness-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "sw-item-badge poor" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-badge']} */ ;
        /** @type {__VLS_StyleScopedClasses['poor']} */ ;
        (idx + 1);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "sw-item-content" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "sw-item-text" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-text']} */ ;
        (weakness);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "sw-item-tip" },
        });
        /** @type {__VLS_StyleScopedClasses['sw-item-tip']} */ ;
        // @ts-ignore
        [weaknesses, weaknesses, weaknesses,];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "sw-empty" },
    });
    /** @type {__VLS_StyleScopedClasses['sw-empty']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "development-focus" },
});
/** @type {__VLS_StyleScopedClasses['development-focus']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "focus-header" },
});
/** @type {__VLS_StyleScopedClasses['focus-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
    ...{ class: "focus-title" },
});
/** @type {__VLS_StyleScopedClasses['focus-title']} */ ;
if (__VLS_ctx.weaknesses.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "focus-tips" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-tips']} */ ;
    for (const [weakness, idx] of __VLS_vFor((__VLS_ctx.weaknesses.slice(0, 2)))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`tip-${idx}`),
            ...{ class: "focus-tip" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-tip']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tip-number" },
        });
        /** @type {__VLS_StyleScopedClasses['tip-number']} */ ;
        (idx + 1);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "tip-content" },
        });
        /** @type {__VLS_StyleScopedClasses['tip-content']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "tip-text" },
        });
        /** @type {__VLS_StyleScopedClasses['tip-text']} */ ;
        (weakness);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "tip-action" },
        });
        /** @type {__VLS_StyleScopedClasses['tip-action']} */ ;
        // @ts-ignore
        [weaknesses, weaknesses,];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "focus-tips" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-tips']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "focus-empty" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-empty']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sw-progress" },
});
/** @type {__VLS_StyleScopedClasses['sw-progress']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "progress-bar-container" },
});
/** @type {__VLS_StyleScopedClasses['progress-bar-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "progress-label" },
});
/** @type {__VLS_StyleScopedClasses['progress-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "progress-bar" },
});
/** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "progress-fill" },
    ...{ style: ({ width: `${__VLS_ctx.strengthScore}%` }) },
    ...{ class: (__VLS_ctx.strengthClass) },
});
/** @type {__VLS_StyleScopedClasses['progress-fill']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "progress-value" },
});
/** @type {__VLS_StyleScopedClasses['progress-value']} */ ;
(__VLS_ctx.strengthLabel);
(__VLS_ctx.strengthScore);
// @ts-ignore
[strengthScore, strengthScore, strengthClass, strengthLabel,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
