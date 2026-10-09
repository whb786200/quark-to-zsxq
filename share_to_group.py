#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键生成「夸克网盘 -> 工程交流2群（筑界）」分享文案。
流程：校验 Cookie -> 扫描「自发群」文件夹 -> 创建永久分享链接 -> 生成可复制的群发文案(message_draft.md)。
注意：本环境没有可用的微信群发通道，只生成 copy-ready 文案，由用户手动粘贴到群。
"""
import os
import sys
import io
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))
PLANNER = os.path.join(ROOT, "daily_quark_plan.py")
VENV_PY = "C:/Users/19586/.workbuddy/binaries/python/envs/default/Scripts/python.exe"


def main():
    send_wechat = "--send-wechat" in sys.argv
    dry_run = "--dry-run" in sys.argv
    if not os.path.exists(VENV_PY):
        print("[错误] 虚拟环境 python 不存在:", VENV_PY)
        return 1
    # 默认：全天、最多100个、创建真实分享链接
    cmd = [
        VENV_PY, PLANNER,
        "--folder", "自发群",
        "--destination", "工程交流2群（筑界）",
        "--slot", "all",
        "--limit", "100",
        "--create-shares",
        "--confirm-share-links", "YES",
        "--output-dir", os.path.join(ROOT, "runs"),
    ]
    print("[run] 执行:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        return proc.returncode
    # 可选：生成文案后直接通过 ClawBot 发到微信群（破卡点B）
    if send_wechat:
        print("[run] 文案已生成，调用 wechat_sender 发送到群…")
        send_cmd = [VENV_PY, os.path.join(ROOT, "wechat_sender.py")]
        if dry_run:
            send_cmd.append("--dry-run")
        subprocess.run(send_cmd, cwd=ROOT)
    else:
        print("[tip] 未加 --send-wechat，仅生成文案。需要自动发群时加 --send-wechat（需先配置 ClawBot）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
