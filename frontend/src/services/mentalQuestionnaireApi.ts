/**
 * API service for the Phase 2A mental questionnaire endpoints.
 * All endpoints require coach_pro / coach_pro_plus / org_pro role or superuser.
 */
import { apiRequest } from '@/services/api'
import type {
  MentalProfileSummary,
  MentalQuestionnaireTemplate,
  MentalQuestionnaireAnswerInput,
} from '@/types/mentalQuestionnaire'

/**
 * Fetch the active questionnaire template (all categories + questions).
 */
export async function getMentalQuestionnaireTemplate(): Promise<MentalQuestionnaireTemplate> {
  return apiRequest<MentalQuestionnaireTemplate>('/api/mental-questionnaires/template')
}

/**
 * Get the latest mental profile summary for a player.
 * Returns a 404-derived error when no responses exist yet.
 */
export async function getLatestMentalProfile(
  playerId: string,
): Promise<MentalProfileSummary> {
  return apiRequest<MentalProfileSummary>(
    `/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/profile/latest`,
  )
}

/**
 * Submit questionnaire answers for a player and receive the updated summary.
 */
export async function submitMentalQuestionnaire(
  playerId: string,
  answers: MentalQuestionnaireAnswerInput[],
): Promise<MentalProfileSummary> {
  return apiRequest<MentalProfileSummary>(
    `/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/responses`,
    {
      method: 'POST',
      body: JSON.stringify({ answers }),
    },
  )
}

/**
 * Get the full response history for a player (newest first).
 */
export async function getMentalResponseHistory(
  playerId: string,
): Promise<MentalProfileSummary[]> {
  return apiRequest<MentalProfileSummary[]>(
    `/api/mental-questionnaires/players/${encodeURIComponent(playerId)}/responses`,
  )
}
