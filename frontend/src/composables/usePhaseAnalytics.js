/**
 * usePhaseAnalytics Composable
 *
 * State management and API integration for match phase analysis.
 * Provides functions to fetch and manage phase data for interactive visualizations.
 */
import { ref, computed } from 'vue';
export function usePhaseAnalytics() {
    // State
    const phaseData = ref(null);
    const predictions = ref(null);
    const trends = ref(null);
    const loading = ref(false);
    const error = ref(null);
    // Computed
    const currentPhase = computed(() => phaseData.value?.current_phase || 'powerplay');
    const phaseIndex = computed(() => phaseData.value?.phase_index || 0);
    const isChasing = computed(() => (predictions.value?.match_prediction.win_probability ?? 0) > 0);
    /**
     * Fetch phase map for a game
     */
    async function fetchPhaseMap(gameId, inningNum) {
        try {
            loading.value = true;
            error.value = null;
            const params = new URLSearchParams();
            if (inningNum)
                params.append('inning_num', inningNum.toString());
            // Use VITE_API_BASE for absolute URL
            const apiBase = import.meta.env.VITE_API_BASE || '';
            const response = await fetch(`${apiBase}/analytics/games/${gameId}/phase-map?${params.toString()}`);
            if (!response.ok) {
                // Silently ignore - feature may not be implemented
                return;
            }
            phaseData.value = await response.json();
        }
        catch (err) {
            // Silently handle errors - analytics features may not be fully implemented
            error.value = null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch phase predictions for a game
     */
    async function fetchPredictions(gameId, inningNum) {
        try {
            loading.value = true;
            error.value = null;
            const params = new URLSearchParams();
            if (inningNum)
                params.append('inning_num', inningNum.toString());
            const response = await fetch(`/api/analytics/games/${gameId}/phase-predictions?${params.toString()}`);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            predictions.value = await response.json();
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to fetch predictions';
            console.error('Predictions error:', err);
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch phase trends for a game
     */
    async function fetchTrends(gameId, inningNum) {
        try {
            loading.value = true;
            error.value = null;
            const params = new URLSearchParams();
            if (inningNum)
                params.append('inning_num', inningNum.toString());
            const response = await fetch(`/api/analytics/games/${gameId}/phase-trends?${params.toString()}`);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            trends.value = await response.json();
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to fetch trends';
            console.error('Trends error:', err);
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch all phase data for a game
     */
    async function fetchAllPhaseData(gameId, inningNum) {
        loading.value = true;
        try {
            await Promise.all([
                fetchPhaseMap(gameId, inningNum),
                fetchPredictions(gameId, inningNum),
                fetchTrends(gameId, inningNum),
            ]);
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Get phase statistics by name
     */
    function getPhaseStats(phaseName) {
        return phaseData.value?.phases.find((p) => p.phase_name === phaseName);
    }
    /**
     * Get phase efficiency percentage
     */
    function getPhaseEfficiency(phaseName) {
        const phase = getPhaseStats(phaseName);
        return phase?.actual_vs_expected_pct || 0;
    }
    /**
     * Get phase performance rating
     */
    function getPhaseRating(phaseName) {
        const efficiency = getPhaseEfficiency(phaseName);
        if (efficiency >= 100)
            return 'excellent';
        if (efficiency >= 85)
            return 'good';
        if (efficiency >= 70)
            return 'average';
        return 'poor';
    }
    /**
     * Get acceleration phase name
     */
    function getAccelerationPhase() {
        if (!phaseData.value?.phases || phaseData.value.phases.length === 0)
            return 'N/A';
        let maxRR = -1;
        let maxPhase = '';
        for (const phase of phaseData.value.phases) {
            if (phase.run_rate > maxRR) {
                maxRR = phase.run_rate;
                maxPhase = phase.phase_name;
            }
        }
        return maxPhase;
    }
    /**
     * Clear all phase data
     */
    function clear() {
        phaseData.value = null;
        predictions.value = null;
        trends.value = null;
        error.value = null;
    }
    /**
     * Refresh phase data
     */
    async function refresh(gameId, inningNum) {
        clear();
        await fetchAllPhaseData(gameId, inningNum);
    }
    return {
        // State
        phaseData,
        predictions,
        trends,
        loading,
        error,
        // Computed
        currentPhase,
        phaseIndex,
        isChasing,
        // Methods
        fetchPhaseMap,
        fetchPredictions,
        fetchTrends,
        fetchAllPhaseData,
        getPhaseStats,
        getPhaseEfficiency,
        getPhaseRating,
        getAccelerationPhase,
        clear,
        refresh,
    };
}
