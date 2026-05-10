/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, watch, computed, nextTick } from 'vue';
import { BaseCard, BaseButton } from '@/components';
const props = withDefaults(defineProps(), {
    modelValue: () => [],
    label: 'Players',
    teamName: '',
    max: 16,
    min: 2,
    placeholder: 'Type a name and press Enter (or paste a comma/newline list)…',
});
const emit = defineEmits();
const names = ref([...props.modelValue]);
const quick = ref('');
const warn = ref(null);
// keep local in sync if parent replaces the array
watch(() => props.modelValue, v => { names.value = [...v]; }, { deep: true });
// normalize + de-dupe (case-insensitive), strip empties
function normalize(list) {
    const out = [];
    const seen = new Set();
    for (const raw of list) {
        const n = raw.trim().replace(/\s+/g, ' ');
        if (!n)
            continue;
        const key = n.toLowerCase();
        if (seen.has(key))
            continue;
        seen.add(key);
        out.push(n);
    }
    return out;
}
function cap(list) {
    if (list.length <= props.max)
        return list;
    warn.value = `Only the first ${props.max} players are kept (limit reached).`;
    return list.slice(0, props.max);
}
function commit(list) {
    const cleaned = cap(normalize(list));
    names.value = cleaned;
    emit('update:modelValue', cleaned);
    emit('change', cleaned);
}
// row edits
function updateAt(i, val) {
    const draft = [...names.value];
    draft[i] = val;
    commit(draft);
}
function removeAt(i) {
    const draft = [...names.value];
    draft.splice(i, 1);
    commit(draft);
}
function move(i, dir) {
    const j = i + dir;
    if (j < 0 || j >= names.value.length)
        return;
    const draft = [...names.value];
    const [it] = draft.splice(i, 1);
    draft.splice(j, 0, it);
    commit(draft);
}
// adding
function addManyFromText(text) {
    const chunks = text.split(/[\n,;]+/g).map(s => s.trim()).filter(Boolean);
    const merged = [...names.value, ...chunks];
    commit(merged);
}
async function handleQuickEnter() {
    if (!quick.value.trim())
        return;
    addManyFromText(quick.value);
    quick.value = '';
    await nextTick();
}
function onQuickPaste(e) {
    const text = e.clipboardData?.getData('text') || '';
    if (!text)
        return;
    e.preventDefault();
    addManyFromText(text);
    quick.value = '';
}
const count = computed(() => names.value.length);
const shortfall = computed(() => Math.max(0, props.min - count.value));
const __VLS_defaults = {
    modelValue: () => [],
    label: 'Players',
    teamName: '',
    max: 16,
    min: 2,
    placeholder: 'Type a name and press Enter (or paste a comma/newline list)…',
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
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
BaseCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    as: "section",
    ...{ class: "pe" },
    dataTestid: (`players-editor-${(__VLS_ctx.teamName || 'team').replace(/\\s+/g, '-').toLowerCase()}`),
}));
const __VLS_2 = __VLS_1({
    as: "section",
    ...{ class: "pe" },
    dataTestid: (`players-editor-${(__VLS_ctx.teamName || 'team').replace(/\\s+/g, '-').toLowerCase()}`),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['pe']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "pe-head" },
});
/** @type {__VLS_StyleScopedClasses['pe-head']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "title" },
});
/** @type {__VLS_StyleScopedClasses['title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
(__VLS_ctx.label);
if (__VLS_ctx.teamName) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "muted" },
    });
    /** @type {__VLS_StyleScopedClasses['muted']} */ ;
    (__VLS_ctx.teamName);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "count" },
});
/** @type {__VLS_StyleScopedClasses['count']} */ ;
(__VLS_ctx.count);
(__VLS_ctx.max);
if (__VLS_ctx.shortfall) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "need" },
    });
    /** @type {__VLS_StyleScopedClasses['need']} */ ;
    (__VLS_ctx.shortfall);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "list" },
});
/** @type {__VLS_StyleScopedClasses['list']} */ ;
for (const [n, i] of __VLS_vFor((__VLS_ctx.names))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (i),
        ...{ class: "row" },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "idx" },
    });
    /** @type {__VLS_StyleScopedClasses['idx']} */ ;
    (i + 1);
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        ...{ onInput: (...[$event]) => {
                __VLS_ctx.updateAt(i, $event.target.value);
                // @ts-ignore
                [teamName, teamName, teamName, label, count, max, shortfall, shortfall, names, updateAt,];
            } },
        ...{ class: "input" },
        placeholder: (`Player #${i + 1}`),
        value: (n),
    });
    /** @type {__VLS_StyleScopedClasses['input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    let __VLS_7;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_8 = __VLS_asFunctionalComponent1(__VLS_7, new __VLS_7({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        title: "Move up",
        disabled: (i === 0),
    }));
    const __VLS_9 = __VLS_8({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        title: "Move up",
        disabled: (i === 0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_8));
    let __VLS_12;
    const __VLS_13 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.move(i, -1);
                // @ts-ignore
                [move,];
            } });
    const { default: __VLS_14 } = __VLS_10.slots;
    // @ts-ignore
    [];
    var __VLS_10;
    var __VLS_11;
    let __VLS_15;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_16 = __VLS_asFunctionalComponent1(__VLS_15, new __VLS_15({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        title: "Move down",
        disabled: (i === __VLS_ctx.names.length - 1),
    }));
    const __VLS_17 = __VLS_16({
        ...{ 'onClick': {} },
        variant: "secondary",
        size: "sm",
        title: "Move down",
        disabled: (i === __VLS_ctx.names.length - 1),
    }, ...__VLS_functionalComponentArgsRest(__VLS_16));
    let __VLS_20;
    const __VLS_21 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.move(i, 1);
                // @ts-ignore
                [names, move,];
            } });
    const { default: __VLS_22 } = __VLS_18.slots;
    // @ts-ignore
    [];
    var __VLS_18;
    var __VLS_19;
    let __VLS_23;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_24 = __VLS_asFunctionalComponent1(__VLS_23, new __VLS_23({
        ...{ 'onClick': {} },
        variant: "danger",
        size: "sm",
        title: "Remove",
    }));
    const __VLS_25 = __VLS_24({
        ...{ 'onClick': {} },
        variant: "danger",
        size: "sm",
        title: "Remove",
    }, ...__VLS_functionalComponentArgsRest(__VLS_24));
    let __VLS_28;
    const __VLS_29 = ({ click: {} },
        { onClick: (...[$event]) => {
                __VLS_ctx.removeAt(i);
                // @ts-ignore
                [removeAt,];
            } });
    const { default: __VLS_30 } = __VLS_26.slots;
    // @ts-ignore
    [];
    var __VLS_26;
    var __VLS_27;
    // @ts-ignore
    [];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "add" },
});
/** @type {__VLS_StyleScopedClasses['add']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    ...{ onKeydown: (__VLS_ctx.handleQuickEnter) },
    ...{ onPaste: (__VLS_ctx.onQuickPaste) },
    ...{ class: "quick" },
    placeholder: (__VLS_ctx.placeholder),
    'data-testid': "players-quick-input",
});
(__VLS_ctx.quick);
/** @type {__VLS_StyleScopedClasses['quick']} */ ;
let __VLS_31;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_32 = __VLS_asFunctionalComponent1(__VLS_31, new __VLS_31({
    ...{ 'onClick': {} },
    variant: "primary",
    disabled: (!__VLS_ctx.quick.trim()),
    dataTestid: "players-add-btn",
}));
const __VLS_33 = __VLS_32({
    ...{ 'onClick': {} },
    variant: "primary",
    disabled: (!__VLS_ctx.quick.trim()),
    dataTestid: "players-add-btn",
}, ...__VLS_functionalComponentArgsRest(__VLS_32));
let __VLS_36;
const __VLS_37 = ({ click: {} },
    { onClick: (__VLS_ctx.handleQuickEnter) });
const { default: __VLS_38 } = __VLS_34.slots;
// @ts-ignore
[handleQuickEnter, handleQuickEnter, onQuickPaste, placeholder, quick, quick,];
var __VLS_34;
var __VLS_35;
let __VLS_39;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_40 = __VLS_asFunctionalComponent1(__VLS_39, new __VLS_39({
    ...{ 'onClick': {} },
    variant: "secondary",
    disabled: (!__VLS_ctx.names.length),
    dataTestid: "players-clear-btn",
}));
const __VLS_41 = __VLS_40({
    ...{ 'onClick': {} },
    variant: "secondary",
    disabled: (!__VLS_ctx.names.length),
    dataTestid: "players-clear-btn",
}, ...__VLS_functionalComponentArgsRest(__VLS_40));
let __VLS_44;
const __VLS_45 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.commit([]);
            // @ts-ignore
            [names, commit,];
        } });
const { default: __VLS_46 } = __VLS_42.slots;
// @ts-ignore
[];
var __VLS_42;
var __VLS_43;
if (__VLS_ctx.warn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "warn" },
    });
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
    (__VLS_ctx.warn);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "hint" },
});
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.em, __VLS_intrinsics.em)({});
// @ts-ignore
[warn, warn,];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
