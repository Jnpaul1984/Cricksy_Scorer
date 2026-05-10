/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
const __VLS_props = defineProps();
const __VLS_emit = defineEmits();
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['btn-generate']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-header']} */ ;
/** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['cues-list']} */ ;
/** @type {__VLS_StyleScopedClasses['cues-list']} */ ;
/** @type {__VLS_StyleScopedClasses['cues-list']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-zones']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-metrics']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-card']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-card']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-card']} */ ;
/** @type {__VLS_StyleScopedClasses['goal-card']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-approve']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coach-suggestions-panel" },
});
/** @type {__VLS_StyleScopedClasses['coach-suggestions-panel']} */ ;
if (!__VLS_ctx.suggestions) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(!__VLS_ctx.suggestions))
                    return;
                __VLS_ctx.$emit('generate');
                // @ts-ignore
                [suggestions, $emit,];
            } },
        ...{ class: "btn-generate" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-generate']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "suggestions-content" },
    });
    /** @type {__VLS_StyleScopedClasses['suggestions-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "focus-section primary" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-section']} */ ;
    /** @type {__VLS_StyleScopedClasses['primary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "focus-card" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "focus-header" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.suggestions.primary_focus.title);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: (['severity-badge', __VLS_ctx.suggestions.primary_focus.severity]) },
    });
    /** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
    (__VLS_ctx.suggestions.primary_focus.severity.toUpperCase());
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "rationale" },
    });
    /** @type {__VLS_StyleScopedClasses['rationale']} */ ;
    (__VLS_ctx.suggestions.primary_focus.rationale);
    if (__VLS_ctx.suggestions.secondary_focus) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "focus-section secondary" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-section']} */ ;
        /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "focus-card" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "focus-header" },
        });
        /** @type {__VLS_StyleScopedClasses['focus-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.suggestions.secondary_focus.title);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: (['severity-badge', __VLS_ctx.suggestions.secondary_focus.severity]) },
        });
        /** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
        (__VLS_ctx.suggestions.secondary_focus.severity.toUpperCase());
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "rationale" },
        });
        /** @type {__VLS_StyleScopedClasses['rationale']} */ ;
        (__VLS_ctx.suggestions.secondary_focus.rationale);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "cues-section" },
    });
    /** @type {__VLS_StyleScopedClasses['cues-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "cues-list" },
    });
    /** @type {__VLS_StyleScopedClasses['cues-list']} */ ;
    for (const [cue, idx] of __VLS_vFor((__VLS_ctx.suggestions.coaching_cues))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (idx),
        });
        (cue);
        // @ts-ignore
        [suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions, suggestions,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "drills-section" },
    });
    /** @type {__VLS_StyleScopedClasses['drills-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "drills-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['drills-grid']} */ ;
    for (const [drill, idx] of __VLS_vFor((__VLS_ctx.suggestions.drills))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (idx),
            ...{ class: "drill-card" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
        (drill.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "drill-desc" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-desc']} */ ;
        (drill.description);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "drill-meta" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-meta']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "drill-tag" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-tag']} */ ;
        (drill.equipment);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "drill-tag" },
        });
        /** @type {__VLS_StyleScopedClasses['drill-tag']} */ ;
        (drill.focus);
        // @ts-ignore
        [suggestions,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "next-goal-section" },
    });
    /** @type {__VLS_StyleScopedClasses['next-goal-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "goal-card" },
    });
    /** @type {__VLS_StyleScopedClasses['goal-card']} */ ;
    if (__VLS_ctx.suggestions.proposed_next_goal.zones.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "goal-zones" },
        });
        /** @type {__VLS_StyleScopedClasses['goal-zones']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
        for (const [zone] of __VLS_vFor((__VLS_ctx.suggestions.proposed_next_goal.zones))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (zone.zone_id),
            });
            (zone.zone_name);
            (zone.target_accuracy);
            // @ts-ignore
            [suggestions, suggestions,];
        }
    }
    if (__VLS_ctx.suggestions.proposed_next_goal.metrics.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "goal-metrics" },
        });
        /** @type {__VLS_StyleScopedClasses['goal-metrics']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
        for (const [metric] of __VLS_vFor((__VLS_ctx.suggestions.proposed_next_goal.metrics))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (metric.code),
            });
            (metric.code);
            ((metric.target_score * 100).toFixed(0));
            // @ts-ignore
            [suggestions, suggestions,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "goal-rationale" },
    });
    /** @type {__VLS_StyleScopedClasses['goal-rationale']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.em, __VLS_intrinsics.em)({});
    (__VLS_ctx.suggestions.rationale);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.suggestions))
                    return;
                __VLS_ctx.$emit('approve-goal', __VLS_ctx.suggestions.proposed_next_goal);
                // @ts-ignore
                [suggestions, suggestions, $emit,];
            } },
        ...{ class: "btn-approve" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-approve']} */ ;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
