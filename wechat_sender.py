#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat_sender.py — 把夸克分享文案发送到微信群（破卡点B）

后端（--backend）：
  clawbot-http : 直连微信官方 iLink Bot API（https://ilinkai.weixin.qq.com），
                 纯 HTTP/JSON，仅依赖 requests，无需安装额外组件。
  clawbot-cli  : 调用 @herai/wxclawbot-cli（Node≥20），由社区维护、协议细节已处理好，
                 需先 `npm i -g @herai/wxclawbot-cli` 并完成 OpenClaw 登录。

前提（用户需自行完成，本模块只负责"发送"）：
  1. 微信升级到支持 ClawBot 的版本，启用 ClawBot 插件并扫码登录，拿到 token；
  2. Bot 已加入目标群「工程交流2群（筑界）」；
  3. config/settings.json 填入 clawbot_token / clawbot_base_url，
     以及目标群 group_id（不知道 id 可用 --discover 按群名反查）。

注意：ClawBot 频限约 7 条/5 分钟/机器人，触发 ret=-2 会自动退避重试。
"""
import os
import sys
import io
import json
import time
import argparse
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, "config", "settings.json")
DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
RUNS_DIR = os.path.join(ROOT, "runs")


# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# 文案来源
# ----------------------------------------------------------------------------
def latest_draft():
    if not os.path.isdir(RUNS_DIR):
        return None
    candidates = []
    for name in os.listdir(RUNS_DIR):
        dp = os.path.join(RUNS_DIR, name, "message_draft.md")
        if os.path.exists(dp):
            candidates.append(dp)
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def read_draft(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------------------------
# 后端 A：直连 iLink Bot API（HTTP/JSON）
# ----------------------------------------------------------------------------
def _auth_headers(token):
    import base64, struct, random
    uin = base64.b64encode(struct.pack("<I", random.randint(0, 2**32 - 1))).decode()
    return {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": uin,
        "Authorization": f"Bearer {token}",
    }


def http_send_text(base_url, token, chat_id, text, dry_run=False):
    """向 chat_id 发送一条文本。chat_id 为群聊 ID（如 xxx@im.wechat 或群 room id）。"""
    url = f"{base_url.rstrip('/')}/ilink/bot/sendmessage"
    # 依据 wechat-clawbot 协议类型构造；如与你的后台不一致，按 dashboard 调整字段即可。
    payload = {
        "to_user_id": chat_id,
        "group_id": chat_id,
        "message_type": 1,  # USER
        "item_list": [
            {"type": 1, "text_item": {"content": text}}  # TEXT=1
        ],
    }
    if dry_run:
        print(f"[dry-run] POST {url}\n          headers={_auth_headers(token)}\n          body={json.dumps(payload, ensure_ascii=False)}")
        return {"ok": True, "dry_run": True}
    import requests
    r = requests.post(url, headers=_auth_headers(token), json=payload, timeout=20)
    print(f"[http] {r.status_code} {r.text[:300]}")
    try:
        return r.json()
    except Exception:
        return {"ok": False, "raw": r.text}


def http_get_updates(base_url, token, buf="", timeout_ms=35000):
    url = f"{base_url.rstrip('/')}/ilink/bot/getupdates"
    payload = {"get_updates_buf": buf, "base_info": {"channel_version": "1.0.2"}}
    import requests
    r = requests.post(url, headers=_auth_headers(token), json=payload, timeout=timeout_ms / 1000 + 5)
    try:
        return r.json()
    except Exception:
        return {}


def discover_group_id(base_url, token, group_name, rounds=6):
    """从收消息流里按群名反查 group_id。需该群近期有消息流入。"""
    buf = ""
    for _ in range(rounds):
        resp = http_get_updates(base_url, token, buf)
        buf = resp.get("get_updates_buf", buf)
        for m in resp.get("msgs", []):
            gid = m.get("group_id")
            # 群消息里通常带群展示名；不同版本字段不同，宽容匹配
            blob = json.dumps(m, ensure_ascii=False)
            if gid and group_name in blob:
                print(f"[discover] 命中群「{group_name}」-> group_id={gid}")
                return gid
        time.sleep(2)
    print(f"[discover] 未在 {rounds} 轮内找到群「{group_name}」，请确认 bot 在群内且该群近期有消息")
    return None


# ----------------------------------------------------------------------------
# 后端 B：wxclawbot-cli（Node）
# ----------------------------------------------------------------------------
def cli_send_text(text, to_id, dry_run=False):
    cmd = ["wxclawbot", "send", "--text", text]
    if to_id:
        cmd += ["--to", to_id]
    if dry_run:
        cmd += ["--dry-run"]
    print(f"[cli] 执行: {' '.join(cmd)}")
    if dry_run:
        return {"ok": True, "dry_run": True}
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("[cli][err]", proc.stderr)
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"ok": proc.returncode == 0, "raw": proc.stdout}


# ----------------------------------------------------------------------------
# 重试（频限 ret=-2）
# ----------------------------------------------------------------------------
def with_ratelimit_retry(fn, max_retry=3):
    for i in range(max_retry):
        res = fn()
        ok = isinstance(res, dict) and (res.get("ok") or res.get("dry_run"))
        err = str(res)
        if ok:
            return res
        if "ret=-2" in err or "rate" in err.lower():
            wait = 8 * (i + 1)
            print(f"[retry] 触发频限，{wait}s 后重试 ({i+1}/{max_retry})")
            time.sleep(wait)
            continue
        return res
    return res


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="把分享文案发送到微信群（ClawBot/iLink）")
    ap.add_argument("--draft", default=None, help="message_draft.md 路径（默认取 runs/ 最新一份）")
    ap.add_argument("--text", default=None, help="直接指定文本（测试/直发用）")
    ap.add_argument("--backend", choices=["clawbot-http", "clawbot-cli"], default="clawbot-http")
    ap.add_argument("--group-name", default=None, help="目标群名，用于反查 group_id")
    ap.add_argument("--group-id", default=None, help="直接指定群 group_id（优先级最高）")
    ap.add_argument("--discover", action="store_true", help="按群名从收消息流反查 group_id")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要发送的内容，不真正发送")
    args = ap.parse_args()

    cfg = load_config()
    token = cfg.get("clawbot_token", "")
    base_url = cfg.get("clawbot_base_url", DEFAULT_BASE_URL)
    gname = args.group_name or cfg.get("wechat_group") or "工程交流2群（筑界）"

    if not args.dry_run and not token:
        print("[错误] config/settings.json 缺少 clawbot_token，无法发送。请先在微信启用 ClawBot 并填入 token。")
        return 2

    # 解析目标群 ID
    chat_id = args.group_id or cfg.get("wechat_group_id", "")
    if (not chat_id) and (args.discover or cfg.get("wechat_send_enabled")):
        if not token:
            print("[错误] 反查 group_id 需要 clawbot_token")
            return 2
        chat_id = discover_group_id(base_url, token, gname)
        if chat_id and not cfg.get("wechat_group_id"):
            cfg["wechat_group_id"] = chat_id
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f"[ok] 已缓存 group_id={chat_id} 到 config")
    if not chat_id:
        print("[错误] 未解析到目标群 group_id。可加 --group-id <id> 或 --discover 反查。")
        return 2

    # 文案内容
    if args.text:
        text = args.text
    else:
        draft = args.draft or latest_draft()
        if not draft or not os.path.exists(draft):
            print("[错误] 找不到 message_draft.md，请先跑 share_to_group.py 生成。")
            return 2
        text = read_draft(draft)
        print(f"[ok] 读取文案: {draft} ({len(text)} 字符)")

    print(f"[send] -> 群「{gname}」(id={chat_id}) backend={args.backend} dry_run={args.dry_run}")

    if args.backend == "clawbot-http":
        res = with_ratelimit_retry(lambda: http_send_text(base_url, token, chat_id, text, dry_run=args.dry_run))
    else:
        res = with_ratelimit_retry(lambda: cli_send_text(text, chat_id, dry_run=args.dry_run))

    print("[result]", json.dumps(res, ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[异常]", e)
        sys.exit(2)
