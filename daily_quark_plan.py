"""
Daily Quark share preparation plan.

Default mode is read-only: validate Quark access, scan the source folder, split the
daily target across time slots, and write a manifest plus copy-ready message drafts.
Creating cloud share links is opt-in and requires an explicit confirmation flag.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any

from quark_share import QuarkShareManager


ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config" / "settings.json"
DEFAULT_FOLDER = "自发群"
DEFAULT_DESTINATION = "工程交流2群（筑界）"
DEFAULT_LIMIT = 100

SLOTS = {
    "noon": {"label": "中午", "window": "12:30-14:00"},
    "night": {"label": "晚上", "window": "21:00-24:00"},
}


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Missing config: {CONFIG_FILE}")
    with CONFIG_FILE.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def resolve_slot(value: str, now: datetime | None = None) -> str:
    if value != "auto":
        return value

    now = now or datetime.now()
    current = now.time()
    if dt_time(12, 30) <= current < dt_time(14, 0):
        return "noon"
    if dt_time(21, 0) <= current <= dt_time(23, 59, 59):
        return "night"
    if current < dt_time(12, 30):
        return "noon"
    return "night"


def make_output_dir(base: Path, slot: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / f"{stamp}_{slot}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def resolve_folder_id(quark: QuarkShareManager, folder: str) -> tuple[str, dict[str, Any] | None]:
    if folder.isdigit() or len(folder) >= 20:
        folder_id = folder
    else:
        folder_id = quark.find_folder_by_name(folder)
        if not folder_id:
            raise RuntimeError(f"Folder not found: {folder}")

    folder_info = quark.get_file_info(folder_id)
    return folder_id, folder_info


def scan_source_files(
    quark: QuarkShareManager,
    folder_id: str,
    max_items: int,
    include_folders: bool,
) -> list[dict[str, Any]]:
    items = list(
        quark.scan_folder_for_sharing(
            folder_id,
            max_items=max_items,
            skip_folders=not include_folders,
        )
    )
    return [item for item in items if item.get("file_id")]


def select_items(items: list[dict[str, Any]], slot: str, limit: int) -> list[dict[str, Any]]:
    limited = items[:limit]
    if slot == "all":
        return limited

    half = math.ceil(limit / 2)
    if slot == "noon":
        return limited[:half]
    if slot == "night":
        return limited[half:limit]
    raise ValueError(f"Unsupported slot: {slot}")


def create_share_links(
    quark: QuarkShareManager,
    items: list[dict[str, Any]],
    expire_time: int,
    password: str,
    delay_seconds: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        title = item.get("title") or item.get("file_name") or item.get("file_id")
        print(f"[share] {index}/{len(items)} {title}")
        if item.get("type") == "doc":
            share_info = quark.create_doc_share(item["file_id"], title, expire_time or None)
        else:
            share_info = quark.create_file_share(
                item["file_id"],
                title,
                expire_time=expire_time or None,
                password=password or None,
            )

        results.append(
            {
                **item,
                "share_url": (share_info or {}).get("share_url", ""),
                "share_pwd": (share_info or {}).get("share_pwd", ""),
                "share_success": bool((share_info or {}).get("share_url")),
            }
        )
        if index < len(items):
            time.sleep(max(delay_seconds, 0))
    return results


def file_size_label(size: int | None) -> str:
    size = int(size or 0)
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def build_markdown(
    manifest: dict[str, Any],
    destination: str,
    slot: str,
    items: list[dict[str, Any]],
) -> str:
    slot_info = SLOTS.get(slot, {"label": "全天", "window": "all"})
    lines = [
        f"# {manifest['date']} {slot_info['label']}共享文件准备清单",
        "",
        f"- 目标群: {destination}",
        f"- 时间段: {slot_info['window']}",
        f"- 文件数: {len(items)}",
        f"- 来源文件夹: {manifest.get('folder_name') or manifest.get('folder_id')}",
        "",
        "## 发送文案",
        "",
        f"今日{slot_info['label']}工程资料共享清单如下，共 {len(items)} 个文件。",
        "请按清单核对后手动发送或复制分享链接。",
        "",
        "## 文件清单",
        "",
    ]

    for index, item in enumerate(items, start=1):
        name = item.get("file_name") or item.get("title") or item.get("file_id")
        lines.append(f"{index}. {name} ({file_size_label(item.get('file_size'))})")
        share_url = item.get("share_url")
        if share_url:
            lines.append(f"   链接: {share_url}")
            if item.get("share_pwd"):
                lines.append(f"   提取码: {item['share_pwd']}")

    lines.append("")
    return "\n".join(lines)


def write_outputs(
    manifest: dict[str, Any],
    items: list[dict[str, Any]],
    output_dir: Path,
    destination: str,
    slot: str,
) -> tuple[Path, Path]:
    manifest_path = output_dir / "manifest.json"
    markdown_path = output_dir / "message_draft.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(
        build_markdown(manifest, destination, slot, items),
        encoding="utf-8",
    )
    return manifest_path, markdown_path


def retry_manifest(args: argparse.Namespace, quark: QuarkShareManager) -> int:
    source_path = Path(args.retry_manifest)
    if not source_path.exists():
        print(f"[error] retry manifest not found: {source_path}")
        return 5

    source = json.loads(source_path.read_text(encoding="utf-8"))
    original_items = source.get("items", [])
    failed_items = [
        item for item in original_items
        if not item.get("share_success") and not item.get("share_url")
    ]
    if not failed_items:
        print("[ok] no failed share items to retry")
        return 0

    if args.confirm_share_links != "YES":
        print("[error] --retry-manifest requires --confirm-share-links YES")
        return 4

    print(f"[retry] retrying failed share items: {len(failed_items)}")
    retried = create_share_links(
        quark,
        failed_items,
        expire_time=args.expire_time,
        password=args.password,
        delay_seconds=args.share_delay,
    )
    retried_by_id = {item.get("file_id"): item for item in retried}
    merged_items = [
        retried_by_id.get(item.get("file_id"), item)
        if not item.get("share_success") and not item.get("share_url")
        else item
        for item in original_items
    ]

    slot = source.get("slot") or resolve_slot(args.slot)
    destination = args.destination or source.get("destination", DEFAULT_DESTINATION)
    out_dir = make_output_dir(Path(args.output_dir), f"{slot}_retry")
    manifest = {
        **source,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "retry_of": str(source_path),
        "retry_failed_count": len(failed_items),
        "retry_success_count": sum(1 for item in retried if item.get("share_success")),
        "selected_file_count": len(merged_items),
        "create_shares": True,
        "items": merged_items,
    }
    manifest_path, markdown_path = write_outputs(manifest, merged_items, out_dir, destination, slot)
    print("[ok] retry manifest generated")
    print(f"  retried: {len(failed_items)}")
    print(f"  retry successes: {manifest['retry_success_count']}")
    print(f"  total successes: {sum(1 for item in merged_items if item.get('share_success'))}/{len(merged_items)}")
    print(f"  manifest: {manifest_path}")
    print(f"  draft: {markdown_path}")
    return 0


def run_plan(args: argparse.Namespace) -> int:
    slot = resolve_slot(args.slot)
    config = load_config()
    cookie = config.get("quark_cookie", "")
    if not cookie:
        print("[error] config/settings.json has no quark_cookie")
        return 2

    quark = QuarkShareManager(cookie)
    if args.validate_cookie:
        print("[check] validating Quark cookie...")
        if not quark.validate_cookie():
            print("[error] Quark cookie is invalid or expired")
            return 3
        print("[ok] Quark cookie is valid")

    if args.retry_manifest:
        return retry_manifest(args, quark)

    folder_id, folder_info = resolve_folder_id(quark, args.folder)
    folder_name = (folder_info or {}).get("file_name", args.folder)
    scan_limit = args.offset + args.limit
    files = scan_source_files(quark, folder_id, scan_limit, include_folders=not args.skip_folders)
    if args.offset:
        files = files[args.offset:]
    selected = select_items(files, slot, args.limit)

    if args.min_count and len(files) < args.min_count:
        print(f"[warn] source folder only has {len(files)} files, below requested {args.min_count}")

    out_dir = make_output_dir(Path(args.output_dir), slot)
    if args.create_shares:
        if args.confirm_share_links != "YES":
            print("[error] --create-shares requires --confirm-share-links YES")
            return 4
        selected = create_share_links(
            quark,
            selected,
            expire_time=args.expire_time,
            password=args.password,
            delay_seconds=args.share_delay,
        )

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "slot": slot,
        "slot_window": SLOTS.get(slot, {"window": "all"})["window"],
        "destination": args.destination,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "source_file_count": len(files),
        "selected_file_count": len(selected),
        "limit": args.limit,
        "offset": args.offset,
        "create_shares": bool(args.create_shares),
        "items": selected,
    }

    manifest_path, markdown_path = write_outputs(manifest, selected, out_dir, args.destination, slot)

    print("[ok] daily plan generated")
    print(f"  folder: {folder_name} ({folder_id})")
    print(f"  source files: {len(files)}")
    print(f"  selected files: {len(selected)}")
    print(f"  slot: {slot} ({manifest['slot_window']})")
    print(f"  manifest: {manifest_path}")
    print(f"  draft: {markdown_path}")
    if not args.create_shares:
        print("  mode: read-only preparation; no share links were created")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare daily Quark file sharing plan without automatic group sending.",
    )
    parser.add_argument("--folder", default=DEFAULT_FOLDER, help="Quark folder name or folder id")
    parser.add_argument("--destination", default=DEFAULT_DESTINATION, help="Human-readable target group label")
    parser.add_argument("--slot", choices=["auto", "noon", "night", "all"], default="auto")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Daily maximum file count to select")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many source items before selecting")
    parser.add_argument("--min-count", type=int, default=DEFAULT_LIMIT, help="Warn if source file count is below this")
    parser.add_argument("--output-dir", default=str(ROOT / "runs"), help="Directory for generated manifests")
    parser.add_argument("--validate-cookie", action="store_true", default=True)
    parser.add_argument("--create-shares", action="store_true", help="Actually create Quark share links")
    parser.add_argument("--confirm-share-links", default="", help="Must be YES when --create-shares is used")
    parser.add_argument("--expire-time", type=int, default=0, help="Share expiry in days; 0 means permanent")
    parser.add_argument("--password", default="", help="Optional extraction password")
    parser.add_argument("--share-delay", type=float, default=3.0, help="Delay between share-link creation requests")
    parser.add_argument("--skip-folders", action="store_true", help="Exclude folders from the prepared list")
    parser.add_argument("--retry-manifest", default="", help="Retry failed share-link items from an existing manifest")

    args = parser.parse_args()
    raise SystemExit(run_plan(args))


if __name__ == "__main__":
    main()
