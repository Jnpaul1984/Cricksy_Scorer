import { ref } from "vue";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const useBallClustering = () => {
    const isLoading = ref(false);
    const fetchBowlerClusters = async (bowlerId) => {
        if (!bowlerId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/ball-clustering/bowlers/${bowlerId}/delivery-clusters`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching bowler clusters:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchBatterVulnerabilities = async (batterId) => {
        if (!batterId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/ball-clustering/batters/${batterId}/delivery-vulnerabilities`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching batter vulnerabilities:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    const fetchMatchupClusterAnalysis = async (bowlerId, batterId) => {
        if (!bowlerId || !batterId)
            return null;
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/ball-clustering/matchups/${bowlerId}/vs/${batterId}/cluster-analysis`);
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
    const fetchClusterTypes = async () => {
        try {
            isLoading.value = true;
            const response = await fetch(`${API_BASE}/ball-clustering/cluster-types`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            return await response.json();
        }
        catch (error) {
            console.error("Error fetching cluster types:", error);
            return null;
        }
        finally {
            isLoading.value = false;
        }
    };
    return {
        isLoading,
        fetchBowlerClusters,
        fetchBatterVulnerabilities,
        fetchMatchupClusterAnalysis,
        fetchClusterTypes,
    };
};
