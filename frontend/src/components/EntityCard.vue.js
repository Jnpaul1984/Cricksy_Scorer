/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import FollowButton from './FollowButton.vue';
import { useFollowSystem } from '@/composables/useFollowSystem';
const props = defineProps();
const emit = defineEmits();
const { isFollowed, follow, unfollow } = useFollowSystem();
const isEntityFollowed = computed(() => isFollowed(props.id));
function handleFollow() {
    follow(props.id, props.entityType, props.name);
    emit('followed', props.id);
}
function handleUnfollow() {
    unfollow(props.id);
    emit('unfollowed', props.id);
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
/** @type {__VLS_StyleScopedClasses['entity-card']} */ ;
/** @type {__VLS_StyleScopedClasses['details-link']} */ ;
/** @type {__VLS_StyleScopedClasses['entity-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "entity-card" },
});
/** @type {__VLS_StyleScopedClasses['entity-card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-header" },
});
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "entity-badge" },
});
/** @type {__VLS_StyleScopedClasses['entity-badge']} */ ;
(__VLS_ctx.entityType);
const __VLS_0 = FollowButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onFollow': {} },
    ...{ 'onUnfollow': {} },
    entityId: (__VLS_ctx.id),
    entityType: (__VLS_ctx.entityType),
    initialFollowing: (__VLS_ctx.isFollowed),
    variant: "secondary",
    size: "sm",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onFollow': {} },
    ...{ 'onUnfollow': {} },
    entityId: (__VLS_ctx.id),
    entityType: (__VLS_ctx.entityType),
    initialFollowing: (__VLS_ctx.isFollowed),
    variant: "secondary",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ follow: {} },
    { onFollow: (__VLS_ctx.handleFollow) });
const __VLS_7 = ({ unfollow: {} },
    { onUnfollow: (__VLS_ctx.handleUnfollow) });
var __VLS_3;
var __VLS_4;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-body" },
});
/** @type {__VLS_StyleScopedClasses['card-body']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "entity-icon" },
});
/** @type {__VLS_StyleScopedClasses['entity-icon']} */ ;
(__VLS_ctx.icon);
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "entity-name" },
});
/** @type {__VLS_StyleScopedClasses['entity-name']} */ ;
(__VLS_ctx.name);
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "entity-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['entity-subtitle']} */ ;
(__VLS_ctx.subtitle);
if (__VLS_ctx.stats) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "entity-stats" },
    });
    /** @type {__VLS_StyleScopedClasses['entity-stats']} */ ;
    for (const [value, label] of __VLS_vFor((__VLS_ctx.stats))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (label),
            ...{ class: "stat" },
        });
        /** @type {__VLS_StyleScopedClasses['stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        (label);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (value);
        // @ts-ignore
        [entityType, entityType, id, isFollowed, handleFollow, handleUnfollow, icon, name, subtitle, stats, stats,];
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-footer" },
});
/** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link'] | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link']} */
routerLink;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    to: (__VLS_ctx.detailsLink),
    ...{ class: "details-link" },
}));
const __VLS_10 = __VLS_9({
    to: (__VLS_ctx.detailsLink),
    ...{ class: "details-link" },
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
/** @type {__VLS_StyleScopedClasses['details-link']} */ ;
const { default: __VLS_13 } = __VLS_11.slots;
// @ts-ignore
[detailsLink,];
var __VLS_11;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
