/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api, { API_BASE, getErrorMessage } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
// ================== Team favorites state ==================
// Map of team.id (as string) -> favorite record id (for quick lookup and deletion)
const teamFavoritesMap = ref(new Map());
const togglingTeamFavorite = ref(new Set());
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const tournamentId = computed(() => String(route.params.tournamentId ?? ''));
const loading = ref(true);
const loaded = ref(false);
const notFound = ref(false);
const errorMessage = ref(null);
const tournament = ref(null);
const teams = ref([]);
const fixtures = ref([]);
const pointsTable = ref([]);
// Edit modal state
const showEditModal = ref(false);
const editSubmitting = ref(false);
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
const sponsors = ref([]);
const sponsorsLoading = ref(false);
const showSponsorModal = ref(false);
const editingSponsor = ref(null);
const sponsorSubmitting = ref(false);
const sponsorLogoFile = ref(null);
const sponsorForm = ref({
    name: '',
    logo_url: '',
    click_url: '',
    weight: 1,
    is_active: true,
});
const showSponsorDeleteConfirm = ref(false);
const sponsorToDelete = ref(null);
const sponsorDeleting = ref(false);
const toast = ref(null);
let toastTimer = null;
function showToast(message, type = 'success', ms = 2500) {
    toast.value = { message, type };
    if (toastTimer)
        window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => (toast.value = null), ms);
}
const canViewDetail = computed(() => authStore.hasAnyRole([
    'free',
    'player_pro',
    'coach_pro',
    'analyst_pro',
    'org_pro',
    'superuser',
]));
const canManageTournaments = computed(() => authStore.canManageTournaments);
const accessLabel = computed(() => {
    const role = authStore.currentUser?.role;
    if (!role)
        return 'Not signed in';
    if (role === 'org_pro')
        return 'Organization Pro';
    if (role === 'superuser')
        return 'Superuser';
    if (role === 'analyst_pro')
        return 'Analyst (read-only)';
    if (role === 'coach_pro')
        return 'Coach (read-only)';
    if (role === 'player_pro')
        return 'Player (read-only)';
    return 'Free (view-only)';
});
function goBack() {
    router.push({ name: 'tournaments' });
}
function goToLogin() {
    const redirect = router.currentRoute.value.fullPath;
    router.push({ name: 'login', query: { redirect } });
}
async function loadTournament() {
    if (!tournamentId.value) {
        notFound.value = true;
        loading.value = false;
        loaded.value = true;
        return;
    }
    loading.value = true;
    errorMessage.value = null;
    notFound.value = false;
    try {
        const [t, pts, teamRows, fixtureRows] = await Promise.all([
            api.getTournament(tournamentId.value),
            api.getPointsTable(tournamentId.value),
            api.getTournamentTeams(tournamentId.value),
            api.getTournamentFixtures(tournamentId.value),
        ]);
        tournament.value = t;
        pointsTable.value = Array.isArray(pts) ? pts : [];
        teams.value = Array.isArray(teamRows) ? teamRows : [];
        fixtures.value = Array.isArray(fixtureRows) ? fixtureRows : [];
    }
    catch (err) {
        const status = err?.status;
        if (status === 404) {
            notFound.value = true;
            tournament.value = null;
            pointsTable.value = [];
            teams.value = [];
            fixtures.value = [];
        }
        else if (status === 401) {
            errorMessage.value =
                'Your session has expired or you are not authorized. Please sign in again.';
        }
        else {
            errorMessage.value = getErrorMessage(err);
        }
    }
    finally {
        loading.value = false;
        loaded.value = true;
    }
}
function reload() {
    loadTournament();
}
// ================== Team favorites functions ==================
async function loadTeamFavorites() {
    if (!authStore.currentUser)
        return;
    try {
        const favorites = await api.getFanFavorites();
        const newMap = new Map();
        for (const fav of favorites) {
            if (fav.favorite_type === 'team' && fav.team_id != null) {
                newMap.set(fav.team_id, String(fav.id));
            }
        }
        teamFavoritesMap.value = newMap;
    }
    catch {
        // Silently fail – favorites are non-critical
    }
}
function isTeamFavorite(teamId) {
    if (teamId == null)
        return false;
    return teamFavoritesMap.value.has(String(teamId));
}
async function toggleTeamFavorite(teamId) {
    if (teamId == null || !authStore.currentUser)
        return;
    const teamIdStr = String(teamId);
    if (togglingTeamFavorite.value.has(teamIdStr))
        return;
    togglingTeamFavorite.value.add(teamIdStr);
    try {
        const existingFavoriteId = teamFavoritesMap.value.get(teamIdStr);
        if (existingFavoriteId) {
            // Remove favorite
            await api.deleteFanFavorite(existingFavoriteId);
            teamFavoritesMap.value.delete(teamIdStr);
        }
        else {
            // Add favorite
            const created = await api.createFanFavorite({
                favorite_type: 'team',
                team_id: teamIdStr,
            });
            teamFavoritesMap.value.set(teamIdStr, String(created.id));
        }
    }
    catch (err) {
        showToast(getErrorMessage(err) || 'Failed to update favorite', 'error');
    }
    finally {
        togglingTeamFavorite.value.delete(teamIdStr);
    }
}
// Edit functions
function openEditModal() {
    if (!tournament.value || !canManageTournaments.value)
        return;
    // Pre-fill form with current tournament data
    editForm.value = {
        name: tournament.value.name || '',
        description: tournament.value.description || '',
        tournament_type: tournament.value.tournament_type || 'league',
        status: tournament.value.status || 'upcoming',
        start_date: tournament.value.start_date ? tournament.value.start_date.split('T')[0] : '',
        end_date: tournament.value.end_date ? tournament.value.end_date.split('T')[0] : '',
    };
    showEditModal.value = true;
}
async function submitEdit() {
    if (!tournament.value || !canManageTournaments.value)
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
        await api.updateTournament(tournamentId.value, payload);
        showEditModal.value = false;
        await loadTournament();
    }
    catch (err) {
        alert(getErrorMessage(err) || 'Failed to update tournament');
    }
    finally {
        editSubmitting.value = false;
    }
}
// Delete functions
function openDeleteConfirm() {
    if (!tournament.value || !canManageTournaments.value)
        return;
    showDeleteConfirm.value = true;
}
async function confirmDelete() {
    if (!tournament.value || !canManageTournaments.value)
        return;
    deleteSubmitting.value = true;
    try {
        await api.deleteTournament(tournamentId.value);
        showDeleteConfirm.value = false;
        router.push({ name: 'tournaments' });
    }
    catch (err) {
        alert(getErrorMessage(err) || 'Failed to delete tournament');
    }
    finally {
        deleteSubmitting.value = false;
    }
}
// ================== Sponsor functions ==================
async function loadSponsors() {
    if (!canManageTournaments.value)
        return;
    sponsorsLoading.value = true;
    try {
        const data = await api.getSponsors();
        sponsors.value = Array.isArray(data) ? data : [];
    }
    catch (err) {
        console.error('Failed to load sponsors:', err);
        sponsors.value = [];
    }
    finally {
        sponsorsLoading.value = false;
    }
}
function resolveSponsorLogo(logoUrl) {
    if (!logoUrl)
        return '';
    // If it's already an absolute URL, use it
    if (logoUrl.startsWith('http://') || logoUrl.startsWith('https://')) {
        return logoUrl;
    }
    // Otherwise, prepend the API base
    return `${API_BASE}${logoUrl.startsWith('/') ? '' : '/'}${logoUrl}`;
}
function truncateUrl(url) {
    try {
        const u = new URL(url);
        return u.hostname + (u.pathname !== '/' ? u.pathname.slice(0, 20) + '...' : '');
    }
    catch {
        return url.length > 30 ? url.slice(0, 30) + '...' : url;
    }
}
function openCreateSponsor() {
    editingSponsor.value = null;
    sponsorLogoFile.value = null;
    sponsorForm.value = {
        name: '',
        logo_url: '',
        click_url: '',
        weight: 1,
        is_active: true,
    };
    showSponsorModal.value = true;
}
function openEditSponsor(sponsor) {
    editingSponsor.value = sponsor;
    sponsorLogoFile.value = null;
    sponsorForm.value = {
        name: sponsor.name,
        logo_url: sponsor.logoUrl || '',
        click_url: sponsor.clickUrl || '',
        weight: sponsor.weight,
        is_active: sponsor.is_active !== false,
    };
    showSponsorModal.value = true;
}
function closeSponsorModal() {
    showSponsorModal.value = false;
    editingSponsor.value = null;
    sponsorLogoFile.value = null;
}
function onLogoFileChange(event) {
    const target = event.target;
    const file = target.files?.[0];
    if (file) {
        sponsorLogoFile.value = file;
    }
}
async function submitSponsor() {
    if (!canManageTournaments.value)
        return;
    sponsorSubmitting.value = true;
    try {
        if (editingSponsor.value) {
            // Update existing sponsor
            await api.updateSponsor(editingSponsor.value.id, {
                name: sponsorForm.value.name,
                click_url: sponsorForm.value.click_url || null,
                weight: sponsorForm.value.weight,
                is_active: sponsorForm.value.is_active,
            });
            showToast('Sponsor updated successfully', 'success');
        }
        else {
            // Create new sponsor with file upload
            if (!sponsorLogoFile.value) {
                showToast('Please select a logo file', 'error');
                sponsorSubmitting.value = false;
                return;
            }
            await api.uploadSponsor({
                name: sponsorForm.value.name,
                logo: sponsorLogoFile.value,
                click_url: sponsorForm.value.click_url || null,
                weight: sponsorForm.value.weight,
            });
            showToast('Sponsor created successfully', 'success');
        }
        closeSponsorModal();
        await loadSponsors();
    }
    catch (err) {
        showToast(getErrorMessage(err) || 'Failed to save sponsor', 'error', 3000);
    }
    finally {
        sponsorSubmitting.value = false;
    }
}
function openDeleteSponsor(sponsor) {
    sponsorToDelete.value = sponsor;
    showSponsorDeleteConfirm.value = true;
}
async function confirmDeleteSponsor() {
    if (!sponsorToDelete.value || !canManageTournaments.value)
        return;
    sponsorDeleting.value = true;
    try {
        await api.deleteSponsor(sponsorToDelete.value.id);
        showToast('Sponsor deleted', 'success');
        showSponsorDeleteConfirm.value = false;
        sponsorToDelete.value = null;
        await loadSponsors();
    }
    catch (err) {
        showToast(getErrorMessage(err) || 'Failed to delete sponsor', 'error', 3000);
    }
    finally {
        sponsorDeleting.value = false;
    }
}
onMounted(() => {
    loadTournament();
    loadSponsors();
    loadTeamFavorites();
});
watch(() => tournamentId.value, (next, prev) => {
    if (next && next !== prev) {
        loadTournament();
    }
});
function formatDate(value) {
    if (!value)
        return '';
    try {
        const d = new Date(value);
        if (Number.isNaN(d.getTime()))
            return String(value);
        return d.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }
    catch {
        return String(value);
    }
}
function formatType(raw) {
    const v = (raw || '').toLowerCase();
    if (v === 'league')
        return 'League';
    if (v === 'knockout')
        return 'Knockout';
    if (v === 'round_robin')
        return 'Round robin';
    return v || 'League';
}
function formatStatus(raw) {
    const v = (raw || '').toLowerCase();
    if (v === 'upcoming')
        return 'Upcoming';
    if (v === 'ongoing')
        return 'Ongoing';
    if (v === 'completed')
        return 'Completed';
    if (v === 'cancelled')
        return 'Cancelled';
    return v || 'Upcoming';
}
function formatFixtureStatus(raw) {
    const v = (raw || '').toLowerCase();
    if (v === 'scheduled')
        return 'Scheduled';
    if (v === 'in_progress')
        return 'In progress';
    if (v === 'completed')
        return 'Completed';
    if (v === 'abandoned')
        return 'Abandoned';
    return v || 'Scheduled';
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['td-type-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['td-status-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['td-status-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['td-status-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['td-status-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['td-layout']} */ ;
/** @type {__VLS_StyleScopedClasses['td-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['td-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['td-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table']} */ ;
/** @type {__VLS_StyleScopedClasses['td-team-fav-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['td-team-fav-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['td-team-fav-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['td-modal']} */ ;
/** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['td-btn-danger-text']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table-sponsors']} */ ;
/** @type {__VLS_StyleScopedClasses['td-table-sponsors']} */ ;
/** @type {__VLS_StyleScopedClasses['td-link-truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['td-checkbox-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "tournament-detail" },
});
/** @type {__VLS_StyleScopedClasses['tournament-detail']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "td-header" },
});
/** @type {__VLS_StyleScopedClasses['td-header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "td-header-main" },
});
/** @type {__VLS_StyleScopedClasses['td-header-main']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.goBack) },
    ...{ class: "td-back" },
    type: "button",
});
/** @type {__VLS_StyleScopedClasses['td-back']} */ ;
if (__VLS_ctx.tournament) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-title-block" },
    });
    /** @type {__VLS_StyleScopedClasses['td-title-block']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({
        ...{ class: "td-title" },
    });
    /** @type {__VLS_StyleScopedClasses['td-title']} */ ;
    (__VLS_ctx.tournament.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "td-subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['td-subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "td-type-pill" },
    });
    /** @type {__VLS_StyleScopedClasses['td-type-pill']} */ ;
    (__VLS_ctx.formatType(__VLS_ctx.tournament.tournament_type || 'league'));
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "td-status-pill" },
        'data-status': (__VLS_ctx.tournament.status || 'upcoming'),
    });
    /** @type {__VLS_StyleScopedClasses['td-status-pill']} */ ;
    (__VLS_ctx.formatStatus(__VLS_ctx.tournament.status || 'upcoming'));
}
if (__VLS_ctx.canManageTournaments && __VLS_ctx.tournament) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "td-role-label" },
    });
    /** @type {__VLS_StyleScopedClasses['td-role-label']} */ ;
    (__VLS_ctx.accessLabel);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-actions-buttons" },
    });
    /** @type {__VLS_StyleScopedClasses['td-actions-buttons']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.reload) },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.openEditModal) },
        type: "button",
        ...{ class: "td-btn td-btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-primary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.openDeleteConfirm) },
        type: "button",
        ...{ class: "td-btn td-btn-danger" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-danger']} */ ;
}
else if (__VLS_ctx.tournament && __VLS_ctx.canViewDetail) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-banner td-banner-info" },
    });
    /** @type {__VLS_StyleScopedClasses['td-banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-banner-info']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
}
let __VLS_0;
/** @ts-ignore @type { | typeof __VLS_components.Teleport | typeof __VLS_components.Teleport} */
Teleport;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    to: "body",
}));
const __VLS_2 = __VLS_1({
    to: "body",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
if (__VLS_ctx.toast) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-toast" },
        ...{ class: (`td-toast-${__VLS_ctx.toast.type}`) },
    });
    /** @type {__VLS_StyleScopedClasses['td-toast']} */ ;
    (__VLS_ctx.toast.message);
}
// @ts-ignore
[goBack, tournament, tournament, tournament, tournament, tournament, tournament, tournament, formatType, formatStatus, canManageTournaments, accessLabel, reload, openEditModal, openDeleteConfirm, canViewDetail, toast, toast, toast,];
var __VLS_3;
if (__VLS_ctx.loading && !__VLS_ctx.loaded) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-state td-state-loading" },
    });
    /** @type {__VLS_StyleScopedClasses['td-state']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-state-loading']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "spinner" },
        'aria-hidden': "true",
    });
    /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
}
else if (__VLS_ctx.notFound) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-state td-state-empty" },
    });
    /** @type {__VLS_StyleScopedClasses['td-state']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-state-empty']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.goBack) },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
}
else if (!__VLS_ctx.canViewDetail) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-state td-state-locked" },
    });
    /** @type {__VLS_StyleScopedClasses['td-state']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-state-locked']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "td-muted" },
    });
    /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.goToLogin) },
        type: "button",
        ...{ class: "td-btn td-btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-primary']} */ ;
}
else if (__VLS_ctx.errorMessage) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-state td-state-error" },
    });
    /** @type {__VLS_StyleScopedClasses['td-state']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-state-error']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.errorMessage);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-state-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-state-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.reload) },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.goBack) },
        type: "button",
        ...{ class: "td-btn td-btn-ghost" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-ghost']} */ ;
}
if (__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament))
                    return;
                __VLS_ctx.showEditModal = false;
                // @ts-ignore
                [goBack, goBack, tournament, canManageTournaments, reload, canViewDetail, loading, loaded, notFound, goToLogin, errorMessage, errorMessage, showEditModal, showEditModal,];
            } },
        ...{ class: "td-modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.submitEdit) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.editForm.name),
        type: "text",
        required: true,
        placeholder: "e.g., Premier League 2024",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        value: (__VLS_ctx.editForm.description),
        placeholder: "Tournament description",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
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
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
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
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.editForm.start_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "date",
    });
    (__VLS_ctx.editForm.end_date);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showEditModal && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament))
                    return;
                __VLS_ctx.showEditModal = false;
                // @ts-ignore
                [showEditModal, submitEdit, editForm, editForm, editForm, editForm, editForm, editForm,];
            } },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "td-btn td-btn-primary" },
        disabled: (__VLS_ctx.editSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-primary']} */ ;
    (__VLS_ctx.editSubmitting ? 'Saving...' : 'Save Changes');
}
if (__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament))
                    return;
                __VLS_ctx.showDeleteConfirm = false;
                // @ts-ignore
                [tournament, canManageTournaments, editSubmitting, editSubmitting, showDeleteConfirm, showDeleteConfirm,];
            } },
        ...{ class: "td-modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal td-modal-confirm" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-modal-confirm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "td-confirm-text" },
    });
    /** @type {__VLS_StyleScopedClasses['td-confirm-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.tournament.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showDeleteConfirm && __VLS_ctx.canManageTournaments && __VLS_ctx.tournament))
                    return;
                __VLS_ctx.showDeleteConfirm = false;
                // @ts-ignore
                [tournament, showDeleteConfirm,];
            } },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
        disabled: (__VLS_ctx.deleteSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.confirmDelete) },
        type: "button",
        ...{ class: "td-btn td-btn-danger" },
        disabled: (__VLS_ctx.deleteSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-danger']} */ ;
    (__VLS_ctx.deleteSubmitting ? 'Deleting...' : 'Delete Tournament');
}
if (__VLS_ctx.showSponsorModal && __VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeSponsorModal) },
        ...{ class: "td-modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    (__VLS_ctx.editingSponsor ? 'Edit Sponsor' : 'Add Sponsor');
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.submitSponsor) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        value: (__VLS_ctx.sponsorForm.name),
        type: "text",
        required: true,
        placeholder: "Sponsor name",
    });
    if (!__VLS_ctx.editingSponsor) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "td-form-group" },
        });
        /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            ...{ onChange: (__VLS_ctx.onLogoFileChange) },
            type: "file",
            accept: ".png,.svg,.webp,image/png,image/svg+xml,image/webp",
            required: true,
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
            ...{ class: "td-muted" },
        });
        /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "td-form-group" },
        });
        /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        if (__VLS_ctx.editingSponsor?.logoUrl) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
                src: (__VLS_ctx.resolveSponsorLogo(__VLS_ctx.editingSponsor.logoUrl)),
                alt: "Current logo",
                ...{ class: "td-current-logo" },
            });
            /** @type {__VLS_StyleScopedClasses['td-current-logo']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
            ...{ class: "td-muted" },
        });
        /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "url",
        placeholder: "https://sponsor-website.com",
    });
    (__VLS_ctx.sponsorForm.click_url);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "number",
        min: "1",
        max: "5",
    });
    (__VLS_ctx.sponsorForm.weight);
    __VLS_asFunctionalElement1(__VLS_intrinsics.small, __VLS_intrinsics.small)({
        ...{ class: "td-muted" },
    });
    /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-form-group td-checkbox-group" },
    });
    /** @type {__VLS_StyleScopedClasses['td-form-group']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-checkbox-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "checkbox",
    });
    (__VLS_ctx.sponsorForm.is_active);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeSponsorModal) },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "td-btn td-btn-primary" },
        disabled: (__VLS_ctx.sponsorSubmitting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-primary']} */ ;
    (__VLS_ctx.sponsorSubmitting ? 'Saving...' : (__VLS_ctx.editingSponsor ? 'Update' : 'Create'));
}
if (__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showSponsorDeleteConfirm = false;
                // @ts-ignore
                [canManageTournaments, canManageTournaments, deleteSubmitting, deleteSubmitting, deleteSubmitting, confirmDelete, showSponsorModal, closeSponsorModal, closeSponsorModal, editingSponsor, editingSponsor, editingSponsor, editingSponsor, editingSponsor, submitSponsor, sponsorForm, sponsorForm, sponsorForm, sponsorForm, onLogoFileChange, resolveSponsorLogo, sponsorSubmitting, sponsorSubmitting, showSponsorDeleteConfirm, showSponsorDeleteConfirm,];
            } },
        ...{ class: "td-modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal td-modal-confirm" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-modal-confirm']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "td-confirm-text" },
    });
    /** @type {__VLS_StyleScopedClasses['td-confirm-text']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (__VLS_ctx.sponsorToDelete?.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['td-modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments))
                    return;
                __VLS_ctx.showSponsorDeleteConfirm = false;
                // @ts-ignore
                [showSponsorDeleteConfirm, sponsorToDelete,];
            } },
        type: "button",
        ...{ class: "td-btn td-btn-outline" },
        disabled: (__VLS_ctx.sponsorDeleting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-outline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.confirmDeleteSponsor) },
        type: "button",
        ...{ class: "td-btn td-btn-danger" },
        disabled: (__VLS_ctx.sponsorDeleting),
    });
    /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['td-btn-danger']} */ ;
    (__VLS_ctx.sponsorDeleting ? 'Deleting...' : 'Delete Sponsor');
}
else if (__VLS_ctx.tournament) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-layout" },
    });
    /** @type {__VLS_StyleScopedClasses['td-layout']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-column" },
    });
    /** @type {__VLS_StyleScopedClasses['td-column']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "td-card" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.dl, __VLS_intrinsics.dl)({
        ...{ class: "td-meta" },
    });
    /** @type {__VLS_StyleScopedClasses['td-meta']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
    (__VLS_ctx.formatType(__VLS_ctx.tournament.tournament_type || 'league'));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
    (__VLS_ctx.formatStatus(__VLS_ctx.tournament.status || 'upcoming'));
    if (__VLS_ctx.tournament.start_date || __VLS_ctx.tournament.end_date) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        if (__VLS_ctx.tournament.start_date) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (__VLS_ctx.formatDate(__VLS_ctx.tournament.start_date));
        }
        if (__VLS_ctx.tournament.start_date && __VLS_ctx.tournament.end_date) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        }
        if (__VLS_ctx.tournament.end_date) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (__VLS_ctx.formatDate(__VLS_ctx.tournament.end_date));
        }
    }
    if (__VLS_ctx.tournament.description) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dt, __VLS_intrinsics.dt)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.dd, __VLS_intrinsics.dd)({});
        (__VLS_ctx.tournament.description);
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "td-card" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-card-header" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.pointsTable.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "td-card-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['td-card-subtitle']} */ ;
    }
    if (__VLS_ctx.pointsTable.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "td-table" },
        });
        /** @type {__VLS_StyleScopedClasses['td-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [row, idx] of __VLS_vFor((__VLS_ctx.pointsTable))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (row.id || row.team_name || idx),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (idx + 1);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.team_name || '—');
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.matches_played ?? row.played ?? 0);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.wins ?? 0);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.losses ?? 0);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.ties ?? 0);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.no_results ?? 0);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (row.points ?? 0);
            // @ts-ignore
            [tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, tournament, formatType, formatStatus, sponsorDeleting, sponsorDeleting, sponsorDeleting, confirmDeleteSponsor, formatDate, formatDate, pointsTable, pointsTable, pointsTable,];
        }
    }
    if (__VLS_ctx.canManageTournaments) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "td-card" },
        });
        /** @type {__VLS_StyleScopedClasses['td-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "td-card-header td-card-header-row" },
        });
        /** @type {__VLS_StyleScopedClasses['td-card-header']} */ ;
        /** @type {__VLS_StyleScopedClasses['td-card-header-row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
        if (__VLS_ctx.sponsors.length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "td-card-subtitle" },
            });
            /** @type {__VLS_StyleScopedClasses['td-card-subtitle']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.openCreateSponsor) },
            type: "button",
            ...{ class: "td-btn td-btn-primary td-btn-sm" },
        });
        /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
        /** @type {__VLS_StyleScopedClasses['td-btn-primary']} */ ;
        /** @type {__VLS_StyleScopedClasses['td-btn-sm']} */ ;
        if (__VLS_ctx.sponsorsLoading) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "td-state td-state-loading td-state-inline" },
            });
            /** @type {__VLS_StyleScopedClasses['td-state']} */ ;
            /** @type {__VLS_StyleScopedClasses['td-state-loading']} */ ;
            /** @type {__VLS_StyleScopedClasses['td-state-inline']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "spinner spinner-sm" },
                'aria-hidden': "true",
            });
            /** @type {__VLS_StyleScopedClasses['spinner']} */ ;
            /** @type {__VLS_StyleScopedClasses['spinner-sm']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
        }
        else if (__VLS_ctx.sponsors.length) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
                ...{ class: "td-table td-table-sponsors" },
            });
            /** @type {__VLS_StyleScopedClasses['td-table']} */ ;
            /** @type {__VLS_StyleScopedClasses['td-table-sponsors']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
            for (const [sponsor] of __VLS_vFor((__VLS_ctx.sponsors))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                    key: (sponsor.id),
                });
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                if (sponsor.logoUrl) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.img)({
                        src: (__VLS_ctx.resolveSponsorLogo(sponsor.logoUrl)),
                        alt: (sponsor.name),
                        ...{ class: "td-sponsor-logo" },
                    });
                    /** @type {__VLS_StyleScopedClasses['td-sponsor-logo']} */ ;
                }
                else {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "td-muted" },
                    });
                    /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
                }
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (sponsor.name);
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                if (sponsor.clickUrl) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
                        href: (sponsor.clickUrl),
                        target: "_blank",
                        rel: "noopener",
                        ...{ class: "td-link-truncate" },
                    });
                    /** @type {__VLS_StyleScopedClasses['td-link-truncate']} */ ;
                    (__VLS_ctx.truncateUrl(sponsor.clickUrl));
                }
                else {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "td-muted" },
                    });
                    /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
                }
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                (sponsor.weight);
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "td-status-badge" },
                    ...{ class: (sponsor.is_active !== false ? 'td-status-active' : 'td-status-inactive') },
                });
                /** @type {__VLS_StyleScopedClasses['td-status-badge']} */ ;
                (sponsor.is_active !== false ? 'Active' : 'Inactive');
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                    ...{ class: "td-actions-cell" },
                });
                /** @type {__VLS_StyleScopedClasses['td-actions-cell']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!!(__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments))
                                return;
                            if (!(__VLS_ctx.tournament))
                                return;
                            if (!(__VLS_ctx.canManageTournaments))
                                return;
                            if (!!(__VLS_ctx.sponsorsLoading))
                                return;
                            if (!(__VLS_ctx.sponsors.length))
                                return;
                            __VLS_ctx.openEditSponsor(sponsor);
                            // @ts-ignore
                            [canManageTournaments, resolveSponsorLogo, sponsors, sponsors, sponsors, openCreateSponsor, sponsorsLoading, truncateUrl, openEditSponsor,];
                        } },
                    type: "button",
                    ...{ class: "td-btn td-btn-ghost td-btn-sm" },
                });
                /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-btn-ghost']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-btn-sm']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!!(__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments))
                                return;
                            if (!(__VLS_ctx.tournament))
                                return;
                            if (!(__VLS_ctx.canManageTournaments))
                                return;
                            if (!!(__VLS_ctx.sponsorsLoading))
                                return;
                            if (!(__VLS_ctx.sponsors.length))
                                return;
                            __VLS_ctx.openDeleteSponsor(sponsor);
                            // @ts-ignore
                            [openDeleteSponsor,];
                        } },
                    type: "button",
                    ...{ class: "td-btn td-btn-ghost td-btn-sm td-btn-danger-text" },
                });
                /** @type {__VLS_StyleScopedClasses['td-btn']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-btn-ghost']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-btn-sm']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-btn-danger-text']} */ ;
                // @ts-ignore
                [];
            }
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-column" },
    });
    /** @type {__VLS_StyleScopedClasses['td-column']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "td-card" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-card-header" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.teams.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "td-card-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['td-card-subtitle']} */ ;
    }
    if (__VLS_ctx.teams.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "td-list" },
        });
        /** @type {__VLS_StyleScopedClasses['td-list']} */ ;
        for (const [team] of __VLS_vFor((__VLS_ctx.teams))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (team.id || team.team_name),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "td-list-main" },
            });
            /** @type {__VLS_StyleScopedClasses['td-list-main']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (team.team_name);
            if (__VLS_ctx.authStore.currentUser && team.id != null) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!!(__VLS_ctx.showSponsorDeleteConfirm && __VLS_ctx.canManageTournaments))
                                return;
                            if (!(__VLS_ctx.tournament))
                                return;
                            if (!(__VLS_ctx.teams.length))
                                return;
                            if (!(__VLS_ctx.authStore.currentUser && team.id != null))
                                return;
                            __VLS_ctx.toggleTeamFavorite(team.id);
                            // @ts-ignore
                            [teams, teams, teams, authStore, toggleTeamFavorite,];
                        } },
                    type: "button",
                    ...{ class: "td-team-fav-btn" },
                    ...{ class: ({ 'td-team-fav-active': __VLS_ctx.isTeamFavorite(team.id) }) },
                    disabled: (__VLS_ctx.togglingTeamFavorite.has(String(team.id))),
                    title: (__VLS_ctx.isTeamFavorite(team.id) ? 'Remove from favorites' : 'Add to favorites'),
                });
                /** @type {__VLS_StyleScopedClasses['td-team-fav-btn']} */ ;
                /** @type {__VLS_StyleScopedClasses['td-team-fav-active']} */ ;
                (__VLS_ctx.isTeamFavorite(team.id) ? '★' : '☆');
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "td-list-secondary" },
            });
            /** @type {__VLS_StyleScopedClasses['td-list-secondary']} */ ;
            ((team.matches_played ?? 0));
            ((team.points ?? 0));
            // @ts-ignore
            [isTeamFavorite, isTeamFavorite, isTeamFavorite, togglingTeamFavorite,];
        }
    }
    if (__VLS_ctx.teams.length && !__VLS_ctx.canManageTournaments) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "td-muted td-footnote" },
        });
        /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
        /** @type {__VLS_StyleScopedClasses['td-footnote']} */ ;
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "td-card" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "td-card-header" },
    });
    /** @type {__VLS_StyleScopedClasses['td-card-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.fixtures.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "td-card-subtitle" },
        });
        /** @type {__VLS_StyleScopedClasses['td-card-subtitle']} */ ;
    }
    if (__VLS_ctx.fixtures.length) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
            ...{ class: "td-list" },
        });
        /** @type {__VLS_StyleScopedClasses['td-list']} */ ;
        for (const [fixture] of __VLS_vFor((__VLS_ctx.fixtures))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                key: (fixture.id),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "td-list-main" },
            });
            /** @type {__VLS_StyleScopedClasses['td-list-main']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (fixture.team_a_name);
            (fixture.team_b_name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "td-list-secondary" },
            });
            /** @type {__VLS_StyleScopedClasses['td-list-secondary']} */ ;
            if (fixture.venue) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                (fixture.venue);
            }
            if (fixture.scheduled_date) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                (__VLS_ctx.formatDate(fixture.scheduled_date));
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (__VLS_ctx.formatFixtureStatus(fixture.status || 'scheduled'));
            // @ts-ignore
            [canManageTournaments, formatDate, teams, fixtures, fixtures, fixtures, formatFixtureStatus,];
        }
    }
    if (__VLS_ctx.fixtures.length && !__VLS_ctx.canManageTournaments) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "td-muted td-footnote" },
        });
        /** @type {__VLS_StyleScopedClasses['td-muted']} */ ;
        /** @type {__VLS_StyleScopedClasses['td-footnote']} */ ;
    }
}
// @ts-ignore
[canManageTournaments, fixtures,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
