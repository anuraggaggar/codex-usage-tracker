"""Command-line interface for local Codex usage tracking."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from codex_usage_tracker.dashboard import generate_dashboard
from codex_usage_tracker.formatting import format_session, format_summary
from codex_usage_tracker.paths import (
    DEFAULT_CODEX_HOME,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_DB_PATH,
)
from codex_usage_tracker.store import (
    export_usage_csv,
    query_session_usage,
    query_summary,
    refresh_usage_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(prog="codex-usage-tracker")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser("refresh", help="Scan Codex logs into SQLite")
    refresh.add_argument("--codex-home", type=Path, default=DEFAULT_CODEX_HOME)
    refresh.add_argument("--include-archived", action="store_true")

    summary = subparsers.add_parser("summary", help="Show aggregate usage summary")
    summary.add_argument(
        "--group-by",
        choices=["date", "model", "effort", "cwd", "thread", "session"],
        default="thread",
    )
    summary.add_argument("--limit", type=int, default=20)

    session = subparsers.add_parser("session", help="Show one session's usage")
    session.add_argument("session_id", nargs="?")
    session.add_argument("--limit", type=int, default=200)

    dashboard = subparsers.add_parser("dashboard", help="Generate static dashboard")
    dashboard.add_argument("--output", type=Path, default=DEFAULT_DASHBOARD_PATH)
    dashboard.add_argument("--limit", type=int, default=5000)
    dashboard.add_argument("--open", action="store_true")

    export = subparsers.add_parser("export", help="Export aggregate usage CSV")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--limit", type=int)

    args = parser.parse_args()

    if args.command == "refresh":
        result = refresh_usage_index(
            codex_home=args.codex_home,
            db_path=args.db,
            include_archived=args.include_archived,
        )
        print(
            f"Scanned {result.scanned_files} files, parsed {result.parsed_events} "
            f"usage events, upserted {result.inserted_or_updated_events} rows into {result.db_path}."
        )
        return 0

    if args.command == "summary":
        print(format_summary(query_summary(args.db, args.group_by, args.limit), args.group_by))
        return 0

    if args.command == "session":
        print(format_session(query_session_usage(args.db, args.session_id, args.limit)))
        return 0

    if args.command == "dashboard":
        output = generate_dashboard(db_path=args.db, output_path=args.output, limit=args.limit)
        print(f"Wrote dashboard to {output}")
        if args.open:
            webbrowser.open(output.resolve().as_uri())
        return 0

    if args.command == "export":
        count = export_usage_csv(output_path=args.output, db_path=args.db, limit=args.limit)
        print(f"Wrote {count} aggregate usage rows to {args.output}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
