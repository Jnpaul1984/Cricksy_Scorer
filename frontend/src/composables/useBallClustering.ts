import { ref } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

interface ClusterData {
  cluster_id: string;
  delivery_type: string;
  cluster_name: string;
  description: string;
  sample_count: number;
  effectiveness_percentage: number;
  success_rate: number;
  average_runs_conceded: number;
}

interface BowlerProfile {
  total_deliveries: number;
  delivery_clusters: ClusterData[];
  primary_clusters: string[];
  variation_score: number;
  clustering_accuracy: number;
  most_effective_cluster: string;
  least_effective_cluster: string;
}

interface BowlerClusterResponse {
  status: string;
  profile: BowlerProfile | null;
}

interface BatterVulnerability {
  vulnerable_clusters: string[];
  vulnerable_delivery_types: Record<string, number>;
  strong_against: string[];
  dismissal_delivery_types: string[];
  recommended_bowling_strategy: string;
}

interface BatterVulnerabilityResponse {
  status: string;
  vulnerability: BatterVulnerability | null;
}

export const useBallClustering = () => {
  const isLoading = ref(false);

  const fetchBowlerClusters = async (bowlerId: string): Promise<BowlerClusterResponse | null> => {
    if (!bowlerId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/ball-clustering/bowlers/${bowlerId}/delivery-clusters`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching bowler clusters:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchBatterVulnerabilities = async (
    batterId: string
  ): Promise<BatterVulnerabilityResponse | null> => {
    if (!batterId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/ball-clustering/batters/${batterId}/delivery-vulnerabilities`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching batter vulnerabilities:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMatchupClusterAnalysis = async (
    bowlerId: string,
    batterId: string
  ): Promise<any | null> => {
    if (!bowlerId || !batterId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/ball-clustering/matchups/${bowlerId}/vs/${batterId}/cluster-analysis`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching matchup analysis:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchClusterTypes = async (): Promise<any | null> => {
    try {
      isLoading.value = true;
      const response = await fetch(`${API_BASE}/ball-clustering/cluster-types`);

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching cluster types:", error);
      return null;
    } finally {
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
