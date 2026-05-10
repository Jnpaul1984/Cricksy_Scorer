/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref } from 'vue';
import { BaseButton, BaseCard, BaseBadge, BaseInput } from '@/components';
import EventOverlay from '@/components/EventOverlay.vue';
// Input demos
const demoInput = ref('');
const demoInputError = ref('');
const showInputError = ref(false);
// Overlay demo
const demoEvent = ref(null);
const demoOverlayVisible = ref(false);
function showOverlay(event) {
    demoEvent.value = event;
    demoOverlayVisible.value = true;
    // Auto-hide after 2 seconds
    setTimeout(() => {
        demoOverlayVisible.value = false;
    }, 2000);
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['ds-header']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-page" },
});
/** @type {__VLS_StyleScopedClasses['ds-page']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "section",
    padding: "lg",
    ...{ class: "ds-showcase" },
}));
const __VLS_2 = __VLS_1({
    as: "section",
    padding: "lg",
    ...{ class: "ds-showcase" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['ds-showcase']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "ds-header" },
});
/** @type {__VLS_StyleScopedClasses['ds-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "ds-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['ds-subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_6;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    variant: "primary",
}));
const __VLS_8 = __VLS_7({
    variant: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
const { default: __VLS_11 } = __VLS_9.slots;
var __VLS_9;
let __VLS_12;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
    variant: "secondary",
}));
const __VLS_14 = __VLS_13({
    variant: "secondary",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
const { default: __VLS_17 } = __VLS_15.slots;
var __VLS_15;
let __VLS_18;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
    variant: "ghost",
}));
const __VLS_20 = __VLS_19({
    variant: "ghost",
}, ...__VLS_functionalComponentArgsRest(__VLS_19));
const { default: __VLS_23 } = __VLS_21.slots;
var __VLS_21;
let __VLS_24;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
    variant: "danger",
}));
const __VLS_26 = __VLS_25({
    variant: "danger",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
const { default: __VLS_29 } = __VLS_27.slots;
var __VLS_27;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row ds-row--align-end" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-row--align-end']} */ ;
let __VLS_30;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_31 = __VLS_asFunctionalComponent1(__VLS_30, new __VLS_30({
    variant: "primary",
    size: "sm",
}));
const __VLS_32 = __VLS_31({
    variant: "primary",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_31));
const { default: __VLS_35 } = __VLS_33.slots;
var __VLS_33;
let __VLS_36;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
    variant: "primary",
    size: "md",
}));
const __VLS_38 = __VLS_37({
    variant: "primary",
    size: "md",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
const { default: __VLS_41 } = __VLS_39.slots;
var __VLS_39;
let __VLS_42;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
    variant: "primary",
    size: "lg",
}));
const __VLS_44 = __VLS_43({
    variant: "primary",
    size: "lg",
}, ...__VLS_functionalComponentArgsRest(__VLS_43));
const { default: __VLS_47 } = __VLS_45.slots;
var __VLS_45;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_48;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_49 = __VLS_asFunctionalComponent1(__VLS_48, new __VLS_48({
    variant: "primary",
    loading: true,
}));
const __VLS_50 = __VLS_49({
    variant: "primary",
    loading: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_49));
const { default: __VLS_53 } = __VLS_51.slots;
var __VLS_51;
let __VLS_54;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_55 = __VLS_asFunctionalComponent1(__VLS_54, new __VLS_54({
    variant: "secondary",
    disabled: true,
}));
const __VLS_56 = __VLS_55({
    variant: "secondary",
    disabled: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_55));
const { default: __VLS_59 } = __VLS_57.slots;
var __VLS_57;
let __VLS_60;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent1(__VLS_60, new __VLS_60({
    variant: "primary",
    fullWidth: true,
}));
const __VLS_62 = __VLS_61({
    variant: "primary",
    fullWidth: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
const { default: __VLS_65 } = __VLS_63.slots;
var __VLS_63;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_66;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_67 = __VLS_asFunctionalComponent1(__VLS_66, new __VLS_66({
    variant: "neutral",
}));
const __VLS_68 = __VLS_67({
    variant: "neutral",
}, ...__VLS_functionalComponentArgsRest(__VLS_67));
const { default: __VLS_71 } = __VLS_69.slots;
var __VLS_69;
let __VLS_72;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent1(__VLS_72, new __VLS_72({
    variant: "primary",
}));
const __VLS_74 = __VLS_73({
    variant: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
const { default: __VLS_77 } = __VLS_75.slots;
var __VLS_75;
let __VLS_78;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_79 = __VLS_asFunctionalComponent1(__VLS_78, new __VLS_78({
    variant: "success",
}));
const __VLS_80 = __VLS_79({
    variant: "success",
}, ...__VLS_functionalComponentArgsRest(__VLS_79));
const { default: __VLS_83 } = __VLS_81.slots;
var __VLS_81;
let __VLS_84;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_85 = __VLS_asFunctionalComponent1(__VLS_84, new __VLS_84({
    variant: "warning",
}));
const __VLS_86 = __VLS_85({
    variant: "warning",
}, ...__VLS_functionalComponentArgsRest(__VLS_85));
const { default: __VLS_89 } = __VLS_87.slots;
var __VLS_87;
let __VLS_90;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_91 = __VLS_asFunctionalComponent1(__VLS_90, new __VLS_90({
    variant: "danger",
}));
const __VLS_92 = __VLS_91({
    variant: "danger",
}, ...__VLS_functionalComponentArgsRest(__VLS_91));
const { default: __VLS_95 } = __VLS_93.slots;
var __VLS_93;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_96;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_97 = __VLS_asFunctionalComponent1(__VLS_96, new __VLS_96({
    variant: "primary",
    uppercase: (false),
}));
const __VLS_98 = __VLS_97({
    variant: "primary",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_97));
const { default: __VLS_101 } = __VLS_99.slots;
var __VLS_99;
let __VLS_102;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_103 = __VLS_asFunctionalComponent1(__VLS_102, new __VLS_102({
    variant: "success",
    uppercase: (false),
}));
const __VLS_104 = __VLS_103({
    variant: "success",
    uppercase: (false),
}, ...__VLS_functionalComponentArgsRest(__VLS_103));
const { default: __VLS_107 } = __VLS_105.slots;
var __VLS_105;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_108;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_109 = __VLS_asFunctionalComponent1(__VLS_108, new __VLS_108({
    variant: "primary",
    condensed: true,
}));
const __VLS_110 = __VLS_109({
    variant: "primary",
    condensed: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_109));
const { default: __VLS_113 } = __VLS_111.slots;
var __VLS_111;
let __VLS_114;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_115 = __VLS_asFunctionalComponent1(__VLS_114, new __VLS_114({
    variant: "success",
    condensed: true,
}));
const __VLS_116 = __VLS_115({
    variant: "success",
    condensed: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_115));
const { default: __VLS_119 } = __VLS_117.slots;
var __VLS_117;
let __VLS_120;
/** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
BaseBadge;
// @ts-ignore
const __VLS_121 = __VLS_asFunctionalComponent1(__VLS_120, new __VLS_120({
    variant: "danger",
    condensed: true,
}));
const __VLS_122 = __VLS_121({
    variant: "danger",
    condensed: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_121));
const { default: __VLS_125 } = __VLS_123.slots;
var __VLS_123;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-grid" },
});
/** @type {__VLS_StyleScopedClasses['ds-grid']} */ ;
let __VLS_126;
/** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
BaseInput;
// @ts-ignore
const __VLS_127 = __VLS_asFunctionalComponent1(__VLS_126, new __VLS_126({
    modelValue: (__VLS_ctx.demoInput),
    label: "Player Name",
    placeholder: "Enter player name",
    helpText: "This is helper text for the input.",
}));
const __VLS_128 = __VLS_127({
    modelValue: (__VLS_ctx.demoInput),
    label: "Player Name",
    placeholder: "Enter player name",
    helpText: "This is helper text for the input.",
}, ...__VLS_functionalComponentArgsRest(__VLS_127));
let __VLS_131;
/** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
BaseInput;
// @ts-ignore
const __VLS_132 = __VLS_asFunctionalComponent1(__VLS_131, new __VLS_131({
    modelValue: (__VLS_ctx.demoInputError),
    label: "Email Address",
    placeholder: "you@example.com",
    error: (__VLS_ctx.showInputError ? 'Please enter a valid email address.' : undefined),
}));
const __VLS_133 = __VLS_132({
    modelValue: (__VLS_ctx.demoInputError),
    label: "Email Address",
    placeholder: "you@example.com",
    error: (__VLS_ctx.showInputError ? 'Please enter a valid email address.' : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_132));
let __VLS_136;
/** @ts-ignore @type { | typeof __VLS_components.BaseInput} */
BaseInput;
// @ts-ignore
const __VLS_137 = __VLS_asFunctionalComponent1(__VLS_136, new __VLS_136({
    modelValue: "Readonly value",
    label: "Disabled Input",
    disabled: true,
}));
const __VLS_138 = __VLS_137({
    modelValue: "Readonly value",
    label: "Disabled Input",
    disabled: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_137));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_141;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_142 = __VLS_asFunctionalComponent1(__VLS_141, new __VLS_141({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}));
const __VLS_143 = __VLS_142({
    ...{ 'onClick': {} },
    variant: "secondary",
    size: "sm",
}, ...__VLS_functionalComponentArgsRest(__VLS_142));
let __VLS_146;
const __VLS_147 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showInputError = !__VLS_ctx.showInputError;
            // @ts-ignore
            [demoInput, demoInputError, showInputError, showInputError, showInputError,];
        } });
const { default: __VLS_148 } = __VLS_144.slots;
// @ts-ignore
[];
var __VLS_144;
var __VLS_145;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-grid ds-grid--cards" },
});
/** @type {__VLS_StyleScopedClasses['ds-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-grid--cards']} */ ;
let __VLS_149;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_150 = __VLS_asFunctionalComponent1(__VLS_149, new __VLS_149({
    padding: "md",
}));
const __VLS_151 = __VLS_150({
    padding: "md",
}, ...__VLS_functionalComponentArgsRest(__VLS_150));
const { default: __VLS_154 } = __VLS_152.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_152;
let __VLS_155;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_156 = __VLS_asFunctionalComponent1(__VLS_155, new __VLS_155({
    padding: "md",
    interactive: true,
}));
const __VLS_157 = __VLS_156({
    padding: "md",
    interactive: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_156));
const { default: __VLS_160 } = __VLS_158.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
// @ts-ignore
[];
var __VLS_158;
let __VLS_161;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_162 = __VLS_asFunctionalComponent1(__VLS_161, new __VLS_161({
    padding: "sm",
    ...{ class: "ds-stat-card" },
}));
const __VLS_163 = __VLS_162({
    padding: "sm",
    ...{ class: "ds-stat-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_162));
/** @type {__VLS_StyleScopedClasses['ds-stat-card']} */ ;
const { default: __VLS_166 } = __VLS_164.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-stat-value" },
});
/** @type {__VLS_StyleScopedClasses['ds-stat-value']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-stat-label" },
});
/** @type {__VLS_StyleScopedClasses['ds-stat-label']} */ ;
// @ts-ignore
[];
var __VLS_164;
let __VLS_167;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_168 = __VLS_asFunctionalComponent1(__VLS_167, new __VLS_167({
    padding: "sm",
    ...{ class: "ds-stat-card" },
}));
const __VLS_169 = __VLS_168({
    padding: "sm",
    ...{ class: "ds-stat-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_168));
/** @type {__VLS_StyleScopedClasses['ds-stat-card']} */ ;
const { default: __VLS_172 } = __VLS_170.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-stat-value" },
});
/** @type {__VLS_StyleScopedClasses['ds-stat-value']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-stat-label" },
});
/** @type {__VLS_StyleScopedClasses['ds-stat-label']} */ ;
// @ts-ignore
[];
var __VLS_170;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
let __VLS_173;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_174 = __VLS_asFunctionalComponent1(__VLS_173, new __VLS_173({
    padding: "md",
    ...{ class: "ds-scoreboard-placeholder" },
}));
const __VLS_175 = __VLS_174({
    padding: "md",
    ...{ class: "ds-scoreboard-placeholder" },
}, ...__VLS_functionalComponentArgsRest(__VLS_174));
/** @type {__VLS_StyleScopedClasses['ds-scoreboard-placeholder']} */ ;
const { default: __VLS_178 } = __VLS_176.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "ds-placeholder-text" },
});
/** @type {__VLS_StyleScopedClasses['ds-placeholder-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.br)({});
// @ts-ignore
[];
var __VLS_176;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-overlay-demo" },
});
/** @type {__VLS_StyleScopedClasses['ds-overlay-demo']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-overlay-container" },
});
/** @type {__VLS_StyleScopedClasses['ds-overlay-container']} */ ;
const __VLS_179 = EventOverlay;
// @ts-ignore
const __VLS_180 = __VLS_asFunctionalComponent1(__VLS_179, new __VLS_179({
    event: (__VLS_ctx.demoEvent),
    visible: (__VLS_ctx.demoOverlayVisible),
}));
const __VLS_181 = __VLS_180({
    event: (__VLS_ctx.demoEvent),
    visible: (__VLS_ctx.demoOverlayVisible),
}, ...__VLS_functionalComponentArgsRest(__VLS_180));
if (!__VLS_ctx.demoOverlayVisible) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "ds-overlay-placeholder" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-overlay-placeholder']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-row" },
});
/** @type {__VLS_StyleScopedClasses['ds-row']} */ ;
let __VLS_184;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_185 = __VLS_asFunctionalComponent1(__VLS_184, new __VLS_184({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "primary",
}));
const __VLS_186 = __VLS_185({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_185));
let __VLS_189;
const __VLS_190 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showOverlay('FOUR');
            // @ts-ignore
            [demoEvent, demoOverlayVisible, demoOverlayVisible, showOverlay,];
        } });
const { default: __VLS_191 } = __VLS_187.slots;
// @ts-ignore
[];
var __VLS_187;
var __VLS_188;
let __VLS_192;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_193 = __VLS_asFunctionalComponent1(__VLS_192, new __VLS_192({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "primary",
}));
const __VLS_194 = __VLS_193({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "primary",
}, ...__VLS_functionalComponentArgsRest(__VLS_193));
let __VLS_197;
const __VLS_198 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showOverlay('SIX');
            // @ts-ignore
            [showOverlay,];
        } });
const { default: __VLS_199 } = __VLS_195.slots;
// @ts-ignore
[];
var __VLS_195;
var __VLS_196;
let __VLS_200;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_201 = __VLS_asFunctionalComponent1(__VLS_200, new __VLS_200({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "danger",
}));
const __VLS_202 = __VLS_201({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "danger",
}, ...__VLS_functionalComponentArgsRest(__VLS_201));
let __VLS_205;
const __VLS_206 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showOverlay('WICKET');
            // @ts-ignore
            [showOverlay,];
        } });
const { default: __VLS_207 } = __VLS_203.slots;
// @ts-ignore
[];
var __VLS_203;
var __VLS_204;
let __VLS_208;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_209 = __VLS_asFunctionalComponent1(__VLS_208, new __VLS_208({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "secondary",
}));
const __VLS_210 = __VLS_209({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "secondary",
}, ...__VLS_functionalComponentArgsRest(__VLS_209));
let __VLS_213;
const __VLS_214 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showOverlay('FIFTY');
            // @ts-ignore
            [showOverlay,];
        } });
const { default: __VLS_215 } = __VLS_211.slots;
// @ts-ignore
[];
var __VLS_211;
var __VLS_212;
let __VLS_216;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_217 = __VLS_asFunctionalComponent1(__VLS_216, new __VLS_216({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "secondary",
}));
const __VLS_218 = __VLS_217({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "secondary",
}, ...__VLS_functionalComponentArgsRest(__VLS_217));
let __VLS_221;
const __VLS_222 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showOverlay('HUNDRED');
            // @ts-ignore
            [showOverlay,];
        } });
const { default: __VLS_223 } = __VLS_219.slots;
// @ts-ignore
[];
var __VLS_219;
var __VLS_220;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "ds-section" },
});
/** @type {__VLS_StyleScopedClasses['ds-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-grid" },
});
/** @type {__VLS_StyleScopedClasses['ds-color-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "ds-color-swatch" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['ds-color-swatch']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
