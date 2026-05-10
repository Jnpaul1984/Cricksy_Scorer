import { ref, computed } from 'vue';
import { API_BASE } from '@/services/api';
/**
 * Build full API URL with base
 */
function buildApiUrl(path) {
    const basePath = `${API_BASE || ''}`;
    return `${basePath}${path}`.replace(/\/+/g, '/').replace('https:/', 'https://').replace('http:/', 'http://');
}
export const usePlayerImprovement = () => {
    const summaryData = ref(null);
    const monthlyStatsData = ref(null);
    const trendData = ref(null);
    const loading = ref(false);
    const error = ref(null);
    const currentPlayerId = ref('');
    const currentMonths = ref(6);
    /**
     * Fetch comprehensive improvement summary
     */
    const fetchImprovementSummary = async (playerId, months = 6) => {
        loading.value = true;
        error.value = null;
        currentPlayerId.value = playerId;
        currentMonths.value = months;
        try {
            const endpoint = buildApiUrl(`/api/player-analytics/players/${playerId}/improvement-summary?months=${months}`);
            const response = await fetch(endpoint);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Player not found');
                }
                throw new Error(`Failed to fetch improvement summary: ${response.statusText}`);
            }
            const data = await response.json();
            summaryData.value = data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'An error occurred';
            summaryData.value = null;
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Fetch monthly statistics breakdown
     */
    const fetchMonthlyStats = async (playerId, limit = 12) => {
        loading.value = true;
        error.value = null;
        try {
            const endpoint = buildApiUrl(`/api/player-analytics/players/${playerId}/monthly-stats?limit_months=${limit}`);
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error('Failed to fetch monthly statistics');
            }
            const data = await response.json();
            monthlyStatsData.value = data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'An error occurred';
            monthlyStatsData.value = null;
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Fetch month-to-month trends
     */
    const fetchTrends = async (playerId, months = 3) => {
        loading.value = true;
        error.value = null;
        try {
            const endpoint = buildApiUrl(`/api/player-analytics/players/${playerId}/improvement-trend?months=${months}`);
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error('Failed to fetch improvement trends');
            }
            const data = await response.json();
            trendData.value = data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'An error occurred';
            trendData.value = null;
        }
        finally {
            loading.value = false;
        }
    };
    /**
     * Get visual indicator for trend
     */
    const getTrendIndicator = (trend) => {
        const indicators = {
            improving: '📈',
            declining: '📉',
            stable: '➡️',
            accelerating: '🚀',
        };
        return indicators[trend] || '❓';
    };
    /**
     * Format trend value for display
     */
    const formatTrendValue = (value) => {
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    };
    /**
     * Refetch current data
     */
    const refetch = async () => {
        if (currentPlayerId.value) {
            await fetchImprovementSummary(currentPlayerId.value, currentMonths.value);
        }
    };
    /**
     * Computed properties for convenience
     */
    const hasData = computed(() => summaryData.value !== null);
    const overallTrend = computed(() => summaryData.value?.overall_trend || null);
    const improvementScore = computed(() => summaryData.value?.improvement_score ?? 0);
    const isImproving = computed(() => summaryData.value?.overall_trend === 'improving' ||
        summaryData.value?.overall_trend === 'accelerating');
    const latestStats = computed(() => summaryData.value?.latest_stats || null);
    const highlights = computed(() => summaryData.value?.highlights || []);
    return {
        summaryData,
        monthlyStatsData,
        trendData,
        loading,
        error,
        fetchImprovementSummary,
        fetchMonthlyStats,
        fetchTrends,
        getTrendIndicator,
        formatTrendValue,
        refetch,
    };
};
