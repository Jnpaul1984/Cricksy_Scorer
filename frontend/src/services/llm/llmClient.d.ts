/**
 * LLM Client with Resilient Fallback
 *
 * Provides a clean interface for calling LLMs with automatic fallback.
 * Primary: Gemini Pro
 * Fallback: Claude Haiku
 *
 * Usage:
 * ```ts
 * const response = await callLLMWithFallback("generate-commentary", {
 *   systemPrompt: "You are a cricket commentator.",
 *   userPrompt: "Describe this delivery: 4 runs, cover drive.",
 * });
 * console.log(response.output); // Generated commentary
 * console.log(response.provider); // "gemini" or "claude"
 * ```
 */
import type { LLMProvider, LLMRequest, LLMResponse } from "./types";
/**
 * Call LLM with automatic fallback.
 *
 * Tries Gemini first, falls back to Claude if Gemini fails.
 * Re-throws if all providers fail.
 *
 * @param taskName - Name of the task (for logging/debugging)
 * @param request - The LLM request payload
 * @returns LLMResponse with output, tokens used, and which provider succeeded
 * @throws LLMError if all providers fail
 *
 * @example
 * ```ts
 * const response = await callLLMWithFallback("match-summary", {
 *   systemPrompt: "Summarize cricket matches concisely.",
 *   userPrompt: "Lions 185/6 beat Falcons 160/8 in T20.",
 *   temperature: 0.5,
 * });
 * ```
 */
export declare function callLLMWithFallback(taskName: string, request: LLMRequest): Promise<LLMResponse>;
/**
 * Call a specific LLM provider directly (no fallback).
 *
 * Use this when you need a specific provider's capabilities.
 *
 * @param provider - Which provider to use
 * @param request - The LLM request payload
 * @returns LLMResponse
 * @throws LLMError if the provider fails
 */
export declare function callLLMDirect(provider: LLMProvider, request: LLMRequest): Promise<LLMResponse>;
/**
 * Check if LLM providers are configured.
 *
 * @returns Object indicating which providers have API keys configured
 */
export declare function checkLLMConfig(): Record<LLMProvider, boolean>;
export type { LLMRequest, LLMResponse, LLMProvider } from "./types";
export { LLMError } from "./types";
export { callGemini } from "./providers/callGemini";
