export declare function useFollowSystem(): {
    follow: (id: string, type: "team" | "player" | "tournament", name: string) => void;
    unfollow: (id: string) => void;
    isFollowed: (id: string) => boolean;
    all: any;
    getByType: (type: "team" | "player" | "tournament") => any;
    recentlyFollowed: any;
};
