/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted, onUnmounted } from 'vue';
import { useBranding } from '@/composables/useBranding';
const props = defineProps();
const emit = defineEmits();
const { fetchOrgBranding } = useBranding();
const brandingData = ref(null);
const loading = ref(false);
const error = ref('');
const autoRefreshInterval = ref(null);
const loadBranding = async () => {
    if (!props.orgId) {
        error.value = 'Organization ID required';
        return;
    }
    try {
        loading.value = true;
        error.value = '';
        const data = await fetchOrgBranding(props.orgId);
        if (data) {
            brandingData.value = data;
            emit('branding-loaded', data);
        }
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load branding';
    }
    finally {
        loading.value = false;
    }
};
const refreshBranding = async () => {
    await loadBranding();
};
const clearError = () => {
    error.value = '';
};
const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
};
const startAutoRefresh = () => {
    if (!props.autoRefresh)
        return;
    autoRefreshInterval.value = setInterval(() => loadBranding(), (props.refreshIntervalSeconds || 30) * 1000);
};
const stopAutoRefresh = () => {
    if (autoRefreshInterval.value) {
        clearInterval(autoRefreshInterval.value);
    }
};
onMounted(() => {
    loadBranding();
    startAutoRefresh();
});
onUnmounted(() => {
    stopAutoRefresh();
});
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
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-refresh']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-refresh']} */ ;
/** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
/** @type {__VLS_StyleScopedClasses['typography-item']} */ ;
/** @type {__VLS_StyleScopedClasses['checkbox-label']} */ ;
/** @type {__VLS_StyleScopedClasses['status-row']} */ ;
/** @type {__VLS_StyleScopedClasses['status-row']} */ ;
/** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['color-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['typography-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['asset-item']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "branding-panel" },
});
/** @type {__VLS_StyleScopedClasses['branding-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-header" },
});
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.refreshBranding) },
    disabled: (__VLS_ctx.loading),
    ...{ class: "btn-refresh" },
});
/** @type {__VLS_StyleScopedClasses['btn-refresh']} */ ;
(__VLS_ctx.loading ? 'Loading...' : 'Refresh');
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-loading" },
    });
    /** @type {__VLS_StyleScopedClasses['state-loading']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-error" },
    });
    /** @type {__VLS_StyleScopedClasses['state-error']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error-message" },
    });
    /** @type {__VLS_StyleScopedClasses['error-message']} */ ;
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.clearError) },
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
}
else if (__VLS_ctx.brandingData) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "branding-content" },
    });
    /** @type {__VLS_StyleScopedClasses['branding-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "section-preview" },
    });
    /** @type {__VLS_StyleScopedClasses['section-preview']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "logo-container" },
    });
    /** @type {__VLS_StyleScopedClasses['logo-container']} */ ;
    if (__VLS_ctx.brandingData.assets.logo_url) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
            src: (__VLS_ctx.brandingData.assets.logo_url),
            alt: "Organization logo",
            ...{ class: "org-logo" },
        });
        /** @type {__VLS_StyleScopedClasses['org-logo']} */ ;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "logo-placeholder" },
        });
        /** @type {__VLS_StyleScopedClasses['logo-placeholder']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "section-colors" },
    });
    /** @type {__VLS_StyleScopedClasses['section-colors']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['color-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.primary }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.primary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.secondary }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.secondary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.accent }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.accent);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.success }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.success);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.warning }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.warning);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-item" },
    });
    /** @type {__VLS_StyleScopedClasses['color-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "color-swatch" },
        ...{ style: ({ backgroundColor: __VLS_ctx.brandingData.colors.error }) },
    });
    /** @type {__VLS_StyleScopedClasses['color-swatch']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "color-label" },
    });
    /** @type {__VLS_StyleScopedClasses['color-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({
        ...{ class: "color-code" },
    });
    /** @type {__VLS_StyleScopedClasses['color-code']} */ ;
    (__VLS_ctx.brandingData.colors.error);
    if (__VLS_ctx.brandingData.typography) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "section-typography" },
        });
        /** @type {__VLS_StyleScopedClasses['section-typography']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "typography-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['typography-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "typography-item" },
        });
        /** @type {__VLS_StyleScopedClasses['typography-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "font-value" },
        });
        /** @type {__VLS_StyleScopedClasses['font-value']} */ ;
        (__VLS_ctx.brandingData.typography.primary_font);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "typography-item" },
        });
        /** @type {__VLS_StyleScopedClasses['typography-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "font-value" },
        });
        /** @type {__VLS_StyleScopedClasses['font-value']} */ ;
        (__VLS_ctx.brandingData.typography.heading_size);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "typography-item" },
        });
        /** @type {__VLS_StyleScopedClasses['typography-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "font-value" },
        });
        /** @type {__VLS_StyleScopedClasses['font-value']} */ ;
        (__VLS_ctx.brandingData.typography.body_size);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "typography-item" },
        });
        /** @type {__VLS_StyleScopedClasses['typography-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "font-value" },
        });
        /** @type {__VLS_StyleScopedClasses['font-value']} */ ;
        (__VLS_ctx.brandingData.typography.line_height);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "section-scope" },
    });
    /** @type {__VLS_StyleScopedClasses['section-scope']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "scope-checkboxes" },
    });
    /** @type {__VLS_StyleScopedClasses['scope-checkboxes']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "checkbox-label" },
    });
    /** @type {__VLS_StyleScopedClasses['checkbox-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "checkbox",
        disabled: true,
    });
    (__VLS_ctx.brandingData.apply_to.viewer);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "checkbox-label" },
    });
    /** @type {__VLS_StyleScopedClasses['checkbox-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "checkbox",
        disabled: true,
    });
    (__VLS_ctx.brandingData.apply_to.scoreboard);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "checkbox-label" },
    });
    /** @type {__VLS_StyleScopedClasses['checkbox-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "checkbox",
        disabled: true,
    });
    (__VLS_ctx.brandingData.apply_to.admin);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    if (Object.keys(__VLS_ctx.brandingData.assets).length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "section-assets" },
        });
        /** @type {__VLS_StyleScopedClasses['section-assets']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "assets-list" },
        });
        /** @type {__VLS_StyleScopedClasses['assets-list']} */ ;
        for (const [asset, idx] of __VLS_vFor((Object.values(__VLS_ctx.brandingData.assets)))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "asset-item" },
            });
            /** @type {__VLS_StyleScopedClasses['asset-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "asset-type" },
            });
            /** @type {__VLS_StyleScopedClasses['asset-type']} */ ;
            (asset.type);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "asset-name" },
            });
            /** @type {__VLS_StyleScopedClasses['asset-name']} */ ;
            (asset.name);
            if (asset.dimensions) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "asset-dimensions" },
                });
                /** @type {__VLS_StyleScopedClasses['asset-dimensions']} */ ;
                (asset.dimensions[0]);
                (asset.dimensions[1]);
            }
            // @ts-ignore
            [refreshBranding, loading, loading, loading, error, error, clearError, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData, brandingData,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "section-status" },
    });
    /** @type {__VLS_StyleScopedClasses['section-status']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "status-info" },
    });
    /** @type {__VLS_StyleScopedClasses['status-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "status-row" },
    });
    /** @type {__VLS_StyleScopedClasses['status-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: (['status-badge', { active: __VLS_ctx.brandingData.is_active }]) },
    });
    /** @type {__VLS_StyleScopedClasses['active']} */ ;
    /** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
    (__VLS_ctx.brandingData.is_active ? 'Active' : 'Inactive');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "status-row" },
    });
    /** @type {__VLS_StyleScopedClasses['status-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "timestamp" },
    });
    /** @type {__VLS_StyleScopedClasses['timestamp']} */ ;
    (__VLS_ctx.formatDate(__VLS_ctx.brandingData.created_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "status-row" },
    });
    /** @type {__VLS_StyleScopedClasses['status-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "timestamp" },
    });
    /** @type {__VLS_StyleScopedClasses['timestamp']} */ ;
    (__VLS_ctx.formatDate(__VLS_ctx.brandingData.updated_at));
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "state-no-data" },
    });
    /** @type {__VLS_StyleScopedClasses['state-no-data']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "help-text" },
    });
    /** @type {__VLS_StyleScopedClasses['help-text']} */ ;
}
// @ts-ignore
[brandingData, brandingData, brandingData, brandingData, formatDate, formatDate,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __typeProps: {},
});
export default {};
