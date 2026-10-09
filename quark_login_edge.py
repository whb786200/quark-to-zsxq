#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夸克网盘登录脚本（持久化上下文版）

核心改进（对齐 QuarkPanTool 思路）：
1. 用 launch_persistent_context 把登录态存进固定 Profile 目录，跨进程/跨天复用；
2. 启动先读缓存 Cookie 并实测校验，有效则【静默免登】直接返回；
3. 仅当缓存失效时才弹 Edge 窗口让你扫码/登录一次；
4. 登录成功把完整 Cookie（含 drive-pc 域 `cookie` 令牌）写入 config/settings.json；
5. 可选 --auto-plan：登录成功后自动跑 daily_quark_plan.py 生成分享文案。
"""
import os
import sys
import json
import time
import io
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, "config", "settings.json")
PROFILE_DIR = os.path.join(ROOT, "edge_login_profile")  # 固定目录 → 登录态持久化
STATUS_FILE = os.path.join(ROOT, "login_status.json")
PAN_URL = "https://pan.quark.cn"
DRIVE_URL = "https://drive-pc.quark.cn/1/clouddrive/file/sort"
WAIT_SECONDS = int(os.environ.get("QUARK_LOGIN_WAIT", "1800"))


def write_status(state, msg=""):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"state": state, "msg": msg, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
    except Exception:
        pass


def has_session_cookie(cookies):
    """真正的登录态 Cookie：夸克会话令牌名为 'cookie'（值较长），兼容 'qhstr'/'qhtoken'/'kps'。
    b-user-id / grey-id / ctoken 等游客也有，不能作为登录依据。"""
    for c in cookies:
        n = c.get("name", "")
        v = c.get("value", "")
        if n in ("cookie", "qhstr", "qhtoken", "kps") and len(v) > 30:
            return True
    return False


def build_cookie_string(cookies):
    parts = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value", "")
        if name and value:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def api_valid(cookie_str):
    """用 Quark 文件列表接口实测 Cookie 是否有效"""
    import requests
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://pan.quark.cn/",
        "Origin": "https://pan.quark.cn",
    }
    params = {
        "_input_charset": "utf-8", "_output_charset": "utf-8",
        "pr": "ucpro", "fr": "pc", "uc_param_str": "",
        "pdir_fid": "0", "_page": "1", "_size": "1",
        "_fetch_total": "1", "_fetch_sub_dirs": "0",
        "_sort": "file_type:asc,file_name:asc",
    }
    try:
        r = requests.get(DRIVE_URL, headers=headers, params=params, timeout=15)
        j = r.json()
        return j.get("code") == 0
    except Exception:
        return False


def save_cookie_to_config(cookie_str):
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = json.load(open(CONFIG_FILE, "r", encoding="utf-8-sig"))
        except Exception:
            cfg = {}
    cfg["quark_cookie"] = cookie_str
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def run_auto_plan():
    """登录成功后自动跑分享计划（扫描+建链接+生成文案）"""
    plan = os.path.join(ROOT, "daily_quark_plan.py")
    if not os.path.exists(plan):
        print("[auto-plan] 找不到 daily_quark_plan.py，跳过")
        return
    cmd = [
        sys.executable, plan,
        "--folder", "自发群",
        "--destination", "工程交流2群（筑界）",
        "--slot", "all", "--limit", "100",
        "--create-shares", "--confirm-share-links", "YES",
    ]
    print("[auto-plan] 运行分享计划：", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, cwd=ROOT)
        print("[auto-plan] 分享计划完成，已生成 message_draft.md")
    except subprocess.CalledProcessError as e:
        print("[auto-plan] 分享计划失败：", e)


def open_login_window_and_wait(p, force_window=False):
    """弹出 Edge 窗口等用户登录，返回 (context, page) 或 None"""
    browser = p.chromium.launch_persistent_context(
        PROFILE_DIR,
        channel="msedge",
        headless=False,
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    )
    context = browser
    page = context.new_page()
    page.goto(PAN_URL, wait_until="domcontentloaded", timeout=60000)
    print("[login] 已打开登录页，请扫码/账号登录…")
    start = time.time()
    logged = False
    while time.time() - start < WAIT_SECONDS:
        time.sleep(3)
        try:
            # 直接用当前 Cookie 实测接口，只要返回 code=0 即视为已登录
            # （不依赖具体令牌字段名，避免漏判）
            cs = build_cookie_string(context.cookies())
            if cs and api_valid(cs):
                logged = True
                break
        except Exception as e:
            print("[login] 轮询异常:", e)
    if not logged:
        write_status("timeout", f"{WAIT_SECONDS}s 内未检测到登录态，请重试。")
        print(f"[login] 超时（{WAIT_SECONDS}s）未登录")
        context.close()
        return None
    # 访问 drive 域，确保会话 Cookie 下发
    try:
        page.goto(DRIVE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
    except Exception:
        pass
    cookie_str = build_cookie_string(context.cookies())
    context.close()
    return cookie_str


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-plan", action="store_true", help="登录成功后自动跑分享计划")
    ap.add_argument("--force", action="store_true", help="忽略缓存，强制弹窗登录")
    args = ap.parse_args()

    write_status("checking", "检查缓存登录态…")
    os.makedirs(PROFILE_DIR, exist_ok=True)

    # 阶段一：headless 读缓存，能静默过就免登
    cached_valid = False
    cached_cookie = ""
    if not args.force:
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    PROFILE_DIR, channel="msedge", headless=True,
                    user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                )
                cookies = ctx.cookies()
                if has_session_cookie(cookies):
                    cand = build_cookie_string(cookies)
                    if api_valid(cand):
                        cached_valid = True
                        cached_cookie = cand
                ctx.close()
        except Exception as e:
            print("[login] 缓存检查异常（将尝试弹窗登录）：", e)

    if cached_valid:
        save_cookie_to_config(cached_cookie)
        write_status("success", f"缓存登录态有效，已静默复用 ({len(cached_cookie)} 字符)")
        print(f"[login] 缓存 Cookie 有效，无需重新登录，已写入 config ({len(cached_cookie)} 字符)")
        if args.auto_plan:
            run_auto_plan()
        return 0

    # 阶段二：缓存失效 → 弹窗登录一次
    write_status("waiting", "缓存失效，请在弹出的 Edge 窗口中登录…")
    with sync_playwright() as p:
        cookie_str = open_login_window_and_wait(p)
        if not cookie_str:
            return 1
        if not api_valid(cookie_str):
            write_status("invalid", "已捕获登录态但 API 校验失败，请重试。")
            print("[login] 捕获到登录态但 API 校验未通过")
            return 1
        save_cookie_to_config(cookie_str)
        write_status("success", f"登录成功且校验通过 ({len(cookie_str)} 字符)")
        print(f"[login] 登录成功并校验通过！Cookie 已写入 config ({len(cookie_str)} 字符)")
        if args.auto_plan:
            run_auto_plan()
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        write_status("error", str(e)[:300])
        print("[login] 异常:", e)
        sys.exit(2)
