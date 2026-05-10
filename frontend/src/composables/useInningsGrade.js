import { ref, computed } from 'vue';
import { useApi } from './useApi';
export function useInningsGrade() {
    const apiService = useApi();
    const grade = ref(null);
    const loading = ref(false);
    const error = ref(null);
    const gradeColor = computed(() => {
        if (!grade.value)
            return '#9ca3af';
        const colors = {
            'A+': '#22c55e',
            'A': '#84cc16',
            'B': '#eab308',
            'C': '#f97316',
            'D': '#ef4444',
        };
        return colors[grade.value.grade] || '#9ca3af';
    });
    const gradeLabel = computed(() => {
        if (!grade.value)
            return 'No grade';
        const labels = {
            'A+': 'Exceptional',
            'A': 'Very Good',
            'B': 'Good',
            'C': 'Average',
            'D': 'Below Average',
        };
        return labels[grade.value.grade] || 'Unknown';
    });
    /**
     * Fetch current innings grade for a game
     */
    async function fetchCurrentGrade(gameId, inningNum) {
        try {
            loading.value = true;
            error.value = null;
            // Use provided inning number or default to 1
            const innings = inningNum || 1;
            const response = await apiService.get(`/analytics/games/${gameId}/innings/${innings}/grade`);
            if (response && response.data) {
                grade.value = response.data;
            }
        }
        catch (err) {
            // Don't treat 400/422/404 as errors - feature may not be implemented yet
            const status = err.response?.status || err.status;
            if (status && ![400, 404, 422, 500].includes(status)) {
                error.value = err.message || 'Failed to fetch innings grade';
                console.error('Failed to fetch innings grade:', err);
            }
            grade.value = null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Fetch grade for specific inning
     */
    async function fetchInningGrade(gameId, inningNum) {
        try {
            loading.value = true;
            error.value = null;
            const response = await apiService.get(`/analytics/games/${gameId}/innings/${inningNum}/grade`);
            if (response && response.data) {
                grade.value = response.data;
            }
        }
        catch (err) {
            error.value = err.message || 'Failed to fetch innings grade';
            console.error('Failed to fetch innings grade:', err);
            grade.value = null;
        }
        finally {
            loading.value = false;
        }
    }
    /**
     * Clear current grade data
     */
    function clear() {
        grade.value = null;
        error.value = null;
    }
    return {
        grade,
        loading,
        error,
        gradeColor,
        gradeLabel,
        fetchCurrentGrade,
        fetchInningGrade,
        clear,
    };
}
