/// <reference types="vite/client" />

/**
 * Vite Environment Variable Type Declarations
 *
 * Extends ImportMetaEnv to provide type safety for custom env variables.
 * All frontend environment variables must be prefixed with VITE_.
 */

interface ImportMetaEnv {
  // -----------------------------------------------------------------------------
  // API Configuration
  // -----------------------------------------------------------------------------

  /** Backend API base URL */
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_BASE?: string;

  /** Application title */
  readonly VITE_APP_TITLE?: string;

  /** Socket.IO URL */
  readonly VITE_SOCKET_URL?: string;

  /** Alternative API URL */
  readonly VITE_API_URL?: string;

  // -----------------------------------------------------------------------------
  // LLM Provider API Keys
  // -----------------------------------------------------------------------------

  /** Google Gemini API Key (Primary LLM provider) */
  readonly VITE_GEMINI_API_KEY?: string;

  /** Anthropic Claude API Key (Fallback LLM provider) */
  readonly VITE_ANTHROPIC_API_KEY?: string;

  // -----------------------------------------------------------------------------
  // Feature Flags
  // -----------------------------------------------------------------------------

  /** Enable AI features ("true" or "false") */
  readonly VITE_ENABLE_AI_FEATURES?: string;

  /** Enable LLM debug logging ("true" or "false") */
  readonly VITE_LLM_DEBUG?: string;

  // -----------------------------------------------------------------------------
  // Vite Built-in Variables
  // -----------------------------------------------------------------------------

  /** Current mode (development, production, etc.) */
  readonly MODE: string;

  /** Base URL for the app */
  readonly BASE_URL: string;

  /** Whether running in production */
  readonly PROD: boolean;

  /** Whether running in development */
  readonly DEV: boolean;

  /** Whether running in SSR mode */
  readonly SSR: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
