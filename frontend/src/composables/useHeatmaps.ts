import { ref } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

interface HeatmapPoint {
  zone: string;
  x_coordinate: number;
  y_coordinate: number;
  value: number;
  count: number;
  detail: string;
}

interface HeatmapResponse {
  status: string;
  player_id?: string;
  player_name?: string;
  bowler_id?: string;
  bowler_name?: string;
  heatmap?: {
    heatmap_id: string;
    heatmap_type: string;
    data_points: HeatmapPoint[];
    average_value: number;
    total_events: number;
    metadata: Record<string, any>;
  };
  message?: string;
}

interface MatchupResponse {
  status: string;
  matchup?: {
    batter_id: string;
    batter_name: string;
    bowler_id: string;
    bowler_name: string;
    total_deliveries: number;
    dangerous_areas: string[];
    weak_overlap_areas: string[];
    dismissal_zones: string[];
    recommendation: string;
  };
}

export const useHeatmaps = () => {
  const isLoading = ref(false);

  const fetchScoresHeatmap = async (playerId: string): Promise<HeatmapResponse | null> => {
    if (!playerId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/heatmaps/players/${playerId}/batting-heatmap`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching scoring heatmap:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchDismissalHeatmap = async (playerId: string): Promise<HeatmapResponse | null> => {
    if (!playerId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/heatmaps/players/${playerId}/dismissal-heatmap`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching dismissal heatmap:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchReleaseZones = async (bowlerId: string): Promise<HeatmapResponse | null> => {
    if (!bowlerId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/heatmaps/bowlers/${bowlerId}/release-zones`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching release zones:", error);
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMatchup = async (
    batterId: string,
    bowlerId: string
  ): Promise<MatchupResponse | null> => {
    if (!batterId || !bowlerId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/heatmaps/matchups/${batterId}/vs/${bowlerId}`
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

  const fetchGameHeatmapSummary = async (
    gameId: string,
    teamSide: "a" | "b"
  ): Promise<any | null> => {
    if (!gameId) return null;

    try {
      isLoading.value = true;
      const response = await fetch(
        `${API_BASE}/heatmaps/games/${gameId}/team-${teamSide}/heatmap-summary`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error("Error fetching game heatmap summary:", error);
      return null;
    } finally {
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
