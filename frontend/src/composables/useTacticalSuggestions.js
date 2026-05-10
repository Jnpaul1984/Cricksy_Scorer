import { ref } from 'vue';
import { API_BASE } from '@/services/api';
export const useTacticalSuggestions = () => {
    const suggestions = ref(null);
    const loading = ref(false);
    const error = ref(null);
    /**
     * Fetch all tactical suggestions for a game
     */
    async function fetchSuggestions(gameId) {
        loading.value = true;
        error.value = null;
        try {
            const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/all`;
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            // Normalize response structure
            const normalized = {
                game_id: data.game_id || gameId,
                timestamp: data.timestamp,
            };
            // Handle both nested and flat response structures
            if (data.suggestions) {
                // Nested structure from /all endpoint
                normalized.best_bowler = data.suggestions.best_bowler;
                normalized.weakness = data.suggestions.weakness_analysis;
                normalized.fielding = data.suggestions.fielding_setup;
            }
            else {
                // Flat structure from individual endpoints
                normalized.best_bowler = data.best_bowler || data.recommendation;
                normalized.weakness = data.weakness_analysis || data.weakness;
                normalized.fielding = data.fielding_setup || data.fielding;
            }
            suggestions.value = normalized;
        }
        catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to fetch suggestions';
            error.value = errorMsg;
            suggestions.value = null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch best bowler recommendation only
     */
    async function fetchBestBowler(gameId) {
        loading.value = true;
        error.value = null;
        try {
            const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/best-bowler`;
            const response = await fetch(apiUrl);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!suggestions.value) {
                suggestions.value = {
                    game_id: gameId,
                };
            }
            suggestions.value.best_bowler = data.recommendation || data.best_bowler;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to fetch bowler suggestion';
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch weakness analysis only
     */
    async function fetchWeaknessAnalysis(gameId) {
        loading.value = true;
        error.value = null;
        try {
            const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/weakness-analysis`;
            const response = await fetch(apiUrl);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!suggestions.value) {
                suggestions.value = {
                    game_id: gameId,
                };
            }
            suggestions.value.weakness = data.weakness_analysis || data.weakness;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to fetch weakness analysis';
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch fielding setup recommendation only
     */
    async function fetchFieldingSetup(gameId) {
        loading.value = true;
        error.value = null;
        try {
            const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/fielding-setup`;
            const response = await fetch(apiUrl);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!suggestions.value) {
                suggestions.value = {
                    game_id: gameId,
                };
            }
            suggestions.value.fielding = data.fielding_setup || data.fielding;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to fetch fielding setup';
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Clear all suggestions and errors
     */
    function clearSuggestions() {
        suggestions.value = null;
        error.value = null;
    }
    return {
        suggestions,
        loading,
        error,
        fetchSuggestions,
        fetchBestBowler,
        fetchWeaknessAnalysis,
        fetchFieldingSetup,
        clearSuggestions,
    };
};
