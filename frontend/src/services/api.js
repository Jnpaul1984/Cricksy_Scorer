// src/services/api.ts
// Single, canonical API client aligned with FastAPI backend & the Pinia game store.
const VITE_BASE = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE : '';
const LEGACY_BASE = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : '';
const RUNTIME_ORIGIN = typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '';
// Parse ?apiBase= from the URL as a runtime override
function getApiBaseFromUrl() {
    if (typeof window === 'undefined')
        return '';
    try {
        const params = new URLSearchParams(window.location.search);
        // Check hash-based routing (#/route?apiBase=...)
        const hashParams = window.location.hash.includes('?')
            ? new URLSearchParams(window.location.hash.split('?')[1])
            : null;
        return (params.get('apiBase') || hashParams?.get('apiBase') || '').replace(/\/+$/, '');
    }
    catch {
        return '';
    }
}
const URL_OVERRIDE = getApiBaseFromUrl();
export const API_BASE = (URL_OVERRIDE || VITE_BASE || LEGACY_BASE || RUNTIME_ORIGIN || '').replace(/\/+$/, '');
// Production-grade logging for API_BASE resolution
const isProduction = import.meta.env.PROD;
if (isProduction && API_BASE === RUNTIME_ORIGIN && !URL_OVERRIDE) {
    console.warn('⚠️ PRODUCTION WARNING: API_BASE fell back to window.origin.', 'This means VITE_API_BASE and VITE_API_BASE_URL are not set.', 'Expected: API endpoint URL. Got:', API_BASE);
}
console.info('API_BASE resolved to:', API_BASE, '| Source:', URL_OVERRIDE ? '?apiBase override' :
    VITE_BASE ? 'VITE_API_BASE' :
        LEGACY_BASE ? 'VITE_API_BASE_URL' :
            'window.origin (fallback)');
export const TOKEN_STORAGE_KEY = 'cricksy_token';
let unauthorizedHandler = null;
export function setUnauthorizedHandler(handler) {
    unauthorizedHandler = handler;
}
export function getStoredToken() {
    if (typeof window === 'undefined')
        return null;
    try {
        return window.localStorage.getItem(TOKEN_STORAGE_KEY);
    }
    catch {
        return null;
    }
}
export function setStoredToken(token) {
    if (typeof window === 'undefined')
        return;
    try {
        if (!token) {
            window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
        else {
            window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
        }
    }
    catch {
        // ignore storage errors (Safari private mode, etc.)
    }
}
function getAuthHeader() {
    const token = getStoredToken();
    if (!token)
        return null;
    return { Authorization: `Bearer ${token}` };
}
function notifyUnauthorized(err) {
    if (unauthorizedHandler) {
        unauthorizedHandler(err);
        return;
    }
    console.warn('[api] 401 unauthorized', err.message);
}
function url(path) {
    if (!API_BASE)
        return path;
    const base = API_BASE.replace(/\/+$/, '');
    const p = path.startsWith('/') ? path : `/${path}`;
    return `${base}${p}`;
}
export function getErrorMessage(err) {
    if (!err)
        return 'Unknown error';
    if (typeof err === 'string')
        return err;
    if (err instanceof Error)
        return err.message || 'Error';
    try {
        const anyErr = err;
        if (anyErr?.detail)
            return String(anyErr.detail);
        if (anyErr?.message)
            return String(anyErr.message);
        if (anyErr?.response?.data?.detail)
            return String(anyErr.response.data.detail);
        if (anyErr?.status && anyErr?.statusText)
            return `${anyErr.status} ${anyErr.statusText}`;
    }
    catch {
        // ignore JSON parsing issues when mining error metadata
    }
    return 'Request failed';
}
/** Low-level fetch wrapper that preserves JSON errors from FastAPI. */
async function request(path, init) {
    const method = (init?.method || 'GET').toUpperCase();
    const hasBody = init?.body !== undefined && init?.body !== null;
    const isForm = typeof FormData !== 'undefined' && init?.body instanceof FormData;
    const isUrlParams = typeof URLSearchParams !== 'undefined' && init?.body instanceof URLSearchParams;
    const isJSONish = hasBody && !isForm && !isUrlParams && typeof init?.body === 'string';
    const authHeader = init?.noAuth ? null : getAuthHeader();
    const res = await fetch(url(path), {
        // For GETs, make results uncacheable so live UI always sees fresh data.
        cache: method === 'GET' ? 'no-store' : init?.cache,
        // If you use cookie/session auth, uncomment the next line:
        // credentials: 'include',
        headers: {
            ...(isJSONish ? { 'Content-Type': 'application/json' } : {}),
            ...(method === 'GET' ? { 'Cache-Control': 'no-store' } : {}),
            ...(authHeader || {}),
            ...(init?.headers || {}),
        },
        ...init,
    });
    if (!res.ok) {
        let detail = undefined;
        try {
            detail = await res.json();
        }
        catch {
            // ignore body parsing errors when building error info
        }
        const msg = detail?.detail || `${res.status} ${res.statusText}`;
        const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        // @ts-expect-error  attach HTTP status for downstream handlers
        err.status = res.status;
        // @ts-expect-error  attach API error payload when available
        err.detail = detail?.detail ?? null;
        if (res.status === 401) {
            notifyUnauthorized(err);
        }
        throw err;
    }
    if (res.status === 204)
        return undefined;
    return (await res.json());
}
export function apiRequestPublic(path, init) {
    const base = init ? { ...init } : {};
    base.noAuth = true;
    return request(path, base);
}
export { request as apiRequest };
async function getInterruptions(gameId) {
    const r = await request(`/games/${encodeURIComponent(gameId)}/interruptions`);
    return Array.isArray(r) ? r
        : Array.isArray(r?.items) ? r.items
            : Array.isArray(r?.interruptions) ? r.interruptions
                : [];
}
/** POST /interruptions/start with best-effort encoding */
async function openInterruption(gameId, kind = 'weather', note) {
    const path = `/games/${encodeURIComponent(gameId)}/interruptions/start`;
    // try JSON {kind, note}
    try {
        const r = await request(path, { method: 'POST', body: JSON.stringify({ kind, note }) });
        return Array.isArray(r?.interruptions) ? r.interruptions.at(-1) : r;
    }
    catch (e) {
        // then form-encoded
        if (e?.status === 400 || e?.status === 422) {
            try {
                const body = new URLSearchParams();
                body.set('kind', kind);
                if (note)
                    body.set('note', note);
                const res = await fetch(url(path), {
                    method: 'POST',
                    body,
                    headers: {
                        ...(getAuthHeader() || {}),
                    },
                }); // browser sets proper header
                if (!res.ok)
                    throw res;
                const j = await res.json();
                return Array.isArray(j?.interruptions) ? j.interruptions.at(-1) : j;
            }
            catch {
                // ignoring fallback failure; we attempt querystring next
            }
            // finally querystring (no body)
            const qs = new URLSearchParams({ kind, ...(note ? { note } : {}) }).toString();
            const res = await fetch(url(`${path}?${qs}`), {
                method: 'POST',
                headers: {
                    ...(getAuthHeader() || {}),
                },
            });
            if (!res.ok) {
                let detail;
                try {
                    detail = await res.json();
                }
                catch {
                    // ignore parse failure for error handling
                }
                const err = new Error(detail?.detail || `${res.status} ${res.statusText}`);
                // @ts-expect-error  expose HTTP status for UI messaging
                err.status = res.status;
                // @ts-expect-error  attach API detail payload for callers
                err.detail = detail?.detail ?? null;
                throw err;
            }
            const j = await res.json();
            return Array.isArray(j?.interruptions) ? j.interruptions.at(-1) : j;
        }
        throw e;
    }
}
/** POST /interruptions/stop  omit {"kind": null}. Accepts JSON, falls back to empty body. */
async function stopInterruption(gameId, kind) {
    const path = `/games/${encodeURIComponent(gameId)}/interruptions/stop`;
    try {
        if (kind) {
            return await request(path, { method: 'POST', body: JSON.stringify({ kind }) });
        }
        // empty body
        return await request(path, { method: 'POST' });
    }
    catch (e) {
        const msg = (e?.detail || e?.message || '').toString().toLowerCase();
        // treat no active interruption as success
        if (e?.status === 400 && (msg.includes('no active') || msg.includes('already stopped'))) {
            return { ok: true, interruptions: [] };
        }
        // try one more time with no body
        if (kind && (e?.status === 400 || e?.status === 422)) {
            return await request(path, { method: 'POST' });
        }
        throw e;
    }
}
export { getInterruptions, openInterruption, stopInterruption };
export async function getDlsPreview(gameId, G50 = 245) {
    return request(`/games/${encodeURIComponent(gameId)}/dls/preview?G50=${G50}`);
}
export async function postDlsApply(gameId, G50 = 245) {
    return request(`/games/${encodeURIComponent(gameId)}/dls/apply?G50=${G50}`, { method: 'POST' });
}
export async function patchReduceOvers(gameId, innings, newOvers) {
    return request(`/games/${encodeURIComponent(gameId)}/overs/reduce`, {
        method: 'PATCH',
        body: JSON.stringify({ innings, new_overs: newOvers }),
    });
}
export async function getMatchCaseStudy(matchId) {
    return request(`/analytics/matches/${encodeURIComponent(matchId)}/case-study`);
}
export async function getMatchAiSummary(matchId) {
    return request(`/analyst/matches/${encodeURIComponent(matchId)}/ai-summary`);
}
export async function getAnalystMatches() {
    return request('/analytics/matches');
}
export async function fetchMatchAiCommentary(matchId) {
    return request(`/matches/${encodeURIComponent(matchId)}/ai-commentary`);
}
export async function generateAICommentary(payload) {
    return request('/ai/commentary', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}
export async function getPlayerAIInsights(playerId) {
    return request(`/api/players/${encodeURIComponent(playerId)}/ai-insights`);
}
/* ----------------------------- API surface ------------------------------- */
export const apiService = {
    /* Games */
    createGame: (body) => request('/games', { method: 'POST', body: JSON.stringify(body) }),
    getGame: (gameId) => request(`/games/${encodeURIComponent(gameId)}`),
    getSnapshot: (gameId) => request(`/games/${encodeURIComponent(gameId)}/snapshot`),
    // ?? ADDED: fetch persisted result for a completed game; returns null on 404
    async getResults(gameId) {
        try {
            return await request(`/games/${encodeURIComponent(gameId)}/results`);
        }
        catch (e) {
            if (e?.status === 404)
                return null;
            return null;
        }
    },
    searchGames: (team_a, team_b) => {
        const qp = new URLSearchParams();
        if (team_a)
            qp.set('team_a', team_a);
        if (team_b)
            qp.set('team_b', team_b);
        const qs = qp.toString();
        return request(`/games/search${qs ? `?${qs}` : ''}`);
    },
    /* Fan Mode */
    createFanMatch: (body) => request('/api/fan/matches', { method: 'POST', body: JSON.stringify(body) }),
    listFanMatches: (limit = 20, offset = 0) => request(`/api/fan/matches?limit=${limit}&offset=${offset}`),
    getFanMatch: (matchId) => request(`/api/fan/matches/${encodeURIComponent(matchId)}`),
    /* Fan Favorites */
    getFanFavorites: () => request('/api/fan/favorites'),
    createFanFavorite: (payload) => request('/api/fan/favorites', {
        method: 'POST',
        body: JSON.stringify(payload),
    }),
    deleteFanFavorite: (favoriteId) => request(`/api/fan/favorites/${encodeURIComponent(favoriteId)}`, {
        method: 'DELETE',
    }),
    /* Scoring */
    scoreDelivery: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/deliveries`, {
        method: 'POST',
        body: JSON.stringify(body),
    }),
    correctDelivery: (gameId, deliveryId, body) => request(`/games/${encodeURIComponent(gameId)}/deliveries/${deliveryId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
    }),
    undoLast: (gameId) => request(`/games/${encodeURIComponent(gameId)}/undo-last`, {
        method: 'POST',
    }),
    /* Match limits / rain */
    setOversLimit: (gameId, body) => {
        const payload = typeof body === 'number' ? { overs_limit: body } : body;
        return request(`/games/${encodeURIComponent(gameId)}/overs-limit`, { method: 'POST', body: JSON.stringify(payload) });
    },
    // 2) Add these two methods to the apiService object (near the other DLS/overs methods)
    dlsRevisedTarget: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/dls/revised-target`, { method: 'POST', body: JSON.stringify(body) }),
    dlsParNow: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/dls/par`, { method: 'POST', body: JSON.stringify(body) }),
    /* Team roles */
    setTeamRoles: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/team-roles`, { method: 'POST', body: JSON.stringify(body) }),
    /* ?? Over gates */
    // Start a new over (select bowler)  matches POST /games/{id}/overs/start
    startOver: (gameId, bowler_id) => request(`/games/${encodeURIComponent(gameId)}/overs/start`, { method: 'POST', body: JSON.stringify({ bowler_id }) }),
    // Mid-over change (injury/other)  matches POST /games/{id}/overs/change_bowler
    changeBowlerMidOver: (gameId, new_bowler_id, reason = 'injury') => request(`/games/${encodeURIComponent(gameId)}/overs/change_bowler`, {
        method: 'POST',
        body: JSON.stringify({ new_bowler_id, reason }),
    }),
    /* ?? Batter gates */
    // Replace the out batter before next ball  POST /games/{id}/batters/replace
    replaceBatter: (gameId, new_batter_id) => request(`/games/${encodeURIComponent(gameId)}/batters/replace`, {
        method: 'POST',
        body: JSON.stringify({ new_batter_id }),
    }),
    // Explicitly set next batter (optional QoL)  POST /games/{id}/next-batter
    setNextBatter: (gameId, batter_id) => request(`/games/${encodeURIComponent(gameId)}/next-batter`, { method: 'POST', body: JSON.stringify({ batter_id }) }),
    deliveries: (gameId, params) => {
        const qp = new URLSearchParams();
        if (params?.innings != null)
            qp.set('innings', String(params.innings));
        if (params?.limit != null)
            qp.set('limit', String(params.limit));
        if (params?.order)
            qp.set('order', params.order); // allow asc/desc order selection
        const qs = qp.toString();
        const path = `/games/${encodeURIComponent(gameId)}/deliveries${qs ? `?${qs}` : ''}`;
        return request(path);
    },
    recentDeliveries: (gameId, limit = 10) => request(`/games/${encodeURIComponent(gameId)}/recent_deliveries?limit=${encodeURIComponent(String(limit))}`),
    // Set openers (optional QoL)  POST /games/{id}/openers
    setOpeners: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/openers`, {
        method: 'POST',
        body: JSON.stringify(body),
    }),
    getInterruptions,
    openInterruption,
    stopInterruption,
    /* Contributors */
    addContributor: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/contributors`, {
        method: 'POST',
        body: JSON.stringify(body),
    }),
    listContributors: (gameId) => request(`/games/${encodeURIComponent(gameId)}/contributors`),
    removeContributor: (gameId, contribId) => request(`/games/${encodeURIComponent(gameId)}/contributors/${contribId}`, {
        method: 'DELETE',
    }),
    /* Sponsors */
    uploadSponsor: (body) => {
        const form = new FormData();
        form.append('name', body.name);
        form.append('logo', body.logo);
        if (body.click_url != null)
            form.append('click_url', body.click_url);
        if (body.weight != null)
            form.append('weight', String(body.weight));
        if (body.surfaces)
            form.append('surfaces', JSON.stringify(body.surfaces));
        if (body.start_at)
            form.append('start_at', body.start_at);
        if (body.end_at)
            form.append('end_at', body.end_at);
        return request('/sponsors', { method: 'POST', body: form });
    },
    /** List all sponsors (active + inactive) */
    getSponsors: () => request('/sponsors'),
    /** Get a single sponsor by ID */
    getSponsor: (sponsorId) => request(`/sponsors/${encodeURIComponent(sponsorId)}`),
    /** Update an existing sponsor (partial update) */
    updateSponsor: (sponsorId, body) => request(`/sponsors/${encodeURIComponent(sponsorId)}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
    }),
    /** Delete a sponsor */
    deleteSponsor: (sponsorId) => request(`/sponsors/${encodeURIComponent(sponsorId)}`, {
        method: 'DELETE',
    }),
    getGameSponsors: (gameId) => request(`/games/${encodeURIComponent(gameId)}/sponsors`),
    logSponsorImpressions: (payload) => request('/sponsor_impressions', {
        method: 'POST',
        body: JSON.stringify(payload),
    }),
    /* Health */
    healthz: () => request('/healthz'),
    /* Admin - Beta User Management */
    createBetaUser: (payload) => request('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify(payload),
    }),
    listBetaUsers: () => request('/api/admin/users'),
    resetUserPassword: (userId, password) => request(`/api/admin/users/${encodeURIComponent(userId)}/reset-password`, {
        method: 'POST',
        body: JSON.stringify(password ? { password } : {}),
    }),
    deactivateUser: (userId) => request(`/api/admin/users/${encodeURIComponent(userId)}/deactivate`, {
        method: 'POST',
    }),
    reactivateUser: (userId) => request(`/api/admin/users/${encodeURIComponent(userId)}/reactivate`, {
        method: 'POST',
    }),
    /* Optional placeholder (backend route not present yet) */
    // This will 404 until you add a backend route; the store calls it only if you wire a UI button.
    startNextInnings: (gameId, body) => request(`/games/${encodeURIComponent(gameId)}/innings/start`, {
        method: 'POST',
        body: JSON.stringify(body),
    }),
    /* Tournament Management */
    // Tournaments
    createTournament: (body) => request('/tournaments/', { method: 'POST', body: JSON.stringify(body) }),
    getTournaments: (skip = 0, limit = 100) => request(`/tournaments/?skip=${skip}&limit=${limit}`),
    getTournament: (tournamentId) => request(`/tournaments/${encodeURIComponent(tournamentId)}`),
    updateTournament: (tournamentId, body) => request(`/tournaments/${encodeURIComponent(tournamentId)}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
    }),
    deleteTournament: (tournamentId) => request(`/tournaments/${encodeURIComponent(tournamentId)}`, {
        method: 'DELETE',
    }),
    // Teams
    addTeamToTournament: (tournamentId, body) => request(`/tournaments/${encodeURIComponent(tournamentId)}/teams`, {
        method: 'POST',
        body: JSON.stringify(body),
    }),
    getTournamentTeams: (tournamentId) => request(`/tournaments/${encodeURIComponent(tournamentId)}/teams`),
    getPointsTable: (tournamentId) => request(`/tournaments/${encodeURIComponent(tournamentId)}/points-table`),
    // Fixtures
    createFixture: (body) => request('/tournaments/fixtures', { method: 'POST', body: JSON.stringify(body) }),
    getFixture: (fixtureId) => request(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`),
    getTournamentFixtures: (tournamentId) => request(`/tournaments/${encodeURIComponent(tournamentId)}/fixtures`),
    updateFixture: (fixtureId, body) => request(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
    }),
    deleteFixture: (fixtureId) => request(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`, {
        method: 'DELETE',
    }),
};
export default apiService;
