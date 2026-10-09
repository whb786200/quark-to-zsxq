#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

ROOT = "C:/Users/19586/.workbuddy/skills/quark-to-zsxq"
cfg = json.load(open(ROOT + "/config/settings.json", encoding="utf-8-sig"))
ck = cfg.get("quark_cookie", "")
print("cookie len:", len(ck))
pairs = [p.strip() for p in ck.split(";") if p.strip()]
names = [p.split("=", 1)[0] for p in pairs]
print("cookie NAMES:", names)

# 实测两个校验接口
base = {
    "_input_charset": "utf-8",
    "_output_charset": "utf-8",
    "_input_enc": "UTF-8",
    "_output_enc": "UTF-8",
}
headers = {
    "Cookie": ck,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://pan.quark.cn/",
    "Origin": "https://pan.quark.cn",
}

for url in [
    "https://drive-pc.quark.cn/1/clouddrive/config",
    "https://drive-pc.quark.cn/1/clouddrive/file/sort",
]:
    try:
        params = dict(base)
        if "file/sort" in url:
            params.update({
                "pr": "ucpro", "fr": "pc", "uc_param_str": "",
                "pdir_fid": "0", "_page": "1", "_size": "1",
                "_fetch_total": "1", "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,file_name:asc",
            })
        r = requests.get(url, headers=headers, params=params, timeout=15)
        try:
            j = r.json()
            print("GET", url, "->", r.status_code, "code=", j.get("code"), "msg=", j.get("message"))
        except Exception:
            print("GET", url, "->", r.status_code, r.text[:200])
    except Exception as e:
        print("GET", url, "ERR", repr(e)[:200])
