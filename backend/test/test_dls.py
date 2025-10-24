# tests/test_dls.py
import pytest
from dls import compute_dls_target, DLSMissingTable

def test_compute_works_with_placeholder(monkeypatch):
    # Point to the test fixture table
    # (or ensure backend/static/dls_20.json exists)
    res = compute_dls_target(
        team1_score=150,
        team1_wickets_lost=5,
        team1_overs_left_at_end=0.0,
        format_overs=20,
        team2_wkts_lost_now=2,
        team2_overs_left_now=10.0,
    )
    assert res.target >= 1



