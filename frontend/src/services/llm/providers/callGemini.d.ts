/**
 * Google Gemini Provider
 *
 * Makes requests to Google's Gemini Pro API.
 * Used as the primary LLM provider.
 */
import type { LLMRequest, LLMResponse } from "../types";
/**
 * Call Google Gemini API.
 *
 * @param request - The LLM request payload
 * @param apiKey - Gemini API key (defaults to env variable)
 * @param timeoutMs - Request timeout in milliseconds
 * @returns LLMResponse with output, tokens used, and provider
 * @throws LLMError if the request fails
 */
export declare function callGemini(request: LLMRequest, apiKey?: string, timeoutMs?: number): Promise<LLMResponse>;
