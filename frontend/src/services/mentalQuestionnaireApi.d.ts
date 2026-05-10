import type { MentalProfileSummary, MentalQuestionnaireTemplate, MentalQuestionnaireAnswerInput } from '@/types/mentalQuestionnaire';
/**
 * Fetch the active questionnaire template (all categories + questions).
 */
export declare function getMentalQuestionnaireTemplate(): Promise<MentalQuestionnaireTemplate>;
/**
 * Get the latest mental profile summary for a player.
 * Returns a 404-derived error when no responses exist yet.
 */
export declare function getLatestMentalProfile(playerId: string): Promise<MentalProfileSummary>;
/**
 * Submit questionnaire answers for a player and receive the updated summary.
 */
export declare function submitMentalQuestionnaire(playerId: string, answers: MentalQuestionnaireAnswerInput[]): Promise<MentalProfileSummary>;
/**
 * Get the full response history for a player (newest first).
 */
export declare function getMentalResponseHistory(playerId: string): Promise<MentalProfileSummary[]>;
