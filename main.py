"""
夸克网盘 → 知识星球 自动发布工具 (增强版)
=============================================
功能:
1. 夸克网盘文件/文件夹 → 创建分享链接
2. 夸克文档 → 创建分享链接
3. 自动将分享链接发布到知识星球
4. 扫描文件夹内所有文件 → 批量创建分享链接 (新!)
5. 按名称查找文件夹 → 一键扫描分享 (新!)

使用方式:
    # 单个文件/文件夹分享并发布到星球
    python main.py --file-id <fid> --title "标题" --group-id <星球ID>

    # 文档分享+发布
    python main.py --doc-id <doc_id> --title "方案文档" --group-id <星球ID>

    # ★★★ 扫描文件夹内所有文件, 批量创建分享链接
    python main.py --scan-folder "自发群" --dry-run        # 先预览扫描结果
    python main.py --scan-folder "自发群"                   # 实际执行批量分享

    # ★★★ 用文件夹ID直接扫描
    python main.py --scan-folder 123456789

    # 仅创建分享链接, 不发星球
    python main.py --file-id <fid> --title "资料包" --no-publish

    # 仅发布已有链接到星球
    python main.py --publish-only --url "https://pan.quark.cn/s/xxx" \
                   --title "好资料" --desc "描述" --group-id <星球ID>

    # 列出根目录文件(调试用)
    python main.py --list-files

    # 搜索文件名(调试用)  
    python main.py --search "工程资料"

    # 初始化配置
    python main.py --init-config
"""

import argparse
import json
import os
import sys
import asyncio
from datetime import datetime

from quark_share import QuarkShareManager
from zsxq_publisher import ZsxqPublisher


# ==================== 配置 ====================

DEFAULT_CONFIG = {
    "quark_cookie": "",       # 夸克网盘Cookie (从 pan.quark.cn F12获取)
    "zsxq_group_id": "",      # 知识星球ID (从URL中提取)
    "default_expire": 0,      # 默认有效期(天), 0=永久
    "default_password": "",   # 默认提取密码(空=无密码)
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "settings.json")


def load_config() -> dict:
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置文件"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ==================== 核心流程 ====================

async def share_and_publish(
    file_id: str,
    title: str,
    content: str = "",
    group_id: str = "",
    item_type: str = "file",
    expire_time: int = 0,
    password: str = "",
    no_publish: bool = False,
) -> dict:
    """
    核心流程: 创建分享链接 → 发布到知识星球
    
    :return: {"share_info": {...}, "published": bool}
    """
    config = load_config()
    
    # Step 1: 验证夸克Cookie
    if not config.get("quark_cookie"):
        print("❌ 未配置夸克网盘Cookie! 请先在 config/settings.json 中设置")
        print("   获取方式: 登录 https://pan.quark.cn → F12 → Network → 复制Cookie")
        return {"success": False, "error": "未配置Cookie"}

    quark = QuarkShareManager(config["quark_cookie"])
    
    if not quark.validate_cookie():
        print("❌ 夸克网盘Cookie已失效或无效")
        return {"success": False, "error": "Cookie无效"}

    print(f"\n{'='*60}")
    print(f"📦 步骤1: 创建夸克分享 - {title} ({item_type})")
    print(f"{'='*60}")

    # Step 2: 创建分享链接
    if item_type == "doc":
        share_info = quark.create_doc_share(file_id, title, expire_time or None)
    else:
        share_info = quark.create_file_share(
            file_id, title,
            expire_time=expire_time or None,
            password=password or None,
        )

    if not share_info or not share_info.get("share_url"):
        print("❌ 分享创建失败!")
        return {"success": False, "error": "分享创建失败", "share_info": share_info}

    share_url = share_info.get("share_url", "")
    share_pwd = share_info.get("share_pwd", "")
    print(f"✅ 分享成功! URL: {share_url}")
    if share_pwd:
        print(f"   密码: {share_pwd}")

    result = {
        "success": True,
        "share_info": share_info,
        "published": False,
    }

    # Step 3: 发布到知识星球
    if no_publish:
        print("\n📋 跳过知识星球发布 (--no-publish)")
        return result

    target_group = group_id or config.get("zsxq_group_id", "")
    if not target_group:
        print("\n⚠️ 未指定知识星球ID, 跳过发布")
        print("   可通过参数 --group-id 或配置 zsxq_group_id 设置")
        return result

    print(f"\n{'='*60}")
    print(f"🌍 步骤2: 发布到知识星球 - {target_group}")
    print(f"{'='*60}")

    publisher = ZsxqPublisher(headless=False)
    await publisher.init()
    
    try:
        published = await publisher.publish_topic(
            group_id=target_group,
            title=title,
            content=content or f"分享资源: {title}",
            share_url=share_url,
            share_pwd=share_pwd or "",
        )
        result["published"] = published
        status = "✅" if published else "❌"
        print(f"{status} 发布结果: {'成功' if published else '失败'}")
    finally:
        await publisher.close()

    return result


async def publish_existing_link(
    url: str,
    title: str,
    content: str = "",
    group_id: str = "",
    share_pwd: str = "",
) -> dict:
    """仅发布已有的分享链接到知识星球"""
    config = load_config()
    target_group = group_id or config.get("zsxq_group_id", "")
    
    if not target_group:
        print("❌ 未指定知识星球ID")
        return {"success": False, "error": "未指定星球ID"}

    publisher = ZsxqPublisher(headless=False)
    await publisher.init()
    
    try:
        published = await publisher.publish_topic(
            group_id=target_group,
            title=title,
            content=content,
            share_url=url,
            share_pwd=share_pwd or "",
        )
        return {"success": True, "published": published}
    finally:
        await publisher.close()


async def run_batch(batch_file: str):
    """批量执行任务 (从JSON文件读取)"""
    with open(batch_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    print(f"\n📋 加载了 {len(tasks)} 个批量任务\n")

    results = []
    for i, task in enumerate(tasks):
        print(f"\n{'#'*60}")
        print(f"# 任务 [{i+1}/{len(tasks)}]: {task.get('title', '未命名')}")
        print(f"{'#'*60}")
        
        r = await share_and_publish(
            file_id=task.get("file_id", ""),
            title=task.get("title", ""),
            content=task.get("content", ""),
            item_type=task.get("type", "file"),
            expire_time=task.get("expire_time", 0),
            password=task.get("password", ""),
            no_publish=task.get("no_publish", False),
        )
        
        task["result"] = r
        results.append(task)

    # 输出汇总报告
    success_count = sum(1 for t in results if t.get("result", {}).get("success"))
    pub_count = sum(1 for t in results 
                    if t.get("result", {}).get("published"))
    
    report_file = os.path.join(
        os.path.dirname(batch_file),
        f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 批量执行完成:")
    print(f"   总计: {len(results)} 个任务")
    print(f"   分享成功: {success_count}/{len(results)}")
    print(f"   星球发布: {pub_count}/{len(results)}")
    print(f"   报告已保存: {report_file}")


# ==================== 文件夹扫描 ====================

def scan_folder_and_share(
    folder_name_or_id: str,
    dry_run: bool = False,
    publish: bool = False,
    group_id: str = "",
) -> dict:
    """
    扫描文件夹 → 批量创建分享链接 → (可选)发布到知识星球

    :param folder_name_or_id: 文件夹名称或ID
    :param dry_run: 仅预览不执行
    :param publish: 是否发布到知识星球
    :param group_id: 星球ID
    :return: 扫描+分享结果
    """
    config = load_config()
    if not config.get("quark_cookie"):
        print("❌ 未配置夸克Cookie!")
        return {"success": False, "error": "未配置Cookie"}

    quark = QuarkShareManager(config["quark_cookie"])
    if not quark.validate_cookie():
        print("❌ Cookie已失效!")
        return {"success": False, "error": "Cookie无效"}

    # 扫描+分享
    result = quark.auto_scan_and_share_folder(
        folder_name_or_id=folder_name_or_id,
        expire_time=config.get("default_expire", 0),
        password=config.get("default_password", ""),
        dry_run=dry_run,
    )

    if not result.get("success") or dry_run or not publish:
        return result

    # 发布到知识星球
    share_results = result.get("results", [])
    if not share_results:
        return result

    target_group = group_id or config.get("zsxq_group_id", "")
    if not target_group:
        print("\n⚠️ 未指定星球ID, 跳过发布")
        return result

    print(f"\n{'='*60}")
    print(f"🌍 开始发布到知识星球 ({target_group})")
    print(f"{'='*60}")

    async def _publish_all():
        publisher = ZsxqPublisher(headless=False)
        await publisher.init()
        try:
            for r in share_results:
                if not r.get("success"):
                    continue
                print(f"\n[发布] {r['title']}")
                await publisher.publish_topic(
                    group_id=target_group,
                    title=r["title"],
                    content=f"分享资源: {r['file_name']}",
                    share_url=r["share_url"],
                    share_pwd=r.get("share_pwd", ""),
                )
                await asyncio.sleep(3)
        finally:
            await publisher.close()

    asyncio.run(_publish_all())
    return result


# ==================== 文件列表/搜索(调试) ====================

def list_files(folder_id: str = "0"):
    """列出指定文件夹的文件"""
    config = load_config()
    if not config.get("quark_cookie"):
        print("[ERROR] 未配置Cookie")
        return

    quark = QuarkShareManager(config["quark_cookie"])
    if not quark.validate_cookie():
        print("[ERROR] Cookie已失效")
        return

    files = quark.get_file_list(folder_id)
    if not files:
        print("文件夹为空")
        return

    print(f"\n共 {len(files)} 个项目:\n")
    print(f"{'类型':<6} {'文件名':<40} {'大小':<12} {'fid'}")
    print("-" * 90)
    for f in files:
        ftype = "[DIR]" if f.get("file_type") == "folder" else "[FILE]"
        fname = f.get("file_name", "")
        size = f.get("size", 0)
        if size > 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f}MB"
        elif size > 1024:
            size_str = f"{size // 1024}KB"
        else:
            size_str = f"{size}B"
        fid = f.get("fid", "")
        print(f"{ftype:<6} {fname:<40} {size_str:<12} {fid}")


def search_files(keyword: str):
    """搜索文件"""
    config = load_config()
    if not config.get("quark_cookie"):
        print("[ERROR] 未配置Cookie")
        return

    quark = QuarkShareManager(config["quark_cookie"])
    if not quark.validate_cookie():
        print("[ERROR] Cookie已失效")
        return

    results = quark.search_files(keyword)
    if not results:
        print(f"未找到含 '{keyword}' 的文件")
        return

    print(f"\n搜索 '{keyword}' 找到 {len(results)} 个结果:\n")
    for f in results:
        ftype = "[DIR]" if f.get("file_type") == "folder" else "[FILE]"
        print(f"  {ftype} {f.get('file_name', '')} (fid={f.get('fid', '')})")


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="夸克网盘→知识星球 自动发布工具 (增强版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单个文件分享+发布
  python main.py --file-id 123456789 --title "工程资料合集" --group-id 1234567

  # 文档分享+发布
  python main.py --doc-id abc123 --title "施工方案文档" --group-id 1234567

  # ★ 扫描文件夹(预览)
  python main.py --scan-folder "自发群" --dry-run

  # ★ 扫描文件夹+分享+发布星球
  python main.py --scan-folder "自发群" --publish

  # 仅分享不发星球
  python main.py --file-id 123456789 --title "资料包" --no-publish

  # 列出根目录文件
  python main.py --list-files

  # 搜索文件
  python main.py --search "工程资料"

  # 初始化配置
  python main.py --init-config
""",
    )

    # 核心参数
    parser.add_argument("--file-id", help="夸克网盘文件/文件夹 ID (fid)")
    parser.add_argument("--doc-id", help="夸克文档 ID")
    parser.add_argument("--title", default="", help="分享/发布标题 (scan-folder可省略)")
    parser.add_argument("--content", default="", help="正文内容(可选)")
    parser.add_argument("--group-id", help="知识星球 ID")

    # 分享选项
    parser.add_argument("--expire-time", type=int, default=0, help="分享有效期(天), 0=永久")
    parser.add_argument("--password", default="", help="提取密码(空=无密码)")

    # 模式控制
    parser.add_argument("--no-publish", action="store_true", help="仅创建分享链接, 不发布到星球")
    parser.add_argument("--publish-only", action="store_true", help="仅发布已有链接到星球")
    parser.add_argument("--url", help="已有的分享链接 (配合 --publish-only 使用)")

    # ★ 新功能: 文件夹扫描
    parser.add_argument("--scan-folder", metavar="NAME_OR_ID",
                        help="扫描文件夹(按名称模糊匹配或直接传ID), 批量创建分享链接")
    parser.add_argument("--dry-run", action="store_true",
                        help="配合 --scan-folder 使用, 仅预览不实际创建分享")
    parser.add_argument("--publish", action="store_true",
                        help="配合 --scan-folder 使用, 分享后自动发布到知识星球")

    # ★ 新功能: 文件列表/搜索
    parser.add_argument("--list-files", nargs="?", const="0", metavar="FOLDER_ID",
                        help="列出文件夹内容 (默认根目录)")
    parser.add_argument("--search", metavar="KEYWORD",
                        help="搜索文件名")

    # 批量模式
    parser.add_argument("--batch", help="批量任务JSON文件路径")

    # 配置管理
    parser.add_argument("--init-config", action="store_true", help="初始化/更新配置文件")

    args = parser.parse_args()

    # 初始化配置
    if args.init_config:
        config = load_config()
        print("\n🔧 配置初始化向导\n")
        cookie = input(f"夸克网盘Cookie [当前: {'已设置' if config['quark_cookie'] else '空'}]: ").strip()
        if cookie:
            config["quark_cookie"] = cookie
        
        gid = input(f"知识星球ID [当前: {config.get('zsxq_group_id', '')}]: ").strip()
        if gid:
            config["zsxq_group_id"] = gid
        
        save_config(config)
        print(f"\n✅ 配置已保存到 {CONFIG_FILE}")
        return

    # 列出文件
    if args.list_files is not None:
        list_files(args.list_files)
        return

    # 搜索文件
    if args.search:
        search_files(args.search)
        return

    # 文件夹扫描模式
    if args.scan_folder:
        scan_folder_and_share(
            folder_name_or_id=args.scan_folder,
            dry_run=args.dry_run,
            publish=args.publish,
            group_id=args.group_id or "",
        )
        return

    # 批量模式
    if args.batch:
        asyncio.run(run_batch(args.batch))
        return

    # 仅发布模式
    if args.publish_only:
        if not args.url:
            print("❌ --publish-only 需要 --url 参数")
            return
        asyncio.run(publish_existing_link(
            url=args.url,
            title=args.title,
            content=args.content,
            group_id=args.group_id,
        ))
        return

    # 单个任务模式
    file_id = args.doc_id or args.file_id
    if not file_id:
        print("❌ 需要指定 --file-id / --doc-id / --scan-folder / --list-files / --search 之一")
        parser.print_help()
        return

    if not args.title:
        print("❌ 单个分享模式需要 --title 参数")
        return

    item_type = "doc" if args.doc_id else "file"
    
    asyncio.run(share_and_publish(
        file_id=file_id,
        title=args.title,
        content=args.content,
        group_id=args.group_id or "",
        item_type=item_type,
        expire_time=args.expire_time,
        password=args.password,
        no_publish=args.no_publish,
    ))


if __name__ == "__main__":
    main()
