/**
 * Application-Specific Type Definitions for Cricksy Scorer
 *
 * These types are used throughout the Vue.js application for component props,
 * state management, routing, and UI interactions.
 */

import type { Player, BattingScorecardEntry, BowlingScorecardEntry } from '@/types';

// ============================================================================
// ENUMS FOR BETTER TYPE SAFETY
// ============================================================================

/**
 * Game status enum for better type safety and IDE autocomplete
 */
export enum GameStatus {
  IN_PROGRESS = 'in_progress',
  INNINGS_BREAK = 'innings_break',
  COMPLETED = 'completed'
}

/**
 * Loading states for async operations
 */
export enum LoadingState {
  IDLE = 'idle',
  LOADING = 'loading',
  SUCCESS = 'success',
  ERROR = 'error'
}

/**
 * Toss decision enum
 */
export enum TossDecision {
  BAT = 'bat',
  BOWL = 'bowl'
}

// ============================================================================
// UI STATE MANAGEMENT
// ============================================================================

/**
 * Global UI state interface for the application
 */
export interface UIState {
  /** Global loading state */
  loading: boolean;

  /** Global error message (null if no error) */
  error: string | null;

  /** Currently selected striker player ID */
  selectedStrikerId: string | null;

  /** Currently selected non-striker player ID */
  selectedNonStrikerId: string | null;

  /** Currently selected bowler player ID */
  selectedBowlerId: string | null;

  /** Whether the scoring controls are disabled */
  scoringDisabled: boolean;

  /** Current active tab in scorecard view */
  activeScorecardTab: 'batting' | 'bowling';
}

/**
 * Loading state for specific operations
 */
export interface OperationState {
  state: LoadingState;
  error: string | null;
}

// ============================================================================
// ROUTING AND NAVIGATION
// ============================================================================

/**
 * Route parameters interface for typed routing
 */
export interface RouteParams {
  gameId?: string;
}

/**
 * Navigation menu item
 */
export interface MenuItem {
  label: string;
  route: string;
  icon?: string;
  disabled?: boolean;
}

// ============================================================================
// COMPONENT PROP TYPES
// ============================================================================

/**
 * Props for the LiveScoreboard component
 */
export interface LiveScoreboardProps {
  teamName: string;
  totalRuns: number;
  totalWickets: number;
  oversCompleted: number;
  ballsThisOver: number;
  target?: number | null;
  currentInning: number;
}

/**
 * Props for scorecard display components
 */
export interface ScorecardProps {
  entries: Record<string, BattingScorecardEntry | BowlingScorecardEntry>;
  type: 'batting' | 'bowling';
  teamName: string;
  isLoading?: boolean;
}

/**
 * Props for the PlayerSelector component
 */
export interface PlayerSelectorProps {
  /** List of available players */
  players: Player[];

  /** Currently selected player ID */
  selectedPlayerId: string | null;

  /** Label for the selector */
  label: string;

  /** Whether the selector is disabled */
  disabled?: boolean;

  /** Whether selection is required */
  required?: boolean;

  /** Player IDs to exclude from selection */
  excludePlayerIds?: string[];

  /** Callback when selection changes */
  onSelectionChange: (playerId: string | null) => void;
}

/**
 * Props for scoring button components
 */
export interface ScoringButtonProps {
  /** The runs value for this button */
  runs: number;

  /** Whether the button is disabled */
  disabled?: boolean;

  /** Whether this is an extra (wide/no-ball) */
  isExtra?: boolean;

  /** Extra type if applicable */
  extraType?: 'wd' | 'nb';

  /** Whether this represents a wicket */
  isWicket?: boolean;

  /** Click handler */
  onClick: () => void;
}

/**
 * Props for game action buttons (start innings, etc.)
 */
export interface GameActionProps {
  /** The action type */
  action: 'start_second_innings' | 'export_game' | 'new_game';

  /** Whether the action is loading */
  loading?: boolean;

  /** Whether the action is disabled */
  disabled?: boolean;

  /** Click handler */
  onClick: () => void;
}

// ============================================================================
// FORM AND VALIDATION TYPES
// ============================================================================

/**
 * Form data for creating a new game
 */
export interface CreateGameFormData {
  team_a_name: string;
  team_b_name: string;
  players_a: string[];
  players_b: string[];
  toss_winner_team: string;
  decision: TossDecision;
}

/**
 * Validation result for forms
 */
export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string[]>;
}

/**
 * Form field validation rule
 */
export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: any) => string | null;
}

// ============================================================================
// STATISTICS AND CALCULATIONS
// ============================================================================

/**
 * Calculated statistics for a batsman
 */
export interface BattingStats {
  runs: number;
  ballsFaced: number;
  strikeRate: number;
  boundaries: number;
  sixes: number;
  isOut: boolean;
}

/**
 * Calculated statistics for a bowler
 */
export interface BowlingStats {
  oversBowled: number;
  runsConceded: number;
  wicketsTaken: number;
  economyRate: number;
  maidens: number;
}

/**
 * Partnership information
 */
export interface Partnership {
  striker: Player;
  nonStriker: Player;
  runs: number;
  balls: number;
  strikeRate: number;
}

/**
 * Over progression information
 */
export interface OverProgression {
  overNumber: number;
  bowler: Player;
  balls: Array<{
    runs: number;
    isExtra: boolean;
    isWicket: boolean;
    extraType?: string;
  }>;
  runsInOver: number;
  wicketsInOver: number;
}

// ============================================================================
// EXPORT AND DATA MANAGEMENT
// ============================================================================

/**
 * Export format options
 */
export enum ExportFormat {
  JSON = 'json',
  CSV = 'csv',
  PDF = 'pdf'
}

/**
 * Export configuration
 */
export interface ExportConfig {
  format: ExportFormat;
  includeDeliveries: boolean;
  includeScorecard: boolean;
  includeStatistics: boolean;
}

/**
 * File download information
 */
export interface DownloadInfo {
  filename: string;
  mimeType: string;
  size: number;
  url: string;
}

// ============================================================================
// NOTIFICATION AND FEEDBACK
// ============================================================================

/**
 * Notification types
 */
export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

/**
 * Notification message
 */
export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number;
  persistent?: boolean;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

/**
 * Generic callback function type
 */
export type Callback<T = void> = (data: T) => void;

/**
 * Generic async callback function type
 */
export type AsyncCallback<T = void> = (data: T) => Promise<void>;

/**
 * Optional properties utility type
 */
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/**
 * Deep partial utility type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Non-nullable utility type
 */
export type NonNullable<T> = T extends null | undefined ? never : T;
