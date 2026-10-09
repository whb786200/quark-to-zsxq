#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用用户粘贴的 Cookie 实测夸克接口，给出确凿证据。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

PASTED = (
    "_UP_A4A_11_=wba3110168ad43cdb6f9d608ec924a33; _UP_D_=pc; "
    "_UP_F7E_8D_=6%2B1AgN%2FzmpQQulaAYtTs7YhsQu%2BwpXo3tB7LcshOFsFlhgFKUTD%2BEW%2BeUwz%2BhTnViMoseJOFmPiNoss70BVBTAs2i70J6G4daUxZLWtdV9tldEfEf9zl6NOT9hgFKXFnZ2TcD1%2F8IxGDQDy34oLa%2BOlXg4gfauZfRUXqOxAXoyOaqvDrBDdT5oIkjKMDRk1%2FOm0qJXeruCswclvHFBht63QKcpHpJNziHFh%2FBabHYoqcmIKQChnGL4InCxl1g1C0s1YxLzJs52lWdoIk19nvWfytP81cJKxfv1GfwBTrR0bS%2FBGt91fGhZMwyZvOKbU%2F8ZkbgrGvmwxqzivluzXqQHrmHUwax9fVlczEGdRq2nJkSi56LgyDrXpsyYdGYA0F4Cj%2Fntr80vkUTca5E0LqLcBEt4UN6jDY; "
    "__pus=83e615e70542064dbbef35126896eecfAAThifTEr4ZIzrdDCc+KJc2WNHfE/kSYb777l/CqdMgd5gMmhqRtDcBCj82gAa75ThaFuBsVF0U0bhBrBItFsXWZ; "
    "__kp=8b7a3d00-b40b-11f1-b7e8-8d12d9fbf34e; __kps=AAScHPgYNdEwDiKX0far3KNS; "
    "__ktd=oyes03f4sRl9tp8zY5CvcQ==; __uid=AAScHPgYNdEwDiKX0far3KNS; "
    "__puus=48d3de7b42eee78886fdb6fa94062c83AARol02EkqBuRKrCzP9XETCOFcs4qFWU4llsBxP3qXMrAlA/N8RYIxqg2n7+BJuQt/ClrdtR75qy8dK4lGfV+VtOaBTbKyn04GFFrH2P0XcQrXM47bHpgPCExa96dfM3LZTAVub+aE3gJsL+26JbTW6phdIvyG8WbWkhfzG6QLNVKKbbbw9YIyGs7JKDYminIjaNBbWJmcT3GrFVkp5Wdvmn; "
    "xlly_s=1; "
    "tfstk=gXrsn4jvHCA_3g6OMCWFV3I9C_mjh9SP1KMYE-KwHcnTHmNITA8NSq5bRSFE6mzZ_xhI9WewbjotctNnXq4Zgfljc-V5L_SP4R2imqCPagWELQqnmjIqDwodrtgkL_SP4RbtImydaryJYWDjHmHtkxIddxHDXm39DMBIHxR9khFYp9Gn3xLvXApdvxHjHmnYMJBInXhxDVFYp9Mm9jH9Y6Mh5fe1ARIA_wTdY5GBDnEIpsczCItjLkMs5beTxnKAKAgswRhC_03sb2emlovDcqyTrSD86CCjikwLXzFRTFlTPxwzl7B2SvubjDGYXgvS9lwbAV4e6FHSffg8XV9PER0YRkiaXsYuLJGtPDzF-1uqf5aoZVQhtSwI_SEsJC1EgzyUX2NRTHNmlrEZvlCdVgRk4b_zME9IrnMIa96BoE0oiGvJUXKTnVHnLuWCdCTmWvDIa96BoE0tKvuPd9O6o; "
    "isg=BBoaoHnpJLsVcKgXADB1afGBa8A8S54lH9OkGySTC614l7rRDtn_NSitZ2MLQRa9"
)

print("== 字段扫描 ==")
names = [p.split("=", 1)[0].strip() for p in PASTED.split(";") if p.strip()]
for n in names:
    print("  -", n)
has_token = any(n in ("cookie", "qhstr", "qhtoken", "kps") for n in names)
print("\n含登录令牌(cookie/qhstr/qhtoken/kps)?", "是 ✅" if has_token else "否 ❌")

print("\n== 实测接口 drive-pc.quark.cn/1/clouddrive/config ==")
headers = {
    "Cookie": PASTED,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://pan.quark.cn/",
}
try:
    r = requests.get("https://drive-pc.quark.cn/1/clouddrive/config", headers=headers, timeout=15)
    print("HTTP", r.status_code)
    try:
        print("JSON:", json.dumps(r.json(), ensure_ascii=False)[:400])
    except Exception:
        print(r.text[:400])
except Exception as e:
    print("请求异常:", e)
