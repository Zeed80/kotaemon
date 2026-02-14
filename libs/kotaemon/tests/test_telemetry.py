import subprocess
import sys
from pathlib import Path

from .conftest import skip_when_haystack_not_installed

_REPO_ROOT = str(Path(__file__).resolve().parents[3])
_LIBS_KOTAEMON = str(Path(__file__).resolve().parents[1])  # libs/kotaemon

_SCRIPT_HAYSTACK_FIRST = """
import os
import sys
sys.path.insert(0, {libs_kotaemon!r})
sys.path.insert(0, {repo_root!r})
os.environ.setdefault("THEFLOW_SETTINGS_MODULE", "flowsettings")
# Ensure telemetry enabled before haystack loads (parent env may have disabled it)
if "HAYSTACK_TELEMETRY_ENABLED" in os.environ:
    del os.environ["HAYSTACK_TELEMETRY_ENABLED"]

# 1. Import haystack first (telemetry enabled by default)
import haystack  # noqa: F401
from haystack.telemetry._telemetry import telemetry as t_before

assert t_before is not None, "telemetry should be set before kotaemon"
assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") != "False"

# 2. Import kotaemon (disables telemetry)
import kotaemon  # noqa: F401
import haystack.telemetry._telemetry as _ht

assert _ht.telemetry is None, "telemetry should be None after kotaemon"
assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"
"""

_SCRIPT_KOTAEMON_FIRST = """
import os
import sys
sys.path.insert(0, {libs_kotaemon!r})
sys.path.insert(0, {repo_root!r})
os.environ.setdefault("THEFLOW_SETTINGS_MODULE", "flowsettings")

# 1. Import kotaemon first (sets env before haystack.telemetry loads)
import kotaemon  # noqa: F401
import haystack  # noqa: F401
import haystack.telemetry._telemetry as _ht

assert _ht.telemetry is None
assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"
"""


@skip_when_haystack_not_installed
def test_disable_telemetry_import_haystack_first():
    """Test that telemetry is disabled when kotaemon lib is initiated after."""
    script = _SCRIPT_HAYSTACK_FIRST.format(
        repo_root=_REPO_ROOT, libs_kotaemon=_LIBS_KOTAEMON
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=_REPO_ROOT,
    )
    assert (
        result.returncode == 0
    ), f"Subprocess failed: stdout={result.stdout}, stderr={result.stderr}"


@skip_when_haystack_not_installed
def test_disable_telemetry_import_haystack_after_kotaemon():
    """Test that telemetry is disabled when kotaemon lib is initiated before."""
    script = _SCRIPT_KOTAEMON_FIRST.format(
        repo_root=_REPO_ROOT, libs_kotaemon=_LIBS_KOTAEMON
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=_REPO_ROOT,
    )
    assert (
        result.returncode == 0
    ), f"Subprocess failed: stdout={result.stdout}, stderr={result.stderr}"
