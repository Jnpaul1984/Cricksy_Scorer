import { ref, computed } from 'vue';
import { useApi } from './useApi';
export function usePlayerCareerAnalytics() {
    const apiService = useApi();
    const summary = ref(null);
    const yearlyStats = ref(null);
    const loading = ref(false);
    const error = ref(null);
    const specialization = computed(() => summary.value?.specialization || '');
    const totalMatches = computed(() => summary.value?.batting_stats.matches || 0);
    const totalRuns = computed(() => summary.value?.batting_stats.total_runs || 0);
    const careerAverage = computed(() => summary.value?.batting_stats.average || 0);
    /**
     * Fetch career summary for a player
     */
    async function fetchCareerSummary(playerId) {
        try {
            loading.value = true;
            error.value = null;
            const response = await apiService.get(`/analytics/players/players/${playerId}/career-summary`);
            if (response && response.data) {
                summary.value = response.data;
            }
        }
        catch (err) {
            error.value = err.message || 'Failed to fetch career summary';
            console.error('Failed to fetch career summary:', err);
            summary.value = null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch yearly statistics for a player
     */
    async function fetchYearlyStats(playerId) {
        try {
            const response = await apiService.get(`/analytics/players/players/${playerId}/year-stats`);
            if (response && response.data) {
                yearlyStats.value = response.data;
            }
        }
        catch (err) {
            console.warn('Failed to fetch yearly stats:', err);
            yearlyStats.value = null;
        }
    }
    /**
     * Fetch career summary with yearly breakdown
     */
    async function fetchFullProfile(playerId) {
        await Promise.all([
            fetchCareerSummary(playerId),
            fetchYearlyStats(playerId),
        ]);
    }
    /**
     * Compare two players
     */
    async function comparePlayers(playerId1, playerId2) {
        try {
            loading.value = true;
            error.value = null;
            const response = await apiService.get(`/analytics/players/players/${playerId1}/comparison?comparison_player_id=${playerId2}`);
            return response?.data || null;
        }
        catch (err) {
            error.value = err.message || 'Failed to compare players';
            console.error('Failed to compare players:', err);
            return null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Clear cached data
     */
    function clear() {
        summary.value = null;
        yearlyStats.value = null;
        error.value = null;
    }
    return {
        // State
        summary,
        yearlyStats,
        loading,
        error,
        // Computed
        specialization,
        totalMatches,
        totalRuns,
        careerAverage,
        // Methods
        fetchCareerSummary,
        fetchYearlyStats,
        fetchFullProfile,
        comparePlayers,
        clear,
    };
}
