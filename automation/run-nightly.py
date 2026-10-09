#!/usr/bin/env python3
"""Run the WorkBuddy Knowledge Star automation with preflight and audit logs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


AUTOMATION_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = AUTOMATION_ROOT.parent
CONFIG_PATH = AUTOMATION_ROOT / "config.json"
SETTINGS_PATH = SKILL_ROOT / "config" / "settings.json"
DEFAULT_COOKIE_PATH = SKILL_ROOT / "config" / "zsxq_cookies.json"
LOG_ROOT = AUTOMATION_ROOT / "logs"
STATE_PATH = AUTOMATION_ROOT / "state.json"

sys.path.insert(0, str(SKILL_ROOT))


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def log_line(log_path: Path, message: str) -> None:
    line = f"{now_text()} {message}"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def first_existing(candidates: list[str]) -> str:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return ""


def source_summary(route: dict[str, Any]) -> dict[str, Any]:
    candidates = [str(item) for item in route.get("source_candidates", [])]
    selected = first_existing(candidates)
    file_count = 0
    count_capped = False
    if selected:
        root = Path(selected)
        if root.is_file():
            file_count = 1
        else:
            # Preflight only needs to establish that a batch is available.
            # Capping the walk keeps a large knowledge-base root responsive.
            for current_root, _, files in os.walk(root):
                file_count += sum(
                    1 for name in files if not name.startswith(".")
                )
                if file_count >= 100:
                    file_count = 100
                    count_capped = True
                    break
    return {
        "candidates": candidates,
        "selected": selected,
        "exists": bool(selected),
        "file_count": file_count,
        "file_count_capped": count_capped,
    }


def preflight(settings: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    for path in (
        SKILL_ROOT / "main.py",
        SKILL_ROOT / "quark_share.py",
        SKILL_ROOT / "zsxq_publisher.py",
    ):
        add(f"file:{path.name}", path.exists(), str(path))

    try:
        import playwright  # noqa: F401
        import requests  # noqa: F401
        add("python_dependencies", True, "playwright and requests import successfully")
    except Exception as exc:
        add("python_dependencies", False, repr(exc))

    cookie = str(settings.get("quark_cookie") or "").strip()
    add(
        "quark_login",
        bool(cookie),
        "quark_cookie configured" if cookie else "config/settings.json has no quark_cookie",
    )

    cookie_file = Path(str(config.get("zsxq_cookie_file") or DEFAULT_COOKIE_PATH))
    if not cookie_file.is_absolute():
        cookie_file = (AUTOMATION_ROOT / cookie_file).resolve()
    add(
        "zsxq_login",
        cookie_file.exists(),
        str(cookie_file) if cookie_file.exists() else f"missing {cookie_file}",
    )

    routes = []
    for route in config.get("routes", []):
        if not route.get("enabled", True):
            continue
        name = str(route.get("name") or "unnamed")
        group_id = str(route.get("group_id") or "")
        add(f"group:{name}", group_id.isdigit() and len(group_id) >= 10, group_id)
        source = source_summary(route)
        add(
            f"source:{name}",
            source["exists"],
            source["selected"] or "none of the configured source paths exists",
        )
        if route.get("source_mode") == "local":
            add(
                f"local_upload_adapter:{name}",
                False,
                "no local-file-to-Quark upload adapter is configured",
            )
        routes.append({**route, "source": source})

    failures = [item["name"] for item in checks if not item["ok"]]
    return {
        "checked_at": now_text(),
        "success": not failures,
        "blocking_failures": failures,
        "checks": checks,
        "routes": routes,
    }


def item_key(route_name: str, item: dict[str, Any]) -> str:
    raw = "|".join(
        (
            route_name,
            str(item.get("file_id") or item.get("fid") or ""),
            str(item.get("title") or item.get("file_name") or ""),
            str(item.get("share_url") or ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_state() -> dict[str, Any]:
    return read_json(STATE_PATH, {"version": 1, "published": {}, "runs": []})


def save_run(state: dict[str, Any], summary: dict[str, Any]) -> None:
    state.setdefault("runs", []).append(summary)
    state["runs"] = state["runs"][-30:]
    write_json(STATE_PATH, state)


async def run_quark_route(
    route: dict[str, Any],
    settings: dict[str, Any],
    state: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    from quark_share import QuarkShareManager
    from zsxq_publisher import ZsxqPublisher

    cookie = str(settings.get("quark_cookie") or "")
    source_folder = str(route.get("source_folder") or settings.get("source_folder") or "")
    if not cookie or not source_folder:
        return {"success": False, "reason": "missing quark_cookie or source_folder"}

    quark = QuarkShareManager(cookie)
    if not quark.validate_cookie():
        return {"success": False, "reason": "Quark cookie validation failed"}

    folder_id = quark.find_folder_by_name(source_folder)
    if not folder_id:
        return {"success": False, "reason": f"Quark folder not found: {source_folder}"}

    items = list(quark.scan_folder_for_sharing(folder_id, max_items=100, skip_folders=False))
    pending = [
        item
        for item in items
        if item_key(route["name"], item) not in state.get("published", {})
    ]
    batch_size = max(int(route.get("batch_size") or 0), 5)
    selected = pending[:batch_size]
    result = {
        "success": True,
        "source_folder": source_folder,
        "source_count": len(items),
        "pending_count": len(pending),
        "selected_count": len(selected),
        "published_count": 0,
        "items": [],
    }
    if dry_run or not selected:
        return result

    cookie_file = (SKILL_ROOT / "config" / "zsxq_cookies.json").resolve()
    publisher = ZsxqPublisher(
        headless=True,
        cookie_file=str(cookie_file),
        slow_mo=250,
    )
    await publisher.init()
    try:
        for item in selected:
            title = str(item.get("title") or item.get("file_name") or "untitled")
            file_id = str(item.get("file_id") or "")
            share_info = quark.create_file_share(file_id, title)
            share_url = str((share_info or {}).get("share_url") or "")
            if not share_url:
                result["items"].append(
                    {"title": title, "success": False, "reason": "share failed"}
                )
                continue
            published = await publisher.publish_topic(
                group_id=str(route["group_id"]),
                title=title,
                content=str(route.get("description") or "Automated resource share"),
                share_url=share_url,
                share_pwd=str((share_info or {}).get("share_pwd") or ""),
            )
            result["items"].append({"title": title, "success": published})
            if published:
                state.setdefault("published", {})[item_key(route["name"], item)] = {
                    "route": route["name"],
                    "title": title,
                    "published_at": now_text(),
                }
                result["published_count"] += 1
            time.sleep(3)
    finally:
        await publisher.close()

    result["success"] = result["published_count"] == len(selected)
    return result


def run_once(dry_run: bool = False) -> int:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = LOG_ROOT / f"run-{run_id}.log"
    config = read_json(CONFIG_PATH, {})
    settings = read_json(SETTINGS_PATH, {})
    state = load_state()
    log_line(log_path, f"run_id={run_id} start dry_run={dry_run}")

    checks = preflight(settings, config)
    write_json(LOG_ROOT / f"preflight-{run_id}.json", checks)
    if not checks["success"]:
        log_line(log_path, "preflight=blocked")
        for failure in checks["blocking_failures"]:
            log_line(log_path, f"blocking_failure={failure}")
        summary = {
            "run_id": run_id,
            "finished_at": now_text(),
            "success": False,
            "dry_run": dry_run,
            "status": "blocked_by_preflight",
            "blocking_failures": checks["blocking_failures"],
        }
        write_json(LOG_ROOT / f"run-{run_id}.json", summary)
        save_run(state, summary)
        return 2

    route_results = []
    overall_success = True
    for route in checks["routes"]:
        name = str(route["name"])
        if route.get("source_mode") == "local":
            result = {
                "success": False,
                "reason": "local upload adapter is not configured",
            }
        else:
            try:
                result = asyncio.run(
                    run_quark_route(route, settings, state, dry_run)
                )
            except Exception as exc:
                result = {"success": False, "reason": repr(exc)}
                traceback.print_exc()
        route_results.append({"route": name, **result})
        overall_success = overall_success and bool(result.get("success"))
        log_line(log_path, f"route={name} success={result.get('success')}")

    summary = {
        "run_id": run_id,
        "finished_at": now_text(),
        "success": overall_success,
        "dry_run": dry_run,
        "status": "completed" if overall_success else "completed_with_failures",
        "routes": route_results,
        "log": str(log_path),
    }
    write_json(LOG_ROOT / f"run-{run_id}.json", summary)
    save_run(state, summary)
    log_line(log_path, f"run_finish success={overall_success}")
    return 0 if overall_success else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        result = preflight(
            read_json(SETTINGS_PATH, {}),
            read_json(CONFIG_PATH, {}),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 2
    return run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
