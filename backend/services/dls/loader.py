from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Union, Mapping, Sequence


class DLSTable:
    """
    DLS resource table for a specific cricket format.
    Provides access to DLS resource percentages for calculating revised targets
    in interrupted cricket matches.
    """

    def __init__(
        self,
        format_overs: int,
        resources: Mapping[Union[int, str], Sequence[float]],
    ) -> None:
        """
        Args:
            format_overs: Number of overs per innings (e.g., 20, 50)
            resources: Mapping of wickets lost (0-9) to resource arrays.
                       Keys may be str (from JSON) or int; values may be any sequence of floats.
        """
        self.format_overs = format_overs
        self.max_balls = format_overs * 6

        # Explicitly type the storage so Pylance knows what's inside.
        self._resources: Dict[int, List[float]] = {}

        # Convert keys to int and values to List[float], with validation.
        for wickets_key, resource_seq in resources.items():
            wickets = int(wickets_key)
            if not (0 <= wickets <= 9):
                raise ValueError(f"Invalid wickets lost: {wickets}, must be 0-9")

            arr = [float(x) for x in resource_seq]
            if len(arr) != self.max_balls + 1:
                raise ValueError(
                    f"Invalid resource array length for {wickets} wickets: "
                    f"{len(arr)}, expected {self.max_balls + 1}"
                )

            self._resources[wickets] = arr

    def resource(self, balls_left: int, wickets_lost: int) -> float:
        """
        Get resource percentage remaining.
        """
        balls_left = max(0, min(balls_left, self.max_balls))
        wickets_lost = max(0, min(wickets_lost, 9))

        if wickets_lost not in self._resources:
            raise ValueError(f"No resource data for {wickets_lost} wickets lost")

        # Now that _resources is Dict[int, List[float]], this is a float.
        return self._resources[wickets_lost][balls_left]

    def get_all_resources(self, wickets_lost: int) -> List[float]:
        """
        Get complete resource array for a given number of wickets lost.
        """
        wickets_lost = max(0, min(wickets_lost, 9))

        if wickets_lost not in self._resources:
            raise ValueError(f"No resource data for {wickets_lost} wickets lost")

        # Avoid list.copy() “unknown” — return a fresh List[float]
        return list(self._resources[wickets_lost])

    def overs_balls_to_balls_left(self, overs: int, balls: int) -> int:
        balls = max(0, min(balls, 5))
        return max(0, min(overs * 6 + balls, self.max_balls))

    def balls_left_to_overs_balls(self, balls_left: int) -> tuple[int, int]:
        balls_left = max(0, min(balls_left, self.max_balls))
        overs = balls_left // 6
        balls = balls_left % 6
        return (overs, balls)

    def __repr__(self) -> str:
        return f"DLSTable(format_overs={self.format_overs}, max_balls={self.max_balls})"


def load_table_from_json(json_path: Union[str, Path]) -> DLSTable:
    """
    Load DLS table from JSON file.
    """
    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"DLS table file not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {json_path}: {e}")

    # Validate required fields
    for field in ("format_overs", "resources"):
        if field not in data:
            raise ValueError(f"Missing required field in JSON: {field}")

    format_overs = int(data["format_overs"])

    # JSON gives us Dict[str, List[float]] (or similar). This matches the widened type.
    resources: Mapping[Union[int, str], Sequence[float]] = data["resources"]

    return DLSTable(format_overs, resources)
