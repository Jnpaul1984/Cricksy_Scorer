/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref } from 'vue';
const props = withDefaults(defineProps(), {
    initialFollowing: false,
    variant: 'primary',
    size: 'md',
});
const emit = defineEmits();
const isFollowing = ref(props.initialFollowing);
const isLoading = ref(false);
async function toggleFollow() {
    isLoading.value = true;
    try {
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (isFollowing.value) {
            emit('unfollow', props.entityId);
            isFollowing.value = false;
        }
        else {
            emit('follow', props.entityId);
            isFollowing.value = true;
        }
    }
    finally {
        isLoading.value = false;
    }
}
const __VLS_defaults = {
    initialFollowing: false,
    variant: 'primary',
    size: 'md',
};
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
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-following']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-following']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['variant-ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['is-following']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.toggleFollow) },
    ...{ class: "follow-btn" },
    ...{ class: ([
            `variant-${__VLS_ctx.variant}`,
            `size-${__VLS_ctx.size}`,
            {
                'is-following': __VLS_ctx.isFollowing,
                'is-loading': __VLS_ctx.isLoading,
            },
        ]) },
    disabled: (__VLS_ctx.isLoading),
});
/** @type {__VLS_StyleScopedClasses['follow-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['is-following']} */ ;
/** @type {__VLS_StyleScopedClasses['is-loading']} */ ;
if (__VLS_ctx.isLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
}
else if (__VLS_ctx.isFollowing) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "icon" },
    });
    /** @type {__VLS_StyleScopedClasses['icon']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "icon" },
    });
    /** @type {__VLS_StyleScopedClasses['icon']} */ ;
}
(__VLS_ctx.isFollowing ? 'Following' : 'Follow');
// @ts-ignore
[toggleFollow, variant, size, isFollowing, isFollowing, isFollowing, isLoading, isLoading, isLoading,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
