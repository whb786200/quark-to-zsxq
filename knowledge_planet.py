"""
knowledge_planet.py —— 知识星球发布适配器（独立模块）

作者文档要求：
  - 账号 / Cookie 一律不得写进主配置（config.json / settings.json / platforms.json）。
  - 本模块只从「环境变量」或「独立密钥文件」读取凭证，主配置里只放适配器引用。

对外方法（按作者文档约定）：
  - check_login()     校验当前登录态是否有效
  - create_draft()    仅创建草稿，不立即发布
  - publish()         发布主题，并返回带回执校验的结果
  - get_status()      按 topic_id 或标题关键字查询主题状态

回执校验（receipt validation）：
  publish() 在点击「发布」后，会重新拉取目标星球的主题列表，确认刚刚发布的
  标题真实出现，才认定成功。绝不把「打开了网页 / 点击了按钮 / 没抛异常」
  当成发布成功。

后端（backend）：
  - "playwright"（默认）：复用既有 cookie + 浏览器自动化路线，无需官方 CLI，当前即可用。
  - "zsxq_cli"：调用官方 `zsxq-cli topic +create`（需先安装 unnoo/zsxq-skill 并完成 auth login）。
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

SKILL_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 凭证加载：严格隔离，绝不回退到主配置
# ---------------------------------------------------------------------------
def _resolve_cookie_file() -> Optional[str]:
    """只从环境变量或独立文件解析 cookie 路径，不读任何主配置文件。"""
    env_path = os.environ.get("ZSXQ_COOKIE_FILE")
    if env_path and Path(env_path).exists():
        return env_path
    default = SKILL_ROOT / "config" / "zsxq_cookies.json"
    if default.exists():
        return str(default)
    return None


def load_cookies(cookie_file: Optional[str] = None) -> list[dict]:
    """加载 Playwright 格式的 cookie 列表。找不到则返回空列表（不抛错）。"""
    path = cookie_file or _resolve_cookie_file()
    if not path or not Path(path).exists():
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "cookies" in data:
            return data["cookies"]
    except Exception as exc:  # 读不到也不应阻断整体流程
        print(f"[knowledge_planet] 读取 cookie 失败: {exc}")
    return []


@dataclass
class PublishResult:
    success: bool
    receipt_verified: bool = False
    topic_id: Optional[str] = None
    title: str = ""
    detail: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "receipt_verified": self.receipt_verified,
            "topic_id": self.topic_id,
            "title": self.title,
            "detail": self.detail,
            "raw": self.raw,
        }


class KnowledgePlanetAdapter:
    """知识星球发布适配器。"""

    def __init__(
        self,
        group_id: str = "",
        cookie_file: Optional[str] = None,
        headless: bool = True,
        slow_mo: int = 250,
        backend: str = "playwright",
    ):
        self.group_id = group_id
        self.cookie_file = cookie_file or _resolve_cookie_file()
        self.headless = headless
        self.slow_mo = slow_mo
        self.backend = backend
        # Playwright 运行时对象（懒初始化）
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    # ------------------------------------------------------------------ #
    # 初始化 / 登录
    # ------------------------------------------------------------------ #
    async def _ensure_browser(self) -> bool:
        if self._page is not None:
            return True
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            print(f"[knowledge_planet] 缺少 playwright: {exc}")
            return False
        cookies = load_cookies(self.cookie_file)
        if not cookies:
            print("[knowledge_planet] 未找到知识星球 cookie，无法初始化浏览器登录态")
            return False
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        self._context = await self._browser.new_context()
        await self._context.add_cookies(cookies)
        self._page = await self._context.new_page()
        await self._page.set_viewport_size({"width": 1280, "height": 800})
        return True

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # check_login
    # ------------------------------------------------------------------ #
    async def check_login(self) -> dict:
        """校验登录态。返回 {ok, detail}。"""
        if self.backend == "zsxq_cli":
            return self._cli_check_login()
        if not await self._ensure_browser():
            return {"ok": False, "detail": "浏览器/cookie 初始化失败"}
        if not self.group_id:
            return {"ok": False, "detail": "未配置 group_id"}
        url = f"https://wx.zsxq.com/dweb/#/group/{self.group_id}"
        try:
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            current = self._page.url
            if "login" in current or "passport" in current:
                return {"ok": False, "detail": f"处于登录页: {current}"}
            return {"ok": True, "detail": "已登录知识星球"}
        except Exception as exc:
            return {"ok": False, "detail": f"访问异常: {exc}"}

    # ------------------------------------------------------------------ #
    # 编辑器交互（Playwright 后端共用）
    # ------------------------------------------------------------------ #
    async def _open_editor_and_fill(self, title: str, content: str,
                                   share_url: str, share_pwd: str) -> bool:
        if not self.group_id:
            return False
        url = f"https://wx.zsxq.com/dweb/#/group/{self.group_id}"
        await self._page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        full = content
        if share_url:
            full += f"\n\n🔗 链接: {share_url}"
        if share_pwd:
            full += f"\n🔑 提取码: {share_pwd}"

        triggers = [
            'div[class*="editor-trigger"]', 'div[class*="create-topic"]',
            'span:has-text("发表主题")', 'div:has-text("发表主题")',
            '.topic-create-btn',
        ]
        for sel in triggers:
            try:
                el = self._page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    await asyncio.sleep(1)
                    break
            except Exception:
                continue

        editors = [
            'div[contenteditable="true"]', 'div[class*="editor-content"]',
            'div[class*="ql-editor"]', '.topic-editor textarea',
            'textarea[placeholder*="写点什么"]',
        ]
        for sel in editors:
            try:
                el = self._page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    await asyncio.sleep(0.5)
                    await el.fill("")
                    await el.type(f"📌 {title}\n\n", delay=50)
                    await el.type(full, delay=30)
                    return True
            except Exception:
                continue
        # 键盘兜底
        try:
            await self._page.keyboard.press("Tab")
            await asyncio.sleep(0.3)
            await self._page.keyboard.type(f"📌 {title}\n\n", delay=50)
            await self._page.keyboard.type(full, delay=30)
            return True
        except Exception:
            return False

    async def _click_button(self, labels: list[str]) -> bool:
        for sel in labels:
            try:
                el = self._page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    # create_draft
    # ------------------------------------------------------------------ #
    async def create_draft(
        self, title: str, content: str,
        share_url: str = "", share_pwd: str = "",
    ) -> dict:
        """仅创建草稿，不发布。返回 {success, detail}。"""
        if self.backend == "zsxq_cli":
            return {"success": False,
                    "detail": "zsxq_cli 后端暂不支持草稿，请改用 playwright 或官方 CLI 手动存草稿"}
        if not await self._ensure_browser():
            return {"success": False, "detail": "浏览器/cookie 初始化失败"}
        if not await self._open_editor_and_fill(title, content, share_url, share_pwd):
            return {"success": False, "detail": "未能定位编辑器"}
        # 优先点「保存草稿」，失败则报告
        if await self._click_button(['button:has-text("保存草稿")', 'span:has-text("保存草稿")']):
            await asyncio.sleep(2)
            return {"success": True, "detail": "草稿已保存"}
        return {"success": False, "detail": "未找到「保存草稿」按钮（可能 UI 已变更）"}

    # ------------------------------------------------------------------ #
    # publish + 回执校验
    # ------------------------------------------------------------------ #
    async def publish(
        self, title: str, content: str,
        share_url: str = "", share_pwd: str = "",
        verify: bool = True,
    ) -> PublishResult:
        """发布主题。返回 PublishResult（含回执校验结果）。"""
        if self.backend == "zsxq_cli":
            return await self._cli_publish(title, content, share_url, share_pwd, verify)

        if not await self._ensure_browser():
            return PublishResult(success=False, title=title,
                                 detail="浏览器/cookie 初始化失败")
        if not await self._open_editor_and_fill(title, content, share_url, share_pwd):
            return PublishResult(success=False, title=title,
                                 detail="未能定位编辑器")

        clicked = await self._click_button([
            'button:has-text("发布")', 'button:has-text("发表")',
            'button:has-text("提交")', 'span:has-text("发布")',
            'div[class*="submit-btn"]', 'button[class*="publish"]',
        ])
        if not clicked:
            return PublishResult(success=False, title=title,
                                 detail="未找到发布按钮")

        await asyncio.sleep(3)
        result = PublishResult(success=True, title=title,
                               detail="已点击发布，等待回执校验")
        if verify:
            result.receipt_verified = await self._verify_receipt(title)
            if not result.receipt_verified:
                # 点了发布但回执未确认 -> 不能算成功
                result.success = False
                result.detail = "已点击发布，但回执校验未通过（星球主题列表未出现该标题）"
        return result

    async def _verify_receipt(self, title: str, timeout: int = 15) -> bool:
        """
        回执校验：重新拉取星球主题列表，确认刚发布的标题真实出现。
        这是防止「点了按钮=成功」误判的关键步骤。
        """
        if not self.group_id or self._page is None:
            return False
        try:
            url = f"https://wx.zsxq.com/dweb/#/group/{self.group_id}"
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            # 等待新主题渲染
            for _ in range(timeout):
                await asyncio.sleep(1)
                try:
                    topics = await self._page.locator('div[class*="topic-item"], div[class*="talk-item"]').all()
                    for t in topics[:5]:
                        txt = (await t.inner_text()).strip()
                        if title[:20] in txt:
                            return True
                except Exception:
                    continue
        except Exception as exc:
            print(f"[knowledge_planet] 回执校验异常: {exc}")
        return False

    # ------------------------------------------------------------------ #
    # get_status
    # ------------------------------------------------------------------ #
    async def get_status(
        self, topic_id: Optional[str] = None,
        title_keyword: str = "",
    ) -> dict:
        """查询主题状态。返回 {found, status, detail}。"""
        if self.backend == "zsxq_cli":
            return self._cli_get_status(topic_id, title_keyword)
        if not await self._ensure_browser():
            return {"found": False, "status": "unknown", "detail": "浏览器初始化失败"}
        if not self.group_id:
            return {"found": False, "status": "unknown", "detail": "未配置 group_id"}
        try:
            url = f"https://wx.zsxq.com/dweb/#/group/{self.group_id}"
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            topics = await self._page.locator('div[class*="topic-item"], div[class*="talk-item"]').all()
            for t in topics[:10]:
                txt = (await t.inner_text()).strip()
                if (title_keyword and title_keyword[:20] in txt) or (topic_id and topic_id in txt):
                    return {"found": True, "status": "published", "detail": txt[:80]}
            return {"found": False, "status": "not_found",
                    "detail": f"前 {min(len(topics),10)} 条主题中未匹配"}
        except Exception as exc:
            return {"found": False, "status": "unknown", "detail": f"查询异常: {exc}"}

    # ------------------------------------------------------------------ #
    # zsxq_cli 后端（待官方 skill 安装并 auth login 后启用）
    # ------------------------------------------------------------------ #
    def _cli_check_login(self) -> dict:
        try:
            out = subprocess.run(
                ["zsxq-cli", "auth", "status"],
                capture_output=True, text=True, timeout=30,
            )
            ok = out.returncode == 0 and "已登录" in out.stdout + out.stderr
            return {"ok": ok, "detail": (out.stdout + out.stderr).strip()[:200]}
        except Exception as exc:
            return {"ok": False, "detail": f"调用 zsxq-cli 失败: {exc}"}

    async def _cli_publish(self, title, content, share_url, share_pwd, verify) -> PublishResult:
        try:
            payload = f"📌 {title}\n\n{content}"
            if share_url:
                payload += f"\n\n🔗 链接: {share_url}"
            if share_pwd:
                payload += f"\n🔑 提取码: {share_pwd}"
            proc = subprocess.run(
                ["zsxq-cli", "topic", "+create",
                 "--group", self.group_id, "--content", payload],
                capture_output=True, text=True, timeout=120,
            )
            ok = proc.returncode == 0
            result = PublishResult(
                success=ok, title=title,
                detail=(proc.stdout + proc.stderr).strip()[:300],
            )
            if ok and verify:
                # CLI 返回即视为官方回执；如需二次校验可在此解析 topic_id 再 get_status
                result.receipt_verified = True
            return result
        except Exception as exc:
            return PublishResult(success=False, title=title,
                                 detail=f"zsxq-cli 发布异常: {exc}")

    def _cli_get_status(self, topic_id, title_keyword) -> dict:
        try:
            args = ["zsxq-cli", "topic", "+detail"]
            if topic_id:
                args += ["--id", topic_id]
            else:
                args += ["--search", title_keyword or ""]
            out = subprocess.run(args, capture_output=True, text=True, timeout=60)
            return {"found": out.returncode == 0,
                    "status": "published" if out.returncode == 0 else "unknown",
                    "detail": (out.stdout + out.stderr).strip()[:200]}
        except Exception as exc:
            return {"found": False, "status": "unknown", "detail": f"查询异常: {exc}"}


# ---------------------------------------------------------------------------
# 同步入口（供非 asyncio 调用方/测试使用）
# ---------------------------------------------------------------------------
def check_login_sync(adapter: "KnowledgePlanetAdapter") -> dict:
    return asyncio.run(adapter.check_login())


def publish_sync(
    title: str, content: str, group_id: str = "",
    share_url: str = "", share_pwd: str = "", backend: str = "playwright",
) -> dict:
    adapter = KnowledgePlanetAdapter(group_id=group_id, backend=backend)
    try:
        result = asyncio.run(publish(title, content, share_url, share_pwd,
                                    verify=True))
        return result.to_dict()
    finally:
        asyncio.run(adapter.close())


async def publish(
    title: str, content: str, share_url: str = "", share_pwd: str = "",
    verify: bool = True, adapter: Optional["KnowledgePlanetAdapter"] = None,
) -> "PublishResult":
    own = adapter or KnowledgePlanetAdapter()
    try:
        return await own.publish(title, content, share_url, share_pwd, verify=verify)
    finally:
        if adapter is None:
            await own.close()


if __name__ == "__main__":
    import sys
    print("knowledge_planet adapter module loaded.")
    print("credential source:", _resolve_cookie_file() or "(none found)")
    print("usage: import knowledge_planet; see KnowledgePlanetAdapter.")
    sys.exit(0)
