/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import api from '@/utils/api';
const router = useRouter();
const auth = useAuthStore();
const canManageTournaments = computed(() => auth.hasAnyRole(['org_pro', 'superuser']));
const isLoggedIn = computed(() => auth.isLoggedIn);
const managementHint = 'Tournament management is reserved for Org Pro accounts.';
const tournaments = ref([]);
const loading = ref(true);
const error = ref('');
const showCreateModal = ref(false);
const newTournament = ref({
    name: '',
    description: '',
    tournament_type: 'league',
    start_date: '',
    end_date: '',
});
// Edit modal state
const showEditModal = ref(false);
const editSubmitting = ref(false);
const tournamentToEdit = ref(null);
const editForm = ref({
    name: '',
    description: '',
    tournament_type: 'league',
    status: 'upcoming',
    start_date: '',
    end_date: '',
});
// Delete confirmation state
const showDeleteConfirm = ref(false);
const deleteSubmitting = ref(false);
const tournamentToDelete = ref(null);
async function loadTournaments() {
    try {
        loading.value = true;
        error.value = '';
        tournaments.value = await api.getTournaments();
    }
    catch (e) {
        error.value = e.message || 'Failed to load tournaments';
    }
    finally {
        loading.value = false;
    }
}
function openCreateModal() {
    if (!canManageTournaments.value) {
        alert(managementHint);
        return;
    }
    showCreateModal.value = true;
}
async function createTournament() {
    if (!canManageTournaments.value) {
        alert(managementHint);
        return;
    }
    try {
        const body = {
            name: newTournament.value.name,
            description: newTournament.value.description || null,
            tournament_type: newTournament.value.tournament_type,
            start_date: newTournament.value.start_date || null,
            end_date: newTournament.value.end_date || null,
        };
        const created = await api.createTournament(body);
        showCreateModal.value = false;
        newTournament.value = {
            name: '',
            description: '',
            tournament_type: 'league',
            start_date: '',
            end_date: '',
        };
        await loadTournaments();
        router.push(`/tournaments/${created.id}`);
    }
    catch (e) {
        alert(e.message || 'Failed to create tournament');
    }
}
// Edit functions
function openEditModal(tournament) {
    if (!canManageTournaments.value)
        return;
    tournamentToEdit.value = tournament;
    editForm.value = {
        name: tournament.name || '',
        description: tournament.description || '',
        tournament_type: tournament.tournament_type || 'league',
        status: tournament.status || 'upcoming',
        start_date: tournament.start_date ? tournament.start_date.split('T')[0] : '',
        end_date: tournament.end_date ? tournament.end_date.split('T')[0] : '',
    };
    showEditModal.value = true;
}
async function submitEdit() {
    if (!tournamentToEdit.value || !canManageTournaments.value)
        return;
    editSubmitting.value = true;
    try {
        const payload = {
            name: editForm.value.name,
            description: editForm.value.description || null,
            tournament_type: editForm.value.tournament_type,
            status: editForm.value.status,
            start_date: editForm.value.start_date || null,
            end_date: editForm.value.end_date || null,
        };
        await api.updateTournament(tournamentToEdit.value.id, payload);
        showEditModal.value = false;
        tournamentToEdit.value = null;
        await loadTournaments();
    }
    catch (e) {
        alert(e.message || 'Failed to update tournament');
    }
    finally {
        editSubmitting.value = false;
    }
}
// Delete functions
function openDeleteConfirm(tournament) {
    if (!canManageTournaments.value)
        return;
    tournamentToDelete.value = tournament;
    showDeleteConfirm.value = true;
}
async function confirmDelete() {
    if (!tournamentToDelete.value || !canManageTournaments.value)
        return;
    deleteSubmitting.value = true;
    try {
        await api.deleteTournament(tournamentToDelete.value.id);
        showDeleteConfirm.value = false;
        tournamentToDelete.value = null;
        await loadTournaments();
    }
    catch (e) {
        alert(e.message || 'Failed to delete tournament');
    }
    finally {
        deleteSubmitting.value = false;
    }
}
function goToTournament(id) {
    router.push(`/tournaments/${id}`);
}
function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString();
}
onMounted(() => {
    loadTournaments();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['tournament-card']} */ ;
/** @type {__VLS_StyleScopedClasses['tournament-card']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['modal']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "tournament-dashboard" },
});
/** @type {__VLS_StyleScopedClasses['tournament-dashboard']} */ ;
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tournament-banner info" },
    });
    /** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
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
else if (!__VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tournament-banner warn" },
    });
    /** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tournament-banner success" },
    });
    /** @type {__VLS_StyleScopedClasses['tournament-banner']} */ ;
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
    disabled: (!__VLS_ctx.canManageTournaments),
    title: (!__VLS_ctx.canManageTournaments ? __VLS_ctx.managementHint : undefined),
});
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
if (!__VLS_ctx.canManageTournaments && __VLS_ctx.isLoggedIn) {
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
}
else if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "error" },
    });
    /** @type {__VLS_StyleScopedClasses['error']} */ ;
    (__VLS_ctx.error);
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "tournaments-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['tournaments-grid']} */ ;
    for (const [tournament] of __VLS_vFor((__VLS_ctx.tournaments))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (tournament.id),
            ...{ class: "tournament-card" },
        });
        /** @type {__VLS_StyleScopedClasses['tournament-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.error))
                        return;
                    __VLS_ctx.goToTournament(tournament.id);
                    // @ts-ignore
                    [isLoggedIn, canManageTournaments, canManageTournaments, canManageTournaments, canManageTournaments, auth, openCreateModal, managementHint, managementHint, loading, error, error, tournaments, goToTournament,];
                } },
            ...{ class: "card-main" },
        });
        /** @type {__VLS_StyleScopedClasses['card-main']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        (tournament.name);
        if (tournament.description) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "description" },
            });
            /** @type {__VLS_StyleScopedClasses['description']} */ ;
            (tournament.description);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "meta" },
        });
        /** @type {__VLS_StyleScopedClasses['meta']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "badge" },
            ...{ class: (`status-${tournament.status}`) },
        });
        /** @type {__VLS_StyleScopedClasses['badge']} */ ;
        (tournament.status);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "type" },
        });
        /** @type {__VLS_StyleScopedClasses['type']} */ ;
        (tournament.tournament_type);
        if (tournament.start_date) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "dates" },
            });
            /** @type {__VLS_StyleScopedClasses['dates']} */ ;
            (__VLS_ctx.formatDate(tournament.start_date));
            if (tournament.end_date) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                (__VLS_ctx.formatDate(tournament.end_date));
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "teams-count" },
        });
        /** @type {__VLS_StyleScopedClasses['teams-count']} */ ;
        (tournament.teams?.length || 0);
        if (__VLS_ctx.canManageTournaments) {
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
                        if (!(__VLS_ctx.canManageTournaments))
                            return;
                        __VLS_ctx.openEditModal(tournament);
                        // @ts-ignore
                        [canManageTournaments, formatDate, formatDate, openEditModal,];
                    } },
                ...{ class: "btn-icon" },
                title: "Edit",
            });
            /** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!!(__VLS_ctx.error))
                            return;
                        if (!(__VLS_ctx.canManageTournaments))
                            return;
                        __VLS_ctx.openDeleteConfirm(tournament);
                        // @ts-ignore
                        [openDeleteConfirm,];
                    } },
                ...{ class: "btn-icon btn-icon-danger" },
                title: "Delete",
            });
            /** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
            /** @type {__VLS_StyleScopedClasses['btn-icon-danger']} */ ;
        }
        // @ts-ignore
        [];
    }
    if (__VLS_ctx.tournaments.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
}
if (__VLS_ctx.showCreateModal && __VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showCreateModal && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showCreateModal = false;
                // @ts-ignore
                [canManageTournaments, tournaments, showCreateModal, showCreateModal,];
            } },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal" },
    });
    /** @type {__VLS_StyleScopedClasses['modal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.createTournament) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.newTournament.name),
        type: "text",
        required: true,
        placeholder: "e.g., Premier League 2024",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        value: (__VLS_ctx.newTournament.description),
        placeholder: "Tournament description",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.newTournament.tournament_type),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "league",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "knockout",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "round-robin",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.newTournament.start_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.newTournament.end_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showCreateModal && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showCreateModal = false;
                // @ts-ignore
                [showCreateModal, createTournament, newTournament, newTournament, newTournament, newTournament, newTournament,];
            } },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "btn-primary" },
        disabled: (!__VLS_ctx.canManageTournaments),
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
}
if (__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showEditModal = false;
                // @ts-ignore
                [canManageTournaments, canManageTournaments, showEditModal, showEditModal,];
            } },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal" },
    });
    /** @type {__VLS_StyleScopedClasses['modal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.submitEdit) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.editForm.name),
        type: "text",
        required: true,
        placeholder: "e.g., Premier League 2024",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        value: (__VLS_ctx.editForm.description),
        placeholder: "Tournament description",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.editForm.tournament_type),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "league",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "knockout",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "round-robin",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.editForm.status),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "upcoming",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "ongoing",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "completed",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "cancelled",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.editForm.start_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.editForm.end_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showEditModal = false;
                // @ts-ignore
                [showEditModal, submitEdit, editForm, editForm, editForm, editForm, editForm, editForm,];
            } },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "btn-primary" },
        disabled: (__VLS_ctx.editSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    (__VLS_ctx.editSubmitting ? 'Saving...' : 'Save Changes');
}
if (__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showDeleteConfirm = false;
                // @ts-ignore
                [canManageTournaments, editSubmitting, editSubmitting, showDeleteConfirm, showDeleteConfirm,];
            } },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal modal-confirm" },
    });
    /** @type {__VLS_StyleScopedClasses['modal']} */ ;
    /** @type {__VLS_StyleScopedClasses['modal-confirm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "confirm-text" },
    });
    /** @type {__VLS_StyleScopedClasses['confirm-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.tournamentToDelete?.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showDeleteConfirm = false;
                // @ts-ignore
                [showDeleteConfirm, tournamentToDelete,];
            } },
        type: "button",
        ...{ class: "btn-secondary" },
        disabled: (__VLS_ctx.deleteSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.confirmDelete) },
        type: "button",
        ...{ class: "btn-danger" },
        disabled: (__VLS_ctx.deleteSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
    (__VLS_ctx.deleteSubmitting ? 'Deleting...' : 'Delete Tournament');
}
// @ts-ignore
[deleteSubmitting, deleteSubmitting, deleteSubmitting, confirmDelete,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
