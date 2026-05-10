/**
 * Environment Variable Utilities
 *
 * Provides type-safe access to environment variables with validation.
 * Uses Vite's import.meta.env for frontend environment variables.
 *
 * All frontend env vars must be prefixed with VITE_ to be exposed.
 */
/**
 * Environment variable configuration.
 */
export interface EnvConfig {
    geminiApiKey: string | undefined;
    anthropicApiKey: string | undefined;
    apiBaseUrl: string;
    enableAiFeatures: boolean;
    llmDebug: boolean;
    isDev: boolean;
    isProd: boolean;
    mode: string;
}
/**
 * Get the current environment configuration.
 *
 * Safely extracts environment variables with defaults.
 */
export declare function getEnvConfig(): EnvConfig;
/**
 * Get cached environment configuration.
 */
export declare function env(): EnvConfig;
/**
 * Get a required environment variable.
 *
 * @throws Error if the variable is not set
 */
export declare function requireEnv(key: string): string;
/**
 * Validation result for environment check.
 */
export interface EnvValidationResult {
    valid: boolean;
    missing: string[];
    warnings: string[];
}
/**
 * Validate that required environment variables are set.
 *
 * @param options - Validation options
 * @returns Validation result with missing/warning lists
 */
export declare function validateEnv(options?: {
    requireLLMKeys?: boolean;
}): EnvValidationResult;
/**
 * Log environment validation results to console.
 *
 * Call this at app startup to surface configuration issues.
 */
export declare function logEnvValidation(): void;
/**
 * Check if AI features are available.
 *
 * Returns true if AI is enabled AND at least one LLM key is configured.
 */
export declare function isAiAvailable(): boolean;
