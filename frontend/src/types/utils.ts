/**
 * Utility Type Definitions for Cricksy Scorer
 * 
 * These types provide helper interfaces for common patterns like API responses,
 * error handling, validation, and other utility functions throughout the application.
 */

// ============================================================================
// API RESPONSE UTILITIES
// ============================================================================

/**
 * Generic API response wrapper that can contain any data type
 */
export interface ApiResponse<T> {
  /** The actual response data */
  data: T;
  
  /** Whether the request was successful */
  success: boolean;
  
  /** Optional message from the server */
  message?: string;
  
  /** HTTP status code */
  status?: number;
  
  /** Additional metadata */
  meta?: {
    timestamp: string;
    requestId?: string;
    version?: string;
  };
}

/**
 * API error response structure
 */
export interface ApiError {
  /** Human-readable error message */
  message: string;
  
  /** HTTP status code */
  status: number;
  
  /** Machine-readable error code */
  code?: string;
  
  /** Additional error details */
  details?: Record<string, any>;
  
  /** Field-specific validation errors */
  fieldErrors?: Record<string, string[]>;
  
  /** Stack trace (development only) */
  stack?: string;
}

/**
 * Paginated API response structure
 */
export interface PaginatedResponse<T> {
  /** Array of items for current page */
  items: T[];
  
  /** Total number of items across all pages */
  total: number;
  
  /** Current page number (1-based) */
  page: number;
  
  /** Number of items per page */
  perPage: number;
  
  /** Total number of pages */
  totalPages: number;
  
  /** Whether there is a next page */
  hasNext: boolean;
  
  /** Whether there is a previous page */
  hasPrev: boolean;
  
  /** URL for next page (if available) */
  nextUrl?: string;
  
  /** URL for previous page (if available) */
  prevUrl?: string;
}

// ============================================================================
// VALIDATION UTILITIES
// ============================================================================

/**
 * Result of a validation operation
 */
export interface ValidationResult {
  /** Whether the validation passed */
  isValid: boolean;
  
  /** Array of error messages */
  errors: string[];
  
  /** Field-specific errors */
  fieldErrors?: Record<string, string[]>;
  
  /** Warnings (non-blocking issues) */
  warnings?: string[];
}

/**
 * Individual validation rule
 */
export interface ValidationRule<T = any> {
  /** Rule name for identification */
  name: string;
  
  /** Validation function */
  validate: (value: T) => boolean | string;
  
  /** Error message if validation fails */
  message: string;
  
  /** Whether this rule is required */
  required?: boolean;
}

/**
 * Schema for validating objects
 */
export type ValidationSchema<T> = {
  [K in keyof T]?: ValidationRule<T[K]>[];
}

// ============================================================================
// ASYNC OPERATION UTILITIES
// ============================================================================

/**
 * State of an async operation
 */
export interface AsyncState<T = any, E = ApiError> {
  /** Current loading state */
  loading: boolean;
  
  /** The data (if successful) */
  data: T | null;
  
  /** The error (if failed) */
  error: E | null;
  
  /** Whether the operation has been attempted */
  initialized: boolean;
  
  /** Timestamp of last update */
  lastUpdated: Date | null;
}

/**
 * Options for async operations
 */
export interface AsyncOptions {
  /** Timeout in milliseconds */
  timeout?: number;
  
  /** Number of retry attempts */
  retries?: number;
  
  /** Delay between retries in milliseconds */
  retryDelay?: number;
  
  /** Whether to show loading indicators */
  showLoading?: boolean;
  
  /** Whether to show error notifications */
  showErrors?: boolean;
}

// ============================================================================
// CACHING UTILITIES
// ============================================================================

/**
 * Cache entry with metadata
 */
export interface CacheEntry<T> {
  /** The cached data */
  data: T;
  
  /** When the data was cached */
  timestamp: Date;
  
  /** When the data expires */
  expiresAt: Date;
  
  /** Cache key */
  key: string;
  
  /** Additional metadata */
  meta?: Record<string, any>;
}

/**
 * Cache configuration options
 */
export interface CacheOptions {
  /** Time to live in milliseconds */
  ttl: number;
  
  /** Maximum number of entries */
  maxSize?: number;
  
  /** Whether to use localStorage for persistence */
  persistent?: boolean;
  
  /** Key prefix for storage */
  keyPrefix?: string;
}

// ============================================================================
// EVENT HANDLING UTILITIES
// ============================================================================

/**
 * Generic event handler type
 */
export type EventHandler<T = any> = (event: T) => void;

/**
 * Async event handler type
 */
export type AsyncEventHandler<T = any> = (event: T) => Promise<void>;

/**
 * Event subscription
 */
export interface EventSubscription {
  /** Unique subscription ID */
  id: string;
  
  /** Event name */
  event: string;
  
  /** Handler function */
  handler: EventHandler;
  
  /** Whether the subscription is active */
  active: boolean;
  
  /** Unsubscribe function */
  unsubscribe: () => void;
}

// ============================================================================
// STORAGE UTILITIES
// ============================================================================

/**
 * Storage adapter interface
 */
export interface StorageAdapter {
  /** Get item from storage */
  getItem(key: string): string | null;
  
  /** Set item in storage */
  setItem(key: string, value: string): void;
  
  /** Remove item from storage */
  removeItem(key: string): void;
  
  /** Clear all items */
  clear(): void;
  
  /** Get all keys */
  keys(): string[];
}

/**
 * Serialized storage value with metadata
 */
export interface StorageValue<T> {
  /** The actual value */
  value: T;
  
  /** When it was stored */
  timestamp: Date;
  
  /** When it expires (optional) */
  expiresAt?: Date;
  
  /** Version for migration purposes */
  version?: number;
}

// ============================================================================
// FORMATTING AND DISPLAY UTILITIES
// ============================================================================

/**
 * Number formatting options
 */
export interface NumberFormatOptions {
  /** Number of decimal places */
  decimals?: number;
  
  /** Thousands separator */
  thousandsSeparator?: string;
  
  /** Decimal separator */
  decimalSeparator?: string;
  
  /** Currency symbol */
  currency?: string;
  
  /** Whether to show plus sign for positive numbers */
  showPlus?: boolean;
}

/**
 * Date formatting options
 */
export interface DateFormatOptions {
  /** Date format pattern */
  format?: string;
  
  /** Locale for formatting */
  locale?: string;
  
  /** Timezone */
  timezone?: string;
  
  /** Whether to show relative time (e.g., "2 hours ago") */
  relative?: boolean;
}

// ============================================================================
// DEBUGGING AND LOGGING UTILITIES
// ============================================================================

/**
 * Log levels
 */
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error'
}

/**
 * Log entry structure
 */
export interface LogEntry {
  /** Log level */
  level: LogLevel;
  
  /** Log message */
  message: string;
  
  /** Timestamp */
  timestamp: Date;
  
  /** Additional data */
  data?: any;
  
  /** Source location */
  source?: string;
  
  /** User ID (if available) */
  userId?: string;
  
  /** Session ID */
  sessionId?: string;
}

// ============================================================================
// PERFORMANCE UTILITIES
// ============================================================================

/**
 * Performance measurement
 */
export interface PerformanceMeasurement {
  /** Operation name */
  name: string;
  
  /** Start time */
  startTime: number;
  
  /** End time */
  endTime: number;
  
  /** Duration in milliseconds */
  duration: number;
  
  /** Additional metadata */
  meta?: Record<string, any>;
}

/**
 * Performance monitoring options
 */
export interface PerformanceOptions {
  /** Whether to enable monitoring */
  enabled: boolean;
  
  /** Sample rate (0-1) */
  sampleRate?: number;
  
  /** Maximum number of measurements to keep */
  maxMeasurements?: number;
  
  /** Whether to log to console */
  logToConsole?: boolean;
}

// ============================================================================
// GENERIC UTILITY TYPES
// ============================================================================

/**
 * Make specific properties optional
 */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/**
 * Make specific properties required
 */
export type RequiredBy<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Extract function parameters
 */
export type Parameters<T extends (...args: any) => any> = T extends (...args: infer P) => any ? P : never;

/**
 * Extract function return type
 */
export type ReturnType<T extends (...args: any) => any> = T extends (...args: any) => infer R ? R : any;

/**
 * Create a type with all properties set to a specific type
 */
export type Record<K extends keyof any, T> = {
  [P in K]: T;
};

/**
 * Exclude null and undefined from a type
 */
export type NonNullable<T> = T extends null | undefined ? never : T;

/**
 * Create a deep readonly version of a type
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * Create a deep partial version of a type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

