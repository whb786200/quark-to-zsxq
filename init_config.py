"""配置向导 - 交互式配置夸克Cookie和知识星球ID"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "settings.json")
DEFAULT_CONFIG = {
    "quark_cookie": "",
    "zsxq_group_id": "",
    "default_expire": 0,
    "default_password": ""
}

def main():
    # 加载已有配置
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        config = {**DEFAULT_CONFIG, **config}
    else:
        config = DEFAULT_CONFIG.copy()

    print()
    print("=" * 50)
    print("  夸克网盘 -> 知识星球 配置向导")
    print("=" * 50)
    
    cookie_status = "[已设置]" if config.get("quark_cookie") else "[空]"
    gid_status = config.get("zsxq_group_id", "") or "[空]"
    print(f"  1. 夸克网盘Cookie: {cookie_status}")
    print(f"  2. 知识星球ID:     {gid_status}")
    print()

    # 输入 Cookie
    current = config.get("quark_cookie", "")
    hint = f"当前: [已设置{len(current)}字符]" if current else "当前: 空"
    val = input(f"请输入夸克网盘Cookie ({hint}, 回车跳过): ").strip()
    if val:
        config["quark_cookie"] = val

    # 输入星球ID
    current_gid = config.get("zsxq_group_id", "")
    hint_gid = f"当前: {current_gid}" if current_gid else "当前: 空"
    val2 = input(f"请输入知识星球ID ({hint_gid}, 回车跳过): ").strip()
    if val2:
        config["zsxq_group_id"] = val2

    # 保存
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print()
    print("✅ 配置已保存到:", CONFIG_FILE)
    print(f"   夸克Cookie: {'[已设置]' if config.get('quark_cookie') else '[空]'}")
    print(f"   星球ID:    {config.get('zsxq_group_id', '') or '[空]'}")

if __name__ == "__main__":
    main()
