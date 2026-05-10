import { ref } from 'vue';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export function useDismissalPatterns() {
    const loading = ref(false);
    const error = ref(null);
    /**
     * Fetch comprehensive dismissal pattern analysis for a player
     */
    async function fetchPlayerAnalysis(playerId) {
        loading.value = true;
        error.value = null;
        try {
            const response = await fetch(`${API_BASE}/dismissal-patterns/players/${playerId}/analysis`);
            if (!response.ok) {
                throw new Error(`Failed to fetch analysis: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Unknown error occurred';
            console.error('Error fetching player analysis:', err);
            return null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch team-level dismissal pattern analysis
     */
    async function fetchTeamAnalysis(gameId, teamSide) {
        loading.value = true;
        error.value = null;
        try {
            const response = await fetch(`${API_BASE}/dismissal-patterns/games/${gameId}/team-${teamSide}/analysis`);
            if (!response.ok) {
                throw new Error(`Failed to fetch team analysis: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Unknown error occurred';
            console.error('Error fetching team analysis:', err);
            return null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Get quick vulnerability score for a player
     */
    async function fetchVulnerabilityScore(playerId) {
        loading.value = true;
        error.value = null;
        try {
            const response = await fetch(`${API_BASE}/dismissal-patterns/players/${playerId}/vulnerability-score`);
            if (!response.ok) {
                throw new Error(`Failed to fetch vulnerability score: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Unknown error occurred';
            console.error('Error fetching vulnerability score:', err);
            return null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Get dismissal trend for a player
     */
    async function fetchDismissalTrend(playerId, period = 'last_10') {
        loading.value = true;
        error.value = null;
        try {
            const response = await fetch(`${API_BASE}/dismissal-patterns/players/${playerId}/trend?period=${period}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch trend: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Unknown error occurred';
            console.error('Error fetching dismissal trend:', err);
            return null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Get risk color for severity/risk level
     */
    function getRiskColor(riskLevel) {
        const colorMap = {
            critical: '#e53e3e',
            high: '#ed8936',
            medium: '#ecc94b',
            low: '#48bb78',
        };
        return colorMap[riskLevel.toLowerCase()] || '#cbd5e0';
    }
    /**
     * Format dismissal type for display
     */
    function formatDismissalType(dismissalType) {
        return dismissalType
            .split('_')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    /**
     * Get severity icon
     */
    function getSeverityIcon(severity) {
        const iconMap = {
            high: '🔴',
            medium: '🟠',
            low: '🟢',
        };
        return iconMap[severity.toLowerCase()] || '⚪';
    }
    /**
     * Get risk level text
     */
    function getRiskLevelText(score) {
        if (score >= 70)
            return 'CRITICAL';
        if (score >= 50)
            return 'HIGH';
        if (score >= 30)
            return 'MEDIUM';
        return 'LOW';
    }
    return {
        loading,
        error,
        fetchPlayerAnalysis,
        fetchTeamAnalysis,
        fetchVulnerabilityScore,
        fetchDismissalTrend,
        getRiskColor,
        formatDismissalType,
        getSeverityIcon,
        getRiskLevelText,
    };
}
