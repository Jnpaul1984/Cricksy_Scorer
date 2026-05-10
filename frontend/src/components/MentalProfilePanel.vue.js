/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted } from 'vue';
import { BaseButton } from '@/components';
import { getMentalQuestionnaireTemplate, getLatestMentalProfile, getMentalResponseHistory, submitMentalQuestionnaire, } from '@/services/mentalQuestionnaireApi';
const props = defineProps();
/** Extract a human-readable message from an unknown API error. */
function apiErrorMessage(err) {
    if (!err)
        return 'An unknown error occurred.';
    if (typeof err === 'string')
        return err;
    const e = err;
    if (typeof e.message === 'string' && e.message)
        return e.message;
    return 'An unexpected error occurred.';
}
/** Return the HTTP status code embedded by apiRequest, or undefined. */
function apiErrorStatus(err) {
    if (!err || typeof err !== 'object')
        return undefined;
    return err.status;
}
// ── Latest profile ─────────────────────────────────────────────────────────
const summaryLoading = ref(false);
const summaryError = ref(null);
const latestProfile = ref(null);
async function loadLatestProfile() {
    summaryLoading.value = true;
    summaryError.value = null;
    try {
        latestProfile.value = await getLatestMentalProfile(props.playerId);
    }
    catch (err) {
        if (apiErrorStatus(err) === 404) {
            // No profile yet — not an error condition
            latestProfile.value = null;
        }
        else {
            summaryError.value = apiErrorMessage(err);
        }
    }
    finally {
        summaryLoading.value = false;
    }
}
// ── Template ───────────────────────────────────────────────────────────────
const templateLoading = ref(false);
const templateError = ref(null);
const template = ref(null);
const showForm = ref(false);
async function openForm() {
    if (template.value) {
        showForm.value = true;
        return;
    }
    templateLoading.value = true;
    templateError.value = null;
    try {
        template.value = await getMentalQuestionnaireTemplate();
        showForm.value = true;
    }
    catch (err) {
        templateError.value = apiErrorMessage(err);
    }
    finally {
        templateLoading.value = false;
    }
}
function closeForm() {
    showForm.value = false;
    submitAttempted.value = false;
    submitError.value = null;
    answers.value = {};
}
// ── Questionnaire submission ────────────────────────────────────────────────
const answers = ref({});
const isSubmitting = ref(false);
const submitError = ref(null);
const submitAttempted = ref(false);
async function handleSubmit() {
    submitAttempted.value = true;
    // Validate: every question must have an answer
    if (!template.value)
        return;
    const allQuestionIds = template.value.categories.flatMap((c) => c.questions.map((q) => q.id));
    const allAnswered = allQuestionIds.every((id) => answers.value[id] !== undefined);
    if (!allAnswered)
        return;
    isSubmitting.value = true;
    submitError.value = null;
    try {
        const payload = allQuestionIds.map((id) => ({ question_id: id, score: answers.value[id] }));
        const updated = await submitMentalQuestionnaire(props.playerId, payload);
        latestProfile.value = updated;
        // Refresh history
        await loadHistory();
        closeForm();
    }
    catch (err) {
        submitError.value = apiErrorMessage(err);
    }
    finally {
        isSubmitting.value = false;
    }
}
// ── History ─────────────────────────────────────────────────────────────────
const historyLoading = ref(false);
const historyError = ref(null);
const history = ref([]);
async function loadHistory() {
    historyLoading.value = true;
    historyError.value = null;
    try {
        history.value = await getMentalResponseHistory(props.playerId);
    }
    catch (err) {
        historyError.value = apiErrorMessage(err);
    }
    finally {
        historyLoading.value = false;
    }
}
// ── Helpers ─────────────────────────────────────────────────────────────────
// Category display labels aligned with backend MentalQuestionnaireCategory enum
// (backend/sql_app/models.py). Update here if the backend adds new categories.
const CATEGORY_LABELS = {
    mental_toughness: 'Mental Toughness',
    pressure_handling: 'Pressure Handling',
    game_awareness: 'Game Awareness / Cricket IQ',
    training_habits: 'Training Habits & Discipline',
};
function formatCategory(raw) {
    return CATEGORY_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
function formatDate(iso) {
    try {
        return new Date(iso).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }
    catch {
        return iso;
    }
}
// ── Mental report export ─────────────────────────────────────────────────────
function exportMentalReport() {
    const profile = latestProfile.value;
    if (!profile)
        return;
    const exportDate = new Date().toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
    const assessmentDate = formatDate(profile.created_at);
    const displayName = props.playerName || `Player ${props.playerId.slice(0, 8)}`;
    const categoryRowsHtml = profile.category_scores
        .map((cs) => `
      <tr>
        <td>${formatCategory(cs.category)}</td>
        <td class="score-cell">${cs.average_score.toFixed(1)} / 5</td>
        <td>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(cs.average_score / 5) * 100}%"></div>
          </div>
        </td>
      </tr>`)
        .join('');
    const strengthsHtml = profile.strengths.length
        ? profile.strengths.map((s) => `<li>${s}</li>`).join('')
        : '<li>No strengths recorded.</li>';
    const developmentHtml = profile.development_areas.length
        ? profile.development_areas.map((d) => `<li>${d}</li>`).join('')
        : '<li>No coaching focus areas recorded.</li>';
    const printContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Mental Analysis Report – ${displayName}</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 32px; color: #333; max-width: 800px; margin: 0 auto; }
    h1 { color: #1a1a2e; border-bottom: 2px solid #1976d2; padding-bottom: 10px; margin-bottom: 4px; }
    h2 { color: #1976d2; margin-top: 28px; margin-bottom: 8px; }
    .meta { font-size: 13px; color: #666; margin-bottom: 24px; }
    .overall-score { font-size: 28px; font-weight: bold; color: #1976d2; }
    .summary-text { font-size: 14px; line-height: 1.6; margin: 8px 0 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; font-size: 13px; }
    th { background: #f5f5f5; font-weight: 600; }
    .score-cell { text-align: center; font-weight: bold; color: #1976d2; }
    .bar-track { height: 8px; background: #e0e0e0; border-radius: 4px; min-width: 120px; }
    .bar-fill { height: 100%; background: #1976d2; border-radius: 4px; }
    ul { margin: 8px 0; padding-left: 20px; }
    li { font-size: 13px; margin-bottom: 4px; line-height: 1.5; }
    .disclaimer { margin-top: 40px; padding: 12px 16px; background: #f5f5f5;
                  border-left: 3px solid #1976d2; font-size: 12px; color: #555;
                  border-radius: 4px; }
    .footer { margin-top: 16px; font-size: 11px; color: #999; text-align: center; }
    @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  </style>
</head>
<body>
  <h1>🧠 Mental Analysis Report</h1>
  <div class="meta">
    <strong>Player:</strong> ${displayName}<br />
    <strong>Assessment date:</strong> ${assessmentDate}<br />
    <strong>Report generated:</strong> ${exportDate}
  </div>

  <h2>Overall Score</h2>
  <div class="overall-score">${profile.overall_average_score.toFixed(1)} / 5</div>
  <p class="summary-text">${profile.overall_summary}</p>

  <h2>Category Scores</h2>
  <table>
    <thead>
      <tr><th>Category</th><th>Score</th><th>Progress</th></tr>
    </thead>
    <tbody>
      ${categoryRowsHtml || '<tr><td colspan="3">No category data.</td></tr>'}
    </tbody>
  </table>

  <h2>💪 Coaching Strengths</h2>
  <ul>${strengthsHtml}</ul>

  <h2>🎯 Growth Opportunities / Coaching Focus</h2>
  <ul>${developmentHtml}</ul>

  <div class="disclaimer">
    ℹ️ This report is a coaching development tool and is not a medical or psychological diagnosis.
  </div>

  <div class="footer">Cricksy Scorer – Mental Analysis Report · ${exportDate}</div>
</body>
</html>`;
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        alert('Could not open report window. Please allow pop-ups and try again.');
        return;
    }
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.onload = () => {
        printWindow.print();
    };
}
// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
    await Promise.all([loadLatestProfile(), loadHistory()]);
});
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['score-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['score-btn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "mental-profile-panel" },
});
/** @type {__VLS_StyleScopedClasses['mental-profile-panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coaching-disclaimer" },
});
/** @type {__VLS_StyleScopedClasses['coaching-disclaimer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "disclaimer-icon" },
});
/** @type {__VLS_StyleScopedClasses['disclaimer-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "profile-summary-section" },
});
/** @type {__VLS_StyleScopedClasses['profile-summary-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header" },
});
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header-actions" },
});
/** @type {__VLS_StyleScopedClasses['section-header-actions']} */ ;
if (__VLS_ctx.latestProfile) {
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.summaryLoading),
    }));
    const __VLS_2 = __VLS_1({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.summaryLoading),
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_5;
    const __VLS_6 = ({ click: {} },
        { onClick: (__VLS_ctx.exportMentalReport) });
    const { default: __VLS_7 } = __VLS_3.slots;
    // @ts-ignore
    [latestProfile, summaryLoading, exportMentalReport,];
    var __VLS_3;
    var __VLS_4;
}
let __VLS_8;
/** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
BaseButton;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    disabled: (__VLS_ctx.summaryLoading),
}));
const __VLS_10 = __VLS_9({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "sm",
    disabled: (__VLS_ctx.summaryLoading),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_13;
const __VLS_14 = ({ click: {} },
    { onClick: (__VLS_ctx.loadLatestProfile) });
const { default: __VLS_15 } = __VLS_11.slots;
if (__VLS_ctx.summaryLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
}
// @ts-ignore
[summaryLoading, summaryLoading, loadLatestProfile,];
var __VLS_11;
var __VLS_12;
if (__VLS_ctx.summaryLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
        'aria-busy': "true",
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "skeleton-line" },
    });
    /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "skeleton-line" },
    });
    /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "skeleton-line short" },
    });
    /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['short']} */ ;
}
else if (__VLS_ctx.summaryError) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error-text" },
    });
    /** @type {__VLS_StyleScopedClasses['error-text']} */ ;
    (__VLS_ctx.summaryError);
}
else if (!__VLS_ctx.latestProfile) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-hint']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "profile-data" },
    });
    /** @type {__VLS_StyleScopedClasses['profile-data']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "overall-score-row" },
    });
    /** @type {__VLS_StyleScopedClasses['overall-score-row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "score-label" },
    });
    /** @type {__VLS_StyleScopedClasses['score-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "overall-score" },
    });
    /** @type {__VLS_StyleScopedClasses['overall-score']} */ ;
    (__VLS_ctx.latestProfile.overall_average_score.toFixed(1));
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "score-date" },
    });
    /** @type {__VLS_StyleScopedClasses['score-date']} */ ;
    (__VLS_ctx.formatDate(__VLS_ctx.latestProfile.created_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "overall-summary" },
    });
    /** @type {__VLS_StyleScopedClasses['overall-summary']} */ ;
    (__VLS_ctx.latestProfile.overall_summary);
    if (__VLS_ctx.latestProfile.category_scores.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "category-scores" },
        });
        /** @type {__VLS_StyleScopedClasses['category-scores']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "subsection-title" },
        });
        /** @type {__VLS_StyleScopedClasses['subsection-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "scores-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['scores-grid']} */ ;
        for (const [cs] of __VLS_vFor((__VLS_ctx.latestProfile.category_scores))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (cs.category),
                ...{ class: "score-card" },
            });
            /** @type {__VLS_StyleScopedClasses['score-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "score-card-label" },
            });
            /** @type {__VLS_StyleScopedClasses['score-card-label']} */ ;
            (__VLS_ctx.formatCategory(cs.category));
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "score-card-value" },
            });
            /** @type {__VLS_StyleScopedClasses['score-card-value']} */ ;
            (cs.average_score.toFixed(1));
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "score-bar-track" },
            });
            /** @type {__VLS_StyleScopedClasses['score-bar-track']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                ...{ class: "score-bar-fill" },
                ...{ style: ({ width: `${(cs.average_score / 5) * 100}%` }) },
            });
            /** @type {__VLS_StyleScopedClasses['score-bar-fill']} */ ;
            // @ts-ignore
            [latestProfile, latestProfile, latestProfile, latestProfile, latestProfile, latestProfile, summaryLoading, summaryError, summaryError, formatDate, formatCategory,];
        }
    }
    if (__VLS_ctx.latestProfile.strengths.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "strengths-block" },
        });
        /** @type {__VLS_StyleScopedClasses['strengths-block']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "subsection-title" },
        });
        /** @type {__VLS_StyleScopedClasses['subsection-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "insight-list" },
        });
        /** @type {__VLS_StyleScopedClasses['insight-list']} */ ;
        for (const [s, idx] of __VLS_vFor((__VLS_ctx.latestProfile.strengths))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (idx),
            });
            (s);
            // @ts-ignore
            [latestProfile, latestProfile,];
        }
    }
    if (__VLS_ctx.latestProfile.development_areas.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "development-block" },
        });
        /** @type {__VLS_StyleScopedClasses['development-block']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "subsection-title" },
        });
        /** @type {__VLS_StyleScopedClasses['subsection-title']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "insight-list" },
        });
        /** @type {__VLS_StyleScopedClasses['insight-list']} */ ;
        for (const [d, idx] of __VLS_vFor((__VLS_ctx.latestProfile.development_areas))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (idx),
            });
            (d);
            // @ts-ignore
            [latestProfile, latestProfile,];
        }
    }
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "questionnaire-section" },
});
/** @type {__VLS_StyleScopedClasses['questionnaire-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header" },
});
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
if (!__VLS_ctx.showForm) {
    let __VLS_16;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent1(__VLS_16, new __VLS_16({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
        disabled: (__VLS_ctx.templateLoading),
    }));
    const __VLS_18 = __VLS_17({
        ...{ 'onClick': {} },
        variant: "primary",
        size: "sm",
        disabled: (__VLS_ctx.templateLoading),
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    let __VLS_21;
    const __VLS_22 = ({ click: {} },
        { onClick: (__VLS_ctx.openForm) });
    const { default: __VLS_23 } = __VLS_19.slots;
    (__VLS_ctx.templateLoading ? 'Loading…' : 'Launch Questionnaire');
    // @ts-ignore
    [showForm, templateLoading, templateLoading, openForm,];
    var __VLS_19;
    var __VLS_20;
}
else {
    let __VLS_24;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }));
    const __VLS_26 = __VLS_25({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    let __VLS_29;
    const __VLS_30 = ({ click: {} },
        { onClick: (__VLS_ctx.closeForm) });
    const { default: __VLS_31 } = __VLS_27.slots;
    // @ts-ignore
    [closeForm,];
    var __VLS_27;
    var __VLS_28;
}
if (__VLS_ctx.templateError) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error-text" },
    });
    /** @type {__VLS_StyleScopedClasses['error-text']} */ ;
    (__VLS_ctx.templateError);
}
if (__VLS_ctx.showForm && __VLS_ctx.template) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "questionnaire-form" },
    });
    /** @type {__VLS_StyleScopedClasses['questionnaire-form']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.handleSubmit) },
    });
    for (const [cat] of __VLS_vFor((__VLS_ctx.template.categories))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (cat.category),
            ...{ class: "category-group" },
        });
        /** @type {__VLS_StyleScopedClasses['category-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
            ...{ class: "category-heading" },
        });
        /** @type {__VLS_StyleScopedClasses['category-heading']} */ ;
        (__VLS_ctx.formatCategory(cat.category));
        for (const [q] of __VLS_vFor((cat.questions))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (q.id),
                ...{ class: "question-item" },
            });
            /** @type {__VLS_StyleScopedClasses['question-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
                for: (`q-${q.id}`),
                ...{ class: "question-label" },
            });
            /** @type {__VLS_StyleScopedClasses['question-label']} */ ;
            (q.question_text);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "score-selector" },
                role: "group",
                'aria-label': (`Score for question ${q.id}, 1 to 5`),
            });
            /** @type {__VLS_StyleScopedClasses['score-selector']} */ ;
            for (const [n] of __VLS_vFor((5))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!(__VLS_ctx.showForm && __VLS_ctx.template))
                                return;
                            __VLS_ctx.answers[q.id] = n;
                            // @ts-ignore
                            [formatCategory, showForm, templateError, templateError, template, template, handleSubmit, answers,];
                        } },
                    key: (n),
                    type: "button",
                    ...{ class: "score-btn" },
                    ...{ class: ({ active: __VLS_ctx.answers[q.id] === n }) },
                    'aria-pressed': (__VLS_ctx.answers[q.id] === n),
                });
                /** @type {__VLS_StyleScopedClasses['score-btn']} */ ;
                /** @type {__VLS_StyleScopedClasses['active']} */ ;
                (n);
                // @ts-ignore
                [answers, answers,];
            }
            if (__VLS_ctx.submitAttempted && !__VLS_ctx.answers[q.id]) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "field-error" },
                });
                /** @type {__VLS_StyleScopedClasses['field-error']} */ ;
            }
            // @ts-ignore
            [answers, submitAttempted,];
        }
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['form-actions']} */ ;
    if (__VLS_ctx.submitError) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "error-text" },
        });
        /** @type {__VLS_StyleScopedClasses['error-text']} */ ;
        (__VLS_ctx.submitError);
    }
    let __VLS_32;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent1(__VLS_32, new __VLS_32({
        type: "submit",
        variant: "primary",
        disabled: (__VLS_ctx.isSubmitting),
    }));
    const __VLS_34 = __VLS_33({
        type: "submit",
        variant: "primary",
        disabled: (__VLS_ctx.isSubmitting),
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    const { default: __VLS_37 } = __VLS_35.slots;
    (__VLS_ctx.isSubmitting ? 'Submitting…' : 'Submit Assessment');
    // @ts-ignore
    [submitError, submitError, isSubmitting, isSubmitting,];
    var __VLS_35;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "history-section" },
});
/** @type {__VLS_StyleScopedClasses['history-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "section-header" },
});
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
if (__VLS_ctx.historyLoading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "loading-state" },
        'aria-busy': "true",
    });
    /** @type {__VLS_StyleScopedClasses['loading-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "skeleton-line" },
    });
    /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "skeleton-line short" },
    });
    /** @type {__VLS_StyleScopedClasses['skeleton-line']} */ ;
    /** @type {__VLS_StyleScopedClasses['short']} */ ;
}
else if (__VLS_ctx.historyError) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "error-text" },
    });
    /** @type {__VLS_StyleScopedClasses['error-text']} */ ;
    (__VLS_ctx.historyError);
}
else if (__VLS_ctx.history.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
        ...{ class: "history-list" },
    });
    /** @type {__VLS_StyleScopedClasses['history-list']} */ ;
    for (const [item] of __VLS_vFor((__VLS_ctx.history))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
            key: (item.session_id),
            ...{ class: "history-item" },
        });
        /** @type {__VLS_StyleScopedClasses['history-item']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "history-item-row" },
        });
        /** @type {__VLS_StyleScopedClasses['history-item-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "history-date" },
        });
        /** @type {__VLS_StyleScopedClasses['history-date']} */ ;
        (__VLS_ctx.formatDate(item.created_at));
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "history-score" },
        });
        /** @type {__VLS_StyleScopedClasses['history-score']} */ ;
        (item.overall_average_score.toFixed(1));
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "history-summary" },
        });
        /** @type {__VLS_StyleScopedClasses['history-summary']} */ ;
        (item.overall_summary);
        // @ts-ignore
        [formatDate, historyLoading, historyError, historyError, history, history,];
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
