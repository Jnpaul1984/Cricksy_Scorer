// frontend/src/composables/useHighlights.ts
import { ref, computed, type Ref } from "vue";

export type EventType = "FOUR" | "SIX" | "WICKET" | "DUCK" | "FIFTY" | "HUNDRED";

export type Batter = {
  id?: string;
  name?: string;
  runs?: number;
  balls?: number;
  out?: boolean;
};

export type Snapshot = {
  total?: { runs?: number; wickets?: number };
  striker?: Batter;
  nonStriker?: Batter;
  // If your scoring pipeline emits this, we prefer it over deltas
  lastBall?: {
    runs?: number;
    isBoundary4?: boolean;
    isBoundary6?: boolean;
    isWicket?: boolean;
    dismissedBatterId?: string;
  };
};

function safe(n: number | undefined | null, d = 0) {
  return typeof n === "number" ? n : d;
}

function crossed(prevVal: number, nextVal: number, mark: number) {
  return prevVal < mark && nextVal >= mark;
}

function detectMilestones(prevB: Batter | undefined, nextB: Batter | undefined): EventType[] {
  if (!nextB) return [];
  const pRuns = safe(prevB?.runs);
  const nRuns = safe(nextB?.runs);
  const outNow = !!nextB?.out;

  // Only fire milestones for *current* innings of a batter (ignore after-out changes)
  if (outNow) return [];

  const events: EventType[] = [];
  if (crossed(pRuns, nRuns, 100)) {
    events.push("HUNDRED");
  } else if (crossed(pRuns, nRuns, 50)) {
    events.push("FIFTY");
  }
  return events;
}

export function diffToEvents(prevSnap: Snapshot | null | undefined, nextSnap: Snapshot | null | undefined): EventType[] {
  if (!prevSnap || !nextSnap) return [];

  const events: EventType[] = [];

  const pRuns = safe(prevSnap.total?.runs);
  const nRuns = safe(nextSnap.total?.runs);
  const pWkts = safe(prevSnap.total?.wickets);
  const nWkts = safe(nextSnap.total?.wickets);

  // Prefer explicit lastBall flags if present
  const lb = nextSnap.lastBall;
  if (lb) {
    if (lb.isBoundary4) events.push("FOUR");
    if (lb.isBoundary6) events.push("SIX");
    if (lb.isWicket) {
      // If the wicket was a duck, show DUCK instead of WICKET
      const dismissedId = lb.dismissedBatterId;
      const prevStriker = prevSnap.striker;
      const prevNonStriker = prevSnap.nonStriker;

      const dismissedWasDuck =
        (dismissedId && ((prevStriker?.id === dismissedId && safe(prevStriker?.runs) === 0) ||
                         (prevNonStriker?.id === dismissedId && safe(prevNonStriker?.runs) === 0)))
        ||
        (!dismissedId && ( // fall back to “someone got out and had 0” if no id
          (prevStriker && prevStriker.out !== true && safe(prevStriker?.runs) === 0) ||
          (prevNonStriker && prevNonStriker.out !== true && safe(prevNonStriker?.runs) === 0)
        ));

      events.push(dismissedWasDuck ? "DUCK" : "WICKET");
    }
  } else {
    // Use deltas if lastBall not available
    const deltaRuns = nRuns - pRuns;
    if (deltaRuns === 4) events.push("FOUR");
    if (deltaRuns === 6) events.push("SIX");
    if (nWkts > pWkts) {
      // Try to infer DUCK vs WICKET using batter runs difference
      const sDuck = prevSnap.striker && safe(prevSnap.striker.runs) === 0 && nextSnap.striker?.out === true;
      const nsDuck = prevSnap.nonStriker && safe(prevSnap.nonStriker.runs) === 0 && nextSnap.nonStriker?.out === true;
      events.push(sDuck || nsDuck ? "DUCK" : "WICKET");
    }
  }

  // Milestones for either batter (prioritize HUNDRED over FIFTY)
  const milestoneEvents: EventType[] = [
    ...detectMilestones(prevSnap.striker, nextSnap.striker),
    ...detectMilestones(prevSnap.nonStriker, nextSnap.nonStriker),
  ].sort((a, b) => (a === "HUNDRED" ? -1 : 0) - (b === "HUNDRED" ? -1 : 0));

  // Merge with dedupe while preserving order
  const seen = new Set<EventType>();
  const merged: EventType[] = [];
  [...events, ...milestoneEvents].forEach((e) => {
    if (!seen.has(e)) {
      seen.add(e);
      merged.push(e);
    }
  });

  return merged;
}

/**
 * useHighlights — queues and plays one animation at a time.
 *
 * @param enable Flag to enable/disable playback
 * @param durationMs Duration per animation (default 1800ms)
 */
export function useHighlights(enable: Ref<boolean>, durationMs: Ref<number>) {
  const queue = ref<EventType[]>([]);
  const current: Ref<EventType | null> = ref(null);
  const isPlaying = computed(() => current.value !== null);
  let timer: number | null = null;

  function clearTimer() {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function playNext() {
    if (!enable.value) return;
    if (current.value !== null) return;
    const next = queue.value.shift();
    if (!next) return;
    current.value = next;

    clearTimer();
    timer = window.setTimeout(() => {
      current.value = null;
      playNext();
    }, Math.max(600, durationMs.value || 1800));
  }

  function enqueue(events: EventType[]) {
    if (!events.length) return;
    queue.value.push(...events);
    if (!isPlaying.value && enable.value) playNext();
  }

  function enqueueFromSnapshots(prev: Snapshot | null | undefined, next: Snapshot | null | undefined) {
    if (!enable.value) return;
    const evs = diffToEvents(prev, next);
    enqueue(evs);
  }

  function reset() {
    clearTimer();
    queue.value = [];
    current.value = null;
  }

  return {
    queue,
    current,
    isPlaying,
    enqueue,
    enqueueFromSnapshots,
    reset,
  };
}
