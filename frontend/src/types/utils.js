/**
 * Utility Type Definitions for Cricksy Scorer
 *
 * These types provide helper interfaces for common patterns like API responses,
 * error handling, validation, and other utility functions throughout the application.
 */
// ============================================================================
// DEBUGGING AND LOGGING UTILITIES
// ============================================================================
/**
 * Log levels
 */
export var LogLevel;
(function (LogLevel) {
    LogLevel["DEBUG"] = "debug";
    LogLevel["INFO"] = "info";
    LogLevel["WARN"] = "warn";
    LogLevel["ERROR"] = "error";
})(LogLevel || (LogLevel = {}));
