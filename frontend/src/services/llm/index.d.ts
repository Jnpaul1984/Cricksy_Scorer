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
export { callLLMWithFallback, callLLMDirect, checkLLMConfig, } from "./llmClient";
export { callGemini } from "./providers/callGemini";
export type { LLMProvider, LLMRequest, LLMResponse, LLMConfig, } from "./types";
export { LLMError } from "./types";
export { env, validateEnv, logEnvValidation, isAiAvailable, } from "../env";
