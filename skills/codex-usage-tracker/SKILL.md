---
name: codex-usage-tracker
description: Use when the user asks about Codex token usage, model/reasoning efficiency, usage dashboards, CSV exports, or per-session/per-turn Codex usage stats from local logs.
---

# Codex Usage Tracker

Use this plugin to inspect aggregate token usage from local Codex session logs.

## Privacy Boundary

The tracker is aggregate-only. It should never return prompts, assistant message text, tool outputs, pasted secrets, or raw transcript snippets.

## Common Workflows

- Refresh the index before answering usage questions.
- Use `usage_summary` for high-level totals by date, model, effort, cwd, thread, or session.
- Use `session_usage` for per-call and per-turn detail for one session.
- Use `generate_usage_dashboard` when the user wants a visual hoverable report.
- Use `export_usage_csv` when the user wants local spreadsheet-friendly data.
