"""Local dashboard server with lazy context API."""

from __future__ import annotations

import json
import webbrowser
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from codex_usage_tracker.context import DEFAULT_CONTEXT_CHARS, load_call_context
from codex_usage_tracker.dashboard import generate_dashboard
from codex_usage_tracker.paths import DEFAULT_DASHBOARD_PATH, DEFAULT_PRICING_PATH


def serve_dashboard(
    db_path: Path,
    output_path: Path = DEFAULT_DASHBOARD_PATH,
    pricing_path: Path = DEFAULT_PRICING_PATH,
    limit: int = 5000,
    since: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    context_chars: int = DEFAULT_CONTEXT_CHARS,
    open_browser: bool = False,
) -> None:
    """Generate and serve the dashboard plus a localhost-only context endpoint."""

    _validate_loopback_host(host)
    output = generate_dashboard(
        db_path=db_path,
        output_path=output_path,
        limit=limit,
        pricing_path=pricing_path,
        since=since,
    )
    handler = partial(
        _UsageDashboardHandler,
        directory=str(output.parent),
        db_path=db_path,
        dashboard_name=output.name,
        context_chars=context_chars,
    )
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/{output.name}"
    print(f"Serving Codex usage dashboard at {url}")
    print("Raw context is loaded only through /api/context after a row action.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
    finally:
        server.server_close()


class _UsageDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: object,
        db_path: Path,
        dashboard_name: str,
        context_chars: int,
        **kwargs: object,
    ) -> None:
        self._db_path = db_path
        self._dashboard_name = dashboard_name
        self._context_chars = context_chars
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
        parsed = urlparse(self.path)
        if parsed.path == "/api/context":
            self._handle_context(parsed.query)
            return
        if parsed.path == "/":
            self.path = f"/{self._dashboard_name}"
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _handle_context(self, query: str) -> None:
        params = parse_qs(query)
        record_id = _first(params.get("record_id"))
        if not record_id:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "record_id is required"},
            )
            return
        include_tool_output = _truthy(_first(params.get("include_tool_output")))
        try:
            payload = load_call_context(
                record_id=record_id,
                db_path=self._db_path,
                max_chars=self._context_chars,
                include_tool_output=include_tool_output,
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        except FileNotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        except OSError as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Could not read source log: {exc}"},
            )
            return
        self._send_json(HTTPStatus.OK, payload)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _first(values: list[str] | None) -> str | None:
    return values[0] if values else None


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _validate_loopback_host(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ip_address(host)
    except ValueError as exc:
        raise ValueError(
            "serve-dashboard --host must be localhost, 127.0.0.1, or ::1"
        ) from exc
    if not address.is_loopback:
        raise ValueError("serve-dashboard refuses to expose raw context off localhost")
