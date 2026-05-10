import { ref } from 'vue';
import { useApi } from './useApi';
export const usePressureAnalytics = () => {
    const { get } = useApi();
    const pressureData = ref(null);
    const criticalMoments = ref([]);
    const phases = ref(null);
    const loading = ref(false);
    const error = ref(null);
    /**
     * Fetch pressure map for a specific game and inning
     */
    const fetchPressureMap = async (gameId, inningNum) => {
        loading.value = true;
        error.value = null;
        try {
            const url = inningNum
                ? `/analytics/games/${gameId}/pressure-map?inning_num=${inningNum}`
                : `/analytics/games/${gameId}/pressure-map`;
            const response = await get(url);
            if (response.success && response.data) {
                pressureData.value = response.data;
                phases.value = response.data.phases;
                criticalMoments.value = response.data.peak_moments || [];
                return response.data;
            }
            else {
                // Silently handle errors - feature may not be fully implemented
                error.value = null;
                return null;
            }
        }
        catch (err) {
            // Silently handle errors - analytics features may not be fully implemented
            error.value = null;
            return null;
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Fetch critical moments (high-pressure deliveries) for a game
     */
    const fetchCriticalMoments = async (gameId, threshold = 70, inningNum) => {
        loading.value = true;
        error.value = null;
        try {
            const params = new URLSearchParams();
            params.append('threshold', threshold.toString());
            if (inningNum)
                params.append('inning_num', inningNum.toString());
            const url = `/analytics/games/${gameId}/critical-moments?${params.toString()}`;
            const response = await get(url);
            if (response.success && response.data) {
                criticalMoments.value = response.data.critical_moments || [];
                return response.data.critical_moments || [];
            }
            else {
                error.value = response.error || 'Failed to fetch critical moments';
                return [];
            }
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'An error occurred';
            return [];
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Fetch pressure phases breakdown for a game
     */
    const fetchPressurePhases = async (gameId, inningNum) => {
        loading.value = true;
        error.value = null;
        try {
            const url = inningNum
                ? `/analytics/games/${gameId}/pressure-phases?inning_num=${inningNum}`
                : `/analytics/games/${gameId}/pressure-phases`;
            const response = await get(url);
            if (response.success && response.data) {
                phases.value = response.data;
                return response.data;
            }
            else {
                error.value = response.error || 'Failed to fetch pressure phases';
                return null;
            }
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'An error occurred';
            return null;
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Calculate pressure statistics from raw data
     */
    const calculatePressureStats = (pressurePoints) => {
        if (!pressurePoints.length) {
            return {
                averagePressure: 0,
                peakPressure: 0,
                minPressure: 0,
                highPressureCount: 0,
                extremePressureCount: 0
            };
        }
        const scores = pressurePoints.map(p => p.pressure_score);
        const averagePressure = scores.reduce((a, b) => a + b, 0) / scores.length;
        const peakPressure = Math.max(...scores);
        const minPressure = Math.min(...scores);
        const highPressureCount = scores.filter(s => s >= 60).length;
        const extremePressureCount = scores.filter(s => s >= 80).length;
        return {
            averagePressure,
            peakPressure,
            minPressure,
            highPressureCount,
            extremePressureCount
        };
    };
    /**
     * Get pressure level description
     */
    const getPressureLevel = (score) => {
        if (score < 20)
            return 'low';
        if (score < 40)
            return 'moderate';
        if (score < 60)
            return 'building';
        if (score < 80)
            return 'high';
        return 'extreme';
    };
    /**
     * Get pressure level with emoji
     */
    const getPressureLevelWithEmoji = (score) => {
        if (score < 20)
            return '🟢 Low';
        if (score < 40)
            return '🟡 Moderate';
        if (score < 60)
            return '🟠 Building';
        if (score < 80)
            return '🔴 High';
        return '🟣 Extreme';
    };
    /**
     * Refresh pressure data from server
     */
    const refresh = async (gameId, inningNum) => {
        await fetchPressureMap(gameId, inningNum);
    };
    /**
     * Clear cached data
     */
    const clear = () => {
        pressureData.value = null;
        criticalMoments.value = [];
        phases.value = null;
        error.value = null;
    };
    return {
        // State
        pressureData,
        criticalMoments,
        phases,
        loading,
        error,
        // Methods
        fetchPressureMap,
        fetchCriticalMoments,
        fetchPressurePhases,
        calculatePressureStats,
        getPressureLevel,
        getPressureLevelWithEmoji,
        refresh,
        clear
    };
};
