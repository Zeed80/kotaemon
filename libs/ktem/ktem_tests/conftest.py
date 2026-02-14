"""Pytest configuration for ktem tests.

ktem modules rely on theflow settings from root-level flowsettings.py.
This conftest ensures theflow can resolve flowsettings when tests are run
from libs/ktem (e.g. `pytest ktem_tests`).
"""

import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
os.environ.setdefault("THEFLOW_SETTINGS_MODULE", "flowsettings")
