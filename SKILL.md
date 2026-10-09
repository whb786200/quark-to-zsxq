---
name: quark-to-zsxq
version: 3.1.0
description: >
  知识星球自动发布技能：按路由采集 AI 开源项目、AI 工程工具/skill 和本地资料，
  在预定时间窗口内去重、批量发布并记录审计结果。支持夸克分享链接与本地资料发布前置检查。
trigger_words:
  - 知识星球自动发布
  - 知识星球定时发布
  - 知识星球自动化
  - AI开源项目发布
  - AI工程工具发布
  - 资料合集发布
  - quark to zsxq
---

# 知识星球自动发布 Skill

## 目标

本 Skill 由 WorkBuddy 原生自动化任务调用，负责：

1. 读取 `automation/config.json` 中的发布路由。
2. 在 Asia/Shanghai 每日 03:00-04:30 窗口内执行。
3. 每个路由单次至少处理 5 个文件或项目，减少零散发布。
4. 使用 `automation/state.json` 去重，使用 `automation/logs/` 留存预检、执行和汇总日志。
5. 任何登录态、源目录、上传适配器或发布结果缺失时，明确记录失败，不假报成功。

## 路由

- AI 开源项目 → `48885151825858`
- AI 工程工具/skill → `28882121842881`
- 太阳能资料 → `88882584141252`
- 成本优化设计 → `48885482121548`
- 城市更新资料 → `28882584141811`
- IMA 其他资料 → `15552114118152`

路由和源目录以 `automation/config.json` 为准，不要在运行提示中另行硬编码或改写。

## 运行入口

在 PowerShell 中：

```powershell
# 预检
.\automation\run-nightly.cmd --preflight

# 不发布的演练
.\automation\run-nightly.cmd --dry-run

# 真实运行
.\automation\run-nightly.cmd
```

WorkBuddy 自动化运行时，先阅读本文件和 `automation/config.json`，再执行：

```powershell
.\automation\run-nightly.cmd
```

## 前置条件

- 夸克登录态：`config/settings.json` 中存在有效 `quark_cookie`，或持久化 Edge 登录态可用。
- 知识星球登录态：`config/zsxq_cookies.json` 存在且有效。
- 本地资料目录存在且可读。
- 本地文件发布必须先经过可用的上传适配器；没有适配器时必须阻断，不得把“扫描到文件”当成“已上传”。

## 审计与恢复

- 每次运行写入 `automation/logs/run-*.json` 和 `run-*.log`。
- 每次预检写入 `automation/logs/preflight-*.json`。
- 去重状态保存在 `automation/state.json`，重复运行不得重复发布已确认成功的项目。
- 失败后优先查看最新运行 JSON 和日志，再修复登录态、目录或适配器；不要直接清空去重状态。
- 发布结果只以页面/API 明确成功或日志中的成功结果为准。

## WorkBuddy 调度约定

- 调度器：WorkBuddy `LocalAutomationScheduler`。
- 主运行时间：每天 03:00。
- 运行窗口：03:00-04:30，时区 Asia/Shanghai。
- WorkBuddy 任务工作目录：`C:\Users\19586\.workbuddy\skills\quark-to-zsxq`。
- 任务失败或被阻断时，必须保留日志并在自动化结果中说明阻断原因。

不要把本 Skill 当作微信群发 Skill 使用；本 Skill 的发布目标是知识星球。
