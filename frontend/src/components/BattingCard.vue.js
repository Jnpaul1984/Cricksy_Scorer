/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { BaseCard, BaseBadge } from '@/components';
import { isValidUUID } from '@/utils';
import { fmtSR } from '@/utils/cricket';
const props = withDefaults(defineProps(), {
    entries: () => [],
    strikerId: undefined,
    nonStrikerId: undefined,
});
/* ---------- helpers ---------- */
const i = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0;
};
const f = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
};
function sr(e) {
    const given = f(e.strike_rate);
    if (given > 0)
        return given.toFixed(1);
    return fmtSR(i(e.runs), i(e.balls_faced));
}
function status(e) {
    if (e.is_out)
        return e.how_out ? `Out (${e.how_out})` : 'Out';
    return 'Not out';
}
const rows = computed(() => (props.entries || []).map((e) => ({
    id: e.player_id,
    name: e.player_name,
    runs: i(e.runs),
    balls: i(e.balls_faced),
    fours: i(e.fours),
    sixes: i(e.sixes),
    sr: sr(e),
    status: status(e),
    isOut: !!e.is_out,
    isStriker: props.strikerId === e.player_id,
    isNonStriker: props.nonStrikerId === e.player_id,
})));
const __VLS_defaults = {
    entries: () => [],
    strikerId: undefined,
    nonStrikerId: undefined,
};
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['name']} */ ;
/** @type {__VLS_StyleScopedClasses['name']} */ ;
/** @type {__VLS_StyleScopedClasses['name']} */ ;
/** @type {__VLS_StyleScopedClasses['player-link']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "section",
    padding: "md",
    ...{ class: "batting-card" },
    'aria-label': "Batting card",
}));
const __VLS_2 = __VLS_1({
    as: "section",
    padding: "md",
    ...{ class: "batting-card" },
    'aria-label': "Batting card",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['batting-card']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
if (__VLS_ctx.rows.length) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.caption, __VLS_intrinsics.caption)({
        ...{ class: "visually-hidden" },
    });
    /** @type {__VLS_StyleScopedClasses['visually-hidden']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.colgroup, __VLS_intrinsics.colgroup)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({
        ...{ style: {} },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.col)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
        ...{ class: "num" },
    });
    /** @type {__VLS_StyleScopedClasses['num']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        scope: "col",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
    for (const [r] of __VLS_vFor((__VLS_ctx.rows))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
            key: (r.id),
            ...{ class: ([{ out: r.isOut, striker: r.isStriker, nonStriker: r.isNonStriker }]) },
        });
        /** @type {__VLS_StyleScopedClasses['out']} */ ;
        /** @type {__VLS_StyleScopedClasses['striker']} */ ;
        /** @type {__VLS_StyleScopedClasses['nonStriker']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "name" },
            title: (r.name),
        });
        /** @type {__VLS_StyleScopedClasses['name']} */ ;
        if (r.isStriker) {
            let __VLS_7;
            /** @ts-ignore @type { | typeof __VLS_components.BaseBadge | typeof __VLS_components.BaseBadge} */
            BaseBadge;
            // @ts-ignore
            const __VLS_8 = __VLS_asFunctionalComponent1(__VLS_7, new __VLS_7({
                variant: "primary",
                condensed: true,
                ...{ class: "strike-indicator" },
            }));
            const __VLS_9 = __VLS_8({
                variant: "primary",
                condensed: true,
                ...{ class: "strike-indicator" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_8));
            /** @type {__VLS_StyleScopedClasses['strike-indicator']} */ ;
            const { default: __VLS_12 } = __VLS_10.slots;
            // @ts-ignore
            [rows, rows,];
            var __VLS_10;
        }
        if (__VLS_ctx.isValidUUID(r.id)) {
            let __VLS_13;
            /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
            RouterLink;
            // @ts-ignore
            const __VLS_14 = __VLS_asFunctionalComponent1(__VLS_13, new __VLS_13({
                to: ({ name: 'PlayerProfile', params: { playerId: r.id } }),
                ...{ class: "player-link nameText" },
            }));
            const __VLS_15 = __VLS_14({
                to: ({ name: 'PlayerProfile', params: { playerId: r.id } }),
                ...{ class: "player-link nameText" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_14));
            /** @type {__VLS_StyleScopedClasses['player-link']} */ ;
            /** @type {__VLS_StyleScopedClasses['nameText']} */ ;
            const { default: __VLS_18 } = __VLS_16.slots;
            (r.name);
            // @ts-ignore
            [isValidUUID,];
            var __VLS_16;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "nameText" },
            });
            /** @type {__VLS_StyleScopedClasses['nameText']} */ ;
            (r.name);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (r.runs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (r.balls);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (r.fours);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (r.sixes);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "num" },
        });
        /** @type {__VLS_StyleScopedClasses['num']} */ ;
        (r.sr);
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "status" },
            title: (r.status),
        });
        /** @type {__VLS_StyleScopedClasses['status']} */ ;
        (r.status);
        // @ts-ignore
        [];
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
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
