"""MCP server exposing aggregate-only Codex usage tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from codex_usage_tracker.dashboard import generate_dashboard
from codex_usage_tracker.formatting import format_session, format_summary
from codex_usage_tracker.paths import (
    DEFAULT_CODEX_HOME,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_DB_PATH,
)
from codex_usage_tracker.store import (
    export_usage_csv as export_csv,
    query_session_usage,
    query_summary,
    refresh_usage_index as refresh_index,
)

mcp = FastMCP("codex-usage-tracker")


@mcp.tool()
def refresh_usage_index(include_archived: bool = False) -> dict[str, Any]:
    """Scan local Codex logs and upsert aggregate usage metrics into SQLite."""

    result = refresh_index(
        codex_home=DEFAULT_CODEX_HOME,
        db_path=DEFAULT_DB_PATH,
        include_archived=include_archived,
    )
    return {
        "scanned_files": result.scanned_files,
        "parsed_events": result.parsed_events,
        "inserted_or_updated_events": result.inserted_or_updated_events,
        "db_path": result.db_path,
    }


@mcp.tool()
def usage_summary(group_by: str = "thread", limit: int = 20) -> str:
    """Summarize aggregate Codex token usage by date, model, effort, cwd, thread, or session."""

    rows = query_summary(DEFAULT_DB_PATH, group_by=group_by, limit=limit)
    return format_summary(rows, group_by)


@mcp.tool()
def session_usage(session_id: str | None = None, limit: int = 200) -> str:
    """Show aggregate per-call usage for one session, defaulting to the latest indexed session."""

    rows = query_session_usage(DEFAULT_DB_PATH, session_id=session_id, limit=limit)
    return format_session(rows)


@mcp.tool()
def generate_usage_dashboard(output_path: str | None = None, limit: int = 5000) -> dict[str, Any]:
    """Generate a local hoverable HTML dashboard from aggregate-only usage metrics."""

    output = Path(output_path).expanduser() if output_path else DEFAULT_DASHBOARD_PATH
    generated = generate_dashboard(DEFAULT_DB_PATH, output_path=output, limit=limit)
    return {"dashboard_path": str(generated), "file_url": generated.resolve().as_uri()}


@mcp.tool()
def export_usage_csv(output_path: str, limit: int | None = None) -> dict[str, Any]:
    """Export aggregate Codex token usage rows to a local CSV file."""

    output = Path(output_path).expanduser()
    rows = export_csv(output_path=output, db_path=DEFAULT_DB_PATH, limit=limit)
    return {"rows": rows, "csv_path": str(output)}


if __name__ == "__main__":
    mcp.run()
