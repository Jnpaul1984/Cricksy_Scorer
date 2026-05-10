/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { reactive, computed, ref } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import PlayersEditor from '@/components/PlayersEditor.vue';
import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
import { getErrorMessage } from '@/utils/api';
const router = useRouter();
const game = useGameStore();
const auth = useAuthStore();
const creating = ref(false);
const errorMsg = ref(null);
const canCreateMatch = computed(() => auth.requireRole('org_pro', 'superuser'));
const isCoachAccount = computed(() => auth.role === 'coach_pro');
const contributorInvitePath = '/contributors/invite';
const form = reactive({
    team_a_name: '',
    team_b_name: '',
    match_type: 'limited',
    overs_limit: 25,
    days_limit: null,
    overs_per_day: null,
    dls_enabled: false,
    toss_winner_team: '',
    decision: 'bat',
});
// ✅ arrays controlled by PlayersEditor
const playersA = ref([]);
const playersB = ref([]);
const canSubmit = computed(() => {
    const a = playersA.value.length >= 2;
    const b = playersB.value.length >= 2;
    return !!(form.team_a_name && form.team_b_name && a && b && form.toss_winner_team);
});
async function onSubmit() {
    if (!canSubmit.value || creating.value)
        return;
    if (!canCreateMatch.value) {
        errorMsg.value = 'Only Organization Pro or Superuser accounts can create matches.';
        return;
    }
    creating.value = true;
    errorMsg.value = null;
    try {
        const payload = {
            team_a_name: form.team_a_name,
            team_b_name: form.team_b_name,
            players_a: playersA.value,
            players_b: playersB.value,
            match_type: form.match_type,
            overs_limit: form.match_type === 'limited' ? form.overs_limit : null,
            days_limit: form.match_type === 'multi_day' ? form.days_limit : null,
            overs_per_day: form.match_type === 'multi_day' ? form.overs_per_day : null,
            dls_enabled: form.dls_enabled,
            interruptions: [],
            toss_winner_team: form.toss_winner_team,
            decision: form.decision,
        };
        const created = (await game.createNewGame(payload));
        await router.push({ name: 'team-select', params: { gameId: created.id } });
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
/** @type {__VLS_StyleScopedClasses['fan-mode-text']} */ ;
/** @type {__VLS_StyleScopedClasses['fan-mode-text']} */ ;
/** @type {__VLS_StyleScopedClasses['fan-mode-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['two']} */ ;
/** @type {__VLS_StyleScopedClasses['fan-mode-content']} */ ;
/** @type {__VLS_StyleScopedClasses['fan-mode-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "setup" },
});
/** @type {__VLS_StyleScopedClasses['setup']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-mode-banner" },
});
/** @type {__VLS_StyleScopedClasses['fan-mode-banner']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-mode-content" },
});
/** @type {__VLS_StyleScopedClasses['fan-mode-content']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "fan-mode-icon" },
});
/** @type {__VLS_StyleScopedClasses['fan-mode-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-mode-text" },
});
/** @type {__VLS_StyleScopedClasses['fan-mode-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
RouterLink;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "/fan",
    ...{ class: "fan-mode-btn" },
    dataTestid: "btn-fan-mode",
}));
const __VLS_2 = __VLS_1({
    to: "/fan",
    ...{ class: "fan-mode-btn" },
    dataTestid: "btn-fan-mode",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['fan-mode-btn']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
var __VLS_3;
if (!__VLS_ctx.canCreateMatch) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "access-banner" },
    });
    /** @type {__VLS_StyleScopedClasses['access-banner']} */ ;
    if (__VLS_ctx.isCoachAccount) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            to: (__VLS_ctx.contributorInvitePath),
        }));
        const __VLS_8 = __VLS_7({
            to: (__VLS_ctx.contributorInvitePath),
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        const { default: __VLS_11 } = __VLS_9.slots;
        // @ts-ignore
        [canCreateMatch, isCoachAccount, contributorInvitePath,];
        var __VLS_9;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card" },
    'aria-disabled': (!__VLS_ctx.canCreateMatch),
});
/** @type {__VLS_StyleScopedClasses['card']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
    ...{ onSubmit: (__VLS_ctx.onSubmit) },
    ...{ class: "form" },
});
/** @type {__VLS_StyleScopedClasses['form']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row two" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['two']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "e.g., Bagatelle",
    'data-testid': "input-team-a",
});
(__VLS_ctx.form.team_a_name);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "e.g., Bridgetown",
    'data-testid': "input-team-b",
});
(__VLS_ctx.form.team_b_name);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
const __VLS_12 = PlayersEditor;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
    modelValue: (__VLS_ctx.playersA),
    label: (`Players - ${__VLS_ctx.form.team_a_name || 'Team A'}`),
    teamName: (__VLS_ctx.form.team_a_name),
    max: (16),
    min: (2),
}));
const __VLS_14 = __VLS_13({
    modelValue: (__VLS_ctx.playersA),
    label: (`Players - ${__VLS_ctx.form.team_a_name || 'Team A'}`),
    teamName: (__VLS_ctx.form.team_a_name),
    max: (16),
    min: (2),
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
const __VLS_17 = PlayersEditor;
// @ts-ignore
const __VLS_18 = __VLS_asFunctionalComponent1(__VLS_17, new __VLS_17({
    modelValue: (__VLS_ctx.playersB),
    label: (`Players - ${__VLS_ctx.form.team_b_name || 'Team B'}`),
    teamName: (__VLS_ctx.form.team_b_name),
    max: (16),
    min: (2),
}));
const __VLS_19 = __VLS_18({
    modelValue: (__VLS_ctx.playersB),
    label: (`Players - ${__VLS_ctx.form.team_b_name || 'Team B'}`),
    teamName: (__VLS_ctx.form.team_b_name),
    max: (16),
    min: (2),
}, ...__VLS_functionalComponentArgsRest(__VLS_18));
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row two" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['two']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.match_type),
    'data-testid': "select-match-type",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "limited",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "multi_day",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "custom",
});
if (__VLS_ctx.form.match_type === 'limited') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "number",
        min: "1",
        max: "120",
        'data-testid': "input-overs-limit",
    });
    (__VLS_ctx.form.overs_limit);
}
else if (__VLS_ctx.form.match_type === 'multi_day') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "number",
        min: "1",
        max: "7",
    });
    (__VLS_ctx.form.days_limit);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "number",
        min: "1",
        max: "120",
    });
    (__VLS_ctx.form.overs_per_day);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row two" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['two']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.dls_enabled),
    'data-testid': "select-dls-enabled",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: (false),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: (true),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.toss_winner_team),
    'data-testid': "select-toss-winner",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "",
});
if (__VLS_ctx.form.team_a_name) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (__VLS_ctx.form.team_a_name),
    });
    (__VLS_ctx.form.team_a_name);
}
if (__VLS_ctx.form.team_b_name) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (__VLS_ctx.form.team_b_name),
    });
    (__VLS_ctx.form.team_b_name);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toggle" },
});
/** @type {__VLS_StyleScopedClasses['toggle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "radio",
    value: "bat",
    'data-testid': "radio-bat",
});
(__VLS_ctx.form.decision);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "radio",
    value: "bowl",
    'data-testid': "radio-bowl",
});
(__VLS_ctx.form.decision);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "actions" },
});
/** @type {__VLS_StyleScopedClasses['actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ class: "primary" },
    type: "submit",
    disabled: (!__VLS_ctx.canSubmit || __VLS_ctx.creating),
    'data-testid': "btn-create-match",
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.creating ? 'Creating…' : 'Create New Match');
if (__VLS_ctx.errorMsg) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.errorMsg);
}
// @ts-ignore
[canCreateMatch, onSubmit, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, form, playersA, playersB, canSubmit, creating, creating, errorMsg, errorMsg,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
