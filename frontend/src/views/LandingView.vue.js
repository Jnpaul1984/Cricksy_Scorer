/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { RouterLink } from 'vue-router';
import logoAvif1024 from '@/assets/optimized/logo-w1024.avif';
import logoWebp1024 from '@/assets/optimized/logo-w1024.webp';
import logoAvif1440 from '@/assets/optimized/logo-w1440.avif';
import logoWebp1440 from '@/assets/optimized/logo-w1440.webp';
import logoAvif480 from '@/assets/optimized/logo-w480.avif';
import logoWebp480 from '@/assets/optimized/logo-w480.webp';
import logoAvif768 from '@/assets/optimized/logo-w768.avif';
import logoWebp768 from '@/assets/optimized/logo-w768.webp';
const logoSources = [
    { width: 480, avif: logoAvif480, webp: logoWebp480 },
    { width: 768, avif: logoAvif768, webp: logoWebp768 },
    { width: 1024, avif: logoAvif1024, webp: logoWebp1024 },
    { width: 1440, avif: logoAvif1440, webp: logoWebp1440 },
];
const logoAvifSrcset = logoSources.map((src) => `${src.avif} ${src.width}w`).join(', ');
const logoWebpSrcset = logoSources.map((src) => `${src.webp} ${src.width}w`).join(', ');
const logoFallbackSrc = logoSources.find((src) => src.width === 768)?.webp ?? logoSources[0].webp;
const personas = [
    {
        icon: '📋',
        title: 'Scorers',
        description: 'Intuitive ball-by-ball scoring with real-time sync and offline support.',
    },
    {
        icon: '🎯',
        title: 'Coaches',
        description: 'Advanced analytics, player performance tracking, and tactical insights.',
    },
    {
        icon: '📊',
        title: 'Analysts',
        description: 'ML-powered predictions, historical data, and exportable reports.',
    },
    {
        icon: '🏏',
        title: 'Fans',
        description: 'Follow live matches, track favorite players, and view leaderboards.',
    },
];
const steps = [
    {
        step: 1,
        title: 'Create a Match',
        description: 'Set up teams, players, and match format in seconds.',
    },
    {
        step: 2,
        title: 'Score Live',
        description: 'Record every ball with our streamlined scoring interface.',
    },
    {
        step: 3,
        title: 'Share & Analyze',
        description: 'Broadcast live scoreboards and dive into rich analytics.',
    },
];
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hero-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['persona-card']} */ ;
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-title']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-tagline']} */ ;
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
/** @type {__VLS_StyleScopedClasses['personas']} */ ;
/** @type {__VLS_StyleScopedClasses['how-it-works']} */ ;
/** @type {__VLS_StyleScopedClasses['cta']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "landing" },
});
/** @type {__VLS_StyleScopedClasses['landing']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "hero" },
});
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-content" },
});
/** @type {__VLS_StyleScopedClasses['hero-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.picture, __VLS_intrinsics.picture)({
    ...{ class: "hero-logo" },
});
/** @type {__VLS_StyleScopedClasses['hero-logo']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.source)({
    srcset: (__VLS_ctx.logoAvifSrcset),
    sizes: "120px",
    type: "image/avif",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.source)({
    srcset: (__VLS_ctx.logoWebpSrcset),
    sizes: "120px",
    type: "image/webp",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.img)({
    src: (__VLS_ctx.logoFallbackSrc),
    sizes: "120px",
    alt: "Cricksy Mascot",
    loading: "eager",
    decoding: "async",
    width: "120",
    height: "120",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({
    ...{ class: "hero-title" },
});
/** @type {__VLS_StyleScopedClasses['hero-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "hero-tagline" },
});
/** @type {__VLS_StyleScopedClasses['hero-tagline']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-actions" },
});
/** @type {__VLS_StyleScopedClasses['hero-actions']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "/login",
    ...{ class: "btn btn-primary" },
}));
const __VLS_2 = __VLS_1({
    to: "/login",
    ...{ class: "btn btn-primary" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
// @ts-ignore
[logoAvifSrcset, logoWebpSrcset, logoFallbackSrc,];
var __VLS_3;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    to: "/fan",
    ...{ class: "btn btn-secondary" },
}));
const __VLS_8 = __VLS_7({
    to: "/fan",
    ...{ class: "btn btn-secondary" },
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
const { default: __VLS_11 } = __VLS_9.slots;
// @ts-ignore
[];
var __VLS_9;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "personas" },
});
/** @type {__VLS_StyleScopedClasses['personas']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "personas-grid" },
});
/** @type {__VLS_StyleScopedClasses['personas-grid']} */ ;
for (const [persona] of __VLS_vFor((__VLS_ctx.personas))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (persona.title),
        ...{ class: "persona-card" },
    });
    /** @type {__VLS_StyleScopedClasses['persona-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "persona-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['persona-icon']} */ ;
    (persona.icon);
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "persona-title" },
    });
    /** @type {__VLS_StyleScopedClasses['persona-title']} */ ;
    (persona.title);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "persona-desc" },
    });
    /** @type {__VLS_StyleScopedClasses['persona-desc']} */ ;
    (persona.description);
    // @ts-ignore
    [personas,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "how-it-works" },
});
/** @type {__VLS_StyleScopedClasses['how-it-works']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "steps-grid" },
});
/** @type {__VLS_StyleScopedClasses['steps-grid']} */ ;
for (const [item] of __VLS_vFor((__VLS_ctx.steps))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (item.step),
        ...{ class: "step-card" },
    });
    /** @type {__VLS_StyleScopedClasses['step-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "step-number" },
    });
    /** @type {__VLS_StyleScopedClasses['step-number']} */ ;
    (item.step);
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "step-title" },
    });
    /** @type {__VLS_StyleScopedClasses['step-title']} */ ;
    (item.title);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "step-desc" },
    });
    /** @type {__VLS_StyleScopedClasses['step-desc']} */ ;
    (item.description);
    // @ts-ignore
    [steps,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "cta" },
});
/** @type {__VLS_StyleScopedClasses['cta']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "cta-title" },
});
/** @type {__VLS_StyleScopedClasses['cta-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "cta-actions" },
});
/** @type {__VLS_StyleScopedClasses['cta-actions']} */ ;
let __VLS_12;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
    to: "/login",
    ...{ class: "btn btn-primary" },
}));
const __VLS_14 = __VLS_13({
    to: "/login",
    ...{ class: "btn btn-primary" },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
const { default: __VLS_17 } = __VLS_15.slots;
// @ts-ignore
[];
var __VLS_15;
let __VLS_18;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
    to: "/fan",
    ...{ class: "btn btn-ghost" },
}));
const __VLS_20 = __VLS_19({
    to: "/fan",
    ...{ class: "btn btn-ghost" },
}, ...__VLS_functionalComponentArgsRest(__VLS_19));
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-ghost']} */ ;
const { default: __VLS_23 } = __VLS_21.slots;
// @ts-ignore
[];
var __VLS_21;
let __VLS_24;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
    to: "/pricing",
    ...{ class: "btn btn-ghost" },
}));
const __VLS_26 = __VLS_25({
    to: "/pricing",
    ...{ class: "btn btn-ghost" },
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
/** @type {__VLS_StyleScopedClasses['btn']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-ghost']} */ ;
const { default: __VLS_29 } = __VLS_27.slots;
// @ts-ignore
[];
var __VLS_27;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
