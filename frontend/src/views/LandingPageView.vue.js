/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { BaseCard, BaseButton, BaseBadge } from '@/components';
import ScoreboardWidget from '@/components/ScoreboardWidget.vue';
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-content']} */ ;
/** @type {__VLS_StyleScopedClasses['feature']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['pricing-tile-header']} */ ;
/** @type {__VLS_StyleScopedClasses['live-demo']} */ ;
/** @type {__VLS_StyleScopedClasses['why-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['why-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
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
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-actions" },
});
/** @type {__VLS_StyleScopedClasses['hero-actions']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push({ path: '/auth/register', query: { plan: 'free' } });
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[];
var __VLS_3;
var __VLS_4;
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "lg",
}));
const __VLS_10 = __VLS_9({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "lg",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push({ name: 'PricingPage' });
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_15 } = __VLS_11.slots;
// @ts-ignore
[];
var __VLS_11;
var __VLS_12;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "hero-visual" },
});
/** @type {__VLS_StyleScopedClasses['hero-visual']} */ ;
let __VLS_16;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
    padding: "lg",
    ...{ class: "hero-demo" },
}));
const __VLS_18 = __VLS_17({
    padding: "lg",
    ...{ class: "hero-demo" },
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
/** @type {__VLS_StyleScopedClasses['hero-demo']} */ ;
const { default: __VLS_21 } = __VLS_19.slots;
const __VLS_22 = ScoreboardWidget;
// @ts-ignore
const __VLS_23 = __VLS_asFunctionalComponent1(__VLS_22, new __VLS_22({
    gameId: "demo",
    canControl: (false),
}));
const __VLS_24 = __VLS_23({
    gameId: "demo",
    canControl: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_23));
// @ts-ignore
[];
var __VLS_19;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "trust" },
});
/** @type {__VLS_StyleScopedClasses['trust']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "trust-title" },
});
/** @type {__VLS_StyleScopedClasses['trust-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "trust-logos" },
});
/** @type {__VLS_StyleScopedClasses['trust-logos']} */ ;
let __VLS_27;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_28 = __VLS_asFunctionalComponent1(__VLS_27, new __VLS_27({
    variant: "neutral",
}));
const __VLS_29 = __VLS_28({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_28));
const { default: __VLS_32 } = __VLS_30.slots;
// @ts-ignore
[];
var __VLS_30;
let __VLS_33;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_34 = __VLS_asFunctionalComponent1(__VLS_33, new __VLS_33({
    variant: "neutral",
}));
const __VLS_35 = __VLS_34({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_34));
const { default: __VLS_38 } = __VLS_36.slots;
// @ts-ignore
[];
var __VLS_36;
let __VLS_39;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_40 = __VLS_asFunctionalComponent1(__VLS_39, new __VLS_39({
    variant: "neutral",
}));
const __VLS_41 = __VLS_40({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_40));
const { default: __VLS_44 } = __VLS_42.slots;
// @ts-ignore
[];
var __VLS_42;
let __VLS_45;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_46 = __VLS_asFunctionalComponent1(__VLS_45, new __VLS_45({
    variant: "neutral",
}));
const __VLS_47 = __VLS_46({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_46));
const { default: __VLS_50 } = __VLS_48.slots;
// @ts-ignore
[];
var __VLS_48;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "features-grid" },
});
/** @type {__VLS_StyleScopedClasses['features-grid']} */ ;
let __VLS_51;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_52 = __VLS_asFunctionalComponent1(__VLS_51, new __VLS_51({
    ...{ class: "feature" },
}));
const __VLS_53 = __VLS_52({
    ...{ class: "feature" },
}, ...__VLS_functionalComponentArgsRest(__VLS_52));
/** @type {__VLS_StyleScopedClasses['feature']} */ ;
const { default: __VLS_56 } = __VLS_54.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_54;
let __VLS_57;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_58 = __VLS_asFunctionalComponent1(__VLS_57, new __VLS_57({
    ...{ class: "feature" },
}));
const __VLS_59 = __VLS_58({
    ...{ class: "feature" },
}, ...__VLS_functionalComponentArgsRest(__VLS_58));
/** @type {__VLS_StyleScopedClasses['feature']} */ ;
const { default: __VLS_62 } = __VLS_60.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_60;
let __VLS_63;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_64 = __VLS_asFunctionalComponent1(__VLS_63, new __VLS_63({
    ...{ class: "feature" },
}));
const __VLS_65 = __VLS_64({
    ...{ class: "feature" },
}, ...__VLS_functionalComponentArgsRest(__VLS_64));
/** @type {__VLS_StyleScopedClasses['feature']} */ ;
const { default: __VLS_68 } = __VLS_66.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_66;
let __VLS_69;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_70 = __VLS_asFunctionalComponent1(__VLS_69, new __VLS_69({
    ...{ class: "feature" },
}));
const __VLS_71 = __VLS_70({
    ...{ class: "feature" },
}, ...__VLS_functionalComponentArgsRest(__VLS_70));
/** @type {__VLS_StyleScopedClasses['feature']} */ ;
const { default: __VLS_74 } = __VLS_72.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_72;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "pricing-preview" },
});
/** @type {__VLS_StyleScopedClasses['pricing-preview']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing-preview-grid" },
});
/** @type {__VLS_StyleScopedClasses['pricing-preview-grid']} */ ;
let __VLS_75;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_76 = __VLS_asFunctionalComponent1(__VLS_75, new __VLS_75({
    ...{ class: "pricing-tile" },
}));
const __VLS_77 = __VLS_76({
    ...{ class: "pricing-tile" },
}, ...__VLS_functionalComponentArgsRest(__VLS_76));
/** @type {__VLS_StyleScopedClasses['pricing-tile']} */ ;
const { default: __VLS_80 } = __VLS_78.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing-tile-header" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
let __VLS_81;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_82 = __VLS_asFunctionalComponent1(__VLS_81, new __VLS_81({
    variant: "neutral",
}));
const __VLS_83 = __VLS_82({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_82));
const { default: __VLS_86 } = __VLS_84.slots;
// @ts-ignore
[];
var __VLS_84;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-copy" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-copy']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-price" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-price']} */ ;
let __VLS_87;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_88 = __VLS_asFunctionalComponent1(__VLS_87, new __VLS_87({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_89 = __VLS_88({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_88));
let __VLS_92;
const __VLS_93 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push({ path: '/auth/register', query: { plan: 'free' } });
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_94 } = __VLS_90.slots;
// @ts-ignore
[];
var __VLS_90;
var __VLS_91;
// @ts-ignore
[];
var __VLS_78;
let __VLS_95;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_96 = __VLS_asFunctionalComponent1(__VLS_95, new __VLS_95({
    ...{ class: "pricing-tile" },
}));
const __VLS_97 = __VLS_96({
    ...{ class: "pricing-tile" },
}, ...__VLS_functionalComponentArgsRest(__VLS_96));
/** @type {__VLS_StyleScopedClasses['pricing-tile']} */ ;
const { default: __VLS_100 } = __VLS_98.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing-tile-header" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
let __VLS_101;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_102 = __VLS_asFunctionalComponent1(__VLS_101, new __VLS_101({
    variant: "primary",
}));
const __VLS_103 = __VLS_102({
    variant: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_102));
const { default: __VLS_106 } = __VLS_104.slots;
// @ts-ignore
[];
var __VLS_104;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-copy" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-copy']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-price" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-price']} */ ;
let __VLS_107;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_108 = __VLS_asFunctionalComponent1(__VLS_107, new __VLS_107({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_109 = __VLS_108({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_108));
let __VLS_112;
const __VLS_113 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push({ name: 'PricingPage' });
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_114 } = __VLS_110.slots;
// @ts-ignore
[];
var __VLS_110;
var __VLS_111;
// @ts-ignore
[];
var __VLS_98;
let __VLS_115;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_116 = __VLS_asFunctionalComponent1(__VLS_115, new __VLS_115({
    ...{ class: "pricing-tile" },
}));
const __VLS_117 = __VLS_116({
    ...{ class: "pricing-tile" },
}, ...__VLS_functionalComponentArgsRest(__VLS_116));
/** @type {__VLS_StyleScopedClasses['pricing-tile']} */ ;
const { default: __VLS_120 } = __VLS_118.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pricing-tile-header" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
let __VLS_121;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_122 = __VLS_asFunctionalComponent1(__VLS_121, new __VLS_121({
    variant: "success",
}));
const __VLS_123 = __VLS_122({
    variant: "success",
}, ...__VLS_functionalComponentArgsRest(__VLS_122));
const { default: __VLS_126 } = __VLS_124.slots;
// @ts-ignore
[];
var __VLS_124;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-copy" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-copy']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "pricing-tile-price" },
});
/** @type {__VLS_StyleScopedClasses['pricing-tile-price']} */ ;
let __VLS_127;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_128 = __VLS_asFunctionalComponent1(__VLS_127, new __VLS_127({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}));
const __VLS_129 = __VLS_128({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_128));
let __VLS_132;
const __VLS_133 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push({ name: 'PricingPage', query: { plan: 'org-starter' } });
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_134 } = __VLS_130.slots;
// @ts-ignore
[];
var __VLS_130;
var __VLS_131;
// @ts-ignore
[];
var __VLS_118;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "live-demo" },
});
/** @type {__VLS_StyleScopedClasses['live-demo']} */ ;
let __VLS_135;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_136 = __VLS_asFunctionalComponent1(__VLS_135, new __VLS_135({
    padding: "lg",
    ...{ class: "demo-card" },
}));
const __VLS_137 = __VLS_136({
    padding: "lg",
    ...{ class: "demo-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_136));
/** @type {__VLS_StyleScopedClasses['demo-card']} */ ;
const { default: __VLS_140 } = __VLS_138.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
const __VLS_141 = ScoreboardWidget;
// @ts-ignore
const __VLS_142 = __VLS_asFunctionalComponent1(__VLS_141, new __VLS_141({
    gameId: "demo",
    canControl: (false),
    ...{ class: "live-demo-widget" },
}));
const __VLS_143 = __VLS_142({
    gameId: "demo",
    canControl: (false),
    ...{ class: "live-demo-widget" },
}, ...__VLS_functionalComponentArgsRest(__VLS_142));
/** @type {__VLS_StyleScopedClasses['live-demo-widget']} */ ;
// @ts-ignore
[];
var __VLS_138;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "why" },
});
/** @type {__VLS_StyleScopedClasses['why']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "why-grid" },
});
/** @type {__VLS_StyleScopedClasses['why-grid']} */ ;
let __VLS_146;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_147 = __VLS_asFunctionalComponent1(__VLS_146, new __VLS_146({}));
const __VLS_148 = __VLS_147({}, ...__VLS_functionalComponentArgsRest(__VLS_147));
const { default: __VLS_151 } = __VLS_149.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_149;
let __VLS_152;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_153 = __VLS_asFunctionalComponent1(__VLS_152, new __VLS_152({}));
const __VLS_154 = __VLS_153({}, ...__VLS_functionalComponentArgsRest(__VLS_153));
const { default: __VLS_157 } = __VLS_155.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_155;
let __VLS_158;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_159 = __VLS_asFunctionalComponent1(__VLS_158, new __VLS_158({}));
const __VLS_160 = __VLS_159({}, ...__VLS_functionalComponentArgsRest(__VLS_159));
const { default: __VLS_163 } = __VLS_161.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_161;
let __VLS_164;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_165 = __VLS_asFunctionalComponent1(__VLS_164, new __VLS_164({}));
const __VLS_166 = __VLS_165({}, ...__VLS_functionalComponentArgsRest(__VLS_165));
const { default: __VLS_169 } = __VLS_167.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_167;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "final-cta" },
});
/** @type {__VLS_StyleScopedClasses['final-cta']} */ ;
let __VLS_170;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_171 = __VLS_asFunctionalComponent1(__VLS_170, new __VLS_170({
    padding: "lg",
    ...{ class: "final-card" },
}));
const __VLS_172 = __VLS_171({
    padding: "lg",
    ...{ class: "final-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_171));
/** @type {__VLS_StyleScopedClasses['final-card']} */ ;
const { default: __VLS_175 } = __VLS_173.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
let __VLS_176;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_177 = __VLS_asFunctionalComponent1(__VLS_176, new __VLS_176({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}));
const __VLS_178 = __VLS_177({
    ...{ 'onClick': {} },
    variant: "primary",
    size: "lg",
}, ...__VLS_functionalComponentArgsRest(__VLS_177));
let __VLS_181;
const __VLS_182 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.$router.push('/auth/register');
            // @ts-ignore
            [$router,];
        } });
const { default: __VLS_183 } = __VLS_179.slots;
// @ts-ignore
[];
var __VLS_179;
var __VLS_180;
// @ts-ignore
[];
var __VLS_173;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
