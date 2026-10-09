# 夸克网盘 → 知识星球 自动发布工具

## 功能

| 模块 | 功能 |
|------|------|
| `quark_share.py` | 夸克网盘文件/文件夹分享、文档分享、批量分享 |
| `zsxq_publisher.py` | 知识星球发布辅助（授权空间使用；群聊群发优先官方 API 或人工确认） |
| `main.py` | CLI 入口，串联全流程 |

## 快速开始

```bash
# 1. 安装依赖
pip install requests playwright
playwright install chromium

# 2. 初始化配置
python main.py --init-config

# 3. 单个文件分享+发布到星球
python main.py --file-id <fid> --title "工程资料合集" --group-id <星球ID>

# 4. 文档分享+发布
python main.py --doc-id <doc_id> --title "施工方案文档" --group-id <星球ID>
```

## 每日运行计划（安全预检）

如果 Cookie 失效，先运行：

```bash
python -X utf8 refresh_quark_cookie.py
```

脚本会打开浏览器，默认最多等待 3 分钟并自动轮询验证；只有夸克接口验证通过，才会写入 `config/settings.json`。需要调整等待时间时：

```bash
python -X utf8 refresh_quark_cookie.py --login-timeout 180
```

如果你已经从开发者工具复制了完整 Cookie，也可以复制后直接运行：

```bat
update_cookie_from_clipboard.bat
```

该脚本要求 Cookie 包含 `ctoken` 和 `b-user-id`，并会在写入后立即跑一次只读预检。

默认只读取夸克文件夹，生成今晚/中午的待发送清单和文案，不创建分享链接，也不向任何群或星球发布：

```bash
python -X utf8 daily_quark_plan.py --folder "自发群" --destination "工程交流2群（筑界）" --slot night --limit 100
```

也可以直接运行：

```bat
run_daily_plan.bat --slot night
```

输出位于 `runs/YYYYMMDD_HHMMSS_<slot>/`：

- `manifest.json`：机器可读清单
- `message_draft.md`：人工核对和复制用文案

如确需创建夸克分享链接，必须显式确认。每次 50 个用：

```bash
python -X utf8 daily_quark_plan.py --folder "自发群" --destination "工程交流2群（筑界）" --slot all --limit 50 --create-shares --confirm-share-links YES
```

下一批 50 个用 `--offset 50`，再下一批用 `--offset 100`：

```bash
python -X utf8 daily_quark_plan.py --folder "自发群" --destination "工程交流2群（筑界）" --slot all --limit 50 --offset 50 --create-shares --confirm-share-links YES
```

如果网络中断导致部分失败，只重试失败项：

```bash
python -X utf8 daily_quark_plan.py --retry-manifest "runs\\YYYYMMDD_HHMMSS_all\\manifest.json" --confirm-share-links YES
```

每日两个时段各 50 个，用：

```bash
python -X utf8 daily_quark_plan.py --slot noon --limit 100 --create-shares --confirm-share-links YES
python -X utf8 daily_quark_plan.py --slot night --limit 100 --create-shares --confirm-share-links YES
```

生成链接后会写入 `message_draft.md`。群发只能通过已授权的官方平台 API 并在发送前显式确认；没有官方 API 时只生成草稿，不通过浏览器或电脑自动化模拟人工群发。

## 使用方式

### 单个任务
```bash
# 文件/文件夹分享 + 发布到星球
python main.py --file-id 123456789 --title "资料包" --group-id 12345678

# 仅分享不发星球
python main.py --file-id 123456789 --title "资料包" --no-publish

# 带密码和有效期
python main.py --file-id 123456789 --title "资料包" --password 8888 --expire-time 7
```

### 批量模式
```bash
# 创建批量任务JSON (config/tasks.json)
python main.py --batch config/tasks.json
```

### 批量任务格式示例 (`config/tasks.json`)
```json
[
  {
    "file_id": "fid_001",
    "type": "file",
    "title": "安全生产资料合集",
    "content": "整理好的安全生产相关资料，包含制度文件、检查表等",
    "expire_time": 0,
    "password": ""
  },
  {
    "file_id": "doc_002", 
    "type": "doc",
    "title": "施工组织设计方案",
    "content": "完整施工方案文档",
    "expire_time": 7,
    "password": ""
  }
]
```

### 仅发布已有链接
```bash
python main.py --publish-only \
  --url "https://pan.quark.cn/s/xxxxxxxx" \
  --title "好资料" \
  --desc "整理好的工程资料" \
  --group-id 12345678
```

## 配置说明 (`config/settings.json`)

```json
{
  "quark_cookie": "你的夸克Cookie",
  "zsxq_group_id": "知识星球ID",
  "default_expire": 0,
  "default_password": ""
}
```

**Cookie获取方式:**
1. 打开 https://pan.quark.cn 并登录
2. 按 F12 → Network 标签页
3. 刷新页面, 点击任意请求
4. 在 Request Headers 中复制完整的 `Cookie` 值

**星球ID获取方式:**
1. 打开知识星球网页版 https://wx.zsxq.com
2. 进入目标星球
3. URL 格式为 `wx.zsxq.com/dweb/#/group/{星球ID}`

## 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  夸克API     │ ──→ │   主流程      │ ──→ │  知识星球     │
│  (requests)  │     │  (main.py)   │     │(Playwright)  │
└─────────────┘     └──────────────┘     └─────────────┘
     │                     │                     │
  •创建分享链接          •串联全流程           •自动登录
  •获取share_url        •CLI参数解析          •输入内容
  •支持密码/有效期       •批量处理             •点击发布
```
