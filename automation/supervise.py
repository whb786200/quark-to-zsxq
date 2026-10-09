#!/usr/bin/env python3
"""Retry a missed nightly start while keeping an audit trail."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
RUNNER = ROOT / "run-nightly.cmd"
LOGS = ROOT / "logs"


def log(message: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LOGS / f"supervisor-{datetime.now():%Y%m%d}.log"
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def today_run_exists() -> bool:
    today = datetime.now().strftime("%Y%m%d")
    return any(LOGS.glob(f"run-{today}-*.json"))


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    start = config.get("window", {}).get("start", "03:00")
    end = config.get("window", {}).get("end", "04:30")
    now = datetime.now()
    start_at = now.replace(
        hour=int(start[:2]), minute=int(start[3:]), second=0, microsecond=0
    )
    end_at = now.replace(
        hour=int(end[:2]), minute=int(end[3:]), second=0, microsecond=0
    )
    if end_at <= start_at:
        end_at += timedelta(days=1)

    log(f"supervisor_start window={start}-{end}")
    while datetime.now() < start_at:
        time.sleep(30)

    launched = False
    while datetime.now() <= end_at:
        if not launched and not today_run_exists():
            log("no run log detected; launching nightly runner")
            subprocess.Popen(
                ["cmd.exe", "/c", str(RUNNER)],
                cwd=str(ROOT.parent),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            launched = True
        time.sleep(300)

    log(f"supervisor_finish launched={launched} run_log_exists={today_run_exists()}")
    return 0 if today_run_exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
