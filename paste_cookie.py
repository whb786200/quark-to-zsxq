#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夸克 Cookie 粘贴诊断 + 入库工具。

用法：
  1) 把从「drive-pc.quark.cn」请求头里复制到的完整 Cookie 字符串，粘贴到本文件同级的
     cookie_paste.txt（或在聊天里发给我，由我写入该文件）；
  2) 运行：python paste_cookie.py
  3) 工具会：① 解析字段 ② 判断是否含登录令牌(cookie=) ③ 实测 API ④ 有效则写入 config 并跑分享计划。

⚠️ 关键：必须是 drive-pc.quark.cn 的 Cookie，不是 pan.quark.cn！
   pan.quark.cn 的 Cookie 只有游客埋点字段，永远 31001 guest。
"""
import os
import sys
import io
import json
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, "config", "settings.json")
COOKIE_FILE = os.path.join(ROOT, "cookie_paste.txt")
DRIVE_URL = "https://drive-pc.quark.cn/1/clouddrive/file/sort"
SESSION_TOKENS = ("cookie", "qhstr", "qhtoken", "kps")


def extract_cookie_from_curl(text):
    """从「Copy as cURL」里抠出 Cookie 字符串。支持 --cookie '...' / -b '...' / -H 'Cookie: ...'。"""
    import re
    # --cookie '...' 或 --cookie "..."
    m = re.search(r"--cookie\s+'([^']*)'", text)
    if not m:
        m = re.search(r'--cookie\s+"([^"]*)"', text)
    if not m:
        m = re.search(r"(?<!\S)-b\s+'([^']*)'", text)
    if not m:
        m = re.search(r"-H\s+'Cookie:\s*([^']*)'", text)
    if not m:
        m = re.search(r'-H\s+"Cookie:\s*([^"]*)"', text)
    if m:
        return m.group(1).strip()
    return ""


def load_pasted():
    if not os.path.exists(COOKIE_FILE):
        return ""
    with open(COOKIE_FILE, "r", encoding="utf-8-sig") as f:
        return f.read().strip()


def field_names(cookie_str):
    out = []
    for p in cookie_str.split(";"):
        p = p.strip()
        if "=" in p:
            out.append(p.split("=", 1)[0].strip())
    return out


def has_session_token(cookie_str):
    names = set(field_names(cookie_str))
    for t in SESSION_TOKENS:
        if t in names:
            # 取该字段值长度判断是否为真实令牌（游客也有 __kps 但很短）
            for p in cookie_str.split(";"):
                p = p.strip()
                if p.startswith(t + "="):
                    val = p.split("=", 1)[1].strip()
                    if len(val) > 30:
                        return True
    return False


def api_valid(cookie_str):
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
        return j.get("code") == 0, j
    except Exception as e:
        return False, {"error": str(e)}


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


def print_guide():
    print("""
────────────────────────────────────────────────────────────
❌ 这份 Cookie 是【游客态】，没有登录令牌(cookie=)。

如何拿到正确的 Cookie（只需一次）：
  1. 在【已登录夸克】的普通浏览器里打开：https://pan.quark.cn
     （就是你能正常看文件的那个网页，drive-pc.quark.cn 直接打开是空白，别用）
  2. 按 F12 → 切到「Network(网络)」标签 → 刷新页面
  3. 在左侧请求列表里找【任意一条 URL 含 drive-pc.quark.cn 的请求】
     （网页看文件时会不断调用它，列表里很多；找不到就点任意一条 pan.quark.cn 请求也行）
  4. 右键那条请求 → Copy → Copy as cURL (bash)
  5. 把整段粘到聊天里发给我（或写入 cookie_paste.txt），我来验证并入库。

⚠️ 也可以只复制「Cookie:」请求头的完整值，但【Copy as cURL 最省事且不易漏字段】。
────────────────────────────────────────────────────────────""")


def main():
    raw = load_pasted()
    if not raw:
        print("[错误] 没找到 cookie_paste.txt，请把 Cookie 或「Copy as cURL」粘贴进去再运行。")
        print_guide()
        return 1

    # 支持两种输入：① 整段 Cookie 字符串 ② 浏览器「Copy as cURL」完整命令
    if raw.lstrip().lower().startswith("curl"):
        cookie_str = extract_cookie_from_curl(raw)
        print("[输入] 识别为 cURL 命令，已从中提取 Cookie")
        if not cookie_str:
            print("[错误] 未能从 cURL 中解析出 Cookie，请确认用的是「Copy as cURL (bash)」。")
            return 1
    else:
        cookie_str = raw

    names = field_names(cookie_str)
    print("== 字段扫描（共 %d 个）==" % len(names))
    for n in names:
        print("  -", n)

    if not has_session_token(cookie_str):
        print("\n[判定] 含登录令牌(cookie/qhstr/qhtoken/kps)?  否 ❌ → 游客态，不可用")
        print_guide()
        return 1

    print("\n[判定] 含登录令牌?  是 ✅")
    print("== 实测 API ==")
    ok, j = api_valid(cookie_str)
    if not ok:
        print("  API 校验未通过：", json.dumps(j, ensure_ascii=False)[:300])
        print_guide()
        return 1

    print("  API 校验通过 ✅ code=0")
    save_cookie_to_config(cookie_str)
    print("[ok] 已写入 config/settings.json 的 quark_cookie 字段")
    run_auto_plan()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[异常]", e)
        sys.exit(2)
