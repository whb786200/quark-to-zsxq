# 微信群发组件（ClawBot / iLink）接入说明

本组件用于把 `message_draft.md` 自动发送到微信群「工程交流2群（筑界）」，破「卡点B」。
采用微信官方 **ClawBot（iLink Bot API）**，合规、无封号风险。

## 一、前置条件（用户需自行完成）

1. **微信客户端升级**到支持 ClawBot 的版本：
   - iOS ≥ 8.0.70 / Android ≥ 8.0.69；PC 端微信 ≥ 4.1.8.67（建议从官网下最新版）。
2. **启用 ClawBot 插件**：微信内 `设置 → 插件 → 微信 ClawBot`，扫码/确认登录。
3. **拿到 Bot Token**：通过 OpenClaw 或 `wxclawbot-cli` 登录后获得（形如 `eyJhbGci...`）。
4. **Bot 加入目标群**：确保 ClawBot 机器人已在「工程交流2群（筑界）」群内。

## 二、配置 config/settings.json

```json
{
  "clawbot_token": "你的Bearer Token",
  "clawbot_base_url": "https://ilinkai.weixin.qq.com",
  "wechat_group_id": "",            // 留空可用 --discover 反查
  "wechat_send_enabled": true
}
```

- `wechat_group_id` 不知道时：先跑一次
  `python wechat_sender.py --discover --group-name "工程交流2群（筑界）"`
  它会从收消息流里按群名反查并自动缓存 group_id（需该群近期有消息）。

## 三、两种后端（--backend）

| 后端 | 依赖 | 说明 |
|------|------|------|
| `clawbot-http`（默认） | 仅 requests | 直连 iLink API，自包含，无需装额外组件 |
| `clawbot-cli` | Node≥20 + `npm i -g @herai/wxclawbot-cli` | 社区维护，协议细节已处理，频限自动退避 |

## 四、用法

```bash
# 1) 仅生成文案（不改发群）
python share_to_group.py

# 2) 生成文案并自动发群
python share_to_group.py --send-wechat

# 3) 仅发群（用已有的最新 message_draft.md）
python wechat_sender.py --dry-run            # 先预览
python wechat_sender.py                      # 真发
python wechat_sender.py --backend clawbot-cli --dry-run

# 4) 反查群 group_id
python wechat_sender.py --discover --group-name "工程交流2群（筑界）"
```

## 五、频限与注意

- 每个机器人账号约 **7 条 / 5 分钟**（服务端共享），触发 `ret=-2` 会自动退避重试。
- 大批量群发建议分批或降低频率。
- 发送内容默认取 `runs/<最新>/message_draft.md` 全文（含分享链接+提取码），可直接在群内阅读。
- 发送失败不会删除已生成的分享链接，可安全重试。
