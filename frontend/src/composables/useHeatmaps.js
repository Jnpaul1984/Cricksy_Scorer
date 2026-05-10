import { ref } from "vue";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const useHeatmaps = () => {
    const isLoading = ref(false);
    const fetchScoresHeatmap = async (playerId) => {
        if (!playerId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/heatmaps/players/${playerId}/batting-heatmap`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching scoring heatmap:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchDismissalHeatmap = async (playerId) => {
        if (!playerId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/heatmaps/players/${playerId}/dismissal-heatmap`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching dismissal heatmap:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchReleaseZones = async (bowlerId) => {
        if (!bowlerId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/heatmaps/bowlers/${bowlerId}/release-zones`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching release zones:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchMatchup = async (batterId, bowlerId) => {
        if (!batterId || !bowlerId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/heatmaps/matchups/${batterId}/vs/${bowlerId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching matchup analysis:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchGameHeatmapSummary = async (gameId, teamSide) => {
        if (!gameId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/heatmaps/games/${gameId}/team-${teamSide}/heatmap-summary`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching game heatmap summary:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    return {
        isLoading,
        fetchScoresHeatmap,
        fetchDismissalHeatmap,
        fetchReleaseZones,
        fetchMatchup,
        fetchGameHeatmapSummary,
    };
};
