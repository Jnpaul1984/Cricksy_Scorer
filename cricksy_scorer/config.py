"""Configuration management for cricket scoring."""

from typing import Any, Dict, Optional
from .io import read_json


__all__ = ["load_config"]


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from a JSON file.

    TODO: Expand with validation and schema checking in follow-up PR.

    Args:
        path: Optional path to configuration JSON file.
              If None, returns empty config (default settings).

    Returns:
        Dictionary containing configuration data
    """
    if path is None:
        # Return default empty configuration
        return {}

    try:
        return read_json(path)
    except FileNotFoundError:
        # If file doesn't exist, return empty config
        return {}
