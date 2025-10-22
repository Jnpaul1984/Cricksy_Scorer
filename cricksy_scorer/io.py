"""I/O utilities for reading and writing JSON files."""

import json
from pathlib import Path
from typing import Any, Dict


__all__ = ["read_json", "write_json"]


def read_json(path: str) -> Dict[str, Any]:
    """Read JSON data from a file.

    Args:
        path: Path to the JSON file

    Returns:
        Dictionary containing the parsed JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: Dict[str, Any], indent: int = 2) -> None:
    """Write data to a JSON file.

    Args:
        path: Path to the output JSON file
        data: Dictionary to write as JSON
        indent: Number of spaces for indentation (default: 2)
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
