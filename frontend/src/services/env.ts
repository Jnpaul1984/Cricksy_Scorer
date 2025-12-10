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
  // LLM Provider Keys
  geminiApiKey: string | undefined;
  anthropicApiKey: string | undefined;

  // Backend
  apiBaseUrl: string;

  // Feature Flags
  enableAiFeatures: boolean;
  llmDebug: boolean;

  // Runtime
  isDev: boolean;
  isProd: boolean;
  mode: string;
}

/**
 * Get the current environment configuration.
 *
 * Safely extracts environment variables with defaults.
 */
export function getEnvConfig(): EnvConfig {
  return {
    // LLM Keys (may be undefined - handled by LLM client)
    geminiApiKey: import.meta.env.VITE_GEMINI_API_KEY || undefined,
    anthropicApiKey: import.meta.env.VITE_ANTHROPIC_API_KEY || undefined,

    // Backend
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",

    // Feature Flags
    enableAiFeatures: import.meta.env.VITE_ENABLE_AI_FEATURES !== "false",
    llmDebug: import.meta.env.VITE_LLM_DEBUG === "true",

    // Runtime
    isDev: import.meta.env.DEV,
    isProd: import.meta.env.PROD,
    mode: import.meta.env.MODE,
  };
}

/**
 * Cached environment config (computed once).
 */
let _envConfig: EnvConfig | null = null;

/**
 * Get cached environment configuration.
 */
export function env(): EnvConfig {
  if (!_envConfig) {
    _envConfig = getEnvConfig();
  }
  return _envConfig;
}

/**
 * Get a required environment variable.
 *
 * @throws Error if the variable is not set
 */
export function requireEnv(key: string): string {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${key}. ` +
        `Please add it to your .env.local file.`
    );
  }
  return value;
}

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
export function validateEnv(options?: {
  requireLLMKeys?: boolean;
}): EnvValidationResult {
  const missing: string[] = [];
  const warnings: string[] = [];

  const config = getEnvConfig();

  // Check LLM keys if AI features are enabled
  if (config.enableAiFeatures || options?.requireLLMKeys) {
    if (!config.geminiApiKey) {
      warnings.push(
        "VITE_GEMINI_API_KEY not set - Gemini provider will be unavailable"
      );
    }
    if (!config.anthropicApiKey) {
      warnings.push(
        "VITE_ANTHROPIC_API_KEY not set - Claude fallback will be unavailable"
      );
    }

    // If both are missing and AI is required, that's an error
    if (!config.geminiApiKey && !config.anthropicApiKey) {
      if (options?.requireLLMKeys) {
        missing.push("At least one LLM API key (VITE_GEMINI_API_KEY or VITE_ANTHROPIC_API_KEY)");
      }
    }
  }

  return {
    valid: missing.length === 0,
    missing,
    warnings,
  };
}

/**
 * Log environment validation results to console.
 *
 * Call this at app startup to surface configuration issues.
 */
export function logEnvValidation(): void {
  const result = validateEnv();
  const config = env();

  if (config.isDev) {
    console.log("[Env] Mode:", config.mode);
    console.log("[Env] API Base:", config.apiBaseUrl);
    console.log("[Env] AI Features:", config.enableAiFeatures ? "enabled" : "disabled");
    console.log("[Env] Gemini Key:", config.geminiApiKey ? "configured" : "not set");
    console.log("[Env] Anthropic Key:", config.anthropicApiKey ? "configured" : "not set");
  }

  if (result.warnings.length > 0) {
    result.warnings.forEach((w) => console.warn("[Env Warning]", w));
  }

  if (!result.valid) {
    result.missing.forEach((m) => console.error("[Env Error] Missing:", m));
  }
}

/**
 * Check if AI features are available.
 *
 * Returns true if AI is enabled AND at least one LLM key is configured.
 */
export function isAiAvailable(): boolean {
  const config = env();
  return (
    config.enableAiFeatures &&
    !!(config.geminiApiKey || config.anthropicApiKey)
  );
}
