/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
const props = withDefaults(defineProps(), {
    sponsors: () => [],
    sponsorRotateMs: 8000,
    sponsorClickable: false,
    showArrows: false,
});
const emit = defineEmits();
const idx = ref(0);
const timer = ref(null);
const hovered = ref(false);
const safeSponsors = computed(() => (props.sponsors || []).filter(s => !!s && !!s.logoUrl));
const count = computed(() => safeSponsors.value.length);
const current = computed(() => safeSponsors.value.length ? safeSponsors.value[idx.value % safeSponsors.value.length] : null);
const activeKey = computed(() => current.value ? (current.value.id ?? idx.value) : `empty-${idx.value}`);
const start = () => {
    stop();
    if (count.value <= 1)
        return;
    timer.value = window.setInterval(() => {
        if (!hovered.value)
            next();
    }, props.sponsorRotateMs);
};
const stop = () => { if (timer.value) {
    clearInterval(timer.value);
    timer.value = null;
} };
const pause = () => { hovered.value = true; };
const resume = () => { hovered.value = false; };
const next = () => { if (count.value)
    idx.value = (idx.value + 1) % count.value; };
const prev = () => { if (count.value)
    idx.value = (idx.value - 1 + count.value) % count.value; };
const go = (i) => { if (count.value)
    idx.value = i % count.value; };
const showArrows = computed(() => props.showArrows && count.value > 1);
const railStyle = computed(() => ({}));
function emitClick(sp) {
    emit('click', sp);
}
watch(current, (sp) => {
    // Fire an impression event every time the visible sponsor changes
    emit('impression', sp ?? null);
});
watch(() => props.sponsorRotateMs, () => start());
watch(safeSponsors, () => { idx.value = 0; start(); });
onMounted(() => { start(); emit('impression', current.value ?? null); });
onBeforeUnmount(() => stop());
const __VLS_defaults = {
    sponsors: () => [],
    sponsorRotateMs: 8000,
    sponsorClickable: false,
    showArrows: false,
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
/** @type {__VLS_StyleScopedClasses['nav']} */ ;
/** @type {__VLS_StyleScopedClasses['dot']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sbar" },
    role: "region",
    'aria-label': "Sponsors",
});
/** @type {__VLS_StyleScopedClasses['sbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "rail" },
    ...{ style: (__VLS_ctx.railStyle) },
});
/** @type {__VLS_StyleScopedClasses['rail']} */ ;
if (__VLS_ctx.showArrows) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.prev) },
        ...{ class: "nav prev" },
        'aria-label': "Previous sponsor",
    });
    /** @type {__VLS_StyleScopedClasses['nav']} */ ;
    /** @type {__VLS_StyleScopedClasses['prev']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ onMouseenter: (__VLS_ctx.pause) },
    ...{ onMouseleave: (__VLS_ctx.resume) },
    ...{ class: "viewport" },
});
/** @type {__VLS_StyleScopedClasses['viewport']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.transition | typeof __VLS_components.Transition | typeof __VLS_components.transition | typeof __VLS_components.Transition} */
transition;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    name: "fade",
    mode: "out-in",
}));
const __VLS_2 = __VLS_1({
    name: "fade",
    mode: "out-in",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    key: (__VLS_ctx.activeKey),
    ...{ class: "slide" },
});
/** @type {__VLS_StyleScopedClasses['slide']} */ ;
if (__VLS_ctx.sponsorClickable && __VLS_ctx.current?.clickUrl) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.sponsorClickable && __VLS_ctx.current?.clickUrl))
                    return;
                __VLS_ctx.emitClick(__VLS_ctx.current);
                // @ts-ignore
                [railStyle, showArrows, prev, pause, resume, activeKey, sponsorClickable, current, current, emitClick,];
            } },
        ...{ class: "logo-link" },
        href: (__VLS_ctx.current.clickUrl),
        target: "_blank",
        rel: "noopener",
    });
    /** @type {__VLS_StyleScopedClasses['logo-link']} */ ;
    if (__VLS_ctx.current) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
            ...{ class: "logo" },
            src: (__VLS_ctx.current.logoUrl),
            alt: (__VLS_ctx.current.name),
        });
        /** @type {__VLS_StyleScopedClasses['logo']} */ ;
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "logo-wrap" },
    });
    /** @type {__VLS_StyleScopedClasses['logo-wrap']} */ ;
    if (__VLS_ctx.current) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
            ...{ class: "logo" },
            src: (__VLS_ctx.current.logoUrl),
            alt: (__VLS_ctx.current.name),
        });
        /** @type {__VLS_StyleScopedClasses['logo']} */ ;
    }
}
// @ts-ignore
[current, current, current, current, current, current, current,];
var __VLS_3;
if (__VLS_ctx.showArrows) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.next) },
        ...{ class: "nav next" },
        'aria-label': "Next sponsor",
    });
    /** @type {__VLS_StyleScopedClasses['nav']} */ ;
    /** @type {__VLS_StyleScopedClasses['next']} */ ;
}
if (__VLS_ctx.sponsors.length > 1) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dots" },
    });
    /** @type {__VLS_StyleScopedClasses['dots']} */ ;
    for (const [sp, i] of __VLS_vFor((__VLS_ctx.sponsors))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.sponsors.length > 1))
                        return;
                    __VLS_ctx.go(i);
                    // @ts-ignore
                    [showArrows, next, sponsors, sponsors, go,];
                } },
            key: (sp.id ?? i),
            ...{ class: "dot" },
            ...{ class: ({ active: i === __VLS_ctx.idx }) },
            'aria-label': (`Go to ${sp.name}`),
        });
        /** @type {__VLS_StyleScopedClasses['dot']} */ ;
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        // @ts-ignore
        [idx,];
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
