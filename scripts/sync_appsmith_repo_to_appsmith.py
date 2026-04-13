#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger an Appsmith Git pull for the configured application."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to the Appsmith repo root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        default=".appsmith-sync.json",
        help="Path to the Appsmith sync config JSON relative to repo root",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Maximum time to wait for the Appsmith pull to complete",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval for pull status",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Export it before running this script. "
            f"{name} should come from a current Appsmith browser session."
        )
    return value


def build_headers(branch: str) -> dict[str, str]:
    cookie_header = get_required_env("APPSMITH_COOKIE_HEADER")
    xsrf_token = get_required_env("APPSMITH_XSRF_TOKEN")
    return {
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie_header,
        "X-XSRF-TOKEN": xsrf_token,
        "X-Requested-By": "Appsmith",
        "branchName": branch,
    }


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"
    req = Request(full_url, method=method, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {full_url} failed with {exc.code}: {body}") from exc
    except URLError as exc:
        raise SystemExit(f"{method} {full_url} failed: {exc}") from exc


def get_status(base_url: str, app_id: str, headers: dict[str, str]) -> dict[str, Any]:
    endpoints = (
        f"{base_url}/api/v1/git/applications/{app_id}/status",
        f"{base_url}/v1/git/status/app/{app_id}",
    )
    for endpoint in endpoints:
        try:
            payload = request_json("GET", endpoint, headers, params={"compareRemote": "true"})
        except SystemExit:
            continue
        return payload
    raise SystemExit("Unable to read Appsmith git status from any known endpoint.")


def trigger_pull(base_url: str, app_id: str, page_id: str, headers: dict[str, str]) -> None:
    endpoints = (
        f"{base_url}/api/v1/git/applications/{app_id}/pull",
        f"{base_url}/v1/git/pull/app/{app_id}",
    )
    last_error: str | None = None
    for endpoint in endpoints:
        try:
            request_json("POST", endpoint, headers, params={"requestPageId": page_id})
            return
        except SystemExit as exc:
            last_error = str(exc)
    raise SystemExit(last_error or "Unable to trigger Appsmith git pull.")


def poll_pull(base_url: str, app_id: str, headers: dict[str, str], timeout_seconds: int, poll_interval_seconds: float) -> None:
    endpoints = (
        f"{base_url}/api/v1/git/applications/{app_id}/poll-pull-status",
        f"{base_url}/v1/git/poll-pull-status/app/{app_id}",
    )
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for endpoint in endpoints:
            try:
                payload = request_json("GET", endpoint, headers)
            except SystemExit:
                continue
            data = payload.get("data")
            if isinstance(data, str):
                state = data
            elif isinstance(data, dict):
                state = data.get("status") or data.get("pullStatus") or data.get("state")
            else:
                state = None
            if state in {"IDLE", "PUBLISHED", "NOT_REQUIRED"}:
                return
            if state in {"IN_PROGRESS", "LOCKED", None}:
                time.sleep(poll_interval_seconds)
                break
            raise SystemExit(f"Unexpected Appsmith pull status: {payload}")
        else:
            time.sleep(poll_interval_seconds)
    raise SystemExit("Timed out waiting for Appsmith git pull to finish.")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    config = load_json((repo_root / args.config).resolve())
    base_url = config["baseUrl"].rstrip("/")
    app_id = config["appId"]
    page_id = config["defaultPageId"]
    branch = config.get("branch", "main")

    headers = build_headers(branch)
    status = get_status(base_url, app_id, headers)
    print(json.dumps({"before": status.get("data", status)}, indent=2))
    trigger_pull(base_url, app_id, page_id, headers)
    poll_pull(
        base_url,
        app_id,
        headers,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    status = get_status(base_url, app_id, headers)
    print(json.dumps({"after": status.get("data", status)}, indent=2))


if __name__ == "__main__":
    main()
