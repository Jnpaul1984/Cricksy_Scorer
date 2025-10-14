# dls/__init__.py
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List

from .loader import DLSTable, load_table_from_json

_SUPPORTED = {20: "icc_dls_international_20.json", 50: "icc_dls_international_50.json"}

def get_supported_formats() -> List[int]:
    return sorted(_SUPPORTED.keys())

def _default_tables_dir() -> Path:
    """
    Resolve the default location of the JSON tables:
    1) DLS_TABLES_DIR env var (if set)
    2) ../dls_tables relative to this file
    """
    import os
    env = os.getenv("DLS_TABLES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # package layout: dls/__init__.py -> ../dls_tables/
    return Path(__file__).resolve().parent.parent.joinpath("dls_tables").resolve()

def get_table_info(format_overs: int) -> Dict[str, Any]:
    """Return metadata without fully constructing DLSTable (cheap file read)."""
    if format_overs not in _SUPPORTED:
        raise ValueError(f"Unsupported format: {format_overs}. Supported: {sorted(_SUPPORTED)}")
    fpath = _default_tables_dir() / _SUPPORTED[format_overs]
    if not fpath.exists():
        raise FileNotFoundError(f"DLS table file not found: {fpath}")
    import json
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # keep only lightweight details
    return {
        "label": data.get("label"),
        "schema_version": data.get("schema_version"),
        "format_overs": data.get("format_overs"),
        "source": data.get("source"),
        "size_bytes": fpath.stat().st_size,
        "path": str(fpath),
    }

@lru_cache(maxsize=2)
def load_international_table(format_overs: int) -> DLSTable:
    """Load and cache the ICC Standard Edition table for 20 or 50 overs."""
    if format_overs not in _SUPPORTED:
        raise ValueError(f"Unsupported format: {format_overs}. Supported: {sorted(_SUPPORTED)}")
    fpath = _default_tables_dir() / _SUPPORTED[format_overs]
    return load_table_from_json(fpath)

def calculate_dls_target(team1_score: int, team1_resources: float,
                         team2_resources: float, G50: int = 245) -> int:
    """
    Standard Edition target calculation:
    - fewer resources: floor(S1 * R2 / R1) + 1
    - more resources:  S1 + floor((R2 - R1) * G50 / 100) + 1
    - equal resources: S1 + 1
    """
    if team2_resources < team1_resources:
        return int(team1_score * team2_resources / team1_resources) + 1
    elif team2_resources > team1_resources:
        extra = int((team2_resources - team1_resources) * G50 / 100)
        return team1_score + extra + 1
    else:
        return team1_score + 1

__all__ = [
    "DLSTable",
    "load_table_from_json",
    "load_international_table",
    "get_supported_formats",
    "get_table_info",
    "calculate_dls_target",
]
