#!/usr/bin/env python3
"""Preview or install Inonu's native Codex and Claude Code skills."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inonu_harness.host_profiles import main


if __name__ == "__main__":
    raise SystemExit(main())
