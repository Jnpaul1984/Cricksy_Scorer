/**
 * LLM Service
 *
 * Resilient LLM abstraction layer with provider fallback.
 *
 * Primary provider: Gemini Pro
 * Fallback provider: Claude Haiku
 *
 * @example
 * ```ts
 * import { callLLMWithFallback } from "@/services/llm";
 *
 * const response = await callLLMWithFallback("task-name", {
 *   systemPrompt: "You are a helpful assistant.",
 *   userPrompt: "What is 2 + 2?",
 * });
 *
 * console.log(response.output); // "4"
 * console.log(response.provider); // "gemini" or "claude"
 * ```
 */
// Main client
export { callLLMWithFallback, callLLMDirect, checkLLMConfig, } from "./llmClient";
// Individual providers (for direct access if needed)
export { callGemini } from "./providers/callGemini";
export { LLMError } from "./types";
// Environment utilities (re-exported for convenience)
export { env, validateEnv, logEnvValidation, isAiAvailable, } from "../env";
