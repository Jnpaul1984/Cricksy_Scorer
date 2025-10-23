"""Tests for I/O utilities."""

import json
import pytest
from pathlib import Path

from cricksy_scorer.io import read_json, write_json


def test_write_and_read_json(tmp_path):
    """Test writing and reading JSON data."""
    test_file = tmp_path / "test.json"
    test_data = {"key": "value", "number": 42}

    # Write JSON
    write_json(str(test_file), test_data)

    # Verify file exists
    assert test_file.exists()

    # Read JSON back
    result = read_json(str(test_file))

    assert result == test_data


def test_write_json_creates_directories(tmp_path):
    """Test that write_json creates parent directories."""
    nested_path = tmp_path / "nested" / "path" / "test.json"
    test_data = {"nested": True}

    write_json(str(nested_path), test_data)

    assert nested_path.exists()
    result = read_json(str(nested_path))
    assert result == test_data


def test_write_json_with_indent(tmp_path):
    """Test that JSON is written with proper indentation."""
    test_file = tmp_path / "indented.json"
    test_data = {"key": "value", "nested": {"data": 123}}

    write_json(str(test_file), test_data, indent=4)

    # Read raw content to verify formatting
    content = test_file.read_text()
    assert "    " in content  # 4-space indent


def test_read_json_file_not_found():
    """Test that read_json raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        read_json("nonexistent_file.json")


def test_read_json_invalid_json(tmp_path):
    """Test that read_json raises JSONDecodeError for invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        read_json(str(invalid_file))


def test_write_read_complex_data(tmp_path):
    """Test writing and reading complex nested data."""
    test_file = tmp_path / "complex.json"
    test_data = {
        "match": {
            "id": "m001",
            "teams": ["Team A", "Team B"],
            "overs": 20,
            "players": [
                {"name": "Player 1", "id": "p1"},
                {"name": "Player 2", "id": "p2"},
            ],
        }
    }

    write_json(str(test_file), test_data)
    result = read_json(str(test_file))

    assert result == test_data
    assert result["match"]["teams"] == ["Team A", "Team B"]
