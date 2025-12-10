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

import { env } from "../env";

import { callGemini } from "./providers/callGemini";
import { LLMError } from "./types";
import type { LLMProvider, LLMRequest, LLMResponse } from "./types";

/**
 * Provider priority order for fallback.
 * Note: Currently Gemini only. Claude support coming later.
 */
const PROVIDER_ORDER: LLMProvider[] = ["gemini"];

/**
 * Map of provider names to their call functions.
 */
const PROVIDER_FUNCTIONS: Record<
  LLMProvider,
  (request: LLMRequest) => Promise<LLMResponse>
> = {
  gemini: callGemini,
  // claude: callClaude, // Coming later
};

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
export async function callLLMWithFallback(
  taskName: string,
  request: LLMRequest
): Promise<LLMResponse> {
  const errors: Array<{ provider: LLMProvider; error: Error }> = [];

  for (const provider of PROVIDER_ORDER) {
    try {
      console.debug(`[LLM] Attempting ${provider} for task: ${taskName}`);

      const callFn = PROVIDER_FUNCTIONS[provider];
      const response = await callFn(request);

      console.debug(
        `[LLM] ${provider} succeeded for task: ${taskName} (${response.tokensUsed} tokens)`
      );

      return response;
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      errors.push({ provider, error: err });

      console.warn(
        `[LLM] ${provider} failed for task: ${taskName}`,
        err.message
      );

      // Continue to next provider
    }
  }

  // All providers failed - throw aggregated error
  const errorMessages = errors
    .map((e) => `${e.provider}: ${e.error.message}`)
    .join("; ");

  throw new LLMError(
    `All LLM providers failed for task "${taskName}". Errors: ${errorMessages}`,
    "all"
  );
}

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
export async function callLLMDirect(
  provider: LLMProvider,
  request: LLMRequest
): Promise<LLMResponse> {
  const callFn = PROVIDER_FUNCTIONS[provider];

  if (!callFn) {
    throw new LLMError(`Unknown provider: ${provider}`, "all");
  }

  return callFn(request);
}

/**
 * Check if LLM providers are configured.
 *
 * @returns Object indicating which providers have API keys configured
 */
export function checkLLMConfig(): Record<LLMProvider, boolean> {
  const config = env();
  return {
    gemini: !!config.geminiApiKey,
  };
}

// Re-export types and individual providers for direct access
export type { LLMRequest, LLMResponse, LLMProvider } from "./types";
export { LLMError } from "./types";
export { callGemini } from "./providers/callGemini";
// export { callClaude } from "./providers/callClaude"; // Coming later
