/**
 * Composable for captain/keeper role badge logic.
 * Shared across ScoreboardWidget, GameScoringView, and LiveScoreboard.
 */
import { type Ref, type ComputedRef } from 'vue'

export interface RoleBadgeOptions {
  /** Current game object (must have team_a_captain_id, team_a_keeper_id, etc.) */
  currentGame: Ref<any> | ComputedRef<any>
  /** Whether team A is currently batting (pre-computed) */
  isBattingTeamA: Ref<boolean> | ComputedRef<boolean>
}

export function useRoleBadge(options: RoleBadgeOptions) {
  const { currentGame, isBattingTeamA } = options

  function isCaptain(playerId: string): boolean {
    const g = currentGame.value
    if (!g || !playerId) return false
    const capId = isBattingTeamA.value ? g.team_a_captain_id : g.team_b_captain_id
    return String(capId ?? '') === playerId
  }

  function isKeeper(playerId: string): boolean {
    const g = currentGame.value
    if (!g || !playerId) return false
    const keeperId = isBattingTeamA.value ? g.team_a_keeper_id : g.team_b_keeper_id
    return String(keeperId ?? '') === playerId
  }

  function roleBadge(playerId: string): string {
    const cap = isCaptain(playerId)
    const wk = isKeeper(playerId)
    if (cap && wk) return ' (C †)'
    if (cap) return ' (C)'
    if (wk) return ' †'
    return ''
  }

  /**
   * Check captain/keeper for the bowling team (opposite of batting team).
   */
  function isBowlingCaptain(playerId: string): boolean {
    const g = currentGame.value
    if (!g || !playerId) return false
    const capId = isBattingTeamA.value ? g.team_b_captain_id : g.team_a_captain_id
    return String(capId ?? '') === playerId
  }

  function isBowlingKeeper(playerId: string): boolean {
    const g = currentGame.value
    if (!g || !playerId) return false
    const keeperId = isBattingTeamA.value ? g.team_b_keeper_id : g.team_a_keeper_id
    return String(keeperId ?? '') === playerId
  }

  function bowlerRoleBadge(playerId: string): string {
    const cap = isBowlingCaptain(playerId)
    const wk = isBowlingKeeper(playerId)
    if (cap && wk) return ' (C †)'
    if (cap) return ' (C)'
    if (wk) return ' †'
    return ''
  }

  return {
    isBattingTeamA,
    isCaptain,
    isKeeper,
    roleBadge,
    isBowlingCaptain,
    isBowlingKeeper,
    bowlerRoleBadge,
  }
}
