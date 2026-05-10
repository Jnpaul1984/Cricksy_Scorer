/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
import { BaseButton } from '@/components';
const props = defineProps();
const filterType = ref('all');
const sortOrder = ref('recent');
const currentPage = ref(1);
const itemsPerPage = 5;
// Use props items or empty array (no mock data)
const feedItems = computed(() => {
    return props.items || [];
});
const filteredFeedItems = computed(() => {
    let result = feedItems.value;
    // Filter by type
    if (filterType.value !== 'all') {
        if (filterType.value === 'matches') {
            result = result.filter((i) => i.type === 'match');
        }
        else if (filterType.value === 'highlights') {
            result = result.filter((i) => i.type === 'highlight');
        }
        else if (filterType.value === 'news') {
            result = result.filter((i) => i.type === 'news');
        }
    }
    // Sort
    if (sortOrder.value === 'recent') {
        result.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    }
    else if (sortOrder.value === 'trending') {
        result.sort((a, b) => (b.reactions?.likes || 0) - (a.reactions?.likes || 0));
    }
    return result;
});
const totalPages = computed(() => Math.ceil(filteredFeedItems.value.length / itemsPerPage));
const paginatedItems = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    return filteredFeedItems.value.slice(start, end);
});
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (hours < 1)
        return 'just now';
    if (hours < 24)
        return `${hours}h ago`;
    if (days < 7)
        return `${days}d ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}
function viewMatchDetails(item) {
    console.log('View match:', item);
    // In real app, navigate to match details view
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
/** @type {__VLS_StyleScopedClasses['filter-select']} */ ;
/** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
/** @type {__VLS_StyleScopedClasses['feed-item']} */ ;
/** @type {__VLS_StyleScopedClasses['feed-controls']} */ ;
/** @type {__VLS_StyleScopedClasses['score-section']} */ ;
/** @type {__VLS_StyleScopedClasses['engagement-section']} */ ;
/** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
/** @type {__VLS_StyleScopedClasses['pagination']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "fan-feed" },
});
/** @type {__VLS_StyleScopedClasses['fan-feed']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feed-header" },
});
/** @type {__VLS_StyleScopedClasses['feed-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "feed-title" },
});
/** @type {__VLS_StyleScopedClasses['feed-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "feed-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['feed-subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feed-controls" },
});
/** @type {__VLS_StyleScopedClasses['feed-controls']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "filter-group" },
});
/** @type {__VLS_StyleScopedClasses['filter-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "filter-label" },
});
/** @type {__VLS_StyleScopedClasses['filter-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.filterType),
    ...{ class: "filter-select" },
});
/** @type {__VLS_StyleScopedClasses['filter-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "all",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "matches",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "highlights",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "news",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sort-group" },
});
/** @type {__VLS_StyleScopedClasses['sort-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "sort-label" },
});
/** @type {__VLS_StyleScopedClasses['sort-label']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.sortOrder),
    ...{ class: "sort-select" },
});
/** @type {__VLS_StyleScopedClasses['sort-select']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "recent",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "trending",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "following",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "feed-container" },
});
/** @type {__VLS_StyleScopedClasses['feed-container']} */ ;
if (__VLS_ctx.filteredFeedItems.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-message" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-message']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-hint']} */ ;
}
for (const [item, idx] of __VLS_vFor((__VLS_ctx.paginatedItems))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        key: (item.id),
        ...{ class: "feed-item" },
    });
    /** @type {__VLS_StyleScopedClasses['feed-item']} */ ;
    if (item.type === 'match') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "match-card" },
        });
        /** @type {__VLS_StyleScopedClasses['match-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-header" },
        });
        /** @type {__VLS_StyleScopedClasses['card-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "entity-info" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
            src: (item.team1?.logo || ''),
            alt: (item.team1?.name),
            ...{ class: "team-logo" },
        });
        /** @type {__VLS_StyleScopedClasses['team-logo']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "entity-meta" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-meta']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-name" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-name']} */ ;
        (item.team1?.name);
        (item.team2?.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-date" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-date']} */ ;
        (__VLS_ctx.formatDate(item.timestamp));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "match-status" },
            ...{ class: (`status-${item.status}`) },
        });
        /** @type {__VLS_StyleScopedClasses['match-status']} */ ;
        (item.status);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-body" },
        });
        /** @type {__VLS_StyleScopedClasses['card-body']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "score-section" },
        });
        /** @type {__VLS_StyleScopedClasses['score-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "team-score" },
        });
        /** @type {__VLS_StyleScopedClasses['team-score']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-name" },
        });
        /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
        (item.team1?.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-runs" },
        });
        /** @type {__VLS_StyleScopedClasses['team-runs']} */ ;
        (item.team1Runs);
        (item.team1Wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-overs" },
        });
        /** @type {__VLS_StyleScopedClasses['team-overs']} */ ;
        (item.team1Overs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "vs-divider" },
        });
        /** @type {__VLS_StyleScopedClasses['vs-divider']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "team-score" },
        });
        /** @type {__VLS_StyleScopedClasses['team-score']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-name" },
        });
        /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
        (item.team2?.name);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-runs" },
        });
        /** @type {__VLS_StyleScopedClasses['team-runs']} */ ;
        (item.team2Runs);
        (item.team2Wickets);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "team-overs" },
        });
        /** @type {__VLS_StyleScopedClasses['team-overs']} */ ;
        (item.team2Overs);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "match-details" },
        });
        /** @type {__VLS_StyleScopedClasses['match-details']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail" },
        });
        /** @type {__VLS_StyleScopedClasses['detail']} */ ;
        (item.venue);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "detail" },
        });
        /** @type {__VLS_StyleScopedClasses['detail']} */ ;
        (item.format);
        if (item.highlights && item.highlights.length > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "highlights" },
            });
            /** @type {__VLS_StyleScopedClasses['highlights']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "highlights-title" },
            });
            /** @type {__VLS_StyleScopedClasses['highlights-title']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                ...{ class: "highlights-list" },
            });
            /** @type {__VLS_StyleScopedClasses['highlights-list']} */ ;
            for (const [highlight, hidx] of __VLS_vFor((item.highlights.slice(0, 3)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (hidx),
                    ...{ class: "highlight-item" },
                });
                /** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
                (highlight);
                // @ts-ignore
                [filterType, sortOrder, filteredFeedItems, paginatedItems, formatDate,];
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "engagement-section" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "engagement-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-count" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-count']} */ ;
        (item.reactions?.likes || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "engagement-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-count" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-count']} */ ;
        (item.reactions?.comments || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "engagement-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-count" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-count']} */ ;
        (item.reactions?.shares || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "engagement-stat" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-stat']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "engagement-count" },
        });
        /** @type {__VLS_StyleScopedClasses['engagement-count']} */ ;
        (item.reactions?.views || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-footer" },
        });
        /** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
        let __VLS_0;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
        }));
        const __VLS_2 = __VLS_1({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        let __VLS_5;
        const __VLS_6 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(item.type === 'match'))
                        return;
                    __VLS_ctx.viewMatchDetails(item);
                    // @ts-ignore
                    [viewMatchDetails,];
                } });
        const { default: __VLS_7 } = __VLS_3.slots;
        // @ts-ignore
        [];
        var __VLS_3;
        var __VLS_4;
    }
    else if (item.type === 'highlight') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "highlight-card" },
        });
        /** @type {__VLS_StyleScopedClasses['highlight-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-header" },
        });
        /** @type {__VLS_StyleScopedClasses['card-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "entity-info" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-name" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-name']} */ ;
        (item.title);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-date" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-date']} */ ;
        (__VLS_ctx.formatDate(item.timestamp));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-body" },
        });
        /** @type {__VLS_StyleScopedClasses['card-body']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "highlight-description" },
        });
        /** @type {__VLS_StyleScopedClasses['highlight-description']} */ ;
        (item.description);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "highlight-video-placeholder" },
        });
        /** @type {__VLS_StyleScopedClasses['highlight-video-placeholder']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (item.duration);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-footer" },
        });
        /** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
        let __VLS_8;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent1(__VLS_8, new __VLS_8({
            variant: "ghost",
            size: "sm",
        }));
        const __VLS_10 = __VLS_9({
            variant: "ghost",
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_9));
        const { default: __VLS_13 } = __VLS_11.slots;
        // @ts-ignore
        [formatDate,];
        var __VLS_11;
    }
    else if (item.type === 'news') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "news-card" },
        });
        /** @type {__VLS_StyleScopedClasses['news-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-header" },
        });
        /** @type {__VLS_StyleScopedClasses['card-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "entity-info" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-name" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-name']} */ ;
        (item.title);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "entity-date" },
        });
        /** @type {__VLS_StyleScopedClasses['entity-date']} */ ;
        (__VLS_ctx.formatDate(item.timestamp));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "news-source" },
        });
        /** @type {__VLS_StyleScopedClasses['news-source']} */ ;
        (item.source);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-body" },
        });
        /** @type {__VLS_StyleScopedClasses['card-body']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "news-snippet" },
        });
        /** @type {__VLS_StyleScopedClasses['news-snippet']} */ ;
        (item.snippet);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-footer" },
        });
        /** @type {__VLS_StyleScopedClasses['card-footer']} */ ;
        let __VLS_14;
        /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
        BaseButton;
        // @ts-ignore
        const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
            variant: "ghost",
            size: "sm",
        }));
        const __VLS_16 = __VLS_15({
            variant: "ghost",
            size: "sm",
        }, ...__VLS_functionalComponentArgsRest(__VLS_15));
        const { default: __VLS_19 } = __VLS_17.slots;
        // @ts-ignore
        [formatDate,];
        var __VLS_17;
    }
    // @ts-ignore
    [];
}
if (__VLS_ctx.totalPages > 1) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "pagination" },
    });
    /** @type {__VLS_StyleScopedClasses['pagination']} */ ;
    let __VLS_20;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.currentPage === 1),
    }));
    const __VLS_22 = __VLS_21({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.currentPage === 1),
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    let __VLS_25;
    const __VLS_26 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!(__VLS_ctx.totalPages > 1))
                    return;
                __VLS_ctx.currentPage--;
                // @ts-ignore
                [totalPages, currentPage, currentPage,];
            } });
    const { default: __VLS_27 } = __VLS_23.slots;
    // @ts-ignore
    [];
    var __VLS_23;
    var __VLS_24;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "page-info" },
    });
    /** @type {__VLS_StyleScopedClasses['page-info']} */ ;
    (__VLS_ctx.currentPage);
    (__VLS_ctx.totalPages);
    let __VLS_28;
    /** @ts-ignore @type { | typeof __VLS_components.BaseButton | typeof __VLS_components.BaseButton} */
    BaseButton;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent1(__VLS_28, new __VLS_28({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.currentPage === __VLS_ctx.totalPages),
    }));
    const __VLS_30 = __VLS_29({
        ...{ 'onClick': {} },
        variant: "ghost",
        size: "sm",
        disabled: (__VLS_ctx.currentPage === __VLS_ctx.totalPages),
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
    let __VLS_33;
    const __VLS_34 = ({ click: {} },
        { onClick: (...[$event]) => {
                if (!(__VLS_ctx.totalPages > 1))
                    return;
                __VLS_ctx.currentPage++;
                // @ts-ignore
                [totalPages, totalPages, currentPage, currentPage, currentPage,];
            } });
    const { default: __VLS_35 } = __VLS_31.slots;
    // @ts-ignore
    [];
    var __VLS_31;
    var __VLS_32;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({
    __typeProps: {},
});
export default {};
