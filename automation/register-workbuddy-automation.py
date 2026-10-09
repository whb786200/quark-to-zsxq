#!/usr/bin/env python3
"""Register this skill in WorkBuddy's native automation store.

The helper is intentionally idempotent: rerunning it updates the named task
instead of creating another copy. A SQLite backup is created before mutation.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


WORKBUDDY_HOME = Path(r"C:\Users\19586\.workbuddy")
DB_PATH = WORKBUDDY_HOME / "workbuddy.db"
SKILL_ROOT = WORKBUDDY_HOME / "skills" / "quark-to-zsxq"
AUTOMATION_NAME = "知识星球自动发布（WorkBuddy）"
OWNER_USER_ID = "50d3552b-1c1a-4557-a734-76b24303e9b6"
MODEL_ID = "hy3"
RRULE = "FREQ=DAILY;BYHOUR=3;BYMINUTE=0"


def next_run_at_ms() -> int:
    zone = timezone(timedelta(hours=8))
    now = datetime.now(zone)
    candidate = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return int(candidate.timestamp() * 1000)


def build_prompt() -> str:
    return f"""执行知识星球自动发布 Skill。

工作目录：{SKILL_ROOT}
必须先阅读：
- {SKILL_ROOT / "SKILL.md"}
- {SKILL_ROOT / "automation" / "config.json"}
- {SKILL_ROOT / "automation" / "state.json"}（如果存在）

执行要求：
1. 使用 Asia/Shanghai 时间，发布窗口为每天 03:00-04:30。
2. 先运行 `automation\\run-nightly.cmd --preflight`，必须使用该入口绑定的 WorkBuddy Python 环境。
3. 预检失败时，只记录失败原因并结束，不得假报已发布。
4. 预检通过后运行 `automation\\run-nightly.cmd`，按配置路由执行。
5. 每个路由单次处理不少于 5 个文件或项目，优先批量处理并按 state.json 去重。
6. AI 开源项目和 AI 工程工具/skill 按配置路由发布；本地资料只有在上传适配器真实可用时才发布。
7. 执行结束后检查最新的 automation/logs/run-*.json 和 run-*.log，报告成功数、失败数、阻断原因和日志路径。
8. 不要把“扫描到文件”“生成草稿”或“打开网页”当成发布成功；必须以实际成功结果为准。
"""


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.stem}.backup-{stamp}{DB_PATH.suffix}")
    source = sqlite3.connect(str(DB_PATH))
    target = sqlite3.connect(str(backup_path))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup_path


def register() -> dict[str, object]:
    backup = backup_database()
    now_ms = int(datetime.now().timestamp() * 1000)
    next_ms = next_run_at_ms()
    prompt = build_prompt()
    cwds = json.dumps([str(SKILL_ROOT)], ensure_ascii=False)
    empty_json = "[]"

    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN IMMEDIATE")
        active = con.execute(
            "SELECT id FROM automations WHERE name = ? AND deleted_at IS NULL "
            "ORDER BY created_at ASC",
            (AUTOMATION_NAME,),
        ).fetchall()

        if active:
            automation_id = str(active[0]["id"])
            for duplicate in active[1:]:
                con.execute(
                    "UPDATE automations SET status='PAUSED', deleted_at=?, updated_at=? "
                    "WHERE id=?",
                    (now_ms, now_ms, duplicate["id"]),
                )
        else:
            automation_id = str(uuid.uuid4())

        values = (
            automation_id,
            AUTOMATION_NAME,
            prompt,
            "ACTIVE",
            "recurring",
            next_ms,
            None,
            cwds,
            RRULE,
            None,
            None,
            None,
            MODEL_ID,
            0,
            empty_json,
            0,
            0,
            None,
            OWNER_USER_ID,
            "confirmed",
            "migration",
            None,
            None,
            empty_json,
            None,
            now_ms,
            now_ms,
            None,
            None,
        )
        con.execute(
            """
            INSERT INTO automations (
                id, name, prompt, status, schedule_type, next_run_at, last_run_at,
                cwds, rrule, scheduled_at, valid_from, valid_until, model_id,
                model_is_thinking, skills_json, push_to_wechat, push_to_wecom_bot,
                wecom_bot_source, owner_user_id, owner_status, owner_source,
                expert_id, expert_marketplace, connector_ids_json, permission_mode,
                created_at, updated_at, deleted_at, context_window
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                prompt=excluded.prompt,
                status=excluded.status,
                schedule_type=excluded.schedule_type,
                next_run_at=excluded.next_run_at,
                last_run_at=excluded.last_run_at,
                cwds=excluded.cwds,
                rrule=excluded.rrule,
                scheduled_at=excluded.scheduled_at,
                valid_from=excluded.valid_from,
                valid_until=excluded.valid_until,
                model_id=excluded.model_id,
                model_is_thinking=excluded.model_is_thinking,
                skills_json=excluded.skills_json,
                push_to_wechat=excluded.push_to_wechat,
                push_to_wecom_bot=excluded.push_to_wecom_bot,
                wecom_bot_source=excluded.wecom_bot_source,
                owner_user_id=excluded.owner_user_id,
                owner_status=excluded.owner_status,
                owner_source=excluded.owner_source,
                expert_id=excluded.expert_id,
                expert_marketplace=excluded.expert_marketplace,
                connector_ids_json=excluded.connector_ids_json,
                permission_mode=excluded.permission_mode,
                updated_at=excluded.updated_at,
                deleted_at=excluded.deleted_at,
                context_window=excluded.context_window
            """,
            values,
        )
        con.commit()
    finally:
        con.close()

    return {
        "id": automation_id,
        "name": AUTOMATION_NAME,
        "status": "ACTIVE",
        "rrule": RRULE,
        "next_run_at": next_ms,
        "next_run_local": datetime.fromtimestamp(
            next_ms / 1000, timezone(timedelta(hours=8))
        ).isoformat(),
        "cwd": str(SKILL_ROOT),
        "backup": str(backup),
    }


if __name__ == "__main__":
    print(json.dumps(register(), ensure_ascii=False, indent=2))
