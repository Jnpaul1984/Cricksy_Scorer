/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import TeamFormModal from '@/components/TeamFormModal.vue';
import { API_BASE, getStoredToken } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const auth = useAuthStore();
// State
const teams = ref([]);
const availablePlayers = ref([]);
const availableCoaches = ref([]);
const loading = ref(true);
const error = ref(null);
const showTeamModal = ref(false);
const editingTeam = ref(null);
// Auth checks
const isLoggedIn = computed(() => !!auth.token);
const canManageTeams = computed(() => {
    const role = auth.role?.toLowerCase() || '';
    return ['org_pro', 'superuser', 'coach_pro'].includes(role);
});
const managementHint = computed(() => {
    if (!isLoggedIn.value)
        return 'Sign in to manage teams';
    if (!canManageTeams.value)
        return 'Requires Org Pro, Coach Pro, or Superuser role';
    return '';
});
// API functions
async function fetchTeams() {
    loading.value = true;
    error.value = null;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const res = await fetch(`${API_BASE}/api/teams`, { headers });
        if (!res.ok) {
            if (res.status === 401) {
                // Return empty for unauthenticated
                teams.value = [];
                return;
            }
            throw new Error(`Failed to fetch teams: ${res.statusText}`);
        }
        teams.value = await res.json();
    }
    catch (err) {
        error.value = err.message || 'Failed to load teams';
        console.error('Error fetching teams:', err);
    }
    finally {
        loading.value = false;
    }
}
async function saveTeam(team) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getStoredToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    try {
        const isNew = !team.id;
        const url = isNew ? `${API_BASE}/api/teams` : `${API_BASE}/api/teams/${team.id}`;
        const method = isNew ? 'POST' : 'PUT';
        const res = await fetch(url, {
            method,
            headers,
            body: JSON.stringify(team)
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || `Failed to save team: ${res.statusText}`);
        }
        await fetchTeams();
    }
    catch (err) {
        error.value = err.message || 'Failed to save team';
        console.error('Error saving team:', err);
    }
}
async function deleteTeam(team) {
    if (!confirm(`Are you sure you want to delete "${team.name}"?`))
        return;
    const headers = { 'Content-Type': 'application/json' };
    const token = getStoredToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    try {
        const res = await fetch(`${API_BASE}/api/teams/${team.id}`, {
            method: 'DELETE',
            headers
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || `Failed to delete team: ${res.statusText}`);
        }
        await fetchTeams();
    }
    catch (err) {
        error.value = err.message || 'Failed to delete team';
        console.error('Error deleting team:', err);
    }
}
// Actions
function openCreateModal() {
    editingTeam.value = null;
    showTeamModal.value = true;
}
function openEditModal(team) {
    editingTeam.value = { ...team };
    showTeamModal.value = true;
}
function handleTeamSaved(team) {
    saveTeam(team);
}
// Fetch available players for the multi-select
async function fetchAvailablePlayers() {
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const res = await fetch(`${API_BASE}/api/players`, { headers });
        if (res.ok) {
            const data = await res.json();
            availablePlayers.value = data.map((p) => ({
                id: p.player_id || p.id,
                name: p.player_name || p.name
            }));
        }
    }
    catch (err) {
        console.warn('Could not fetch players:', err);
    }
}
// Fetch available coaches for the select
async function fetchAvailableCoaches() {
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        // Fetch users with coach_pro role
        const res = await fetch(`${API_BASE}/api/users?role=coach_pro`, { headers });
        if (res.ok) {
            const data = await res.json();
            availableCoaches.value = data.map((u) => ({
                id: u.id,
                name: u.username || u.email || u.id
            }));
        }
    }
    catch (err) {
        console.warn('Could not fetch coaches:', err);
    }
}
onMounted(() => {
    fetchTeams();
    fetchAvailablePlayers();
    fetchAvailableCoaches();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['team-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
/** @type {__VLS_StyleScopedClasses['competition-tag']} */ ;
/** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['more']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['team-management']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "team-management" },
});
/** @type {__VLS_StyleScopedClasses['team-management']} */ ;
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-banner info" },
    });
    /** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
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
else if (!__VLS_ctx.canManageTeams) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-banner warn" },
    });
    /** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "team-banner success" },
    });
    /** @type {__VLS_StyleScopedClasses['team-banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['success']} */ ;
    (__VLS_ctx.auth.role || 'org_pro');
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-actions" },
});
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.openCreateModal) },
    ...{ class: "btn-primary" },
    disabled: (!__VLS_ctx.canManageTeams),
    title: (!__VLS_ctx.canManageTeams ? __VLS_ctx.managementHint : 'Create a new team'),
});
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
if (!__VLS_ctx.canManageTeams && __VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
        ...{ class: "hint-inline" },
    });
    /** @type {__VLS_StyleScopedClasses['hint-inline']} */ ;
    (__VLS_ctx.managementHint);
}
if (__VLS_ctx.loading) {
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
        ...{ class: "error-banner" },
    });
    /** @type {__VLS_StyleScopedClasses['error-banner']} */ ;
    (__VLS_ctx.error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.fetchTeams) },
        ...{ class: "btn-link" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-link']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "teams-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['teams-grid']} */ ;
    for (const [team] of __VLS_vFor((__VLS_ctx.teams))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (team.id),
            ...{ class: "team-card" },
        });
        /** @type {__VLS_StyleScopedClasses['team-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-header" },
        });
        /** @type {__VLS_StyleScopedClasses['card-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "team-name" },
        });
        /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
        (team.name);
        if (__VLS_ctx.canManageTeams) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "card-actions" },
            });
            /** @type {__VLS_StyleScopedClasses['card-actions']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!!(__VLS_ctx.error))
                            return;
                        if (!(__VLS_ctx.canManageTeams))
                            return;
                        __VLS_ctx.openEditModal(team);
                        // @ts-ignore
                        [isLoggedIn, canManageTeams, canManageTeams, canManageTeams, canManageTeams, canManageTeams, auth, openCreateModal, managementHint, managementHint, loading, error, error, fetchTeams, teams, openEditModal,];
                    } },
                ...{ class: "btn-icon" },
                title: "Edit team",
            });
            /** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!!(__VLS_ctx.error))
                            return;
                        if (!(__VLS_ctx.canManageTeams))
                            return;
                        __VLS_ctx.deleteTeam(team);
                        // @ts-ignore
                        [deleteTeam,];
                    } },
                ...{ class: "btn-icon btn-icon-danger" },
                title: "Delete team",
            });
            /** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
            /** @type {__VLS_StyleScopedClasses['btn-icon-danger']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "card-body" },
        });
        /** @type {__VLS_StyleScopedClasses['card-body']} */ ;
        if (team.home_ground) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat-row" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-icon" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (team.home_ground);
        }
        if (team.season) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "stat-row" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-icon" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-label" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "stat-value" },
            });
            /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
            (team.season);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (team.players?.length || 0);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (team.coach_name || 'None assigned');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stat-row" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "stat-value" },
        });
        /** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
        (team.competitions?.length || 0);
        if (team.competitions?.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "competitions-tags" },
            });
            /** @type {__VLS_StyleScopedClasses['competitions-tags']} */ ;
            for (const [comp] of __VLS_vFor((team.competitions.slice(0, 3)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    key: (comp.id),
                    ...{ class: "competition-tag" },
                });
                /** @type {__VLS_StyleScopedClasses['competition-tag']} */ ;
                (comp.name);
                // @ts-ignore
                [];
            }
            if (team.competitions.length > 3) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "competition-tag more" },
                });
                /** @type {__VLS_StyleScopedClasses['competition-tag']} */ ;
                /** @type {__VLS_StyleScopedClasses['more']} */ ;
                (team.competitions.length - 3);
            }
        }
        if (team.players?.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "players-preview" },
            });
            /** @type {__VLS_StyleScopedClasses['players-preview']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "players-avatars" },
            });
            /** @type {__VLS_StyleScopedClasses['players-avatars']} */ ;
            for (const [player, idx] of __VLS_vFor((team.players.slice(0, 5)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (player.id),
                    ...{ class: "player-avatar" },
                    title: (player.name),
                    ...{ style: ({ '--index': idx }) },
                });
                /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
                (player.name.charAt(0).toUpperCase());
                // @ts-ignore
                [];
            }
            if (team.players.length > 5) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "player-avatar more" },
                });
                /** @type {__VLS_StyleScopedClasses['player-avatar']} */ ;
                /** @type {__VLS_StyleScopedClasses['more']} */ ;
                (team.players.length - 5);
            }
        }
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.teams.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-icon']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        if (__VLS_ctx.canManageTeams) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (__VLS_ctx.openCreateModal) },
                ...{ class: "btn-primary" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
        }
    }
}
const __VLS_6 = TeamFormModal;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    ...{ 'onSaved': {} },
    visible: (__VLS_ctx.showTeamModal),
    team: (__VLS_ctx.editingTeam),
    availablePlayers: (__VLS_ctx.availablePlayers),
    availableCoaches: (__VLS_ctx.availableCoaches),
}));
const __VLS_8 = __VLS_7({
    ...{ 'onSaved': {} },
    visible: (__VLS_ctx.showTeamModal),
    team: (__VLS_ctx.editingTeam),
    availablePlayers: (__VLS_ctx.availablePlayers),
    availableCoaches: (__VLS_ctx.availableCoaches),
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
let __VLS_11;
const __VLS_12 = ({ saved: {} },
    { onSaved: (__VLS_ctx.handleTeamSaved) });
var __VLS_9;
var __VLS_10;
// @ts-ignore
[canManageTeams, openCreateModal, teams, showTeamModal, editingTeam, availablePlayers, availableCoaches, handleTeamSaved,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
