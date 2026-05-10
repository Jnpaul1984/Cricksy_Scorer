/**
 * Application-Specific Type Definitions for Cricksy Scorer
 *
 * These types are used throughout the Vue.js application for component props,
 * state management, routing, and UI interactions.
 */
// ============================================================================
// ENUMS FOR BETTER TYPE SAFETY
// ============================================================================
/**
 * Game status enum for better type safety and IDE autocomplete
 */
export var GameStatus;
(function (GameStatus) {
    GameStatus["IN_PROGRESS"] = "in_progress";
    GameStatus["INNINGS_BREAK"] = "innings_break";
    GameStatus["COMPLETED"] = "completed";
})(GameStatus || (GameStatus = {}));
/**
 * Loading states for async operations
 */
export var LoadingState;
(function (LoadingState) {
    LoadingState["IDLE"] = "idle";
    LoadingState["LOADING"] = "loading";
    LoadingState["SUCCESS"] = "success";
    LoadingState["ERROR"] = "error";
})(LoadingState || (LoadingState = {}));
/**
 * Toss decision enum
 */
export var TossDecision;
(function (TossDecision) {
    TossDecision["BAT"] = "bat";
    TossDecision["BOWL"] = "bowl";
})(TossDecision || (TossDecision = {}));
// ============================================================================
// EXPORT AND DATA MANAGEMENT
// ============================================================================
/**
 * Export format options
 */
export var ExportFormat;
(function (ExportFormat) {
    ExportFormat["JSON"] = "json";
    ExportFormat["CSV"] = "csv";
    ExportFormat["PDF"] = "pdf";
})(ExportFormat || (ExportFormat = {}));
// ============================================================================
// NOTIFICATION AND FEEDBACK
// ============================================================================
/**
 * Notification types
 */
export var NotificationType;
(function (NotificationType) {
    NotificationType["SUCCESS"] = "success";
    NotificationType["ERROR"] = "error";
    NotificationType["WARNING"] = "warning";
    NotificationType["INFO"] = "info";
})(NotificationType || (NotificationType = {}));
