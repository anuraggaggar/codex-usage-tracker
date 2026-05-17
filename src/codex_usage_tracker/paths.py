"""Shared filesystem defaults for local Codex usage tracking."""

from __future__ import annotations

from pathlib import Path


APP_DIR = Path.home() / ".codex-usage-tracker"
DEFAULT_DB_PATH = APP_DIR / "usage.sqlite3"
DEFAULT_DASHBOARD_PATH = APP_DIR / "dashboard.html"
DEFAULT_CODEX_HOME = Path.home() / ".codex"
