/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { BaseCard } from '@/components';
import { fmtEconomy, oversDisplayFromBalls } from '@/utils/cricket';
const props = defineProps();
function econ(e) {
    const given = Number(e.economy);
    if (Number.isFinite(given) && given > 0)
        return given.toFixed(2);
    const balls = Number(e.balls_bowled);
    if (Number.isFinite(balls) && balls > 0)
        return fmtEconomy(Number(e.runs_conceded) || 0, balls);
    // Fallback from overs decimal, e.g. 3.4 → 22 balls
    const ob = Number(e.overs_bowled);
    if (!Number.isFinite(ob) || ob <= 0)
        return '—';
    const whole = Math.trunc(ob);
    const fracBalls = Math.round((ob - whole) * 10);
    const ballsFromOvers = whole * 6 + Math.min(5, Math.max(0, fracBalls));
    return fmtEconomy(Number(e.runs_conceded) || 0, ballsFromOvers);
}
function oversText(e) {
    const balls = Number(e.balls_bowled);
    if (Number.isFinite(balls) && balls >= 0)
        return oversDisplayFromBalls(balls);
    const ob = Number(e.overs_bowled);
    if (!Number.isFinite(ob))
        return '0.0';
    return ob.toFixed(1);
}
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "section",
    padding: "md",
    ...{ class: "bowling-card" },
}));
const __VLS_2 = __VLS_1({
    as: "section",
    padding: "md",
    ...{ class: "bowling-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['bowling-card']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
if (props.entries.length) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [e] of __VLS_vFor((props.entries))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (e.player_id),
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "name" },
        });
        /** @type {__VLS_StyleScopedClasses['name']} */ ;
        (e.player_name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (__VLS_ctx.oversText(e));
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (Number(e.maidens) || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (Number(e.runs_conceded) || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (Number(e.wickets_taken) || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (__VLS_ctx.econ(e));
        // @ts-ignore
        [oversText, econ,];
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty" },
    });
    /** @type {__VLS_StyleScopedClasses['empty']} */ ;
}
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
