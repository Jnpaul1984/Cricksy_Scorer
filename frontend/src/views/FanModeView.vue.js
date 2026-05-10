/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { reactive, computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import FanFeedWidget from '@/components/FanFeedWidget.vue';
import FanStatsWidget from '@/components/FanStatsWidget.vue';
import { apiService, getErrorMessage } from '@/services/api';
const router = useRouter();
const creating = ref(false);
const errorMsg = ref(null);
const activeTab = ref('feed');
const form = reactive({
    match_name: '',
    format: 'T20',
    custom_overs: 10,
    team_a_name: '',
    team_b_name: '',
});
const oversLimit = computed(() => {
    switch (form.format) {
        case 'T20': return 20;
        case 'T10': return 10;
        case 'custom': return form.custom_overs ?? 20;
        default: return 20;
    }
});
const displayMatchName = computed(() => form.match_name.trim() || 'My Backyard Match');
const canSubmit = computed(() => form.team_a_name.trim() !== '' &&
    form.team_b_name.trim() !== '' &&
    !creating.value);
async function onSubmit() {
    if (!canSubmit.value)
        return;
    creating.value = true;
    errorMsg.value = null;
    try {
        const result = await apiService.createFanMatch({
            home_team_name: form.team_a_name.trim(),
            away_team_name: form.team_b_name.trim(),
            match_type: form.format === 'custom' ? `${oversLimit.value}-over` : form.format,
            overs_limit: oversLimit.value,
        });
        // Redirect to scoring view
        await router.push({ name: 'GameScoringView', params: { gameId: result.id } });
    }
    catch (e) {
        errorMsg.value = getErrorMessage(e);
    }
    finally {
        creating.value = false;
    }
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['format-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['format-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['field-row']} */ ;
/** @type {__VLS_StyleScopedClasses['field']} */ ;
/** @type {__VLS_StyleScopedClasses['start-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['start-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['back-link']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['field-row']} */ ;
/** @type {__VLS_StyleScopedClasses['vs']} */ ;
/** @type {__VLS_StyleScopedClasses['format-options']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-mode-view" },
});
/** @type {__VLS_StyleScopedClasses['fan-mode-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tab-nav" },
});
/** @type {__VLS_StyleScopedClasses['tab-nav']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'feed';
            // @ts-ignore
            [activeTab,];
        } },
    ...{ class: "tab-btn" },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'feed' }) },
});
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'stats';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: "tab-btn" },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'stats' }) },
});
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'create';
            // @ts-ignore
            [activeTab, activeTab,];
        } },
    ...{ class: "tab-btn" },
    ...{ class: ({ active: __VLS_ctx.activeTab === 'create' }) },
});
/** @type {__VLS_StyleScopedClasses['tab-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
if (__VLS_ctx.activeTab === 'feed') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tab-panel" },
    });
    /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
    const __VLS_0 = FanFeedWidget;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({}));
    const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
else if (__VLS_ctx.activeTab === 'stats') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tab-panel" },
    });
    /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
    const __VLS_5 = FanStatsWidget;
    // @ts-ignore
    const __VLS_6 = __VLS_asFunctionalComponent1(__VLS_5, new __VLS_5({}));
    const __VLS_7 = __VLS_6({}, ...__VLS_functionalComponentArgsRest(__VLS_6));
}
else if (__VLS_ctx.activeTab === 'create') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tab-panel" },
    });
    /** @type {__VLS_StyleScopedClasses['tab-panel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card" },
    });
    /** @type {__VLS_StyleScopedClasses['card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "header" },
    });
    /** @type {__VLS_StyleScopedClasses['header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.onSubmit) },
        ...{ class: "form" },
    });
    /** @type {__VLS_StyleScopedClasses['form']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "field" },
    });
    /** @type {__VLS_StyleScopedClasses['field']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "match-name",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "optional" },
    });
    /** @type {__VLS_StyleScopedClasses['optional']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "match-name",
        value: (__VLS_ctx.form.match_name),
        type: "text",
        placeholder: (__VLS_ctx.displayMatchName),
        'data-testid': "input-match-name",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "field" },
    });
    /** @type {__VLS_StyleScopedClasses['field']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "format-options" },
    });
    /** @type {__VLS_StyleScopedClasses['format-options']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.activeTab === 'feed'))
                    return;
                if (!!(__VLS_ctx.activeTab === 'stats'))
                    return;
                if (!(__VLS_ctx.activeTab === 'create'))
                    return;
                __VLS_ctx.form.format = 'T20';
                // @ts-ignore
                [activeTab, activeTab, activeTab, activeTab, onSubmit, form, form, displayMatchName,];
            } },
        type: "button",
        ...{ class: "format-btn" },
        ...{ class: ({ active: __VLS_ctx.form.format === 'T20' }) },
        'data-testid': "btn-format-t20",
    });
    /** @type {__VLS_StyleScopedClasses['format-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.activeTab === 'feed'))
                    return;
                if (!!(__VLS_ctx.activeTab === 'stats'))
                    return;
                if (!(__VLS_ctx.activeTab === 'create'))
                    return;
                __VLS_ctx.form.format = 'T10';
                // @ts-ignore
                [form, form,];
            } },
        type: "button",
        ...{ class: "format-btn" },
        ...{ class: ({ active: __VLS_ctx.form.format === 'T10' }) },
        'data-testid': "btn-format-t10",
    });
    /** @type {__VLS_StyleScopedClasses['format-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.activeTab === 'feed'))
                    return;
                if (!!(__VLS_ctx.activeTab === 'stats'))
                    return;
                if (!(__VLS_ctx.activeTab === 'create'))
                    return;
                __VLS_ctx.form.format = 'custom';
                // @ts-ignore
                [form, form,];
            } },
        type: "button",
        ...{ class: "format-btn" },
        ...{ class: ({ active: __VLS_ctx.form.format === 'custom' }) },
        'data-testid': "btn-format-custom",
    });
    /** @type {__VLS_StyleScopedClasses['format-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    if (__VLS_ctx.form.format === 'custom') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "field" },
        });
        /** @type {__VLS_StyleScopedClasses['field']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: "custom-overs",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            id: "custom-overs",
            type: "number",
            min: "1",
            max: "50",
            placeholder: "e.g., 5",
            'data-testid': "input-custom-overs",
        });
        (__VLS_ctx.form.custom_overs);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "field-row" },
    });
    /** @type {__VLS_StyleScopedClasses['field-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "field" },
    });
    /** @type {__VLS_StyleScopedClasses['field']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "team-a",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "team-a",
        value: (__VLS_ctx.form.team_a_name),
        type: "text",
        placeholder: "e.g., Backyard Legends",
        required: true,
        'data-testid': "input-team-a",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "vs" },
    });
    /** @type {__VLS_StyleScopedClasses['vs']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "field" },
    });
    /** @type {__VLS_StyleScopedClasses['field']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "team-b",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "team-b",
        value: (__VLS_ctx.form.team_b_name),
        type: "text",
        placeholder: "e.g., Street Stars",
        required: true,
        'data-testid': "input-team-b",
    });
    if (__VLS_ctx.errorMsg) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "error" },
        });
        /** @type {__VLS_StyleScopedClasses['error']} */ ;
        (__VLS_ctx.errorMsg);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "actions" },
    });
    /** @type {__VLS_StyleScopedClasses['actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "start-btn" },
        disabled: (!__VLS_ctx.canSubmit),
        'data-testid': "btn-start-match",
    });
    /** @type {__VLS_StyleScopedClasses['start-btn']} */ ;
    if (__VLS_ctx.creating) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "spinner" },
        });
        /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    }
    (__VLS_ctx.creating ? 'Starting...' : '🏏 Start Match');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "footer" },
    });
    /** @type {__VLS_StyleScopedClasses['footer']} */ ;
    let __VLS_10;
    /** @ts-ignore @type { | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link'] | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link']} */
    routerLink;
    // @ts-ignore
    const __VLS_11 = __VLS_asFunctionalComponent1(__VLS_10, new __VLS_10({
        to: "/setup",
        ...{ class: "back-link" },
    }));
    const __VLS_12 = __VLS_11({
        to: "/setup",
        ...{ class: "back-link" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_11));
    /** @type {__VLS_StyleScopedClasses['back-link']} */ ;
    const { default: __VLS_15 } = __VLS_13.slots;
    // @ts-ignore
    [form, form, form, form, form, errorMsg, errorMsg, canSubmit, creating, creating,];
    var __VLS_13;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
