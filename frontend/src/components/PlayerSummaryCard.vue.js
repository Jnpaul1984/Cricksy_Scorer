/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
const props = defineProps();
const emit = defineEmits();
function copyToClipboard() {
    if (!props.summary)
        return;
    const text = `
🎯 What to Focus On:
${props.summary.focus_area}

📝 Key Points:
${props.summary.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n')}

💪 ${props.summary.encouragement}

🚀 Next Steps:
${props.summary.next_steps}
  `.trim();
    navigator.clipboard.writeText(text).then(() => {
        alert('Player summary copied to clipboard!');
    });
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
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-content']} */ ;
/** @type {__VLS_StyleScopedClasses['points-list']} */ ;
/** @type {__VLS_StyleScopedClasses['points-list']} */ ;
/** @type {__VLS_StyleScopedClasses['encouragement-box']} */ ;
/** @type {__VLS_StyleScopedClasses['encouragement-box']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-close']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-close']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-copy']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "player-summary-card" },
});
/** @type {__VLS_StyleScopedClasses['player-summary-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-header" },
});
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "badge" },
});
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
if (!__VLS_ctx.summary) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "summary-content" },
    });
    /** @type {__VLS_StyleScopedClasses['summary-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "focus-area" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-area']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "focus-text" },
    });
    /** @type {__VLS_StyleScopedClasses['focus-text']} */ ;
    (__VLS_ctx.summary.focus_area);
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "key-points" },
    });
    /** @type {__VLS_StyleScopedClasses['key-points']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "points-list" },
    });
    /** @type {__VLS_StyleScopedClasses['points-list']} */ ;
    for (const [point, idx] of __VLS_vFor((__VLS_ctx.summary.key_points))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (idx),
        });
        (point);
        // @ts-ignore
        [summary, summary, summary,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "encouragement" },
    });
    /** @type {__VLS_StyleScopedClasses['encouragement']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "encouragement-box" },
    });
    /** @type {__VLS_StyleScopedClasses['encouragement-box']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "icon" },
    });
    /** @type {__VLS_StyleScopedClasses['icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.summary.encouragement);
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "next-steps" },
    });
    /** @type {__VLS_StyleScopedClasses['next-steps']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "steps-text" },
    });
    /** @type {__VLS_StyleScopedClasses['steps-text']} */ ;
    (__VLS_ctx.summary.next_steps);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-footer" },
});
/** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.$emit('close');
            // @ts-ignore
            [summary, summary, $emit,];
        } },
    ...{ class: "btn-close" },
});
/** @type {__VLS_StyleScopedClasses['btn-close']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.copyToClipboard) },
    ...{ class: "btn-copy" },
});
/** @type {__VLS_StyleScopedClasses['btn-copy']} */ ;
// @ts-ignore
[copyToClipboard,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
