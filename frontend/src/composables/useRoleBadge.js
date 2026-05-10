export function useRoleBadge(options) {
    const { currentGame, isBattingTeamA } = options;
    function isCaptain(playerId) {
        const g = currentGame.value;
        if (!g || !playerId)
            return false;
        const capId = isBattingTeamA.value ? g.team_a_captain_id : g.team_b_captain_id;
        return String(capId ?? '') === playerId;
    }
    function isKeeper(playerId) {
        const g = currentGame.value;
        if (!g || !playerId)
            return false;
        const keeperId = isBattingTeamA.value ? g.team_a_keeper_id : g.team_b_keeper_id;
        return String(keeperId ?? '') === playerId;
    }
    function roleBadge(playerId) {
        const cap = isCaptain(playerId);
        const wk = isKeeper(playerId);
        if (cap && wk)
            return ' (C †)';
        if (cap)
            return ' (C)';
        if (wk)
            return ' †';
        return '';
    }
    /**
     * Check captain/keeper for the bowling team (opposite of batting team).
     */
    function isBowlingCaptain(playerId) {
        const g = currentGame.value;
        if (!g || !playerId)
            return false;
        const capId = isBattingTeamA.value ? g.team_b_captain_id : g.team_a_captain_id;
        return String(capId ?? '') === playerId;
    }
    function isBowlingKeeper(playerId) {
        const g = currentGame.value;
        if (!g || !playerId)
            return false;
        const keeperId = isBattingTeamA.value ? g.team_b_keeper_id : g.team_a_keeper_id;
        return String(keeperId ?? '') === playerId;
    }
    function bowlerRoleBadge(playerId) {
        const cap = isBowlingCaptain(playerId);
        const wk = isBowlingKeeper(playerId);
        if (cap && wk)
            return ' (C †)';
        if (cap)
            return ' (C)';
        if (wk)
            return ' †';
        return '';
    }
    return {
        isBattingTeamA,
        isCaptain,
        isKeeper,
        roleBadge,
        isBowlingCaptain,
        isBowlingKeeper,
        bowlerRoleBadge,
    };
}
