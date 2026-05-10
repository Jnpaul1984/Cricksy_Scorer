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
export declare const useBallClustering: () => {
    isLoading: any;
    fetchBowlerClusters: (bowlerId: string) => Promise<BowlerClusterResponse | null>;
    fetchBatterVulnerabilities: (batterId: string) => Promise<BatterVulnerabilityResponse | null>;
    fetchMatchupClusterAnalysis: (bowlerId: string, batterId: string) => Promise<any | null>;
    fetchClusterTypes: () => Promise<any | null>;
};
export {};
