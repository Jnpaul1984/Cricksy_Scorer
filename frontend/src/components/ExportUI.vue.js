/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, reactive } from 'vue';
import { BaseButton, BaseCard } from '@/components';
const props = defineProps();
const showModal = ref(false);
const isExporting = ref(false);
// Export format options
const formats = [
    {
        value: 'csv',
        label: 'CSV',
        icon: '📊',
        desc: 'Comma-separated values, open in Excel',
    },
    {
        value: 'json',
        label: 'JSON',
        icon: '{}',
        desc: 'JSON format for programmatic use',
    },
];
const exportFormat = ref('csv');
// Filter state
const filters = reactive({
    dateFrom: '',
    dateTo: '',
    player: '',
    dismissalType: '',
    phase: '',
});
const resetFilters = () => {
    filters.dateFrom = '';
    filters.dateTo = '';
    filters.player = '';
    filters.dismissalType = '';
    filters.phase = '';
};
// Computed properties
const formatLabel = computed(() => {
    const fmt = formats.find((f) => f.value === exportFormat.value);
    return fmt?.label || 'Unknown';
});
// Estimate rows and file size based on filters
const estimatedRows = computed(() => {
    let count = props.data?.length || 0;
    // Apply rough filter reduction
    if (filters.player)
        count = Math.floor(count * 0.5);
    if (filters.dismissalType)
        count = Math.floor(count * 0.7);
    if (filters.phase)
        count = Math.floor(count * 0.33);
    return Math.max(0, count);
});
const estimatedFileSize = computed(() => {
    const rowSize = exportFormat.value === 'csv' ? 120 : 180; // bytes per row
    const totalBytes = estimatedRows.value * rowSize;
    if (totalBytes < 1024)
        return totalBytes + ' B';
    if (totalBytes < 1024 * 1024)
        return (totalBytes / 1024).toFixed(1) + ' KB';
    return (totalBytes / (1024 * 1024)).toFixed(1) + ' MB';
});
// Download handler
async function downloadData() {
    isExporting.value = true;
    try {
        // Simulate data preparation
        await new Promise((resolve) => setTimeout(resolve, 500));
        // Generate mock data
        const exportData = generateExportData();
        // Create file and download
        if (exportFormat.value === 'csv') {
            downloadCSV(exportData);
        }
        else {
            downloadJSON(exportData);
        }
        // Close modal
        showModal.value = false;
    }
    catch (error) {
        console.error('Export failed:', error);
        alert('Export failed. Please try again.');
    }
    finally {
        isExporting.value = false;
    }
}
// Generate mock data based on filters
function generateExportData() {
    const sampleData = [
        {
            date: '2025-12-18',
            player: 'Player A',
            runs: 45,
            balls: 32,
            strikeRate: 140.6,
            dismissal: 'caught',
            phase: 'powerplay',
        },
        {
            date: '2025-12-18',
            player: 'Player B',
            runs: 28,
            balls: 21,
            strikeRate: 133.3,
            dismissal: 'not_out',
            phase: 'middle',
        },
        {
            date: '2025-12-17',
            player: 'Player C',
            runs: 67,
            balls: 48,
            strikeRate: 139.6,
            dismissal: 'bowled',
            phase: 'death',
        },
    ];
    return sampleData.filter((row) => {
        if (filters.dateFrom && row.date < filters.dateFrom)
            return false;
        if (filters.dateTo && row.date > filters.dateTo)
            return false;
        if (filters.player && !row.player.toLowerCase().includes(filters.player.toLowerCase()))
            return false;
        if (filters.dismissalType && row.dismissal !== filters.dismissalType)
            return false;
        if (filters.phase && row.phase !== filters.phase)
            return false;
        return true;
    });
}
// CSV download
function downloadCSV(data) {
    if (data.length === 0) {
        alert('No data to export with current filters');
        return;
    }
    const headers = Object.keys(data[0]);
    const csv = [
        headers.join(','),
        ...data.map((row) => headers
            .map((h) => {
            const val = row[h];
            if (typeof val === 'string' && val.includes(',')) {
                return `"${val}"`;
            }
            return val;
        })
            .join(',')),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    downloadBlob(blob, `export-${new Date().toISOString().split('T')[0]}.csv`);
}
// JSON download
function downloadJSON(data) {
    if (data.length === 0) {
        alert('No data to export with current filters');
        return;
    }
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
    downloadBlob(blob, `export-${new Date().toISOString().split('T')[0]}.json`);
}
// Generic blob download
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
// Close modal
function closeModal() {
    showModal.value = false;
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
/** @type {__VLS_StyleScopedClasses['export-close']} */ ;
/** @type {__VLS_StyleScopedClasses['format-option']} */ ;
/** @type {__VLS_StyleScopedClasses['format-option']} */ ;
/** @type {__VLS_StyleScopedClasses['format-option']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
/** @type {__VLS_StyleScopedClasses['reset-filters-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['export-modal-overlay']} */ ;
/** @type {__VLS_StyleScopedClasses['export-modal']} */ ;
/** @type {__VLS_StyleScopedClasses['export-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['date-range-inputs']} */ ;
/** @type {__VLS_StyleScopedClasses['export-actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "export-ui" },
});
/** @type {__VLS_StyleScopedClasses['export-ui']} */ ;
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "ghost",
    ...{ class: "export-trigger-btn" },
    title: "Export data as CSV or JSON",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    size: "sm",
    variant: "ghost",
    ...{ class: "export-trigger-btn" },
    title: "Export data as CSV or JSON",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_5;
const __VLS_6 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.showModal = true;
            // @ts-ignore
            [showModal,];
        } });
/** @type {__VLS_StyleScopedClasses['export-trigger-btn']} */ ;
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[];
var __VLS_3;
var __VLS_4;
if (__VLS_ctx.showModal) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeModal) },
        ...{ class: "export-modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['export-modal-overlay']} */ ;
    let __VLS_8;
    /** @ts-ignore @type { | typeof __VLS_components.BaseCard | typeof __VLS_components.BaseCard} */
    BaseCard;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
        ...{ class: "export-modal" },
    }));
    const __VLS_10 = __VLS_9({
        ...{ class: "export-modal" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    /** @type {__VLS_StyleScopedClasses['export-modal']} */ ;
    const { default: __VLS_13 } = __VLS_11.slots;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-header" },
    });
    /** @type {__VLS_StyleScopedClasses['export-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        ...{ class: "export-title" },
    });
    /** @type {__VLS_StyleScopedClasses['export-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeModal) },
        ...{ class: "export-close" },
        title: "Close",
    });
    /** @type {__VLS_StyleScopedClasses['export-close']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-content" },
    });
    /** @type {__VLS_StyleScopedClasses['export-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-section" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "export-section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-format-options" },
    });
    /** @type {__VLS_StyleScopedClasses['export-format-options']} */ ;
    for (const [fmt] of __VLS_vFor((__VLS_ctx.formats))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            key: (fmt.value),
            ...{ class: "format-option" },
        });
        /** @type {__VLS_StyleScopedClasses['format-option']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            type: "radio",
            value: (fmt.value),
        });
        (__VLS_ctx.exportFormat);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "format-label" },
        });
        /** @type {__VLS_StyleScopedClasses['format-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "format-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['format-icon']} */ ;
        (fmt.icon);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "format-text" },
        });
        /** @type {__VLS_StyleScopedClasses['format-text']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "format-name" },
        });
        /** @type {__VLS_StyleScopedClasses['format-name']} */ ;
        (fmt.label);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "format-desc" },
        });
        /** @type {__VLS_StyleScopedClasses['format-desc']} */ ;
        (fmt.desc);
        // @ts-ignore
        [showModal, closeModal, closeModal, formats, exportFormat,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-section" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "export-section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['export-filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "filter-label" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "date-range-inputs" },
    });
    /** @type {__VLS_StyleScopedClasses['date-range-inputs']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
        ...{ class: "filter-input" },
        placeholder: "From",
    });
    (__VLS_ctx.filters.dateFrom);
    /** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "date-separator" },
    });
    /** @type {__VLS_StyleScopedClasses['date-separator']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
        ...{ class: "filter-input" },
        placeholder: "To",
    });
    (__VLS_ctx.filters.dateTo);
    /** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['export-filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "filter-label" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.filters.player),
        type: "text",
        ...{ class: "filter-input" },
        placeholder: "Search by name or ID...",
    });
    /** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['export-filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "filter-label" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.filters.dismissalType),
        ...{ class: "filter-input" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bowled",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "caught",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "lbw",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "stumped",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "run_out",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-filter-group" },
    });
    /** @type {__VLS_StyleScopedClasses['export-filter-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "filter-label" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.filters.phase),
        ...{ class: "filter-input" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "powerplay",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "middle",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "death",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.resetFilters) },
        ...{ class: "reset-filters-btn" },
        title: "Clear all filters",
    });
    /** @type {__VLS_StyleScopedClasses['reset-filters-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-section" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
        ...{ class: "export-section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['export-section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-preview" },
    });
    /** @type {__VLS_StyleScopedClasses['export-preview']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "preview-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-label" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-value" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-value']} */ ;
    (__VLS_ctx.estimatedRows);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "preview-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-label" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-value" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-value']} */ ;
    (__VLS_ctx.estimatedFileSize);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "preview-stat" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-stat']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-label" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "preview-value" },
    });
    /** @type {__VLS_StyleScopedClasses['preview-value']} */ ;
    (__VLS_ctx.formatLabel);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "export-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['export-actions']} */ ;
    let __VLS_14;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }));
    const __VLS_16 = __VLS_15({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_15));
    let __VLS_19;
    const __VLS_20 = ({ click: {} },
        { onClick: (__VLS_ctx.closeModal) });
    const { default: __VLS_21 } = __VLS_17.slots;
    // @ts-ignore
    [closeModal, filters, filters, filters, filters, filters, resetFilters, estimatedRows, estimatedFileSize, formatLabel,];
    var __VLS_17;
    var __VLS_18;
    let __VLS_22;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_23 = __VLS_asFunctionalComponent1(__VLS_22, new __VLS_22({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
        loading: (__VLS_ctx.isExporting),
    }));
    const __VLS_24 = __VLS_23({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
        loading: (__VLS_ctx.isExporting),
    }, ...__VLS_functionalComponentArgsRest(__VLS_23));
    let __VLS_27;
    const __VLS_28 = ({ click: {} },
        { onClick: (__VLS_ctx.downloadData) });
    const { default: __VLS_29 } = __VLS_25.slots;
    if (__VLS_ctx.isExporting) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    }
    // @ts-ignore
    [isExporting, isExporting, downloadData,];
    var __VLS_25;
    var __VLS_26;
    // @ts-ignore
    [];
    var __VLS_11;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
