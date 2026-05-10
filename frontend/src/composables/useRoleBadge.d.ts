/**
 * Composable for captain/keeper role badge logic.
 * Shared across ScoreboardWidget, GameScoringView, and LiveScoreboard.
 */
import { type Ref, type ComputedRef } from 'vue';
export interface RoleBadgeOptions {
    /** Current game object (must have team_a_captain_id, team_a_keeper_id, etc.) */
    currentGame: Ref<any> | ComputedRef<any>;
    /** Whether team A is currently batting (pre-computed) */
    isBattingTeamA: Ref<boolean> | ComputedRef<boolean>;
}
export declare function useRoleBadge(options: RoleBadgeOptions): {
    isBattingTeamA: any;
    isCaptain: (playerId: string) => boolean;
    isKeeper: (playerId: string) => boolean;
    roleBadge: (playerId: string) => string;
    isBowlingCaptain: (playerId: string) => boolean;
    isBowlingKeeper: (playerId: string) => boolean;
    bowlerRoleBadge: (playerId: string) => string;
};
