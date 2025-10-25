# backend/tests/conftest.py
import sys
import pathlib

# Repo root = two levels up from this file (Cricksy_Scorer/)
ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)
