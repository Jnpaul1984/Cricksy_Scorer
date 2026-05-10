/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, watch, computed } from 'vue';
import { BaseCard, BaseButton, BaseBadge } from '@/components';
const props = defineProps();
const emit = defineEmits(['update:visible']);
const guideUrl = 'https://github.com/Jnpaul1984/Cricksy_Scorer/blob/main/docs/beta/Cricksy_Beta_Tester_Guide.md';
const matchChecklist = [
    'Create a new match',
    'Add teams and players',
    'Score 5–10 overs ball-by-ball',
    'Record wickets and extras',
    'Try retire hurt, bowler change, etc.',
];
const viewerChecklist = [
    'Open the public viewer',
    'Check live score updates',
    'Share a match link and open on another device',
];
const profileChecklist = [
    'Open a player profile',
    'Review stats and graphs',
    'Read AI summaries',
];
const dashboardChecklist = [
    'Open Analyst Workspace or Org Dashboard',
    'Filter matches or teams',
    'Review analytics and charts',
];
const checked = ref({
    match: Array(matchChecklist.length).fill(false),
    viewer: Array(viewerChecklist.length).fill(false),
    profile: Array(profileChecklist.length).fill(false),
    dash: Array(dashboardChecklist.length).fill(false),
});
const showDashboards = computed(() => {
    // This prop should be set by parent based on user profile, or you can inject user store here
    // For now, always show for demo; replace with real logic as needed
    return true;
});
watch(() => props.visible, (val) => {
    if (!val) {
        // Reset checklist when closed
        checked.value = {
            match: Array(matchChecklist.length).fill(false),
            viewer: Array(viewerChecklist.length).fill(false),
            profile: Array(profileChecklist.length).fill(false),
            dash: Array(dashboardChecklist.length).fill(false),
        };
    }
});
function close() {
    emit('update:visible', false);
}
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Teleport | typeof __VLS_components.Teleport} */
Teleport;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "body",
}));
const __VLS_2 = __VLS_1({
    to: "body",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
transition;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    name: "fade",
}));
const __VLS_8 = __VLS_7({
    name: "fade",
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
const { default: __VLS_11 } = __VLS_9.slots;
if (__VLS_ctx.visible) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    let __VLS_12;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
        ...{ class: "beta-modal" },
        padding: "lg",
    }));
    const __VLS_14 = __VLS_13({
        ...{ class: "beta-modal" },
        padding: "lg",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    /** @type {__VLS_StyleScopedClasses['beta-modal']} */ ;
    const { default: __VLS_17 } = __VLS_15.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
        ...{ class: "modal-title" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "modal-intro" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-intro']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "checklist-section" },
    });
    /** @type {__VLS_StyleScopedClasses['checklist-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    let __VLS_18;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
        variant: "primary",
    }));
    const __VLS_20 = __VLS_19({
        variant: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    const { default: __VLS_23 } = __VLS_21.slots;
    // @ts-ignore
    [visible, close,];
    var __VLS_21;
    for (const [item, i] of __VLS_vFor((__VLS_ctx.matchChecklist))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: ('match-' + i),
            ...{ class: "checklist-item" },
        });
        /** @type {__VLS_StyleScopedClasses['checklist-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            id: ('match-' + i),
            type: "checkbox",
        });
        (__VLS_ctx.checked.match[i]);
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: ('match-' + i),
        });
        (item);
        // @ts-ignore
        [matchChecklist, checked,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "checklist-section" },
    });
    /** @type {__VLS_StyleScopedClasses['checklist-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    let __VLS_24;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
        variant: "success",
    }));
    const __VLS_26 = __VLS_25({
        variant: "success",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    const { default: __VLS_29 } = __VLS_27.slots;
    // @ts-ignore
    [];
    var __VLS_27;
    for (const [item, i] of __VLS_vFor((__VLS_ctx.viewerChecklist))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: ('viewer-' + i),
            ...{ class: "checklist-item" },
        });
        /** @type {__VLS_StyleScopedClasses['checklist-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            id: ('viewer-' + i),
            type: "checkbox",
        });
        (__VLS_ctx.checked.viewer[i]);
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: ('viewer-' + i),
        });
        (item);
        // @ts-ignore
        [checked, viewerChecklist,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "checklist-section" },
    });
    /** @type {__VLS_StyleScopedClasses['checklist-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    let __VLS_30;
    /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
    BaseBadge;
    // @ts-ignore
    const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
        variant: "warning",
    }));
    const __VLS_32 = __VLS_31({
        variant: "warning",
    }, ...__VLS_functionalComponentArgsRest(__VLS_31));
    const { default: __VLS_35 } = __VLS_33.slots;
    // @ts-ignore
    [];
    var __VLS_33;
    for (const [item, i] of __VLS_vFor((__VLS_ctx.profileChecklist))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: ('profile-' + i),
            ...{ class: "checklist-item" },
        });
        /** @type {__VLS_StyleScopedClasses['checklist-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            id: ('profile-' + i),
            type: "checkbox",
        });
        (__VLS_ctx.checked.profile[i]);
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: ('profile-' + i),
        });
        (item);
        // @ts-ignore
        [checked, profileChecklist,];
    }
    if (__VLS_ctx.showDashboards) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "checklist-section" },
        });
        /** @type {__VLS_StyleScopedClasses['checklist-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        let __VLS_36;
        /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
        BaseBadge;
        // @ts-ignore
        const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
            variant: "neutral",
        }));
        const __VLS_38 = __VLS_37({
            variant: "neutral",
        }, ...__VLS_functionalComponentArgsRest(__VLS_37));
        const { default: __VLS_41 } = __VLS_39.slots;
        // @ts-ignore
        [showDashboards,];
        var __VLS_39;
        for (const [item, i] of __VLS_vFor((__VLS_ctx.dashboardChecklist))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: ('dash-' + i),
                ...{ class: "checklist-item" },
            });
            /** @type {__VLS_StyleScopedClasses['checklist-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
                id: ('dash-' + i),
                type: "checkbox",
            });
            (__VLS_ctx.checked.dash[i]);
            __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
                for: ('dash-' + i),
            });
            (item);
            // @ts-ignore
            [checked, dashboardChecklist,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
    let __VLS_42;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
        ...{ 'onClick': {} },
        variant: "secondary",
    }));
    const __VLS_44 = __VLS_43({
        ...{ 'onClick': {} },
        variant: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_43));
    let __VLS_47;
    const __VLS_48 = ({ click: {} },
        { onClick: (__VLS_ctx.close) });
    const { default: __VLS_49 } = __VLS_45.slots;
    // @ts-ignore
    [close,];
    var __VLS_45;
    var __VLS_46;
    let __VLS_50;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_51 = __VLS_asFunctionalComponent1(__VLS_50, new __VLS_50({
        as: "a",
        href: (__VLS_ctx.guideUrl),
        target: "_blank",
        variant: "primary",
    }));
    const __VLS_52 = __VLS_51({
        as: "a",
        href: (__VLS_ctx.guideUrl),
        target: "_blank",
        variant: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_51));
    const { default: __VLS_55 } = __VLS_53.slots;
    // @ts-ignore
    [guideUrl,];
    var __VLS_53;
    // @ts-ignore
    [];
    var __VLS_15;
}
// @ts-ignore
[];
var __VLS_9;
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    emits: {},
    __typeProps: {},
});
export default {};
