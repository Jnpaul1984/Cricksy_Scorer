/**
 * API service for the Phase 2A mental questionnaire endpoints.
 * All endpoints require coach_pro / coach_pro_plus / org_pro role or superuser.
 */
import { apiRequest } from '@/services/api';
/**
 * Fetch the active questionnaire template (all categories + questions).
 */
export async function getMentalQuestionnaireTemplate() {
    return apiRequest('/api/mental-questionnaires/template');
}
/**
 * Get the latest mental profile summary for a player.
 * Returns a 404-derived error when no responses exist yet.
 */
export async function getLatestMentalProfile(playerId) {
    return apiRequest(`/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/profile/latest`);
}
/**
 * Submit questionnaire answers for a player and receive the updated summary.
 */
export async function submitMentalQuestionnaire(playerId, answers) {
    return apiRequest(`/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/responses`, {
        method: 'POST',
        body: JSON.stringify({ answers }),
    });
}
/**
 * Get the full response history for a player (newest first).
 */
export async function getMentalResponseHistory(playerId) {
    return apiRequest(`/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/responses`);
}
