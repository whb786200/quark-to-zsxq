"""
夸克网盘分享模块 - 增强版
========================================
功能:
1. 夸克网盘文件/文件夹分享链接创建
2. 夸克文档分享链接创建
3. 文件列表获取 & 文件夹扫描（支持分页自动翻页）
4. 搜索文件 / 获取文件信息
5. 异步任务轮询（完善异步分享的 share_id 获取）
6. 自发群文件夹批量扫描+分享（一键扫描文件夹内所有可转发文件）
基于夸克 PC 端 API (drive-pc.quark.cn)
"""

import json
import time
import requests
from typing import Optional, List, Dict, Generator


class QuarkShareManager:
    """夸克网盘分享管理器 - 创建分享链接、查询分享列表"""

    def __init__(self, cookie: str):
        self.cookie = cookie.strip()
        self.base_params = {
            "_input_charset": "utf-8",
            "_output_charset": "utf-8",
            "_input_enc": "UTF-8",
            "_output_enc": "UTF-8",
        }
        self.headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://pan.quark.cn/',
            'Origin': 'https://pan.quark.cn',
            'Sec-Fetch-Site': 'same-site',
        }

    # ==================== 文件/文件夹分享 ====================

    def create_file_share(
        self,
        file_id: str,
        title: str,
        expire_time: Optional[int] = None,
        password: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        为文件或文件夹创建分享链接

        :param file_id: 文件或文件夹ID (fid)
        :param title: 分享标题
        :param expire_time: 有效期(天), None/0=永久, 正整数=天数
        :param password: 提取密码, 可选
        :return: {"share_url": "...", "share_pwd": "..."} 或 None
        """
        create_url = 'https://drive-pc.quark.cn/1/clouddrive/share'
        params = self._pc_params()

        # 构建请求体
        create_data = {
            "fid_list": [file_id],
            "title": title,
            "url_type": 1,
            "expired_type": 1,   # 1=永久
            "expire_time": 0,
        }

        if expire_time and isinstance(expire_time, int) and expire_time > 0:
            create_data["expired_type"] = 2
            create_data["expire_time"] = expire_time * 86400

        if password:
            create_data["password"] = password

        try:
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            resp = requests.post(create_url, headers=headers, params=params, json=create_data, timeout=30)
            if resp.status_code >= 400:
                print(f"[夸克] 创建分享失败: http={resp.status_code} {self._response_message(resp)}")
                return None
            result = resp.json()

            if result.get('code') != 0:
                print(f"[夸克] 创建分享失败: {result.get('message', '未知错误')}")
                return None

            # 获取 share_id (支持同步和异步两种模式)
            share_id = self._extract_share_id(result)
            if not share_id:
                return None

            # 用 share_id 获取完整的分享URL和密码
            share_info = self._get_share_url(share_id)
            if share_info and share_info.get('share_url'):
                print(f"[夸克] 分享创建成功! URL: {share_info.get('share_url')}")
                return share_info
            else:
                print(f"[夸克] Share ID获取成功({share_id})，但获取详情失败")
                return {"share_id": share_id}

        except Exception as e:
            print(f"[夸克] 创建分享异常: {e}")
            return None

    # ==================== 文档分享 ====================

    def create_doc_share(
        self,
        doc_id: str,
        title: str,
        expire_time: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        为夸克文档创建分享链接

        :param doc_id: 文档ID
        :param title: 分享标题
        :param expire_time: 有效期(天)
        :return: {"share_url": "...", ...} 或 None
        """
        try:
            # 夸克文档分享接口
            url = 'https://doc-api.quark.cn/api/doc/share/create'
            params = self.base_params.copy()
            data = {
                "doc_id": doc_id,
                "title": title,
                "url_type": 1,
                "expired_type": 1,
                "expire_time": 0,
            }
            if expire_time and isinstance(expire_time, int) and expire_time > 0:
                data["expired_type"] = 2
                data["expire_time"] = expire_time * 86400

            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            headers['Referer'] = 'https://pan.quark.cn/doc/'
            resp = requests.post(url, headers=headers, params=params, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            if result.get('code') == 0:
                share_data = result.get('data', {})
                share_url = share_data.get('share_url', '')
                if share_url:
                    print(f"[夸克文档] 分享成功: {share_url}")
                    return {"share_url": share_url, **share_data}
            
            # 如果文档专用接口失败, 尝试用通用分享接口
            print(f"[夸克文档] 专用接口失败, 尝试通用方式: {result.get('message')}")
            return self.create_file_share(doc_id, title, expire_time)

        except Exception as e:
            print(f"[夸克文档] 分享异常: {e}, 尝试通用方式")
            return self.create_file_share(doc_id, title, expire_time)

    # ==================== 批量分享 ====================

    def batch_create_shares(self, items: List[Dict]) -> List[Dict]:
        """
        批量创建分享链接
        
        :param items: [{"file_id": "...", "title": "...", "type": "file|doc", ...}]
        :return: 每个item的分享结果列表
        """
        results = []
        for i, item in enumerate(items):
            print(f"\n--- [{i+1}/{len(items)}] 分享: {item.get('title', '')} ---")
            item_type = item.get("type", "file")
            file_id = item.get("file_id")
            title = item.get("title", "")
            expire = item.get("expire_time")
            password = item.get("password")

            if item_type == "doc":
                info = self.create_doc_share(file_id, title, expire)
            else:
                info = self.create_file_share(file_id, title, expire, password)

            results.append({
                "item": item,
                "success": info is not None,
                "share_info": info or {},
            })

            # 避免请求过快
            time.sleep(1)

        # 输出汇总
        success_count = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"批量分享完成: {success_count}/{len(results)} 成功")
        for r in results:
            status = "✅" if r["success"] else "❌"
            url = r.get("share_info", {}).get("share_url", "失败")
            print(f"  {status} {r['item'].get('title', '')}: {url}")

        return results

    # ==================== 内部方法 ====================

    def _extract_share_id(self, result: Dict) -> Optional[str]:
        """从创建响应中提取 share_id"""
        task_sync = result.get('data', {}).get('task_sync')
        
        if task_sync:
            # 同步模式
            task_resp = result.get('data', {}).get('task_resp', {})
            if task_resp.get('code') == 0:
                return task_resp.get('data', {}).get('share_id')
            else:
                print(f"[夸克] 同步创建失败: {task_resp.get('message')}")
                return None
        else:
            # 异步模式 - 需要轮询
            task_id = result.get('data', {}).get('task_id')
            if not task_id:
                print("[夸克] 响应中无 task_id 和同步结果")
                return None
            
            print(f"[夸克] 异步任务已提交: {task_id}, 开始轮询...")
            return self._poll_async_task(task_id)

    def _poll_async_task(self, task_id: str, max_retries: int = 20, interval: float = 1.5) -> Optional[str]:
        """
        轮询异步分享任务，直到获取 share_id

        :param task_id: 异步任务ID
        :param max_retries: 最大重试次数 (默认20次, 约30秒)
        :param interval: 每次轮询间隔(秒)
        :return: share_id 或 None(超时/失败)
        """
        import requests as _req
        url = "https://drive-pc.quark.cn/1/clouddrive/task"
        params = {
            **self._pc_params(),
            "task_id": task_id,
        }
        headers = self.headers.copy()

        for i in range(max_retries):
            try:
                resp = _req.get(url, headers=headers, params=params, timeout=10)
                if resp.status_code >= 400:
                    print(f"[夸克-异步] 轮询失败: http={resp.status_code} {self._response_message(resp)}")
                    time.sleep(interval)
                    continue
                result = resp.json()

                if result.get("code") != 0:
                    print(f"[夸克-异步] 轮询第{i+1}次: {result.get('message', '')}")
                    time.sleep(interval)
                    continue

                task_data = result.get("data", {})
                status = task_data.get("status", "")
                
                if status in ("completed", "done", 2):
                    share_id = task_data.get("share_id") or task_data.get("data", {}).get("share_id")
                    if share_id:
                        print(f"[夸克-异步] 任务完成! share_id={share_id}")
                        return share_id
                
                elif status == "failed":
                    err_msg = task_data.get("message", "未知错误")
                    print(f"[夸克-异步] 任务失败: {err_msg}")
                    return None

                # 仍在处理中
                if (i + 1) % 5 == 0 or i < 3:
                    print(f"[夸克-异步] 等待中... ({i+1}/{max_retries})")

            except Exception as e:
                print(f"[夸克-异步] 轮询异常(第{i+1}次): {e}")

            time.sleep(interval)

        print("[夸克-异步] 轮询超时")
        return None

    def _get_share_url(self, share_id: str) -> Optional[Dict]:
        """根据 share_id 获取完整分享信息"""
        url = 'https://drive-pc.quark.cn/1/clouddrive/share/password'
        params = self._pc_params()
        data = {"share_id": share_id}
        try:
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            resp = requests.post(url, headers=headers, params=params, json=data, timeout=15)
            if resp.status_code >= 400:
                print(f"[夸克] 获取分享详情失败: http={resp.status_code} {self._response_message(resp)}")
                return {}
            result = resp.json()
            if result.get('code') == 0:
                return result.get('data', {})
            else:
                print(f"[夸克] 获取分享详情失败: code={result.get('code')}")
                return {}
        except Exception as e:
            print(f"[夸克] 获取分享详情异常: {e}")
            return {}

    def _pc_params(self) -> Dict:
        params = self.base_params.copy()
        params.update({
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
        })
        return params

    @staticmethod
    def _response_message(response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                return f"code={data.get('code')} message={data.get('message') or data.get('msg') or ''}".strip()
        except Exception:
            pass
        content_type = response.headers.get("content-type", "")
        return f"content-type={content_type}"

    # ==================== 文件管理 ====================

    def get_file_list(
        self,
        folder_id: str = "0",
        page_size: int = 50,
        sort_by: str = "file_type:asc,file_name:asc",
        max_items: Optional[int] = None,
    ) -> List[Dict]:
        """
        获取文件夹内的文件列表（自动翻页获取全部）

        :param folder_id: 文件夹ID, '0' 或 'root' 表示根目录
        :param page_size: 每页数量 (默认50)
        :param sort_by: 排序方式, 如 'file_name:asc', 'updated_at:desc'
        :return: 文件列表, 每个 item 包含 fid, file_name, file_type, size 等
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/file/sort"
        all_files = []
        page = 1
        total = None

        # 根目录统一用 0
        pdir_fid = "0" if folder_id in ("0", "root", "") else folder_id

        while True:
            params = {
                **self.base_params,
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": pdir_fid,
                "_page": str(page),
                "_size": str(page_size),
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": sort_by,
            }
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=15)
                resp.raise_for_status()
                result = resp.json()

                if result.get("code") != 0:
                    print(f"[夸克] 获取文件列表失败: {result.get('message')}")
                    break

                current_files = result.get("data", {}).get("list", [])
                if not current_files:
                    break

                all_files.extend(current_files)
                if max_items is not None and len(all_files) >= max_items:
                    return all_files[:max_items]

                metadata = result.get("data", {}).get("metadata", {})
                if total is None:
                    total = metadata.get("_total")

                if total is not None and len(all_files) >= total:
                    break

                page += 1
            except Exception as e:
                print(f"[夸克] 获取文件列表异常(第{page}页): {e}")
                break

        return all_files

    def get_folder_list(self, parent_id: str = "0") -> List[Dict]:
        """获取指定目录下的所有子文件夹"""
        files = self.get_file_list(parent_id)
        return [f for f in files if f.get("file_type") == "folder" or f.get("dir") is True]

    def search_files(self, keyword: str, folder_id: str = "0") -> List[Dict]:
        """在指定文件夹中搜索文件"""
        url = "https://drive-pc.quark.cn/1/clouddrive/file/search"
        pdir_fid = "0" if folder_id in ("0", "root", "") else folder_id
        params = {
            **self.base_params,
            "pr": "ucpro",
            "fr": "pc",
            "pdir_fid": pdir_fid,
            "query": keyword,
        }
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {}).get("list", [])
        except Exception as e:
            print(f"[夸克] 搜索文件异常: {e}")
        return []

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """获取单个文件的详细信息"""
        url = "https://drive-pc.quark.cn/1/clouddrive/file/info"
        params = {**self.base_params, "fid": file_id}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data")
        except Exception as e:
            print(f"[夸克] 获取文件信息异常: {e}")
        return None

    def scan_folder_for_sharing(
        self,
        folder_id: str = "0",
        title_prefix: str = "",
        skip_folders: bool = True,
        max_items: Optional[int] = None,
    ) -> Generator[Dict, None, None]:
        """
        扫描文件夹内所有可分享的文件，逐个 yield 出来供批量分享使用

        :param folder_id: 要扫描的文件夹ID
        :param title_prefix: 分享标题前缀
        :param skip_folders: 是否跳过子文件夹（只分享文件）
        :yield: {"file_id", "title", "type", "file_name", ...}
        """
        files = self.get_file_list(folder_id, sort_by="file_type:asc,file_name:asc", max_items=max_items)

        for f in files:
            ftype = f.get("file_type", "")
            fname = f.get("file_name", "")

            if skip_folders and (ftype == "folder" or f.get("dir") is True):
                continue

            title = f"{title_prefix}{fname}" if title_prefix else fname

            yield {
                "file_id": f.get("fid"),
                "title": title,
                "type": "doc" if self._is_doc_file(fname) else "file",
                "file_name": fname,
                "file_size": f.get("size", 0),
                "file_type": ftype,
                "updated_at": f.get("updated_at"),
            }

    @staticmethod
    def _is_doc_file(filename: str) -> bool:
        """判断是否为文档类型文件（用于决定走哪个分享接口）"""
        doc_extensions = {
            ".doc", ".docx", ".pdf", ".xls", ".xlsx",
            ".ppt", ".pptx", ".txt", ".md",
        }
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return f".{ext}" in doc_extensions

    def find_folder_by_name(self, name: str, parent_id: str = "0") -> Optional[str]:
        """
        按名称搜索并返回文件夹 ID
        支持模糊匹配（包含即可）
        """
        items = self.get_file_list(parent_id, max_items=500)
        for f in items:
            if name.lower() in f.get("file_name", "").lower():
                print(f"[夸克] 找到文件夹: {f['file_name']} (fid={f['fid']})")
                return f.get("fid")
        print(f"[夸克] 未找到名称含 '{name}' 的文件夹")
        return None

    def auto_scan_and_share_folder(
        self,
        folder_name_or_id: str,
        target_group_id: str = "",
        content_template: str = "",
        expire_time: int = 0,
        password: str = "",
        dry_run: bool = False,
    ) -> Dict:
        """
        一键扫描文件夹 → 生成所有文件/文档的分享链接
        （不自动发布到星球，返回结果供调用方决定如何分发）

        :param folder_name_or_id: 文件夹名称(模糊匹配) 或 直接传文件夹ID
        :param target_group_id: 目标星球ID(预留，本方法仅生成链接)
        :param content_template: 内容模板, 支持 {title}, {file_name}, {size} 占位符
        :param expire_time: 有效期(天), 0=永久
        :param password: 提取密码
        :param dry_run: 仅扫描不创建分享
        :return: {"folder_info", "files", "results", "summary"}
        """
        # 解析文件夹ID
        if folder_name_or_id and not folder_name_or_id.isdigit():
            folder_id = self.find_folder_by_name(folder_name_or_id)
            if not folder_id:
                return {"success": False, "error": f"未找到文件夹: {folder_name_or_id}"}
        else:
            folder_id = folder_name_or_id or "0"

        # 获取文件夹信息
        folder_info = self.get_file_info(folder_id)

        # 扫描文件
        files_to_share = list(self.scan_folder_for_sharing(folder_id))

        if not files_to_share:
            return {
                "success": False,
                "error": f"文件夹为空或无可分享文件 (fid={folder_id})",
                "folder_info": folder_info,
            }

        print(f"\n[扫描] 文件夹 '{folder_info.get('file_name', folder_id)}' 共发现 {len(files_to_share)} 个可分享文件:")
        for i, f in enumerate(files_to_share):
            fsize = f["file_size"]
            size_str = f"{fsize / 1024 / 1024:.1f}MB" if fsize > 1024 * 1024 else f"{fsize // 1024}KB"
            print(f"  [{i+1}] {f['file_name']} ({f['type']}) - {size_str}")

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "folder_info": folder_info,
                "files": files_to_share,
                "summary": f"共 {len(files_to_share)} 个文件待分享（dry run）",
            }

        # 逐个创建分享
        results = []
        for i, item in enumerate(files_to_share):
            print(f"\n{'─'*50}")
            print(f"  分享 [{i+1}/{len(files_to_share)}]: {item['title']}")

            if item["type"] == "doc":
                share_info = self.create_doc_share(item["file_id"], item["title"], expire_time)
            else:
                share_info = self.create_file_share(item["file_id"], item["title"], expire_time, password or None)

            results.append({
                **item,
                "share_url": share_info.get("share_url", "") if share_info else "",
                "share_pwd": share_info.get("share_pwd", "") if share_info else "",
                "success": share_info is not None and bool(share_info.get("share_url")),
            })
            time.sleep(1.5)  # 避免频率限制

        success_count = sum(1 for r in results if r["success"])
        summary = f"分享完成: {success_count}/{len(results)} 成功"
        print(f"\n[汇总] {summary}")
        for r in results:
            status = "✅" if r["success"] else "❌"
            print(f"  {status} {r['title']}: {r['share_url'] or '失败'}")

        return {
            "success": True,
            "folder_info": folder_info,
            "files": files_to_share,
            "results": results,
            "summary": summary,
            "success_count": success_count,
            "total_count": len(results),
        }

    def get_share_list(self) -> List[Dict]:
        """获取我的分享列表"""
        url = 'https://drive-pc.quark.cn/1/clouddrive/share/list'
        try:
            resp = requests.get(url, headers=self.headers, params=self.base_params, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') == 0:
                return result.get('data', {}).get('list', [])
            return []
        except Exception as e:
            print(f"[夸克] 获取分享列表异常: {e}")
            return []

    def validate_cookie(self) -> bool:
        """验证 Cookie 是否有效"""
        try:
            url = 'https://drive-pc.quark.cn/1/clouddrive/config'
            resp = requests.get(url, headers=self.headers, params=self.base_params, timeout=10)
            result = resp.json()
            if result.get('code') == 0:
                return True
        except Exception:
            pass

        try:
            url = "https://drive-pc.quark.cn/1/clouddrive/file/sort"
            params = {
                **self.base_params,
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": "0",
                "_page": "1",
                "_size": "1",
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,file_name:asc",
            }
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            result = resp.json()
            return result.get('code') == 0
        except Exception:
            return False
