#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


class AppsmithApiError(RuntimeError):
    def __init__(
        self,
        method: str,
        url: str,
        status_code: int | None,
        payload: Any = None,
        message: str | None = None,
    ) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.payload = payload
        self.api_code = extract_api_code(payload)
        self.api_message = extract_api_message(payload)
        detail = self.api_message or message or f"{method} {url} failed"
        if self.api_code:
            detail = f"{self.api_code}: {detail}"
        super().__init__(detail)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync the split Appsmith repo into a live Appsmith application. "
            "Prefers Git pull when the app is Git-connected and falls back to "
            "direct REST API deploy for non-Git apps."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to the Appsmith repo root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        default=".appsmith-sync.json",
        help="Path to the sync config file relative to the repo root",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "git", "direct"),
        default="auto",
        help="Sync mode: auto (default), git-only, or direct-only",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=300.0,
        help="Maximum seconds to wait for Git pull status polling",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval for Git pull status",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip Appsmith publish after a direct API deploy",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def get_required_env(name: str) -> str:
    import os

    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Environment variable {name} is required.")
    return value


def build_headers(config: dict[str, Any]) -> dict[str, str]:
    cookie_header = get_required_env("APPSMITH_COOKIE_HEADER")
    xsrf_token = get_required_env("APPSMITH_XSRF_TOKEN")
    headers = {
        "Accept": "application/json",
        "Cookie": cookie_header,
        "X-XSRF-TOKEN": xsrf_token,
    }
    branch = config.get("branch")
    if branch:
        headers["branchname"] = str(branch)
    return headers


def extract_api_code(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response_meta = payload.get("responseMeta")
    if isinstance(response_meta, dict):
        err = response_meta.get("error")
        if isinstance(err, dict):
            for key in ("code", "errorCode"):
                value = err.get(key)
                if value:
                    return str(value)
        for key in ("errorCode", "code"):
            value = response_meta.get(key)
            if value:
                return str(value)
    for key in ("errorCode", "code"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def extract_api_message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response_meta = payload.get("responseMeta")
    if isinstance(response_meta, dict):
        err = response_meta.get("error")
        if isinstance(err, dict):
            for key in ("message", "detail", "subtitle", "title"):
                value = err.get(key)
                if value:
                    return str(value)
        for key in ("message", "subtitle", "title"):
            value = response_meta.get(key)
            if value:
                return str(value)
    for key in ("message", "detail", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    payload: Any | None = None,
) -> Any:
    if params:
        query = parse.urlencode(
            {
                key: value
                for key, value in params.items()
                if value is not None
            }
        )
        if query:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"

    data = None
    request_headers = dict(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with request.urlopen(req) as response:
            raw = response.read()
            if not raw:
                return {}
            parsed = json.loads(raw.decode("utf-8"))
    except error.HTTPError as exc:
        raw = exc.read()
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                parsed = {"message": raw.decode("utf-8", errors="replace")}
        raise AppsmithApiError(method, url, exc.code, parsed) from exc
    except error.URLError as exc:
        raise AppsmithApiError(method, url, None, None, str(exc.reason)) from exc

    if isinstance(parsed, dict):
        response_meta = parsed.get("responseMeta")
        if isinstance(response_meta, dict) and response_meta.get("success") is False:
            raise AppsmithApiError(method, url, 200, parsed)
    return parsed


def unwrap_data(payload: Any) -> Any:
    value = payload
    while isinstance(value, dict) and "data" in value and "responseMeta" in value:
        value = value["data"]
    return value


def extract_collection(payload: Any, candidate_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    value = unwrap_data(payload)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in candidate_keys:
            items = value.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def sort_widget_node(node: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        bool(node.get("detachFromLayout", False)),
        node.get("topRow", 0),
        node.get("leftColumn", 0),
        node.get("widgetName", ""),
    )


def load_repo_page_payload(page_dir: Path) -> tuple[dict[str, Any], list[Any]]:
    page_name = page_dir.name
    payload = load_json(page_dir / f"{page_name}.json")
    layout = payload["unpublishedPage"]["layouts"][0]
    dsl = copy.deepcopy(layout["dsl"])
    layout_on_load_actions = copy.deepcopy(layout.get("layoutOnLoadActions", []))
    return dsl, layout_on_load_actions


def build_page_dsl(page_dir: Path) -> tuple[dict[str, Any], list[Any]]:
    root_dsl, layout_on_load_actions = load_repo_page_payload(page_dir)
    widgets_dir = page_dir / "widgets"
    if not widgets_dir.exists():
        root_dsl["children"] = []
        return root_dsl, layout_on_load_actions

    widgets_by_id: dict[str, dict[str, Any]] = {}
    child_stubs_by_parent: dict[str, list[dict[str, Any]]] = {}
    widgets_by_parent: dict[str, list[dict[str, Any]]] = {}

    for widget_path in sorted(widgets_dir.rglob("*.json")):
        widget = load_json(widget_path)
        widget_id = str(widget["widgetId"])
        child_stubs_by_parent[widget_id] = copy.deepcopy(widget.get("children", []))
        widget_copy = copy.deepcopy(widget)
        widget_copy.pop("children", None)
        widgets_by_id[widget_id] = widget_copy
        parent_id = str(widget_copy.get("parentId", ""))
        widgets_by_parent.setdefault(parent_id, []).append(widget_copy)

    def build_canvas_stub(stub: dict[str, Any]) -> dict[str, Any]:
        canvas = copy.deepcopy(stub)
        canvas_id = str(canvas["widgetId"])
        canvas_children = [
            rebuild_widget(str(child["widgetId"]))
            for child in sorted(widgets_by_parent.get(canvas_id, []), key=sort_widget_node)
        ]
        if canvas_children:
            canvas["children"] = canvas_children
        else:
            canvas.pop("children", None)
        return canvas

    def rebuild_widget(widget_id: str) -> dict[str, Any]:
        widget = copy.deepcopy(widgets_by_id[widget_id])
        stubs = child_stubs_by_parent.get(widget_id, [])
        built_children: list[dict[str, Any]] = []
        seen_widget_ids: set[str] = set()

        for stub in stubs:
            stub_id = str(stub.get("widgetId", ""))
            stub_type = stub.get("type")
            if stub_id in widgets_by_id:
                built_children.append(rebuild_widget(stub_id))
                seen_widget_ids.add(stub_id)
            elif stub_type == "CANVAS_WIDGET" and stub_id:
                built_children.append(build_canvas_stub(stub))
            else:
                built_children.append(copy.deepcopy(stub))

        extras = [
            child
            for child in widgets_by_parent.get(widget_id, [])
            if str(child["widgetId"]) not in seen_widget_ids
        ]
        for extra in sorted(extras, key=sort_widget_node):
            built_children.append(rebuild_widget(str(extra["widgetId"])))

        if built_children:
            widget["children"] = built_children
        else:
            widget.pop("children", None)
        return widget

    root_children = [
        rebuild_widget(str(widget["widgetId"]))
        for widget in sorted(widgets_by_parent.get("0", []), key=sort_widget_node)
    ]
    root_dsl["children"] = root_children
    return root_dsl, layout_on_load_actions


def load_sync_config(repo_root: Path, config_path: str) -> dict[str, Any]:
    config = load_json((repo_root / config_path).resolve())
    required = ("baseUrl", "appId", "defaultPageId")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise SystemExit(f"Missing required sync config values: {', '.join(missing)}")
    return config


def is_git_config_error(exc: AppsmithApiError) -> bool:
    haystack = " ".join(
        [
            str(exc.api_code or ""),
            str(exc.api_message or ""),
            str(exc),
        ]
    ).lower()
    return (
        "ae-git-4031" in haystack
        or "unable to find the git configuration" in haystack
        or "git configuration is invalid" in haystack
        or "git configuration" in haystack and "invalid" in haystack
    )


def git_pull_sync(
    base_url: str,
    app_id: str,
    default_page_id: str,
    headers: dict[str, str],
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> None:
    status_url = f"{base_url}/api/v1/git/applications/{app_id}/status"
    request_json("GET", status_url, headers, params={"compareRemote": "true"})

    pull_url = f"{base_url}/api/v1/git/applications/{app_id}/pull"
    request_json(
        "POST",
        pull_url,
        headers,
        params={"requestPageId": default_page_id},
    )

    poll_url = f"{base_url}/api/v1/git/applications/{app_id}/poll-pull-status"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = request_json("GET", poll_url, headers)
        data = unwrap_data(payload)
        if not isinstance(data, dict):
            raise SystemExit(f"Unexpected poll payload: {json.dumps(payload, indent=2)}")

        if data.get("isPulling") is False:
            if data.get("isPullSuccessful") is False:
                raise SystemExit(json.dumps(payload, indent=2))
            if data.get("areBranchEqual") is False and data.get("isPullSuccessful") is None:
                time.sleep(poll_interval_seconds)
                continue
            print("Git sync complete.")
            return

        time.sleep(poll_interval_seconds)

    raise SystemExit("Timed out waiting for Appsmith Git pull to complete.")


def fetch_live_repo_context(
    base_url: str,
    app_id: str,
    default_page_id: str,
    headers: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    consolidated = request_json(
        "GET",
        f"{base_url}/api/v1/consolidated-api/edit",
        headers,
        params={"defaultPageId": default_page_id},
    )
    data = consolidated.get("data", {})
    live_pages = extract_collection(data.get("pages"), ("pages", "pageList"))
    live_datasources = extract_collection(
        data.get("datasources"), ("datasourceList", "datasources")
    )

    pages_by_name = {
        str(page["name"]): page
        for page in live_pages
        if isinstance(page, dict) and page.get("name")
    }
    datasources_by_name = {
        str(datasource["name"]): datasource
        for datasource in live_datasources
        if isinstance(datasource, dict) and datasource.get("name")
    }
    return pages_by_name, datasources_by_name


def fetch_layout_id(
    base_url: str,
    page_id: str,
    headers: dict[str, str],
) -> str:
    payload = request_json("GET", f"{base_url}/api/v1/pages/{page_id}", headers)
    data = unwrap_data(payload)
    if not isinstance(data, dict):
        raise SystemExit(f"Unexpected page payload: {json.dumps(payload, indent=2)}")
    layouts = data.get("layouts", [])
    if not layouts:
        raise SystemExit(f"Page {page_id} has no layouts.")
    layout_id = layouts[0].get("id")
    if not layout_id:
        raise SystemExit(f"Page {page_id} layout is missing an id.")
    return str(layout_id)


def build_live_datasource_reference(datasource: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": datasource["id"],
        "name": datasource["name"],
        "pluginId": datasource["pluginId"],
        "isAutoGenerated": datasource.get("isAutoGenerated", False),
    }


def deploy_pages(
    repo_root: Path,
    base_url: str,
    app_id: str,
    headers: dict[str, str],
    pages_by_name: dict[str, dict[str, Any]],
) -> list[str]:
    deployed_pages: list[str] = []
    pages_root = repo_root / "pages"
    for page_dir in sorted(path for path in pages_root.iterdir() if path.is_dir()):
        page_name = page_dir.name
        live_page = pages_by_name.get(page_name)
        if not live_page:
            raise SystemExit(f"Live Appsmith app is missing page '{page_name}'.")
        page_id = str(live_page["id"])
        layout_id = fetch_layout_id(base_url, page_id, headers)
        dsl, layout_on_load_actions = build_page_dsl(page_dir)
        payload = {
            "applicationId": app_id,
            "id": layout_id,
            "dsl": dsl,
            "layoutOnLoadActions": layout_on_load_actions,
        }
        request_json(
            "PUT",
            f"{base_url}/api/v1/layouts/{layout_id}/pages/{page_id}",
            headers,
            params={"applicationId": app_id},
            payload=payload,
        )
        deployed_pages.append(page_name)
    return deployed_pages


def fetch_live_actions_for_page(
    base_url: str,
    page_id: str,
    headers: dict[str, str],
) -> dict[str, dict[str, Any]]:
    payload = request_json(
        "GET",
        f"{base_url}/api/v1/actions",
        headers,
        params={"pageId": page_id},
    )
    data = unwrap_data(payload)
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected actions view payload: {json.dumps(payload, indent=2)}")

    actions_by_name: dict[str, dict[str, Any]] = {}
    for action in data:
        if not isinstance(action, dict):
            continue
        action_name = action.get("name")
        if not action_name:
            continue
        actions_by_name[str(action_name)] = action

    return actions_by_name


def deploy_actions(
    repo_root: Path,
    base_url: str,
    headers: dict[str, str],
    pages_by_name: dict[str, dict[str, Any]],
    datasources_by_name: dict[str, dict[str, Any]],
) -> list[str]:
    deployed_actions: list[str] = []
    pages_root = repo_root / "pages"
    for page_dir in sorted(path for path in pages_root.iterdir() if path.is_dir()):
        live_page = pages_by_name.get(page_dir.name)
        if not live_page:
            raise SystemExit(f"Live Appsmith page '{page_dir.name}' not found.")
        live_page_id = str(live_page["id"])
        live_actions_by_name = fetch_live_actions_for_page(
            base_url, live_page_id, headers
        )

        queries_root = page_dir / "queries"
        if not queries_root.exists():
            continue

        for action_dir in sorted(path for path in queries_root.iterdir() if path.is_dir()):
            metadata_path = action_dir / "metadata.json"
            body_path = action_dir / f"{action_dir.name}.txt"
            if not metadata_path.exists() or not body_path.exists():
                continue

            metadata = load_json(metadata_path)
            body = body_path.read_text(encoding="utf-8")
            payload = copy.deepcopy(metadata)
            payload["unpublishedAction"]["actionConfiguration"]["body"] = body

            page_name = str(payload["unpublishedAction"]["pageId"])
            if page_name != page_dir.name:
                raise SystemExit(
                    f"Action metadata page '{page_name}' does not match directory "
                    f"'{page_dir.name}' for action "
                    f"{page_dir.name}/{action_dir.name}."
                )
            payload["unpublishedAction"]["pageId"] = live_page_id

            datasource_name = payload["unpublishedAction"]["datasource"]["name"]
            live_datasource = datasources_by_name.get(datasource_name)
            if not live_datasource:
                raise SystemExit(
                    f"Live Appsmith datasource '{datasource_name}' not found for action "
                    f"{page_dir.name}/{action_dir.name}."
                )
            ua_name = str(payload["unpublishedAction"]["name"])
            live_action = live_actions_by_name.get(ua_name)
            if live_action and live_action.get("id"):
                request_json(
                    "DELETE",
                    f"{base_url}/api/v1/actions/{live_action['id']}",
                    headers,
                )

            payload = {
                "pageId": str(live_page["id"]),
                "name": ua_name,
                "pluginType": payload["pluginType"],
                "pluginId": str(live_datasource["pluginId"]),
                "datasource": build_live_datasource_reference(live_datasource),
                "actionConfiguration": payload["unpublishedAction"]["actionConfiguration"],
                "runBehaviour": payload["unpublishedAction"].get("runBehaviour", "MANUAL"),
                "userSetOnLoad": payload["unpublishedAction"].get("userSetOnLoad", False),
                "dynamicBindingPathList": payload["unpublishedAction"].get(
                    "dynamicBindingPathList", []
                ),
                "confirmBeforeExecute": payload["unpublishedAction"].get(
                    "confirmBeforeExecute", False
                ),
            }
            request_json(
                "POST",
                f"{base_url}/api/v1/actions",
                headers,
                payload=payload,
            )
            deployed_actions.append(f"{page_dir.name}/{action_dir.name}")
    return deployed_actions


def direct_sync(
    repo_root: Path,
    config: dict[str, Any],
    headers: dict[str, str],
    publish: bool,
) -> None:
    base_url = str(config["baseUrl"]).rstrip("/")
    app_id = str(config["appId"])
    default_page_id = str(config["defaultPageId"])

    pages_by_name, datasources_by_name = fetch_live_repo_context(
        base_url, app_id, default_page_id, headers
    )
    deployed_pages = deploy_pages(repo_root, base_url, app_id, headers, pages_by_name)
    deployed_actions = deploy_actions(
        repo_root,
        base_url,
        headers,
        pages_by_name,
        datasources_by_name,
    )

    if publish:
        request_json(
            "POST",
            f"{base_url}/api/v1/applications/publish/{app_id}",
            headers,
        )

    jsobjects_root = repo_root / "jsobjects"
    if jsobjects_root.exists() and any(jsobjects_root.iterdir()):
        print("Warning: jsobjects/ exists, but direct sync does not deploy JSObjects.")

    print(f"Direct sync complete. Updated {len(deployed_pages)} page(s).")
    for page_name in deployed_pages:
        print(f"  page: {page_name}")
    print(f"Updated {len(deployed_actions)} action(s).")
    for action_name in deployed_actions:
        print(f"  action: {action_name}")
    if publish:
        print("Published Appsmith application.")
    else:
        print("Skipped Appsmith publish (--no-publish).")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    config = load_sync_config(repo_root, args.config)
    headers = build_headers(config)
    base_url = str(config["baseUrl"]).rstrip("/")
    app_id = str(config["appId"])
    default_page_id = str(config["defaultPageId"])

    if args.mode == "direct":
        direct_sync(repo_root, config, headers, publish=not args.no_publish)
        return

    if args.mode == "git":
        git_pull_sync(
            base_url,
            app_id,
            default_page_id,
            headers,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        return

    try:
        git_pull_sync(
            base_url,
            app_id,
            default_page_id,
            headers,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
    except AppsmithApiError as exc:
        if not is_git_config_error(exc):
            raise
        print(f"Git sync unavailable ({exc}). Falling back to direct API deploy.")
        direct_sync(repo_root, config, headers, publish=not args.no_publish)


if __name__ == "__main__":
    main()
