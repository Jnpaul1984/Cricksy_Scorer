# backend/dls.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Iterable, Literal, Mapping, Optional
import csv
import os
import json
import math

# ------------------------------
# Resource tables (externalized)
# ------------------------------
# We load â€œresources remaining (%)â€ as a function of (overs_remaining, wickets_lost).
# Files must be rectangular CSVs with header: overs_remaining, w0, w1, ..., w9
# Example rows (overs_remaining descending to 0):
# overs_remaining,w0,w1,w2,...,w9
# 50,100.0,96.7,93.5,...,45.0
# ...
# 0,0,0,0,...,0

@dataclass
class ResourceTable:
    # resources[overs_remaining][wickets_lost] -> percentage 0..100
    resources: List[List[float]]  # index by overs_remaining (int), 0..M
    max_overs: int

    @classmethod
    def from_csv(cls, path: str) -> "ResourceTable":
        if not os.path.exists(path):
            raise FileNotFoundError(f"DLS resource CSV not found: {path}")
        rows: List[List[float]] = []
        with open(path, "r", newline="") as f:
            r = csv.DictReader(f)
            # Expect overs_remaining + w0..w9
            tmp: Dict[int, List[float]] = {}
            max_over = 0
            for rec in r:
                o = int(float(rec["overs_remaining"]))
                max_over = max(max_over, o)
                cols: List[float] = []
                for w in range(10):
                    cols.append(float(rec.get(f"w{w}", 0.0)))
                tmp[o] = cols
            # Normalize to contiguous 0..max_over
            rows = [tmp.get(o, [0.0]*10) for o in range(max_over + 1)]
        return cls(resources=rows, max_overs=len(rows)-1)

    def R(self, overs_remaining: float, wickets_lost: int) -> float:
        """
        Return resources remaining (%) for a given (overs_remaining, wickets_lost).
        Linearâ€‘interpolate on fractional overs; clamp wickets 0..9 and overs 0..max.
        """
        w = max(0, min(9, wickets_lost))
        if overs_remaining <= 0:
            return 0.0
        if overs_remaining >= self.max_overs:
            return self.resources[self.max_overs][w]
        # Interpolate between floor and ceil
        lo = int(overs_remaining)
        hi = min(self.max_overs, lo + 1)
        frac = overs_remaining - lo
        Rlo = self.resources[lo][w]
        Rhi = self.resources[hi][w]
        return (1 - frac) * Rlo + frac * Rhi


@dataclass
class DLSEnv:
    table: ResourceTable
    # G is the â€œaverage 50-over scoreâ€ constant used in DLS (ICC uses ~245 for ODI).
    # For T20, you may prefer ~150. We make it configurable but rarely needed except for special cases.
    G: float = 245.0


# ------------------------------
# Ledger helpers
# ------------------------------
@dataclass
class InningsState:
    # Balls bowled so far, wickets fallen so far
    balls_bowled: int
    wickets_lost: int


def balls_from_overs(overs: int, balls: int) -> int:
    return overs * 6 + balls


def overs_balls_from_balls(total_balls: int) -> Tuple[int, int]:
    return divmod(max(0, total_balls), 6)


def wickets_from_ledger(deliveries: Iterable[Mapping[str, Any]]) -> int:
    w = 0
    for d in deliveries:
        if bool(d.get("is_wicket")):
            w += 1
    return w


def compute_state_from_ledger(deliveries: List[Mapping[str, Any]]) -> InningsState:
    # Legal deliveries increment balls; wides/noâ€‘balls do not (per your scoring rules)
    balls = 0
    wkts = 0
    for d in deliveries:
        extra = (d.get("extra_type") or d.get("extra") or "").lower()
        legal = extra not in ("wd", "wide", "nb", "no_ball")
        if legal:
            balls += 1
        if d.get("is_wicket"):
            wkts += 1
    return InningsState(balls_bowled=balls, wickets_lost=wkts)


# ------------------------------
# Interruptions model
# ------------------------------
# Weâ€™ll rely on a simple history of oversâ€‘limit changes captured at the moment they were applied.
# Each record: { "at_delivery_index": int, "new_overs_limit": int }
Interruption = Dict[str, Any]


def total_resources_team1(
    *,
    env: DLSEnv,
    max_overs_initial: int,
    deliveries: List[Mapping[str, Any]],
    interruptions: List[Interruption],
) -> float:
    """
    Compute Team 1 total resources (%) considering oversâ€‘limit reductions at specific
    moments (with wickets at those moments).
    Implements the â€œresources lostâ€ sum: sum( R(u_before,w) - R(u_after,w) )
    """
    # Sort by when they occurred
    ints = sorted(
        [i for i in interruptions if "at_delivery_index" in i and "new_overs_limit" in i],
        key=lambda i: int(i["at_delivery_index"])
    )

    # Starting resources for Team 1: R(M, 0)
    R_total = env.table.R(max_overs_initial, 0)
    balls_so_far = 0
    wkts_so_far = 0
    limit_now = max_overs_initial

    for it in ints:
        idx = int(it["at_delivery_index"])
        new_limit = int(it["new_overs_limit"])
        # recompute wickets at interruption using the prefix of deliveries
        prefix = deliveries[:idx]
        st = compute_state_from_ledger(prefix)
        balls_so_far = st.balls_bowled
        wkts_so_far = st.wickets_lost

        # Overs remaining just before interruption:
        overs_bowled_float = balls_so_far / 6.0
        u_before = max(0.0, limit_now - overs_bowled_float)
        u_after = max(0.0, new_limit - overs_bowled_float)

        lost = env.table.R(u_before, wkts_so_far) - env.table.R(u_after, wkts_so_far)
        R_total -= max(0.0, lost)
        limit_now = new_limit

    # Clamp to [0, 100]
    return max(0.0, min(100.0, R_total))


def total_resources_team2(
    *,
    env: DLSEnv,
    max_overs_current: int,
    delivered_balls_so_far: int,
    wickets_lost_so_far: int,
) -> float:
    """Resources available to Team 2 from the start or â€œremaining right nowâ€ while chasing."""
    overs_bowled_float = delivered_balls_so_far / 6.0
    u = max(0.0, max_overs_current - overs_bowled_float)
    return env.table.R(u, wickets_lost_so_far)


def revised_target(
    *,
    S1: int,              # Team 1 runs
    R1_total: float,      # Team 1 total resources used (%)
    R2_total: float,      # Team 2 total resources available (%)
) -> int:
    # Standard DLS revised target: floor(S1 * (R2/R1)) + 1
    if R1_total <= 0.0:
        return S1 + 1  # safety; shouldn't happen
    import math
    return int(math.floor(S1 * (R2_total / R1_total)) + 1)


def par_score_now(
    *,
    S1: int,
    R1_total: float,
    R2_used_so_far: float,
) -> int:
    # Par while chasing after some balls: floor(S1 * (R2_used / R1)) + 1
    if R1_total <= 0.0:
        return 0
    import math
    return int(math.floor(S1 * (R2_used_so_far / R1_total)) + 1)


# Convenience to load T20/ODI tables
def load_env(kind: Literal["odi", "t20"], base_dir: str) -> DLSEnv:
    # Put your CSVs in backend/static/dls/{odi.csv,t20.csv}
    path = os.path.join(base_dir, "static", "dls", f"{kind}.csv")
    table = ResourceTable.from_csv(path)
    # Choose G constant (rarely used in simple R2/R1 scenarios, but kept configurable)
    G = 245.0 if kind == "odi" else 150.0
    return DLSEnv(table=table, G=G)


# ---------------------------------------------------------------------------
# Lightweight public helper used by tests / CLI tooling
# ---------------------------------------------------------------------------
class DLSMissingTable(FileNotFoundError):
    """Raised when no DLS lookup table is available for the requested format."""


@dataclass
class DLSComputation:
    target: int
    par_score: int
    R1_total: float
    R2_total: float
    R2_used: float


def _load_json_table(path: Path, format_overs: int) -> ResourceTable:
    """Build a ResourceTable from a legacy JSON placeholder file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    max_wickets = 10  # DLS tables define wickets lost 0..9 (10th wicket ends innings)
    resources: List[List[float]] = []

    for overs_left in range(format_overs + 1):
        overs_bowled = float(format_overs - overs_left)
        row: List[float] = []
        for w in range(max_wickets):
            w_key = str(w)
            series: Optional[Dict[str, Any]] = payload.get(w_key)
            if not series:
                # Fallback to simple proportional model when data missing
                remaining = max(0.0, (overs_left / max(1, format_overs)) * 100.0)
                row.append(remaining)
                continue

            start_raw = float(series.get("0", 100.0))
            end_raw = float(series.get(str(format_overs), 0.0))
            denom = start_raw - end_raw if start_raw != end_raw else 1.0

            ob_floor = int(math.floor(overs_bowled))
            ob_ceil = int(math.ceil(overs_bowled))
            ob_floor = max(0, min(format_overs, ob_floor))
            ob_ceil = max(0, min(format_overs, ob_ceil))

            raw_floor = float(series.get(str(ob_floor), end_raw))
            raw_ceil = float(series.get(str(ob_ceil), end_raw))

            if ob_floor == ob_ceil:
                raw = raw_floor
            else:
                frac = overs_bowled - ob_floor
                raw = raw_floor + (raw_ceil - raw_floor) * frac

            remaining = (raw - end_raw) / (denom or 1.0) * 100.0
            remaining = max(0.0, min(100.0, remaining))
            row.append(remaining)
        resources.append(row)

    return ResourceTable(resources=resources, max_overs=format_overs)


def _resource_table_for_format(format_overs: int) -> ResourceTable:
    base_dir = Path(__file__).resolve().parent

    # Priority: CSV in static/dls/<format>.csv (matches load_env expectations)
    csv_path = base_dir / "static" / "dls" / f"{format_overs}.csv"
    if csv_path.exists():
        return ResourceTable.from_csv(str(csv_path))

    # Fallback: legacy JSON placeholder static/dls_<overs>.json
    json_path = base_dir / "static" / f"dls_{format_overs}.json"
    if json_path.exists():
        return _load_json_table(json_path, format_overs=format_overs)

    raise DLSMissingTable(f"No DLS table found for {format_overs}-over format")


def compute_dls_target(
    *,
    team1_score: int,
    team1_wickets_lost: int,
    team1_overs_left_at_end: float,
    format_overs: int,
    team2_wkts_lost_now: int,
    team2_overs_left_now: float,
) -> DLSComputation:
    """
    Best-effort DLS calculation using locally bundled tables.

    This helper favours correctness when CSV tables are present, but gracefully
    degrades to a simplified JSON placeholder so automated tests and offline
    tooling have deterministic behaviour.
    """
    table = _resource_table_for_format(format_overs)
    env = DLSEnv(table=table, G=150.0 if format_overs <= 20 else 245.0)

    wickets1 = max(0, min(9, int(team1_wickets_lost)))
    wickets2 = max(0, min(9, int(team2_wkts_lost_now)))

    overs_left_team1 = max(0.0, min(float(format_overs), float(team1_overs_left_at_end)))
    overs_left_team2 = max(0.0, min(float(format_overs), float(team2_overs_left_now)))

    R_start = env.table.R(format_overs, 0)
    R1_remaining = env.table.R(overs_left_team1, wickets1)
    R1_total = max(0.0, R_start - R1_remaining)
    if R1_total <= 0.0:
        R1_total = max(R_start, 1.0)

    R2_remaining = env.table.R(overs_left_team2, wickets2)
    R2_total = max(0.0, R2_remaining)
    R2_used = max(0.0, R_start - R2_remaining)

    target = revised_target(S1=team1_score, R1_total=R1_total, R2_total=R2_total)
    par = par_score_now(S1=team1_score, R1_total=R1_total, R2_used_so_far=R2_used)

    return DLSComputation(
        target=max(1, target),
        par_score=max(0, par),
        R1_total=R1_total,
        R2_total=R2_total,
        R2_used=R2_used,
    )



