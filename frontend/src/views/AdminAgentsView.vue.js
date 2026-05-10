/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { marked } from 'marked';
import { ref, computed, onMounted } from 'vue';
import { highlightMitigations } from './highlightMitigations';
import { apiRequest } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const usage = ref(null);
async function fetchUsage() {
    usage.value = await apiRequest('/admin/agents/usage');
}
onMounted(() => {
    fetchUsage();
});
const agents = ref([
    {
        key: 'feedback_digest',
        name: 'Feedback Digest',
        description: 'Groups user feedback by theme and severity, proposes next actions.',
        since: '',
        until: '',
        loading: false,
        result: null,
    },
    {
        key: 'ai_usage_tracker',
        name: 'AI Usage Tracker',
        description: 'Summarizes daily AI token spend, detects abuse, suggests cost optimizations.',
        since: '',
        until: '',
        loading: false,
        result: null,
    },
    {
        key: 'error_watcher',
        name: 'Error Watcher',
        description: 'Summarizes recurring backend errors and slow endpoints.',
        since: '',
        until: '',
        loading: false,
        result: null,
    },
    {
        key: 'beta_ux_analyzer',
        name: 'Beta UX Analyzer',
        description: 'Combines feedback and page views to identify top friction points.',
        since: '',
        until: '',
        loading: false,
        result: null,
    },
    {
        key: 'cyber_security_watcher',
        name: 'Cybersecurity Watcher',
        description: 'Detects suspicious logins, spikes, and errors. Inputs: auth, request, rate-limit, error logs. Outputs: findings, evidence, mitigations.',
        since: '',
        until: '',
        loading: false,
        result: null,
        quickPresets: [
            { label: 'Last 1h', since: () => new Date(Date.now() - 60 * 60 * 1000).toISOString().slice(0, 10), until: () => new Date().toISOString().slice(0, 10) },
            { label: 'Last 24h', since: () => new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10), until: () => new Date().toISOString().slice(0, 10) },
            { label: 'Last 7d', since: () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10), until: () => new Date().toISOString().slice(0, 10) },
        ],
    },
]);
const auth = useAuthStore();
const isAdmin = computed(() => auth.user?.role === 'superuser' || auth.user?.role === 'org_pro');
function renderMarkdown(md) {
    return marked.parse(md || '');
}
async function runAgent(agent) {
    agent.loading = true;
    agent.result = null;
    try {
        const resp = await apiRequest('/admin/agents/run', {
            method: 'POST',
            body: JSON.stringify({
                agentKey: agent.key,
                since: agent.since,
                until: agent.until,
            }),
        });
        agent.result = resp;
        await fetchUsage();
    }
    catch {
        agent.result = { markdownReport: 'Error running agent.' };
    }
    finally {
        agent.loading = false;
    }
}
function copyResult(md) {
    navigator.clipboard.writeText(md);
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['usage-table']} */ ;
/** @type {__VLS_StyleScopedClasses['usage-table']} */ ;
/** @type {__VLS_StyleScopedClasses['usage-table']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "admin-agents-view" },
});
/** @type {__VLS_StyleScopedClasses['admin-agents-view']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
if (!__VLS_ctx.isAdmin) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    if (__VLS_ctx.usage) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "usage-panel" },
        });
        /** @type {__VLS_StyleScopedClasses['usage-panel']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.b, __VLS_intrinsics.b)({});
        (__VLS_ctx.usage.todayTokens);
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "usage-table" },
        });
        /** @type {__VLS_StyleScopedClasses['usage-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [run] of __VLS_vFor((__VLS_ctx.usage.recent))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (run.id),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.createdAt);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.agentKey);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.userId);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.tokensOut);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.model);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (run.status);
            // @ts-ignore
            [isAdmin, usage, usage, usage,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "agent-cards" },
    });
    /** @type {__VLS_StyleScopedClasses['agent-cards']} */ ;
    for (const [agent] of __VLS_vFor((__VLS_ctx.agents))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (agent.key),
            ...{ class: "agent-card" },
        });
        /** @type {__VLS_StyleScopedClasses['agent-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        (agent.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (agent.description);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "inputs" },
        });
        /** @type {__VLS_StyleScopedClasses['inputs']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            type: "date",
        });
        (agent.since);
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            type: "date",
        });
        (agent.until);
        if (agent.quickPresets) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            for (const [preset] of __VLS_vFor((agent.quickPresets))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (() => { agent.since = preset.since(); agent.until = preset.until(); }) },
                    key: (preset.label),
                });
                (preset.label);
                // @ts-ignore
                [agents,];
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.isAdmin))
                        return;
                    __VLS_ctx.runAgent(agent);
                    // @ts-ignore
                    [runAgent,];
                } },
            disabled: (agent.loading),
        });
        if (agent.result) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "result-panel" },
            });
            /** @type {__VLS_StyleScopedClasses['result-panel']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "markdown" },
            });
            __VLS_asFunctionalDirective(__VLS_directives.vHtml, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.highlightMitigations(__VLS_ctx.renderMarkdown(agent.result.markdownReport), agent.key)) }, null, null);
            /** @type {__VLS_StyleScopedClasses['markdown']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "meta" },
            });
            /** @type {__VLS_StyleScopedClasses['meta']} */ ;
            (agent.result.modelUsed);
            (agent.result.tokenUsage);
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(!__VLS_ctx.isAdmin))
                            return;
                        if (!(agent.result))
                            return;
                        __VLS_ctx.copyResult(agent.result.markdownReport);
                        // @ts-ignore
                        [highlightMitigations, renderMarkdown, copyResult,];
                    } },
            });
        }
        // @ts-ignore
        [];
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
