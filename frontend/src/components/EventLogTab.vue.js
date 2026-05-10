/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, watch, nextTick } from 'vue';
import { useGameStore } from '@/stores/gameStore';
import { useAuthStore } from '@/stores/authStore';
import { storeToRefs } from 'pinia';
const __VLS_props = defineProps();
// ---- Stores
const gameStore = useGameStore();
const authStore = useAuthStore();
const { liveSnapshot } = storeToRefs(gameStore);
const { user } = storeToRefs(authStore);
// ---- Event Management
const gameEvents = ref([]);
const newEventType = ref('other');
const newEventNote = ref('');
const showAddEvent = ref(false);
// ---- Timeline & Display
const timelineItems = computed(() => {
    const items = [];
    // Add deliveries from liveSnapshot
    if (liveSnapshot.value?.deliveries) {
        for (const d of liveSnapshot.value.deliveries) {
            const over = d.over_number ?? 0;
            const ball = d.ball_number ?? 0;
            const strikerName = getPlayerName(d.striker_id) || 'Unknown';
            const bowlerName = getPlayerName(d.bowler_id) || 'Unknown';
            let label = `${strikerName} vs ${bowlerName}: ${d.runs_scored ?? 0}${getExtraLabel(d)}`;
            if (d.is_wicket) {
                const dismissedName = getPlayerName(d.dismissed_player_id) || 'Unknown';
                label += ` - WICKET! ${dismissedName}`;
            }
            items.push({
                id: `delivery-${over}-${ball}`,
                type: 'delivery',
                timestamp: d.at_utc || new Date().toISOString(),
                content: label,
                metadata: { over, ball },
            });
        }
    }
    // Add non-delivery events
    for (const event of gameEvents.value) {
        items.push({
            id: `event-${event.id}`,
            type: 'event',
            timestamp: event.timestamp,
            content: formatEventContent(event),
            metadata: { eventType: event.type, enteredBy: event.enteredBy },
        });
    }
    // Sort by timestamp (newest first for log view)
    return items.sort((a, b) => {
        const aTime = new Date(a.timestamp).getTime();
        const bTime = new Date(b.timestamp).getTime();
        return bTime - aTime; // Descending
    });
});
// Scroll to bottom when items change
const timelineContainer = ref(null);
watch(timelineItems, async () => {
    await nextTick();
    if (timelineContainer.value) {
        timelineContainer.value.scrollTop = timelineContainer.value.scrollHeight;
    }
});
// ---- Over Summary
const lastCompletedOver = computed(() => {
    if (!liveSnapshot.value?.deliveries || liveSnapshot.value.deliveries.length === 0) {
        return null;
    }
    const deliveries = liveSnapshot.value.deliveries;
    const lastDelivery = deliveries[deliveries.length - 1];
    const lastOverNum = lastDelivery?.over_number ?? 0;
    // If we're in the middle of an over (ball_number > 0), show the previous completed over
    const targetOver = (lastDelivery?.ball_number ?? 0) === 0 ? lastOverNum - 1 : lastOverNum;
    if (targetOver <= 0)
        return null;
    const overBalls = deliveries.filter((d) => d.over_number === targetOver);
    if (overBalls.length === 0)
        return null;
    return { over: targetOver, balls: overBalls };
});
const overSummaryText = computed(() => {
    if (!lastCompletedOver.value) {
        return 'Unavailable';
    }
    const { over, balls } = lastCompletedOver.value;
    const bowlerName = getPlayerName(balls[0]?.bowler_id) || 'Unknown bowler';
    const totalRuns = balls.reduce((sum, b) => sum + (b.runs_scored ?? 0), 0);
    const wickets = balls.filter((b) => b.is_wicket).length;
    const maidens = balls.every((b) => (b.runs_scored ?? 0) === 0) ? 'Maiden' : '';
    return `Over ${over} (${bowlerName}): ${totalRuns} runs, ${wickets} wicket(s) ${maidens}`.trim();
});
// ---- Helpers
function getPlayerName(playerId) {
    if (!playerId)
        return null;
    // Try from current game state batting/bowling cards
    const allPlayers = new Map();
    if (liveSnapshot.value?.current_state?.batting_scorecard) {
        for (const [playerId, entry] of Object.entries(liveSnapshot.value.current_state.batting_scorecard)) {
            allPlayers.set(playerId, entry.player_name ?? 'Unknown');
        }
    }
    if (liveSnapshot.value?.current_state?.bowling_scorecard) {
        for (const [playerId, entry] of Object.entries(liveSnapshot.value.current_state.bowling_scorecard)) {
            allPlayers.set(playerId, entry.player_name ?? 'Unknown');
        }
    }
    return allPlayers.get(playerId) ?? null;
}
function getExtraLabel(delivery) {
    if (!delivery.extra_type)
        return '';
    const map = {
        wd: ' (Wide)',
        nb: ' (No-ball)',
        b: ' (Bye)',
        lb: ' (Leg-bye)',
    };
    return map[delivery.extra_type] ?? '';
}
function formatEventContent(event) {
    const typeLabel = {
        drinks: '🥤 Drinks break',
        injury: '🏥 Injury',
        delay: '⏸️ Delay',
        ball_change: '⚪ Ball change',
        other: '📌 Event',
    }[event.type] || 'Event';
    return `${typeLabel}${event.note ? ': ' + event.note : ''}`;
}
async function addEvent() {
    if (!newEventType.value)
        return;
    const eventId = `evt-${Date.now()}`;
    const now = new Date().toISOString();
    const enteredBy = user.value?.name || user.value?.email || 'Operator';
    gameEvents.value.push({
        id: eventId,
        type: newEventType.value,
        timestamp: now,
        note: newEventNote.value,
        enteredBy,
    });
    // Reset form
    newEventType.value = 'other';
    newEventNote.value = '';
    showAddEvent.value = false;
}
function copyOverSummary() {
    const text = overSummaryText.value;
    if (text === 'Unavailable') {
        alert('No completed overs yet');
        return;
    }
    navigator.clipboard.writeText(text).then(() => {
        alert('Over summary copied!');
    });
}
function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    catch {
        return 'Unknown time';
    }
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
/** @type {__VLS_StyleScopedClasses['event-log-header']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-add-event']} */ ;
/** @type {__VLS_StyleScopedClasses['sel']} */ ;
/** @type {__VLS_StyleScopedClasses['inp']} */ ;
/** @type {__VLS_StyleScopedClasses['sel']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-cancel']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-cancel']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
/** @type {__VLS_StyleScopedClasses['over-summary-section']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-item']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-item']} */ ;
/** @type {__VLS_StyleScopedClasses['delivery']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-item']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-item']} */ ;
/** @type {__VLS_StyleScopedClasses['event']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "event-log-tab" },
});
/** @type {__VLS_StyleScopedClasses['event-log-tab']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "event-log-header" },
});
/** @type {__VLS_StyleScopedClasses['event-log-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.showAddEvent = !__VLS_ctx.showAddEvent;
            // @ts-ignore
            [showAddEvent, showAddEvent,];
        } },
    ...{ class: "btn-add-event" },
});
/** @type {__VLS_StyleScopedClasses['btn-add-event']} */ ;
(__VLS_ctx.showAddEvent ? '✕ Close' : '+ Add Event');
if (__VLS_ctx.showAddEvent) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "add-event-form" },
    });
    /** @type {__VLS_StyleScopedClasses['add-event-form']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.newEventType),
        ...{ class: "sel" },
    });
    /** @type {__VLS_StyleScopedClasses['sel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "drinks",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "injury",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "delay",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "ball_change",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "other",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.newEventNote),
        type: "text",
        ...{ class: "inp" },
        placeholder: "e.g., Rain delay, player injury...",
        maxlength: "200",
    });
    /** @type {__VLS_StyleScopedClasses['inp']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['form-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showAddEvent))
                    return;
                __VLS_ctx.showAddEvent = false;
                // @ts-ignore
                [showAddEvent, showAddEvent, showAddEvent, newEventType, newEventNote,];
            } },
        ...{ class: "btn-cancel" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-cancel']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.addEvent) },
        ...{ class: "btn-submit" },
        disabled: (!__VLS_ctx.newEventType),
    });
    /** @type {__VLS_StyleScopedClasses['btn-submit']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "over-summary-section" },
});
/** @type {__VLS_StyleScopedClasses['over-summary-section']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "summary-box" },
});
/** @type {__VLS_StyleScopedClasses['summary-box']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "summary-text" },
});
/** @type {__VLS_StyleScopedClasses['summary-text']} */ ;
(__VLS_ctx.overSummaryText);
if (__VLS_ctx.overSummaryText !== 'Unavailable') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.copyOverSummary) },
        ...{ class: "btn-copy" },
        title: "Copy to clipboard",
    });
    /** @type {__VLS_StyleScopedClasses['btn-copy']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ref: "timelineContainer",
    ...{ class: "timeline-container" },
});
/** @type {__VLS_StyleScopedClasses['timeline-container']} */ ;
if (__VLS_ctx.timelineItems.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
}
for (const [item] of __VLS_vFor((__VLS_ctx.timelineItems))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (item.id),
        ...{ class: (['timeline-item', item.type]) },
    });
    /** @type {__VLS_StyleScopedClasses['timeline-item']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "item-timestamp" },
    });
    /** @type {__VLS_StyleScopedClasses['item-timestamp']} */ ;
    (__VLS_ctx.formatTime(item.timestamp));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "item-content" },
    });
    /** @type {__VLS_StyleScopedClasses['item-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "item-text" },
    });
    /** @type {__VLS_StyleScopedClasses['item-text']} */ ;
    (item.content);
    if (item.metadata?.enteredBy) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "item-by" },
        });
        /** @type {__VLS_StyleScopedClasses['item-by']} */ ;
        (item.metadata.enteredBy);
    }
    // @ts-ignore
    [newEventType, addEvent, overSummaryText, overSummaryText, copyOverSummary, timelineItems, timelineItems, formatTime,];
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
