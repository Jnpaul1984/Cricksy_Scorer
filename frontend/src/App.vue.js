/// <reference types="../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, RouterView } from 'vue-router';
import logoAvif1024 from '@/assets/optimized/logo-w1024.avif';
import logoWebp1024 from '@/assets/optimized/logo-w1024.webp';
import logoAvif1440 from '@/assets/optimized/logo-w1440.avif';
import logoWebp1440 from '@/assets/optimized/logo-w1440.webp';
import logoAvif480 from '@/assets/optimized/logo-w480.avif';
import logoWebp480 from '@/assets/optimized/logo-w480.webp';
import logoAvif768 from '@/assets/optimized/logo-w768.avif';
import logoWebp768 from '@/assets/optimized/logo-w768.webp';
import BetaChecklistModal from '@/components/BetaChecklistModal.vue';
import FeedbackModal from '@/components/FeedbackModal.vue';
import QuotaWarningBanner from '@/components/QuotaWarningBanner.vue';
import { useAuthStore } from '@/stores/authStore';
const isDev = computed(() => import.meta.env.DEV);
const showFeedbackModal = ref(false);
const showBetaChecklist = ref(false);
const auth = useAuthStore();
const showBetaGuide = computed(() => Boolean(auth.user && auth.user.beta_tag));
function handleFeedbackSubmit(payload) {
    // TODO: Send feedback to backend API
    console.log('Feedback submitted:', payload);
    // For now, just log it - will integrate with backend later
}
// Keyboard shortcut: "F" to open feedback modal
function handleKeydown(e) {
    // Don't trigger if user is typing in an input/textarea
    const target = e.target;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
    }
    // "F" key opens feedback modal
    if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        showFeedbackModal.value = true;
    }
}
onMounted(() => {
    // hide the tiny fallback text from index.html once Vue is mounted
    const el = document.getElementById('app');
    if (el)
        el.classList.add('loaded');
    // Add keyboard listener
    window.addEventListener('keydown', handleKeydown);
});
onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown);
});
const logoSources = [
    { width: 480, avif: logoAvif480, webp: logoWebp480 },
    { width: 768, avif: logoAvif768, webp: logoWebp768 },
    { width: 1024, avif: logoAvif1024, webp: logoWebp1024 },
    { width: 1440, avif: logoAvif1440, webp: logoWebp1440 },
];
const logoAvifSrcset = logoSources.map((src) => `${src.avif} ${src.width}w`).join(', ');
const logoWebpSrcset = logoSources.map((src) => `${src.webp} ${src.width}w`).join(', ');
const logoFallbackSrc = logoSources.find((src) => src.width === 768)?.webp ?? logoSources[0].webp;
const logoSizes = '32px';
// Auth store for role-based navigation
const showCoachNav = computed(() => auth.isCoach || auth.isOrg || auth.isSuper);
const showAnalystNav = computed(() => auth.isAnalyst || auth.isOrg || auth.isSuper);
const showAdminNav = computed(() => auth.isSuper);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['brand-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['nav']} */ ;
/** @type {__VLS_StyleScopedClasses['nav']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-admin']} */ ;
/** @type {__VLS_StyleScopedClasses['user-menu-item']} */ ;
/** @type {__VLS_StyleScopedClasses['logout-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['feedback-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "app" },
});
/** @type {__VLS_StyleScopedClasses['app']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "app-header" },
});
/** @type {__VLS_StyleScopedClasses['app-header']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "/",
    ...{ class: "brand" },
}));
const __VLS_2 = __VLS_1({
    to: "/",
    ...{ class: "brand" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.picture, __VLS_intrinsics.picture)({
    ...{ class: "brand-logo" },
});
/** @type {__VLS_StyleScopedClasses['brand-logo']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.source)({
    srcset: (__VLS_ctx.logoAvifSrcset),
    sizes: (__VLS_ctx.logoSizes),
    type: "image/avif",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.source)({
    srcset: (__VLS_ctx.logoWebpSrcset),
    sizes: (__VLS_ctx.logoSizes),
    type: "image/webp",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.img)({
    src: (__VLS_ctx.logoFallbackSrc),
    sizes: (__VLS_ctx.logoSizes),
    alt: "Cricksy Mascot",
    loading: "eager",
    decoding: "async",
    width: "32",
    height: "32",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
// @ts-ignore
[logoAvifSrcset, logoSizes, logoSizes, logoSizes, logoWebpSrcset, logoFallbackSrc,];
var __VLS_3;
__VLS_asFunctionalElement1(__VLS_intrinsics.nav, __VLS_intrinsics.nav)({
    ...{ class: "nav" },
});
/** @type {__VLS_StyleScopedClasses['nav']} */ ;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    to: "/landing",
}));
const __VLS_8 = __VLS_7({
    to: "/landing",
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
const { default: __VLS_11 } = __VLS_9.slots;
// @ts-ignore
[];
var __VLS_9;
let __VLS_12;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
    to: "/setup",
}));
const __VLS_14 = __VLS_13({
    to: "/setup",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
const { default: __VLS_17 } = __VLS_15.slots;
// @ts-ignore
[];
var __VLS_15;
if (__VLS_ctx.showCoachNav) {
    let __VLS_18;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
        to: "/coach/dashboard",
    }));
    const __VLS_20 = __VLS_19({
        to: "/coach/dashboard",
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    const { default: __VLS_23 } = __VLS_21.slots;
    // @ts-ignore
    [showCoachNav,];
    var __VLS_21;
}
if (__VLS_ctx.showAnalystNav) {
    let __VLS_24;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
        to: "/analyst/workspace",
    }));
    const __VLS_26 = __VLS_25({
        to: "/analyst/workspace",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    const { default: __VLS_29 } = __VLS_27.slots;
    // @ts-ignore
    [showAnalystNav,];
    var __VLS_27;
}
if (__VLS_ctx.showAdminNav) {
    let __VLS_30;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
        to: "/admin/beta-users",
        ...{ class: "nav-admin" },
    }));
    const __VLS_32 = __VLS_31({
        to: "/admin/beta-users",
        ...{ class: "nav-admin" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_31));
    /** @type {__VLS_StyleScopedClasses['nav-admin']} */ ;
    const { default: __VLS_35 } = __VLS_33.slots;
    // @ts-ignore
    [showAdminNav,];
    var __VLS_33;
}
let __VLS_36;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
    to: "/pricing",
}));
const __VLS_38 = __VLS_37({
    to: "/pricing",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
const { default: __VLS_41 } = __VLS_39.slots;
// @ts-ignore
[];
var __VLS_39;
let __VLS_42;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
    to: "/help",
    title: "Help & Guide",
}));
const __VLS_44 = __VLS_43({
    to: "/help",
    title: "Help & Guide",
}, ...__VLS_functionalComponentArgsRest(__VLS_43));
const { default: __VLS_47 } = __VLS_45.slots;
// @ts-ignore
[];
var __VLS_45;
if (__VLS_ctx.isDev) {
    let __VLS_48;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent1(__VLS_48, new __VLS_48({
        to: "/design-system",
        ...{ class: "nav-dev" },
    }));
    const __VLS_50 = __VLS_49({
        to: "/design-system",
        ...{ class: "nav-dev" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    /** @type {__VLS_StyleScopedClasses['nav-dev']} */ ;
    const { default: __VLS_53 } = __VLS_51.slots;
    // @ts-ignore
    [isDev,];
    var __VLS_51;
}
if (__VLS_ctx.showBetaGuide) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showBetaGuide))
                    return;
                __VLS_ctx.showBetaChecklist = true;
                // @ts-ignore
                [showBetaGuide, showBetaChecklist,];
            } },
        ...{ class: "beta-guide-btn" },
        ...{ style: {} },
        title: "Open Beta Checklist",
    });
    /** @type {__VLS_StyleScopedClasses['beta-guide-btn']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.showFeedbackModal = true;
            // @ts-ignore
            [showFeedbackModal,];
        } },
    ...{ class: "feedback-btn" },
    title: "Send Feedback (F)",
});
/** @type {__VLS_StyleScopedClasses['feedback-btn']} */ ;
if (__VLS_ctx.auth.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "user-menu" },
    });
    /** @type {__VLS_StyleScopedClasses['user-menu']} */ ;
    let __VLS_54;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_55 = __VLS_asFunctionalComponent1(__VLS_54, new __VLS_54({
        to: "/profile",
        ...{ class: "user-menu-item" },
        title: "Profile",
    }));
    const __VLS_56 = __VLS_55({
        to: "/profile",
        ...{ class: "user-menu-item" },
        title: "Profile",
    }, ...__VLS_functionalComponentArgsRest(__VLS_55));
    /** @type {__VLS_StyleScopedClasses['user-menu-item']} */ ;
    const { default: __VLS_59 } = __VLS_57.slots;
    // @ts-ignore
    [auth,];
    var __VLS_57;
    let __VLS_60;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent1(__VLS_60, new __VLS_60({
        to: "/settings",
        ...{ class: "user-menu-item" },
        title: "Settings",
    }));
    const __VLS_62 = __VLS_61({
        to: "/settings",
        ...{ class: "user-menu-item" },
        title: "Settings",
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    /** @type {__VLS_StyleScopedClasses['user-menu-item']} */ ;
    const { default: __VLS_65 } = __VLS_63.slots;
    // @ts-ignore
    [];
    var __VLS_63;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.auth.isLoggedIn))
                    return;
                __VLS_ctx.auth.logout();
                __VLS_ctx.$router.push('/login');
                // @ts-ignore
                [auth, $router,];
            } },
        ...{ class: "user-menu-item logout-btn" },
        title: "Log out",
    });
    /** @type {__VLS_StyleScopedClasses['user-menu-item']} */ ;
    /** @type {__VLS_StyleScopedClasses['logout-btn']} */ ;
}
const __VLS_66 = QuotaWarningBanner;
// @ts-ignore
const __VLS_67 = __VLS_asFunctionalComponent1(__VLS_66, new __VLS_66({}));
const __VLS_68 = __VLS_67({}, ...__VLS_functionalComponentArgsRest(__VLS_67));
__VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "app-main" },
});
/** @type {__VLS_StyleScopedClasses['app-main']} */ ;
let __VLS_71;
/** @ts-ignore @type { | typeof __VLS_components.RouterView} */
RouterView;
// @ts-ignore
const __VLS_72 = __VLS_asFunctionalComponent1(__VLS_71, new __VLS_71({}));
const __VLS_73 = __VLS_72({}, ...__VLS_functionalComponentArgsRest(__VLS_72));
__VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
    ...{ class: "app-footer" },
});
/** @type {__VLS_StyleScopedClasses['app-footer']} */ ;
(new Date().getFullYear());
const __VLS_76 = FeedbackModal;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent1(__VLS_76, new __VLS_76({
    ...{ 'onSubmitted': {} },
    visible: (__VLS_ctx.showFeedbackModal),
}));
const __VLS_78 = __VLS_77({
    ...{ 'onSubmitted': {} },
    visible: (__VLS_ctx.showFeedbackModal),
}, ...__VLS_functionalComponentArgsRest(__VLS_77));
let __VLS_81;
const __VLS_82 = ({ submitted: {} },
    { onSubmitted: (__VLS_ctx.handleFeedbackSubmit) });
var __VLS_79;
var __VLS_80;
const __VLS_83 = BetaChecklistModal;
// @ts-ignore
const __VLS_84 = __VLS_asFunctionalComponent1(__VLS_83, new __VLS_83({
    visible: (__VLS_ctx.showBetaChecklist),
}));
const __VLS_85 = __VLS_84({
    visible: (__VLS_ctx.showBetaChecklist),
}, ...__VLS_functionalComponentArgsRest(__VLS_84));
// @ts-ignore
[showBetaChecklist, showFeedbackModal, handleFeedbackSubmit,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
