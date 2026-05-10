/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
const props = defineProps();
const noteText = ref('');
const lastSaved = ref(null);
const isSaving = ref(false);
const showHistory = ref(false);
const noteHistory = ref([]);
let autoSaveInterval = null;
const STORAGE_KEY_PREFIX = 'coach-notebook-';
const MAX_HISTORY = 10; // Keep last 10 saves
// Load note from localStorage on mount
onMounted(() => {
    if (props.profile?.player_id) {
        const storageKey = STORAGE_KEY_PREFIX + props.profile.player_id;
        const savedNote = localStorage.getItem(storageKey);
        if (savedNote) {
            try {
                const parsed = JSON.parse(savedNote);
                noteText.value = parsed.content || '';
                lastSaved.value = parsed.lastSaved ? new Date(parsed.lastSaved) : null;
                noteHistory.value = (parsed.history || []).map((entry) => ({
                    ...entry,
                    timestamp: new Date(entry.timestamp),
                }));
            }
            catch (err) {
                console.warn('Failed to restore coach notebook:', err);
            }
        }
    }
    // Start autosave interval
    autoSaveInterval = setInterval(autoSave, 30000); // Every 30 seconds
});
// Cleanup on unmount
onUnmounted(() => {
    if (autoSaveInterval)
        clearInterval(autoSaveInterval);
    // Final save on unmount
    if (noteText.value || lastSaved.value) {
        autoSave();
    }
});
// Watch profile changes to reload notes
watch(() => props.profile?.player_id, () => {
    if (props.profile?.player_id) {
        const storageKey = STORAGE_KEY_PREFIX + props.profile.player_id;
        const savedNote = localStorage.getItem(storageKey);
        if (savedNote) {
            try {
                const parsed = JSON.parse(savedNote);
                noteText.value = parsed.content || '';
                lastSaved.value = parsed.lastSaved ? new Date(parsed.lastSaved) : null;
                noteHistory.value = (parsed.history || []).map((entry) => ({
                    ...entry,
                    timestamp: new Date(entry.timestamp),
                }));
            }
            catch (err) {
                console.warn('Failed to restore coach notebook:', err);
            }
        }
    }
});
// Auto-save function
function autoSave() {
    if (!props.profile?.player_id)
        return;
    if (!noteText.value && !lastSaved.value)
        return;
    isSaving.value = true;
    // Simulate network delay for realism
    setTimeout(() => {
        try {
            const storageKey = STORAGE_KEY_PREFIX + props.profile.player_id;
            const currentTime = new Date();
            // Add to history
            const historyEntry = {
                timestamp: currentTime,
                content: noteText.value,
            };
            noteHistory.value = [historyEntry, ...noteHistory.value].slice(0, MAX_HISTORY);
            // Save to localStorage
            localStorage.setItem(storageKey, JSON.stringify({
                content: noteText.value,
                lastSaved: currentTime.toISOString(),
                playerId: props.profile.player_id,
                history: noteHistory.value.map((entry) => ({
                    timestamp: entry.timestamp.toISOString(),
                    content: entry.content,
                })),
            }));
            lastSaved.value = currentTime;
            isSaving.value = false;
        }
        catch (err) {
            console.error('Failed to save coach notebook:', err);
            isSaving.value = false;
        }
    }, 300);
}
// Manual note change handler
function onNoteChange() {
    // Autosave will handle it on timer
}
// Restore a previous version
function restoreVersion(content) {
    if (confirm('Restore this version? Current notes will be overwritten.')) {
        noteText.value = content;
        autoSave();
        showHistory.value = false;
    }
}
// Formatting utilities
function formatTime(date) {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000)
        return 'just now';
    if (diff < 3600000)
        return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000)
        return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}
function formatFullTime(date) {
    return date.toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function truncateText(text, length) {
    return text.length > length ? text.substring(0, length) + '...' : text;
}
// Stats
const wordCount = computed(() => {
    return noteText.value.trim().split(/\s+/).filter((word) => word.length > 0).length;
});
const charCount = computed(() => {
    return noteText.value.length;
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
/** @type {__VLS_StyleScopedClasses['save-status']} */ ;
/** @type {__VLS_StyleScopedClasses['notebook-textarea']} */ ;
/** @type {__VLS_StyleScopedClasses['notebook-textarea']} */ ;
/** @type {__VLS_StyleScopedClasses['history-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['history-header']} */ ;
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['history-entry']} */ ;
/** @type {__VLS_StyleScopedClasses['restore-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['notebook-header']} */ ;
/** @type {__VLS_StyleScopedClasses['notebook-footer']} */ ;
/** @type {__VLS_StyleScopedClasses['footer-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['history-entry']} */ ;
/** @type {__VLS_StyleScopedClasses['history-time']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coach-notebook-widget" },
});
/** @type {__VLS_StyleScopedClasses['coach-notebook-widget']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "notebook-header" },
});
/** @type {__VLS_StyleScopedClasses['notebook-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
    ...{ class: "notebook-title" },
});
/** @type {__VLS_StyleScopedClasses['notebook-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "notebook-info" },
});
/** @type {__VLS_StyleScopedClasses['notebook-info']} */ ;
if (__VLS_ctx.lastSaved) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "save-status" },
        ...{ class: ({ saving: __VLS_ctx.isSaving }) },
    });
    /** @type {__VLS_StyleScopedClasses['save-status']} */ ;
    /** @type {__VLS_StyleScopedClasses['saving']} */ ;
    (__VLS_ctx.isSaving ? '💾 Saving...' : `✓ Saved ${__VLS_ctx.formatTime(__VLS_ctx.lastSaved)}`);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "notebook-container" },
});
/** @type {__VLS_StyleScopedClasses['notebook-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    ...{ onInput: (__VLS_ctx.onNoteChange) },
    value: (__VLS_ctx.noteText),
    ...{ class: "notebook-textarea" },
    placeholder: "Write your coaching notes here... (autosaves every 30 seconds)",
});
/** @type {__VLS_StyleScopedClasses['notebook-textarea']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "notebook-footer" },
});
/** @type {__VLS_StyleScopedClasses['notebook-footer']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "footer-stats" },
});
/** @type {__VLS_StyleScopedClasses['footer-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
(__VLS_ctx.wordCount);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "stat" },
});
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
(__VLS_ctx.charCount);
if (__VLS_ctx.noteHistory.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "footer-history" },
    });
    /** @type {__VLS_StyleScopedClasses['footer-history']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.noteHistory.length > 0))
                    return;
                __VLS_ctx.showHistory = !__VLS_ctx.showHistory;
                // @ts-ignore
                [lastSaved, lastSaved, isSaving, isSaving, formatTime, onNoteChange, noteText, wordCount, charCount, noteHistory, showHistory, showHistory,];
            } },
        ...{ class: "history-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['history-btn']} */ ;
    (__VLS_ctx.noteHistory.length);
    (__VLS_ctx.noteHistory.length !== 1 ? 's' : '');
}
if (__VLS_ctx.showHistory && __VLS_ctx.noteHistory.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "notebook-history" },
    });
    /** @type {__VLS_StyleScopedClasses['notebook-history']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "history-header" },
    });
    /** @type {__VLS_StyleScopedClasses['history-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showHistory && __VLS_ctx.noteHistory.length > 0))
                    return;
                __VLS_ctx.showHistory = false;
                // @ts-ignore
                [noteHistory, noteHistory, noteHistory, showHistory, showHistory,];
            } },
        ...{ class: "close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "history-list" },
    });
    /** @type {__VLS_StyleScopedClasses['history-list']} */ ;
    for (const [entry, idx] of __VLS_vFor((__VLS_ctx.noteHistory))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (`history-${idx}`),
            ...{ class: "history-entry" },
        });
        /** @type {__VLS_StyleScopedClasses['history-entry']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "history-time" },
        });
        /** @type {__VLS_StyleScopedClasses['history-time']} */ ;
        (__VLS_ctx.formatFullTime(entry.timestamp));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "history-preview" },
        });
        /** @type {__VLS_StyleScopedClasses['history-preview']} */ ;
        (__VLS_ctx.truncateText(entry.content, 60));
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.showHistory && __VLS_ctx.noteHistory.length > 0))
                        return;
                    __VLS_ctx.restoreVersion(entry.content);
                    // @ts-ignore
                    [noteHistory, formatFullTime, truncateText, restoreVersion,];
                } },
            ...{ class: "restore-btn" },
            title: "Restore this version",
        });
        /** @type {__VLS_StyleScopedClasses['restore-btn']} */ ;
        // @ts-ignore
        [];
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
