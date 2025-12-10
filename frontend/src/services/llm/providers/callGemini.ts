/**
 * Google Gemini Provider
 *
 * Makes requests to Google's Gemini Pro API.
 * Used as the primary LLM provider.
 */

import { env } from "../../env";
import { LLMError } from "../types";
import type { LLMRequest, LLMResponse } from "../types";

/** Default Gemini model */
const DEFAULT_MODEL = "gemini-pro";

/** Gemini API base URL */
const GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

/**
 * Gemini API response structure.
 */
interface GeminiResponse {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string;
      }>;
    };
    finishReason?: string;
  }>;
  usageMetadata?: {
    promptTokenCount?: number;
    candidatesTokenCount?: number;
    totalTokenCount?: number;
  };
  error?: {
    code?: number;
    message?: string;
    status?: string;
  };
}

/**
 * Call Google Gemini API.
 *
 * @param request - The LLM request payload
 * @param apiKey - Gemini API key (defaults to env variable)
 * @param timeoutMs - Request timeout in milliseconds
 * @returns LLMResponse with output, tokens used, and provider
 * @throws LLMError if the request fails
 */
export async function callGemini(
  request: LLMRequest,
  apiKey?: string,
  timeoutMs: number = 30000
): Promise<LLMResponse> {
  const key = apiKey || env().geminiApiKey;

  if (!key) {
    throw new LLMError(
      "Gemini API key not configured",
      "gemini",
      401
    );
  }

  const model = request.model || DEFAULT_MODEL;
  const url = `${GEMINI_API_BASE}/${model}:generateContent?key=${key}`;

  // Build the request body
  // Gemini uses a different structure - combine system + user prompts
  const contents = [];

  // Add system prompt as first user message if provided
  if (request.systemPrompt) {
    contents.push({
      role: "user",
      parts: [{ text: request.systemPrompt }],
    });
    contents.push({
      role: "model",
      parts: [{ text: "Understood. I'll follow these instructions." }],
    });
  }

  // Add the main user prompt
  contents.push({
    role: "user",
    parts: [{ text: request.userPrompt }],
  });

  const body = {
    contents,
    generationConfig: {
      temperature: request.temperature ?? 0.7,
      maxOutputTokens: request.maxTokens ?? 2048,
      topP: 0.95,
      topK: 40,
    },
  };

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const data: GeminiResponse = await response.json();

    // Check for API error response
    if (data.error) {
      throw new LLMError(
        data.error.message || "Gemini API error",
        "gemini",
        data.error.code || response.status
      );
    }

    if (!response.ok) {
      throw new LLMError(
        `Gemini API returned status ${response.status}`,
        "gemini",
        response.status
      );
    }

    // Extract the generated text
    const output = data.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!output) {
      const finishReason = data.candidates?.[0]?.finishReason;
      throw new LLMError(
        `Gemini returned no output. Finish reason: ${finishReason || "unknown"}`,
        "gemini"
      );
    }

    // Calculate tokens used
    const tokensUsed =
      data.usageMetadata?.totalTokenCount ||
      (data.usageMetadata?.promptTokenCount || 0) +
        (data.usageMetadata?.candidatesTokenCount || 0);

    return {
      output,
      tokensUsed,
      provider: "gemini",
    };
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle abort/timeout
    if (error instanceof Error && error.name === "AbortError") {
      throw new LLMError(
        `Gemini request timed out after ${timeoutMs}ms`,
        "gemini",
        408
      );
    }

    // Re-throw LLMError as-is
    if (error instanceof LLMError) {
      throw error;
    }

    // Wrap other errors
    throw new LLMError(
      `Gemini request failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      "gemini",
      undefined,
      error instanceof Error ? error : undefined
    );
  }
}
