#!/usr/bin/env python3
"""Register this repo as a home-local Codex plugin."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PLUGIN_NAME = "codex-usage-tracker"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    plugin_parent = Path.home() / "plugins"
    plugin_link = plugin_parent / PLUGIN_NAME
    marketplace_path = Path.home() / ".agents" / "plugins" / "marketplace.json"

    plugin_parent.mkdir(parents=True, exist_ok=True)
    if plugin_link.exists() or plugin_link.is_symlink():
        if plugin_link.resolve() != repo_root:
            print(
                f"Refusing to overwrite existing plugin path: {plugin_link}",
                file=sys.stderr,
            )
            return 1
    else:
        plugin_link.symlink_to(repo_root, target_is_directory=True)

    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace = _load_marketplace(marketplace_path)
    _upsert_marketplace_entry(marketplace)
    marketplace_path.write_text(
        json.dumps(marketplace, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print(f"Registered {PLUGIN_NAME} at {plugin_link}")
    print(f"Updated {marketplace_path}")
    print("Restart Codex to discover the plugin.")
    return 0


def _load_marketplace(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "name": "local",
            "interface": {"displayName": "Local Plugins"},
            "plugins": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid marketplace JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Marketplace JSON must be an object: {path}")
    data.setdefault("name", "local")
    data.setdefault("interface", {"displayName": "Local Plugins"})
    data.setdefault("plugins", [])
    if not isinstance(data["plugins"], list):
        raise SystemExit(f"Marketplace plugins field must be a list: {path}")
    return data


def _upsert_marketplace_entry(marketplace: dict[str, Any]) -> None:
    entry = {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": f"./plugins/{PLUGIN_NAME}",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }
    plugins = marketplace["plugins"]
    for index, existing in enumerate(plugins):
        if isinstance(existing, dict) and existing.get("name") == PLUGIN_NAME:
            plugins[index] = entry
            return
    plugins.append(entry)


if __name__ == "__main__":
    raise SystemExit(main())
