/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
const __VLS_props = defineProps();
const emit = defineEmits();
const feedbackText = ref('');
const email = ref('');
const isSubmitting = ref(false);
const canSubmit = computed(() => feedbackText.value.trim().length > 0 && !isSubmitting.value);
function close() {
    emit('update:visible', false);
}
async function submit() {
    if (!canSubmit.value)
        return;
    isSubmitting.value = true;
    try {
        emit('submitted', {
            text: feedbackText.value.trim(),
            email: email.value.trim() || undefined,
        });
        // Reset form
        feedbackText.value = '';
        email.value = '';
        close();
    }
    finally {
        isSubmitting.value = false;
    }
}
function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
        close();
    }
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
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-btn--secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['fade-enter-active']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
/** @type {__VLS_StyleScopedClasses['fade-leave-active']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
/** @type {__VLS_StyleScopedClasses['fade-enter-from']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
/** @type {__VLS_StyleScopedClasses['fade-leave-to']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
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
/** @ts-ignore @type { | typeof __VLS_components.Transition | typeof __VLS_components.Transition} */
Transition;
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
        ...{ onClick: (__VLS_ctx.handleBackdropClick) },
        ...{ class: "modal-backdrop" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "modal-header" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "close-btn" },
        'aria-label': "Close",
    });
    /** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-body" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "required" },
    });
    /** @type {__VLS_StyleScopedClasses['required']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
        value: (__VLS_ctx.feedbackText),
        ...{ class: "ds-input feedback-textarea" },
        placeholder: "Tell us what's on your mind...",
        rows: "5",
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    /** @type {__VLS_StyleScopedClasses['feedback-textarea']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "email",
        ...{ class: "ds-input" },
        placeholder: "your@email.com",
    });
    (__VLS_ctx.email);
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
        ...{ class: "modal-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "ds-btn ds-btn--secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['ds-btn--secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.submit) },
        ...{ class: "ds-btn ds-btn--primary" },
        disabled: (!__VLS_ctx.canSubmit),
    });
    /** @type {__VLS_StyleScopedClasses['ds-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['ds-btn--primary']} */ ;
    (__VLS_ctx.isSubmitting ? 'Sending...' : 'Send');
}
// @ts-ignore
[visible, handleBackdropClick, close, close, feedbackText, email, submit, canSubmit, isSubmitting,];
var __VLS_9;
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
