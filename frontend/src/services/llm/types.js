/**
 * LLM Abstraction Layer Types
 *
 * Shared types for the resilient LLM client with provider fallback support.
 */
/**
 * Error thrown when all LLM providers fail.
 */
export class LLMError extends Error {
    provider;
    statusCode;
    originalError;
    constructor(message, provider, statusCode, originalError) {
        super(message);
        this.name = "LLMError";
        this.provider = provider;
        this.statusCode = statusCode;
        this.originalError = originalError;
    }
}
