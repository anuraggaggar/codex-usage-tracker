# Codex Usage Tracker

Local Codex plugin and dashboard for tracking aggregate token usage from Codex session logs.

## What It Does

- Reads local Codex JSONL logs from `~/.codex/sessions/**/*.jsonl`.
- Optionally includes `~/.codex/archived_sessions/*.jsonl`.
- Stores aggregate-only usage metrics in local SQLite.
- Exposes MCP tools for refresh, summaries, session detail, CSV export, and dashboard generation.
- Generates a static hoverable dashboard for local review.
- Provides a read-only doctor command for local plugin/MCP setup checks.
- Optionally estimates costs from a user-maintained local pricing file.

The tracker intentionally does not store prompts, assistant messages, tool outputs, pasted secrets, or raw transcript snippets.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

## Usage

Refresh the local aggregate index:

```bash
codex-usage-tracker refresh
```

Check setup:

```bash
codex-usage-tracker doctor
```

Generate the local dashboard:

```bash
codex-usage-tracker dashboard --open
codex-usage-tracker open-dashboard
```

Show a summary:

```bash
codex-usage-tracker summary --group-by model
codex-usage-tracker summary --group-by thread --limit 20
codex-usage-tracker summary --preset today
codex-usage-tracker summary --preset last-7-days
codex-usage-tracker summary --preset expensive
codex-usage-tracker expensive --limit 10
```

Show one session:

```bash
codex-usage-tracker session <session-id>
```

Export CSV:

```bash
codex-usage-tracker export --output usage.csv
```

Enable optional cost estimates:

```bash
codex-usage-tracker init-pricing
```

Edit `~/.codex-usage-tracker/pricing.json` with current USD-per-million-token rates for the models you want to estimate. The tracker does not fetch pricing automatically because prices change and the config should remain local and explicit.

## Install As A Local Codex Plugin

After installing the Python package in the repo-local `.venv`, register the plugin locally:

```bash
python scripts/install_local_plugin.py
```

Restart Codex after registration so it can discover the plugin. The installer symlinks this repo into `~/plugins/codex-usage-tracker` and updates `~/.agents/plugins/marketplace.json` without removing existing entries.

## MCP Tools

- `refresh_usage_index`
- `usage_doctor`
- `usage_summary`
- `session_usage`
- `most_expensive_usage_calls`
- `generate_usage_dashboard`
- `export_usage_csv`
- `init_usage_pricing_config`

## Data Privacy

The SQLite database is stored at `~/.codex-usage-tracker/usage.sqlite3` by default and contains only aggregate metrics:

- session id, thread name, cwd, source file, turn id, timestamps
- model, reasoning effort, context window
- token counts and derived efficiency ratios

Raw chat text and tool outputs are ignored by the parser and are never written to the tracker database or dashboard.

Cost estimates are calculated only from aggregate token fields and your local pricing config. They are omitted when no matching model price is configured.

## Test

```bash
python -m pytest
python -m compileall src
codex-usage-tracker doctor
codex-usage-tracker dashboard --output /tmp/codex-usage-dashboard.html
codex-usage-tracker expensive --limit 5
```
