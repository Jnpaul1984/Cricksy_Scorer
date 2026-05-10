/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend, } from 'chart.js';
import { ref, computed, onMounted, watch } from 'vue';
import { Bar, Pie } from 'vue-chartjs';
import { API_BASE, getStoredToken } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);
const auth = useAuthStore();
// State
const loading = ref(true);
const error = ref(null);
const stats = ref(null);
// Filters
const filterYear = ref(new Date().getFullYear());
const filterMonth = ref(null);
const filterUserId = ref(null);
const filterOrgId = ref(null);
// Auth checks
const isLoggedIn = computed(() => !!auth.token);
const canViewOrgStats = computed(() => {
    const role = auth.role?.toLowerCase() || '';
    return ['org_pro', 'superuser'].includes(role);
});
// Chart colors
const featureColors = [
    '#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
];
// Computed chart data
const monthlyChartData = computed(() => {
    if (!stats.value)
        return { labels: [], datasets: [] };
    return {
        labels: stats.value.by_month.map(m => m.month),
        datasets: [
            {
                label: 'Tokens Used',
                data: stats.value.by_month.map(m => m.tokens),
                backgroundColor: '#4f46e5',
                borderRadius: 4,
            },
        ],
    };
});
const featurePieData = computed(() => {
    if (!stats.value || stats.value.by_feature.length === 0) {
        return { labels: [], datasets: [] };
    }
    return {
        labels: stats.value.by_feature.map(f => formatFeatureName(f.feature)),
        datasets: [
            {
                data: stats.value.by_feature.map(f => f.tokens),
                backgroundColor: stats.value.by_feature.map((_, i) => featureColors[i % featureColors.length]),
                borderWidth: 0,
            },
        ],
    };
});
const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            callbacks: {
                label: (ctx) => `${ctx.parsed.y.toLocaleString()} tokens`,
            },
        },
    },
    scales: {
        y: {
            beginAtZero: true,
            ticks: {
                callback: (value) => {
                    const num = typeof value === 'number' ? value : parseFloat(value);
                    return num >= 1000 ? `${num / 1000}k` : num;
                },
            },
        },
    },
};
const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'right',
            labels: {
                padding: 15,
                usePointStyle: true,
                font: { size: 12 },
            },
        },
        tooltip: {
            callbacks: {
                label: (ctx) => {
                    const value = ctx.parsed;
                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                    const pct = ((value / total) * 100).toFixed(1);
                    return `${ctx.label}: ${value.toLocaleString()} tokens (${pct}%)`;
                },
            },
        },
    },
};
// Helper functions
function formatFeatureName(feature) {
    return feature
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}
function formatTokens(tokens) {
    if (tokens >= 1_000_000)
        return `${(tokens / 1_000_000).toFixed(1)}M`;
    if (tokens >= 1_000)
        return `${(tokens / 1_000).toFixed(1)}k`;
    return tokens.toString();
}
// API
async function fetchUsageStats() {
    loading.value = true;
    error.value = null;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const params = new URLSearchParams();
        if (filterYear.value)
            params.set('year', String(filterYear.value));
        if (filterMonth.value)
            params.set('month', String(filterMonth.value));
        if (filterUserId.value)
            params.set('user_id', filterUserId.value);
        if (filterOrgId.value)
            params.set('org_id', filterOrgId.value);
        const url = `${API_BASE}/api/ai-usage/stats?${params.toString()}`;
        const res = await fetch(url, { headers });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || 'Failed to fetch usage stats');
        }
        stats.value = await res.json();
    }
    catch (err) {
        error.value = err.message || 'An error occurred';
        console.error('Error fetching usage stats:', err);
    }
    finally {
        loading.value = false;
    }
}
// Month options
const monthOptions = [
    { value: null, label: 'All Months' },
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
];
const yearOptions = computed(() => {
    const currentYear = new Date().getFullYear();
    return [
        { value: null, label: 'All Years' },
        ...Array.from({ length: 3 }, (_, i) => ({
            value: currentYear - i,
            label: String(currentYear - i),
        })),
    ];
});
// Watch filters
watch([filterYear, filterMonth, filterUserId, filterOrgId], () => {
    fetchUsageStats();
});
onMounted(() => {
    if (isLoggedIn.value) {
        fetchUsageStats();
    }
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['banner']} */ ;
/** @type {__VLS_StyleScopedClasses['banner']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-fill']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-fill']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['data-table']} */ ;
/** @type {__VLS_StyleScopedClasses['usage-dashboard']} */ ;
/** @type {__VLS_StyleScopedClasses['charts-row']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
/** @type {__VLS_StyleScopedClasses['pie']} */ ;
/** @type {__VLS_StyleScopedClasses['filters']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "usage-dashboard" },
});
/** @type {__VLS_StyleScopedClasses['usage-dashboard']} */ ;
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "banner info" },
    });
    /** @type {__VLS_StyleScopedClasses['banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['info']} */ ;
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
    RouterLink;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        to: "/login",
        ...{ class: "link-inline" },
    }));
    const __VLS_2 = __VLS_1({
        to: "/login",
        ...{ class: "link-inline" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['link-inline']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    // @ts-ignore
    [isLoggedIn,];
    var __VLS_3;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
if (__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "filters" },
    });
    /** @type {__VLS_StyleScopedClasses['filters']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.filterYear),
        ...{ class: "ds-input" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    for (const [opt] of __VLS_vFor((__VLS_ctx.yearOptions))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (opt.value ?? 'all'),
            value: (opt.value),
        });
        (opt.label);
        // @ts-ignore
        [isLoggedIn, filterYear, yearOptions,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.filterMonth),
        ...{ class: "ds-input" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    for (const [opt] of __VLS_vFor((__VLS_ctx.monthOptions))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (opt.value ?? 'all'),
            value: (opt.value),
        });
        (opt.label);
        // @ts-ignore
        [filterMonth, monthOptions,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.fetchUsageStats) },
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
}
if (__VLS_ctx.loading && __VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading" },
    });
    /** @type {__VLS_StyleScopedClasses['loading']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "banner error" },
    });
    /** @type {__VLS_StyleScopedClasses['banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.fetchUsageStats) },
        ...{ class: "btn-link" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-link']} */ ;
}
else if (__VLS_ctx.stats && __VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dashboard-content" },
    });
    /** @type {__VLS_StyleScopedClasses['dashboard-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "quota-section" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "quota-card" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "quota-header" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "quota-label" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "quota-value" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-value']} */ ;
    (__VLS_ctx.formatTokens(__VLS_ctx.stats.quota.used));
    if (__VLS_ctx.stats.quota.limit) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (__VLS_ctx.formatTokens(__VLS_ctx.stats.quota.limit));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "unlimited" },
        });
        /** @type {__VLS_StyleScopedClasses['unlimited']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "progress-bar" },
    });
    /** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "progress-fill" },
        ...{ class: ({ warning: __VLS_ctx.stats.quota.percentage > 75, danger: __VLS_ctx.stats.quota.percentage > 90 }) },
        ...{ style: ({ width: `${Math.min(__VLS_ctx.stats.quota.percentage, 100)}%` }) },
    });
    /** @type {__VLS_StyleScopedClasses['progress-fill']} */ ;
    /** @type {__VLS_StyleScopedClasses['warning']} */ ;
    /** @type {__VLS_StyleScopedClasses['danger']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "quota-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['quota-footer']} */ ;
    if (__VLS_ctx.stats.quota.limit) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        (__VLS_ctx.stats.quota.percentage.toFixed(1));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "unlimited-note" },
        });
        /** @type {__VLS_StyleScopedClasses['unlimited-note']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stats-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['stats-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-info" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.formatTokens(__VLS_ctx.stats.total_tokens));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-info" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.stats.total_requests.toLocaleString());
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-info" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.stats.by_feature.length);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-card" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-info" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-value" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
    (__VLS_ctx.stats.total_requests > 0 ? Math.round(__VLS_ctx.stats.total_tokens / __VLS_ctx.stats.total_requests) : 0);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stat-label" },
    });
    /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "charts-row" },
    });
    /** @type {__VLS_StyleScopedClasses['charts-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "chart-section" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.stats.by_month.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chart-container" },
        });
        /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.Bar} */
        Bar;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            data: (__VLS_ctx.monthlyChartData),
            options: (__VLS_ctx.barChartOptions),
        }));
        const __VLS_8 = __VLS_7({
            data: (__VLS_ctx.monthlyChartData),
            options: (__VLS_ctx.barChartOptions),
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-chart" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-chart']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "chart-section" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.stats.by_feature.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "chart-container pie" },
        });
        /** @type {__VLS_StyleScopedClasses['chart-container']} */ ;
        /** @type {__VLS_StyleScopedClasses['pie']} */ ;
        let __VLS_11;
        /** @ts-ignore @type { | typeof __VLS_components.Pie} */
        Pie;
        // @ts-ignore
        const __VLS_12 = __VLS_asFunctionalComponent1(__VLS_11, new __VLS_11({
            data: (__VLS_ctx.featurePieData),
            options: (__VLS_ctx.pieChartOptions),
        }));
        const __VLS_13 = __VLS_12({
            data: (__VLS_ctx.featurePieData),
            options: (__VLS_ctx.pieChartOptions),
        }, ...__VLS_functionalComponentArgsRest(__VLS_12));
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-chart" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-chart']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    if (__VLS_ctx.canViewOrgStats && __VLS_ctx.stats.top_users.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "top-users-section" },
        });
        /** @type {__VLS_StyleScopedClasses['top-users-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "table-wrapper" },
        });
        /** @type {__VLS_StyleScopedClasses['table-wrapper']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "data-table" },
        });
        /** @type {__VLS_StyleScopedClasses['data-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [user, idx] of __VLS_vFor((__VLS_ctx.stats.top_users))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (user.user_id),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "rank" },
            });
            /** @type {__VLS_StyleScopedClasses['rank']} */ ;
            (idx + 1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "email" },
            });
            /** @type {__VLS_StyleScopedClasses['email']} */ ;
            (user.email);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "tokens" },
            });
            /** @type {__VLS_StyleScopedClasses['tokens']} */ ;
            (__VLS_ctx.formatTokens(user.tokens));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "requests" },
            });
            /** @type {__VLS_StyleScopedClasses['requests']} */ ;
            (user.request_count.toLocaleString());
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "avg" },
            });
            /** @type {__VLS_StyleScopedClasses['avg']} */ ;
            (user.request_count > 0 ? Math.round(user.tokens / user.request_count) : 0);
            // @ts-ignore
            [isLoggedIn, isLoggedIn, fetchUsageStats, fetchUsageStats, loading, error, error, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, stats, formatTokens, formatTokens, formatTokens, formatTokens, monthlyChartData, barChartOptions, featurePieData, pieChartOptions, canViewOrgStats,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "features-section" },
    });
    /** @type {__VLS_StyleScopedClasses['features-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.stats.by_feature.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "table-wrapper" },
        });
        /** @type {__VLS_StyleScopedClasses['table-wrapper']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "data-table" },
        });
        /** @type {__VLS_StyleScopedClasses['data-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [feat] of __VLS_vFor((__VLS_ctx.stats.by_feature))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (feat.feature),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "feature-name" },
            });
            /** @type {__VLS_StyleScopedClasses['feature-name']} */ ;
            (__VLS_ctx.formatFeatureName(feat.feature));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "tokens" },
            });
            /** @type {__VLS_StyleScopedClasses['tokens']} */ ;
            (__VLS_ctx.formatTokens(feat.tokens));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "requests" },
            });
            /** @type {__VLS_StyleScopedClasses['requests']} */ ;
            (feat.request_count.toLocaleString());
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "percentage" },
            });
            /** @type {__VLS_StyleScopedClasses['percentage']} */ ;
            (((feat.tokens / __VLS_ctx.stats.total_tokens) * 100).toFixed(1));
            // @ts-ignore
            [stats, stats, stats, formatTokens, formatFeatureName,];
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
