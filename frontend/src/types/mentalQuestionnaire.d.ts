/**
 * TypeScript types for the Phase 2A mental questionnaire API.
 * Matches backend schemas in backend/sql_app/schemas.py.
 */
export interface MentalQuestionnaireCategoryScore {
    category: string;
    average_score: number;
}
export interface MentalProfileSummary {
    session_id: string;
    player_id: string;
    submitted_by_user_id: string;
    overall_average_score: number;
    overall_summary: string;
    strengths: string[];
    development_areas: string[];
    category_scores: MentalQuestionnaireCategoryScore[];
    created_at: string;
}
export interface MentalQuestionnaireQuestion {
    id: number;
    category: string;
    question_text: string;
    display_order: number;
}
export interface MentalQuestionnaireCategoryTemplate {
    category: string;
    questions: MentalQuestionnaireQuestion[];
}
export interface MentalQuestionnaireTemplate {
    categories: MentalQuestionnaireCategoryTemplate[];
}
export interface MentalQuestionnaireAnswerInput {
    question_id: number;
    score: number;
}
