import { type Ref } from "vue";
export type EventType = "FOUR" | "SIX" | "WICKET" | "DUCK" | "FIFTY" | "HUNDRED";
export type Batter = {
    id?: string;
    name?: string;
    runs?: number;
    balls?: number;
    out?: boolean;
};
export type Snapshot = {
    total?: {
        runs?: number;
        wickets?: number;
    };
    striker?: Batter;
    nonStriker?: Batter;
    lastBall?: {
        runs?: number;
        isBoundary4?: boolean;
        isBoundary6?: boolean;
        isWicket?: boolean;
        dismissedBatterId?: string;
    };
};
export declare function diffToEvents(prevSnap: Snapshot | null | undefined, nextSnap: Snapshot | null | undefined): EventType[];
/**
 * useHighlights — queues and plays one animation at a time.
 *
 * @param enable Flag to enable/disable playback
 * @param durationMs Duration per animation (default 1800ms)
 */
export declare function useHighlights(enable: Ref<boolean>, durationMs: Ref<number>): {
    queue: any;
    current: Ref<EventType | null>;
    isPlaying: any;
    enqueue: (events: EventType[]) => void;
    enqueueFromSnapshots: (prev: Snapshot | null | undefined, next: Snapshot | null | undefined) => void;
    reset: () => void;
};
