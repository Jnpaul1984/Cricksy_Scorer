/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted } from 'vue';
import { API_BASE, getStoredToken } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
const auth = useAuthStore();
// State
const loading = ref(true);
const error = ref(null);
const seats = ref([]);
const users = ref([]);
const teams = ref([]);
const showAssignModal = ref(false);
const selectedUserId = ref(null);
const selectedRole = ref('free');
const isExporting = ref(false);
// Auth checks
const isLoggedIn = computed(() => !!auth.token);
const canManageOrg = computed(() => {
    const role = auth.role?.toLowerCase() || '';
    return ['org_pro', 'superuser'].includes(role);
});
// Seat definitions with friendly labels
const seatDefinitions = [
    { role: 'coach_pro', label: 'Coach Pro', icon: '🎯' },
    { role: 'analyst_pro', label: 'Analyst Pro', icon: '📊' },
    { role: 'player_pro', label: 'Player Pro', icon: '🏏' },
    { role: 'org_pro', label: 'Org Pro', icon: '🏢' },
];
// API functions
async function fetchOrgData() {
    loading.value = true;
    error.value = null;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const token = getStoredToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        // Fetch users to count seats
        const usersRes = await fetch(`${API_BASE}/api/users`, { headers });
        if (usersRes.ok) {
            users.value = await usersRes.json();
        }
        // Fetch teams
        const teamsRes = await fetch(`${API_BASE}/api/teams`, { headers });
        if (teamsRes.ok) {
            const teamsData = await teamsRes.json();
            teams.value = teamsData.map((t) => ({
                id: t.id,
                name: t.name,
                players_count: t.players?.length || 0,
                coach_name: t.coach_name,
                season: t.season
            }));
        }
        // Calculate seat usage
        calculateSeats();
    }
    catch (err) {
        error.value = err.message || 'Failed to load organization data';
        console.error('Error fetching org data:', err);
    }
    finally {
        loading.value = false;
    }
}
function calculateSeats() {
    seats.value = seatDefinitions.map(def => {
        const usedCount = users.value.filter(u => u.role === def.role).length;
        return {
            role: def.role,
            label: def.label,
            used: usedCount,
            limit: null // No hard limit for now, can be configured
        };
    });
}
function getUsersForRole(role) {
    return users.value.filter(u => u.role === role);
}
async function assignRole(userId, newRole) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getStoredToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    try {
        const res = await fetch(`${API_BASE}/api/users/${userId}/role`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ role: newRole })
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || 'Failed to update role');
        }
        await fetchOrgData();
        showAssignModal.value = false;
    }
    catch (err) {
        error.value = err.message || 'Failed to assign role';
    }
}
async function revokeRole(userId) {
    if (!confirm('Are you sure you want to revoke this user\'s role? They will be set to Free tier.')) {
        return;
    }
    await assignRole(userId, 'free');
}
function openAssignModal(userId) {
    selectedUserId.value = userId || null;
    selectedRole.value = 'coach_pro';
    showAssignModal.value = true;
}
// PDF Export
async function exportToPDF() {
    isExporting.value = true;
    try {
        // Create a printable version of the dashboard
        const printContent = generatePrintContent();
        // Open print dialog
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            throw new Error('Could not open print window. Please allow popups.');
        }
        printWindow.document.write(printContent);
        printWindow.document.close();
        // Wait for content to load then print
        printWindow.onload = () => {
            printWindow.print();
            printWindow.close();
        };
    }
    catch (err) {
        error.value = err.message || 'Failed to export PDF';
    }
    finally {
        isExporting.value = false;
    }
}
function generatePrintContent() {
    const date = new Date().toLocaleDateString();
    const seatsHtml = seats.value.map(s => `
    <tr>
      <td>${s.label}</td>
      <td>${s.used}</td>
      <td>${s.limit ?? 'Unlimited'}</td>
    </tr>
  `).join('');
    const teamsHtml = teams.value.map(t => `
    <tr>
      <td>${t.name}</td>
      <td>${t.players_count}</td>
      <td>${t.coach_name || 'None'}</td>
      <td>${t.season || '-'}</td>
    </tr>
  `).join('');
    return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Organization Report - ${date}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
        h1 { color: #1a1a2e; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }
        h2 { color: #4f46e5; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f5f5f5; font-weight: 600; }
        tr:nth-child(even) { background: #fafafa; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #4f46e5; }
        .stat-label { font-size: 12px; color: #666; }
        .footer { margin-top: 40px; font-size: 12px; color: #888; text-align: center; }
        @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
      </style>
    </head>
    <body>
      <h1>🏢 Organization Management Report</h1>
      <p>Generated on ${date}</p>

      <div class="summary">
        <div class="stat-box">
          <div class="stat-value">${teams.value.length}</div>
          <div class="stat-label">Total Teams</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${users.value.length}</div>
          <div class="stat-label">Total Users</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${seats.value.reduce((sum, s) => sum + s.used, 0)}</div>
          <div class="stat-label">Assigned Seats</div>
        </div>
      </div>

      <h2>📊 Seat Allocation</h2>
      <table>
        <thead>
          <tr>
            <th>Seat Type</th>
            <th>Used</th>
            <th>Limit</th>
          </tr>
        </thead>
        <tbody>
          ${seatsHtml || '<tr><td colspan="3">No seat data</td></tr>'}
        </tbody>
      </table>

      <h2>🏏 Teams</h2>
      <table>
        <thead>
          <tr>
            <th>Team Name</th>
            <th>Players</th>
            <th>Coach</th>
            <th>Season</th>
          </tr>
        </thead>
        <tbody>
          ${teamsHtml || '<tr><td colspan="4">No teams</td></tr>'}
        </tbody>
      </table>

      <div class="footer">
        Cricksy Scorer - Organization Management Report
      </div>
    </body>
    </html>
  `;
}
onMounted(() => {
    fetchOrgData();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['org-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['org-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['user-item']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-table']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-table']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-table']} */ ;
/** @type {__VLS_StyleScopedClasses['teams-table']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['org-management']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['seats-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['users-by-role']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "org-management" },
});
/** @type {__VLS_StyleScopedClasses['org-management']} */ ;
if (!__VLS_ctx.isLoggedIn) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-banner info" },
    });
    /** @type {__VLS_StyleScopedClasses['org-banner']} */ ;
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
else if (!__VLS_ctx.canManageOrg) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-banner warn" },
    });
    /** @type {__VLS_StyleScopedClasses['org-banner']} */ ;
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header" },
});
/** @type {__VLS_StyleScopedClasses['header']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-text" },
});
/** @type {__VLS_StyleScopedClasses['header-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "subtitle" },
});
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "header-actions" },
});
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.exportToPDF) },
    ...{ class: "btn-secondary" },
    disabled: (__VLS_ctx.isExporting || !__VLS_ctx.canManageOrg),
});
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
(__VLS_ctx.isExporting ? 'Exporting...' : '📄 Export PDF');
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.openAssignModal();
            // @ts-ignore
            [canManageOrg, canManageOrg, exportToPDF, isExporting, isExporting, openAssignModal,];
        } },
    ...{ class: "btn-primary" },
    disabled: (!__VLS_ctx.canManageOrg),
});
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
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
        ...{ onClick: (__VLS_ctx.fetchOrgData) },
        ...{ class: "btn-link" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-link']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "org-content" },
    });
    /** @type {__VLS_StyleScopedClasses['org-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "seats-section" },
    });
    /** @type {__VLS_StyleScopedClasses['seats-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "seats-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['seats-grid']} */ ;
    for (const [seat] of __VLS_vFor((__VLS_ctx.seats))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (seat.role),
            ...{ class: "seat-card" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "seat-icon" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-icon']} */ ;
        (__VLS_ctx.seatDefinitions.find(d => d.role === seat.role)?.icon || '👤');
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "seat-info" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-info']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "seat-label" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-label']} */ ;
        (seat.label);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "seat-usage" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-usage']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "seat-count" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-count']} */ ;
        (seat.used);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "seat-limit" },
        });
        /** @type {__VLS_StyleScopedClasses['seat-limit']} */ ;
        (seat.limit ?? '∞');
        if (__VLS_ctx.canManageOrg && seat.used > 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!!(__VLS_ctx.error))
                            return;
                        if (!(__VLS_ctx.canManageOrg && seat.used > 0))
                            return;
                        __VLS_ctx.openAssignModal();
                        // @ts-ignore
                        [canManageOrg, canManageOrg, openAssignModal, loading, error, error, fetchOrgData, seats, seatDefinitions,];
                    } },
                ...{ class: "btn-ghost btn-sm" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-ghost']} */ ;
            /** @type {__VLS_StyleScopedClasses['btn-sm']} */ ;
        }
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "users-section" },
    });
    /** @type {__VLS_StyleScopedClasses['users-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "users-by-role" },
    });
    /** @type {__VLS_StyleScopedClasses['users-by-role']} */ ;
    for (const [def] of __VLS_vFor((__VLS_ctx.seatDefinitions))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            key: (def.role),
            ...{ class: "role-group" },
        });
        /** @type {__VLS_StyleScopedClasses['role-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
            ...{ class: "role-title" },
        });
        /** @type {__VLS_StyleScopedClasses['role-title']} */ ;
        (def.icon);
        (def.label);
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "role-count" },
        });
        /** @type {__VLS_StyleScopedClasses['role-count']} */ ;
        (__VLS_ctx.getUsersForRole(def.role).length);
        if (__VLS_ctx.getUsersForRole(def.role).length === 0) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "no-users" },
            });
            /** @type {__VLS_StyleScopedClasses['no-users']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({
                ...{ class: "user-list" },
            });
            /** @type {__VLS_StyleScopedClasses['user-list']} */ ;
            for (const [user] of __VLS_vFor((__VLS_ctx.getUsersForRole(def.role)))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                    key: (user.id),
                    ...{ class: "user-item" },
                });
                /** @type {__VLS_StyleScopedClasses['user-item']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: "user-email" },
                });
                /** @type {__VLS_StyleScopedClasses['user-email']} */ ;
                (user.email);
                if (__VLS_ctx.canManageOrg) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                        ...{ onClick: (...[$event]) => {
                                if (!!(__VLS_ctx.loading))
                                    return;
                                if (!!(__VLS_ctx.error))
                                    return;
                                if (!!(__VLS_ctx.getUsersForRole(def.role).length === 0))
                                    return;
                                if (!(__VLS_ctx.canManageOrg))
                                    return;
                                __VLS_ctx.revokeRole(user.id);
                                // @ts-ignore
                                [canManageOrg, seatDefinitions, getUsersForRole, getUsersForRole, getUsersForRole, revokeRole,];
                            } },
                        ...{ class: "btn-icon btn-icon-danger" },
                        title: "Revoke seat",
                    });
                    /** @type {__VLS_StyleScopedClasses['btn-icon']} */ ;
                    /** @type {__VLS_StyleScopedClasses['btn-icon-danger']} */ ;
                }
                // @ts-ignore
                [];
            }
        }
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "teams-section" },
    });
    /** @type {__VLS_StyleScopedClasses['teams-section']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "section-header" },
    });
    /** @type {__VLS_StyleScopedClasses['section-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.canManageOrg) {
        let __VLS_6;
        /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            to: "/teams",
            ...{ class: "btn-link" },
        }));
        const __VLS_8 = __VLS_7({
            to: "/teams",
            ...{ class: "btn-link" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        /** @type {__VLS_StyleScopedClasses['btn-link']} */ ;
        const { default: __VLS_11 } = __VLS_9.slots;
        // @ts-ignore
        [canManageOrg,];
        var __VLS_9;
    }
    if (__VLS_ctx.teams.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        if (__VLS_ctx.canManageOrg) {
            let __VLS_12;
            /** @ts-ignore @type { | typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
            RouterLink;
            // @ts-ignore
            const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({
                to: "/teams",
                ...{ class: "btn-primary" },
            }));
            const __VLS_14 = __VLS_13({
                to: "/teams",
                ...{ class: "btn-primary" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_13));
            /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
            const { default: __VLS_17 } = __VLS_15.slots;
            // @ts-ignore
            [canManageOrg, teams,];
            var __VLS_15;
        }
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "teams-table-wrapper" },
        });
        /** @type {__VLS_StyleScopedClasses['teams-table-wrapper']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "teams-table" },
        });
        /** @type {__VLS_StyleScopedClasses['teams-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [team] of __VLS_vFor((__VLS_ctx.teams))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (team.id),
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "team-name" },
            });
            /** @type {__VLS_StyleScopedClasses['team-name']} */ ;
            (team.name);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (team.players_count);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (team.coach_name || '—');
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (team.season || '—');
            // @ts-ignore
            [teams,];
        }
    }
}
let __VLS_18;
/** @ts-ignore @type { | typeof __VLS_components.Teleport | typeof __VLS_components.Teleport} */
Teleport;
// @ts-ignore
const __VLS_19 = __VLS_asFunctionalComponent1(__VLS_18, new __VLS_18({
    to: "body",
}));
const __VLS_20 = __VLS_19({
    to: "body",
}, ...__VLS_functionalComponentArgsRest(__VLS_19));
const { default: __VLS_23 } = __VLS_21.slots;
let __VLS_24;
/** @ts-ignore @type { | typeof __VLS_components.Transition | typeof __VLS_components.Transition} */
Transition;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent1(__VLS_24, new __VLS_24({
    name: "fade",
}));
const __VLS_26 = __VLS_25({
    name: "fade",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
const { default: __VLS_29 } = __VLS_27.slots;
if (__VLS_ctx.showAssignModal) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showAssignModal))
                    return;
                __VLS_ctx.showAssignModal = false;
                // @ts-ignore
                [showAssignModal, showAssignModal,];
            } },
        ...{ class: "modal-backdrop" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-backdrop']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "modal-header" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showAssignModal))
                    return;
                __VLS_ctx.showAssignModal = false;
                // @ts-ignore
                [showAssignModal,];
            } },
        'aria-label': "Close",
        ...{ class: "close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-body" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedUserId),
        ...{ class: "ds-input" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
    });
    for (const [user] of __VLS_vFor((__VLS_ctx.users.filter(u => u.role === 'free')))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (user.id),
            value: (user.id),
        });
        (user.email);
        // @ts-ignore
        [selectedUserId, users,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "field-label" },
    });
    /** @type {__VLS_StyleScopedClasses['field-label']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        value: (__VLS_ctx.selectedRole),
        ...{ class: "ds-input" },
    });
    /** @type {__VLS_StyleScopedClasses['ds-input']} */ ;
    for (const [def] of __VLS_vFor((__VLS_ctx.seatDefinitions))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
            key: (def.role),
            value: (def.role),
        });
        (def.icon);
        (def.label);
        // @ts-ignore
        [seatDefinitions, selectedRole,];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
        ...{ class: "modal-footer" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showAssignModal))
                    return;
                __VLS_ctx.showAssignModal = false;
                // @ts-ignore
                [showAssignModal,];
            } },
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showAssignModal))
                    return;
                __VLS_ctx.assignRole(__VLS_ctx.selectedUserId, __VLS_ctx.selectedRole);
                // @ts-ignore
                [selectedUserId, selectedRole, assignRole,];
            } },
        ...{ class: "btn-primary" },
        disabled: (!__VLS_ctx.selectedUserId),
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
}
// @ts-ignore
[selectedUserId,];
var __VLS_27;
// @ts-ignore
[];
var __VLS_21;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
