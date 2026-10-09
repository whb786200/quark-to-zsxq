"""
知识星球自动发布模块
- 基于 Playwright 浏览器自动化
- 在知识星球网页版 (wx.zsxq.com) 发布主题
- 支持发布文字+链接内容
"""

import asyncio
import time
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext


class ZsxqPublisher:
    """知识星球自动发布器 - Playwright 浏览器自动化"""

    def __init__(
        self,
        headless: bool = False,
        cookie_file: str = "config/zsxq_cookies.json",
        slow_mo: int = 500,
    ):
        """
        :param headless: 是否无头模式运行 (首次登录建议 False)
        :param cookie_file: Cookie 持久化文件路径
        :param slow_mo: 操作间隔(ms), 模拟人类速度
        """
        self.headless = headless
        self.cookie_file = cookie_file
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None

    # ==================== 初始化 & 登录 ====================

    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
        self.context = await self._load_or_create_context()
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})

    async def _load_or_create_context(self) -> BrowserContext:
        """加载已保存的Cookie或创建新上下文"""
        import os
        context = await self.browser.new_context()

        # 尝试加载已保存的 Cookie
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    import json
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("[星球] 已加载已保存的Cookie")
            except Exception as e:
                print(f"[星球] 加载Cookie失败: {e}")

        return context

    async def _save_cookies(self):
        """保存当前Cookie到文件"""
        import os
        cookies = await self.context.cookies()
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            import json
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"[星球] Cookie已保存到 {self.cookie_file}")

    async def ensure_login(self, group_id: str) -> bool:
        """
        确保已登录知识星球，如未登录则等待用户手动登录

        :param group_id: 星球ID (从URL中获取)
        :return: 是否已登录
        """
        url = f"https://wx.zsxq.com/dweb/#/group/{group_id}"
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # 检查是否在登录页面
        current_url = self.page.url
        if "login" in current_url or "passport" in current_url:
            print("\n[星球] ⚠️ 需要登录！请在弹出的浏览器中扫码/登录...")
            print("[星球] 登录完成后，此脚本会自动继续...")

            # 等待登录完成 (最多等待5分钟)
            for _ in range(300):
                await asyncio.sleep(1)
                current_url = self.page.url
                if "login" not in current_url and "passport" not in current_url:
                    print("[星球] ✅ 登录成功!")
                    await self._save_cookies()
                    return True

            print("[星球] ❌ 登录超时")
            return False

        # 已登录
        print("[星球] ✅ 已登录")
        return True

    # ==================== 发布主题 ====================

    async def publish_topic(
        self,
        group_id: str,
        title: str,
        content: str,
        share_url: str = "",
        share_pwd: str = "",
    ) -> bool:
        """
        发布主题到知识星球

        :param group_id: 星球ID
        :param title: 主题标题
        :param content: 主题正文
        :param share_url: 分享链接 (可选, 会附加在正文后)
        :param share_pwd: 提取密码 (可选)
        :return: 是否发布成功
        """
        # 确保已登录
        if not await self.ensure_login(group_id):
            return False

        # 导航到星球首页
        url = f"https://wx.zsxq.com/dweb/#/group/{group_id}"
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # 拼接完整内容
        full_content = content
        if share_url:
            full_content += f"\n\n🔗 链接: {share_url}"
        if share_pwd:
            full_content += f"\n🔑 提取码: {share_pwd}"

        try:
            # 1. 点击"发表主题"按钮 / 找到编辑区域
            print("[星球] 正在定位编辑区域...")
            
            # 尝试点击 "发表主题" 入口按钮 (知识星球可能需要先点击才能展开编辑器)
            editor_triggers = [
                'div[class*="editor-trigger"]',
                'div[class*="create-topic"]',
                'span:has-text("发表主题")',
                'div:has-text("发表主题")',
                '.topic-create-btn',
            ]
            
            clicked = False
            for selector in editor_triggers:
                try:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        clicked = True
                        print(f"[星球] 点击了编辑触发器: {selector}")
                        await asyncio.sleep(1)
                        break
                except Exception:
                    continue
            
            # 2. 找到文本编辑区域并输入内容
            print("[星球] 正在输入内容...")
            
            # 知识星球的编辑器是一个 contenteditable div
            editor_selectors = [
                'div[contenteditable="true"]',
                'div[class*="editor-content"]',
                'div[class*="ql-editor"]',
                '.topic-editor textarea',
                'textarea[placeholder*="写点什么"]',
            ]

            editor_found = False
            for selector in editor_selectors:
                try:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=3000):
                        await el.click()
                        await asyncio.sleep(0.5)
                        # 清空已有内容
                        await el.fill("")
                        # 输入标题
                        await el.type(f"📌 {title}\n\n", delay=50)
                        # 输入正文
                        await el.type(full_content, delay=30)
                        editor_found = True
                        print(f"[星球] 已输入内容到: {selector}")
                        break
                except Exception:
                    continue

            if not editor_found:
                # 尝试用键盘快捷方式
                print("[星球] 常规选择器未找到编辑器, 尝试键盘输入...")
                await self.page.keyboard.press("Tab")
                await asyncio.sleep(0.3)
                await self.page.keyboard.type(f"📌 {title}\n\n", delay=50)
                await self.page.keyboard.type(full_content, delay=30)
                editor_found = True

            # 3. 点击发布按钮
            print("[星球] 正在发布...")
            await asyncio.sleep(1)

            publish_selectors = [
                'button:has-text("发布")',
                'button:has-text("发表")',
                'button:has-text("提交")',
                'span:has-text("发布")',
                'div[class*="submit-btn"]',
                'button[class*="publish"]',
            ]

            for selector in publish_selectors:
                try:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        print(f"[星球] 点击了发布按钮: {selector}")
                        await asyncio.sleep(3)
                        # 检查是否发布成功 (URL变化或弹窗消失)
                        return True
                except Exception:
                    continue

            print("[星球] ❌ 未找到发布按钮")
            return False

        except Exception as e:
            print(f"[星球] 发布异常: {e}")
            return False

    # ==================== 批量发布 ====================

    async def batch_publish(self, group_id: str, topics: list) -> list:
        """
        批量发布主题到知识星球

        :param group_id: 星球ID
        :param topics: [{"title": "...", "content": "...", "share_url": "...", "share_pwd": "..."}]
        :return: 每条发布结果
        """
        results = []
        for i, topic in enumerate(topics):
            print(f"\n--- [{i+1}/{len(topics)}] 发布: {topic.get('title', '')} ---")
            success = await self.publish_topic(
                group_id=group_id,
                title=topic.get("title", ""),
                content=topic.get("content", ""),
                share_url=topic.get("share_url", ""),
                share_pwd=topic.get("share_pwd", ""),
            )
            results.append({
                "title": topic.get("title"),
                "success": success,
            })
            # 防止频繁操作
            if i < len(topics) - 1:
                print("[星球] 等待3秒...")
                await asyncio.sleep(3)

        # 汇总
        success_count = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"批量发布完成: {success_count}/{len(results)} 成功")

        return results

    # ==================== 清理 ====================

    async def close(self):
        """关闭浏览器, 保存Cookie"""
        try:
            await self._save_cookies()
        except Exception:
            pass
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[星球] 浏览器已关闭")
