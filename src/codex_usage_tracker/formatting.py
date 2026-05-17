"""Human-readable report formatting."""

from __future__ import annotations

from typing import Any


def format_summary(rows: list[dict[str, Any]], group_by: str) -> str:
    if not rows:
        return "No Codex usage records found. Run refresh_usage_index first."

    lines = [f"Codex usage summary by {group_by}", ""]
    for row in rows:
        label = row.get("group_key") or "Unknown"
        total = _fmt_int(row.get("total_tokens"))
        calls = _fmt_int(row.get("model_calls"))
        sessions = _fmt_int(row.get("sessions"))
        cached = _fmt_int(row.get("cached_input_tokens"))
        uncached = _fmt_int(row.get("uncached_input_tokens"))
        output = _fmt_int(row.get("output_tokens"))
        reasoning = _fmt_int(row.get("reasoning_output_tokens"))
        cache_ratio = _fmt_pct(row.get("avg_cache_ratio"))
        lines.append(
            f"- {label}: {total} total tokens across {calls} model calls "
            f"({sessions} sessions, {cached} cached input, {uncached} uncached input, "
            f"{output} output, {reasoning} reasoning output, avg cache {cache_ratio})"
        )
    return "\n".join(lines)


def format_session(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No usage records found for that session."

    first = rows[0]
    thread = first.get("thread_name") or first.get("session_id")
    lines = [
        f"Codex session usage: {thread}",
        f"Session: {first.get('session_id')}",
        "",
    ]
    for index, row in enumerate(rows, 1):
        label = row.get("event_timestamp") or f"call {index}"
        lines.append(
            f"{index}. {label} | {row.get('model') or 'unknown'} "
            f"({row.get('effort') or 'unknown'}) | "
            f"last call {_fmt_int(row.get('total_tokens'))} tokens | "
            f"cumulative {_fmt_int(row.get('cumulative_total_tokens'))} tokens | "
            f"cache {_fmt_pct(row.get('cache_ratio'))} | "
            f"context {_fmt_pct(row.get('context_window_percent'))}"
        )
    return "\n".join(lines)


def _fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_pct(value: object) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"
