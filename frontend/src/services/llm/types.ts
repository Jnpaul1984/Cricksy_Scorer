/**
 * LLM Abstraction Layer Types
 *
 * Shared types for the resilient LLM client with provider fallback support.
 */

/**
 * Supported LLM providers.
 * Note: Claude support will be added in a future update.
 */
export type LLMProvider = "gemini";

/**
 * Request payload for LLM calls.
 */
export interface LLMRequest {
  /** System-level instructions for the model */
  systemPrompt?: string;

  /** User message / main prompt content */
  userPrompt: string;

  /** Model identifier (provider-specific, optional override) */
  model?: string;

  /** Sampling temperature (0-1, lower = more deterministic) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;
}

/**
 * Response from an LLM call.
 */
export interface LLMResponse {
  /** Generated text output */
  output: string;

  /** Total tokens used (prompt + completion) */
  tokensUsed: number;

  /** Which provider fulfilled this request */
  provider: LLMProvider;
}

/**
 * Error thrown when all LLM providers fail.
 */
export class LLMError extends Error {
  public readonly provider: LLMProvider | "all";
  public readonly statusCode?: number;
  public readonly originalError?: Error;

  constructor(
    message: string,
    provider: LLMProvider | "all",
    statusCode?: number,
    originalError?: Error
  ) {
    super(message);
    this.name = "LLMError";
    this.provider = provider;
    this.statusCode = statusCode;
    this.originalError = originalError;
  }
}

/**
 * Configuration for LLM providers.
 */
export interface LLMConfig {
  /** Gemini API key */
  geminiApiKey?: string;

  /** Anthropic API key */
  anthropicApiKey?: string;

  /** Default temperature for all calls */
  defaultTemperature?: number;

  /** Default max tokens for all calls */
  defaultMaxTokens?: number;

  /** Timeout in milliseconds */
  timeoutMs?: number;
}
