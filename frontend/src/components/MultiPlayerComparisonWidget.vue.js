/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed } from 'vue';
const activeCompTab = ref('batting');
const selectedPlayers = ref([]);
const playerSearch = ref([null, null, null]);
const compTabs = [
    { id: 'batting', icon: '🏏', label: 'Batting' },
    { id: 'bowling', icon: '🎯', label: 'Bowling' },
    { id: 'form', icon: '📈', label: 'Form' },
    { id: 'radar', icon: '🎲', label: 'Radar' },
    { id: 'h2h', icon: '⚡', label: 'H2H' },
];
// Player database (empty - should be provided via API or props)
const allPlayers = computed(() => []);
const availablePlayers = computed(() => allPlayers.value.filter((p) => !selectedPlayers.value.find((sp) => sp.id === p.id)));
const battingStats = {
    Runs: (p) => p.batting.runs,
    Average: (p) => p.batting.average.toFixed(2),
    'Strike Rate': (p) => p.batting.strikeRate.toFixed(1),
    Centuries: (p) => p.batting.centuries,
    Fifties: (p) => p.batting.fifties,
};
const bowlingStats = {
    Wickets: (p) => p.bowling.wickets,
    Economy: (p) => p.bowling.economy.toFixed(2),
    Average: (p) => p.bowling.average.toFixed(2),
    'Best Figures': (p) => p.bowling.bestFigures,
};
// Head-to-head records - NO FAKE DATA
// Required: GET /players/head-to-head
const headToHeadRecords = computed(() => {
    // Return empty array - real H2H data must come from backend
    return [];
});
function addPlayer(slotIdx) {
    if (!playerSearch.value[slotIdx])
        return;
    const player = allPlayers.value.find((p) => p.id === playerSearch.value[slotIdx]);
    if (player && !selectedPlayers.value.find((sp) => sp.id === player.id)) {
        selectedPlayers.value.push(player);
    }
    playerSearch.value[slotIdx] = null;
}
function removePlayer(slotIdx) {
    selectedPlayers.value.splice(slotIdx, 1);
}
function getRank(players, statFn, player) {
    const values = players.map((p) => {
        const v = statFn(p);
        return typeof v === 'number' ? v : parseFloat(v);
    });
    const playerValue = values.find((_, i) => players[i].id === player.id) || 0;
    const rank = values.filter((v) => v > playerValue).length + 1;
    return `#${rank}`;
}
function getPlayerForm(player) {
    return player.form.slice(-10);
}
function getFormSummary(player) {
    const wins = player.form.filter((f) => f === 'W').length;
    return `${wins}/10 matches won`;
}
function getRadarPoints(player) {
    const center = 200;
    const radius = 100;
    const angles = [0, 72, 144, 216, 288]; // 5 points
    const values = [
        player.batting.average / 50,
        player.bowling.wickets / 50,
        80 / 100,
        player.experience / 10,
        player.form.filter((f) => f === 'W').length / 10,
    ];
    return angles
        .map((angle, i) => {
        const rad = (angle * Math.PI) / 180;
        const x = center + Math.cos(rad - Math.PI / 2) * radius * Math.min(values[i], 1);
        const y = center + Math.sin(rad - Math.PI / 2) * radius * Math.min(values[i], 1);
        return `${x},${y}`;
    })
        .join(' ');
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['empty-state-no-players']} */ ;
/** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['comp-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['comp-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['radar-polygon']} */ ;
/** @type {__VLS_StyleScopedClasses['radar-polygon']} */ ;
/** @type {__VLS_StyleScopedClasses['radar-polygon']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['player-0']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['player-1']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
/** @type {__VLS_StyleScopedClasses['player-2']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['player-selection']} */ ;
/** @type {__VLS_StyleScopedClasses['comp-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['comp-tab']} */ ;
/** @type {__VLS_StyleScopedClasses['comparison-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['h2h-stats']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "multi-player-comparison" },
});
/** @type {__VLS_StyleScopedClasses['multi-player-comparison']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "comp-header" },
});
/** @type {__VLS_StyleScopedClasses['comp-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({
    ...{ class: "comp-title" },
});
/** @type {__VLS_StyleScopedClasses['comp-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "comp-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['comp-subtitle']} */ ;
if (__VLS_ctx.allPlayers.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state-no-players" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state-no-players']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
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
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "player-selection" },
    });
    /** @type {__VLS_StyleScopedClasses['player-selection']} */ ;
    for (const [slot, idx] of __VLS_vFor((3))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (idx),
            ...{ class: "player-slot" },
        });
        /** @type {__VLS_StyleScopedClasses['player-slot']} */ ;
        if (__VLS_ctx.selectedPlayers[idx]) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-selected" },
            });
            /** @type {__VLS_StyleScopedClasses['player-selected']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-header" },
            });
            /** @type {__VLS_StyleScopedClasses['player-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-avatar" },
            });
            /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
            (__VLS_ctx.selectedPlayers[idx].initials);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-name" },
            });
            /** @type {__VLS_StyleScopedClasses['player-name']} */ ;
            (__VLS_ctx.selectedPlayers[idx].name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "player-team" },
            });
            /** @type {__VLS_StyleScopedClasses['player-team']} */ ;
            (__VLS_ctx.selectedPlayers[idx].team);
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.allPlayers.length === 0))
                            return;
                        if (!(__VLS_ctx.selectedPlayers[idx]))
                            return;
                        __VLS_ctx.removePlayer(idx);
                        // @ts-ignore
                        [allPlayers, selectedPlayers, selectedPlayers, selectedPlayers, selectedPlayers, removePlayer,];
                    } },
                ...{ class: "remove-btn" },
            });
            /** @type {__VLS_StyleScopedClasses['remove-btn']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "player-selector" },
            });
            /** @type {__VLS_StyleScopedClasses['player-selector']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
                ...{ onChange: (...[$event]) => {
                        if (!!(__VLS_ctx.allPlayers.length === 0))
                            return;
                        if (!!(__VLS_ctx.selectedPlayers[idx]))
                            return;
                        __VLS_ctx.addPlayer(idx);
                        // @ts-ignore
                        [addPlayer,];
                    } },
                value: (__VLS_ctx.playerSearch[idx]),
                ...{ class: "player-select" },
            });
            /** @type {__VLS_StyleScopedClasses['player-select']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
                value: "",
            });
            (idx + 1);
            for (const [p] of __VLS_vFor((__VLS_ctx.availablePlayers))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
                    key: (p.id),
                    value: (p.id),
                });
                (p.name);
                (p.team);
                // @ts-ignore
                [playerSearch, availablePlayers,];
            }
        }
        // @ts-ignore
        [];
    }
}
if (__VLS_ctx.selectedPlayers.length > 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "comparison-container" },
    });
    /** @type {__VLS_StyleScopedClasses['comparison-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "comp-tabs" },
    });
    /** @type {__VLS_StyleScopedClasses['comp-tabs']} */ ;
    for (const [tab] of __VLS_vFor((__VLS_ctx.compTabs))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.selectedPlayers.length > 0))
                        return;
                    __VLS_ctx.activeCompTab = tab.id;
                    // @ts-ignore
                    [selectedPlayers, compTabs, activeCompTab,];
                } },
            key: (tab.id),
            ...{ class: "comp-tab" },
            ...{ class: ({ active: __VLS_ctx.activeCompTab === tab.id }) },
        });
        /** @type {__VLS_StyleScopedClasses['comp-tab']} */ ;
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        (tab.icon);
        (tab.label);
        // @ts-ignore
        [activeCompTab,];
    }
    if (__VLS_ctx.activeCompTab === 'batting') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-comparison" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-comparison']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "comparison-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['comparison-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "comp-label" },
        });
        /** @type {__VLS_StyleScopedClasses['comp-label']} */ ;
        for (const [player] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (player.id),
                ...{ class: "comp-label" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-label']} */ ;
            (player.name);
            // @ts-ignore
            [selectedPlayers, activeCompTab,];
        }
        for (const [stat, label] of __VLS_vFor((__VLS_ctx.battingStats))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (label),
                ...{ class: "comp-row" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "comp-row-label" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-row-label']} */ ;
            (label);
            for (const [player] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (player.id),
                    ...{ class: "comp-value" },
                });
                /** @type {__VLS_StyleScopedClasses['comp-value']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "value-display" },
                });
                /** @type {__VLS_StyleScopedClasses['value-display']} */ ;
                (stat(player));
                if (__VLS_ctx.selectedPlayers.length > 1) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "value-rank" },
                    });
                    /** @type {__VLS_StyleScopedClasses['value-rank']} */ ;
                    (__VLS_ctx.getRank(__VLS_ctx.selectedPlayers, stat, player));
                }
                // @ts-ignore
                [selectedPlayers, selectedPlayers, selectedPlayers, battingStats, getRank,];
            }
            // @ts-ignore
            [];
        }
    }
    else if (__VLS_ctx.activeCompTab === 'bowling') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-comparison" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-comparison']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "comparison-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['comparison-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "comp-label" },
        });
        /** @type {__VLS_StyleScopedClasses['comp-label']} */ ;
        for (const [player] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (player.id),
                ...{ class: "comp-label" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-label']} */ ;
            (player.name);
            // @ts-ignore
            [selectedPlayers, activeCompTab,];
        }
        for (const [stat, label] of __VLS_vFor((__VLS_ctx.bowlingStats))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (label),
                ...{ class: "comp-row" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "comp-row-label" },
            });
            /** @type {__VLS_StyleScopedClasses['comp-row-label']} */ ;
            (label);
            for (const [player] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (player.id),
                    ...{ class: "comp-value" },
                });
                /** @type {__VLS_StyleScopedClasses['comp-value']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "value-display" },
                });
                /** @type {__VLS_StyleScopedClasses['value-display']} */ ;
                (stat(player));
                if (__VLS_ctx.selectedPlayers.length > 1) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "value-rank" },
                    });
                    /** @type {__VLS_StyleScopedClasses['value-rank']} */ ;
                    (__VLS_ctx.getRank(__VLS_ctx.selectedPlayers, stat, player));
                }
                // @ts-ignore
                [selectedPlayers, selectedPlayers, selectedPlayers, getRank, bowlingStats,];
            }
            // @ts-ignore
            [];
        }
    }
    else if (__VLS_ctx.activeCompTab === 'form') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "form-comparison" },
        });
        /** @type {__VLS_StyleScopedClasses['form-comparison']} */ ;
        for (const [player] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (player.id),
                ...{ class: "player-form" },
            });
            /** @type {__VLS_StyleScopedClasses['player-form']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({
                ...{ class: "form-player-name" },
            });
            /** @type {__VLS_StyleScopedClasses['form-player-name']} */ ;
            (player.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "form-dots" },
            });
            /** @type {__VLS_StyleScopedClasses['form-dots']} */ ;
            for (const [result, idx] of __VLS_vFor((__VLS_ctx.getPlayerForm(player)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span)({
                    key: (idx),
                    ...{ class: "form-dot" },
                    ...{ class: (`result-${result}`) },
                    title: (result),
                });
                /** @type {__VLS_StyleScopedClasses['form-dot']} */ ;
                // @ts-ignore
                [selectedPlayers, activeCompTab, getPlayerForm,];
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "form-summary" },
            });
            /** @type {__VLS_StyleScopedClasses['form-summary']} */ ;
            (__VLS_ctx.getFormSummary(player));
            // @ts-ignore
            [getFormSummary,];
        }
    }
    else if (__VLS_ctx.activeCompTab === 'radar') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "radar-comparison" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-comparison']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "radar-chart" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-chart']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.svg, __VLS_intrinsics.svg)({
            viewBox: "0 0 400 400",
            ...{ class: "radar-svg" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-svg']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: "200",
            cy: "200",
            r: "40",
            ...{ class: "radar-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: "200",
            cy: "200",
            r: "80",
            ...{ class: "radar-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.circle)({
            cx: "200",
            cy: "200",
            r: "120",
            ...{ class: "radar-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: "200",
            y: "30",
            ...{ class: "radar-label" },
            'text-anchor': "middle",
        });
        /** @type {__VLS_StyleScopedClasses['radar-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: "345",
            y: "110",
            ...{ class: "radar-label" },
            'text-anchor': "middle",
        });
        /** @type {__VLS_StyleScopedClasses['radar-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: "345",
            y: "290",
            ...{ class: "radar-label" },
            'text-anchor': "middle",
        });
        /** @type {__VLS_StyleScopedClasses['radar-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: "55",
            y: "290",
            ...{ class: "radar-label" },
            'text-anchor': "middle",
        });
        /** @type {__VLS_StyleScopedClasses['radar-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.text, __VLS_intrinsics.text)({
            x: "55",
            y: "110",
            ...{ class: "radar-label" },
            'text-anchor': "middle",
        });
        /** @type {__VLS_StyleScopedClasses['radar-label']} */ ;
        for (const [player, idx] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.polygon)({
                key: (player.id),
                points: (__VLS_ctx.getRadarPoints(player)),
                ...{ class: (`radar-polygon player-${idx}`) },
            });
            // @ts-ignore
            [selectedPlayers, activeCompTab, getRadarPoints,];
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "radar-legend" },
        });
        /** @type {__VLS_StyleScopedClasses['radar-legend']} */ ;
        for (const [player, idx] of __VLS_vFor((__VLS_ctx.selectedPlayers))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (player.id),
                ...{ class: "legend-item" },
            });
            /** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "legend-color" },
                ...{ class: (`player-${idx}`) },
            });
            /** @type {__VLS_StyleScopedClasses['legend-color']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "legend-label" },
            });
            /** @type {__VLS_StyleScopedClasses['legend-label']} */ ;
            (player.name);
            // @ts-ignore
            [selectedPlayers,];
        }
    }
    else if (__VLS_ctx.activeCompTab === 'h2h') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "h2h-comparison" },
        });
        /** @type {__VLS_StyleScopedClasses['h2h-comparison']} */ ;
        for (const [matchup, idx] of __VLS_vFor((__VLS_ctx.headToHeadRecords))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                key: (idx),
                ...{ class: "h2h-record" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-record']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "h2h-teams" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-teams']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-name" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-name']} */ ;
            (matchup.player1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-vs" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-vs']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-name" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-name']} */ ;
            (matchup.player2);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "h2h-stats" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-stats']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "h2h-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-label" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-label']} */ ;
            (matchup.player1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-value" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-value']} */ ;
            (matchup.p1Wins);
            (matchup.p2Wins);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "h2h-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-label" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-text" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-text']} */ ;
            (matchup.p1Wins + matchup.p2Wins);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "h2h-stat" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-stat']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-label" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-label']} */ ;
            (matchup.player2);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "h2h-win-rate" },
            });
            /** @type {__VLS_StyleScopedClasses['h2h-win-rate']} */ ;
            (((matchup.p2Wins / (matchup.p1Wins + matchup.p2Wins)) * 100).toFixed(0));
            // @ts-ignore
            [activeCompTab, headToHeadRecords,];
        }
    }
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "empty-state" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-icon" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "empty-text" },
    });
    /** @type {__VLS_StyleScopedClasses['empty-text']} */ ;
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
