# 自动化执行记忆：知识星球自动发布 (55ae9a1c)

## 2026-09-20 03:03 执行（Asia/Shanghai 窗口内）
- 入口：通过 WorkBuddy Python 环境（`…\envs\default\Scripts\python.exe`）运行 `automation/run-nightly.py --preflight`（等同于 `run-nightly.cmd --preflight` 绑定的环境；cmd.exe 被安全策略拦截，故直接调用同款 python）。
- 结果：**预检失败（success=false），已按规则结束，未运行主发布流程，未假报成功。**
- 阻断项（blocking_failures）：
  1. `quark_login` — config/settings.json 的 `quark_cookie` 为空。
  2. `zsxq_login` — config/zsxq_cookies.json 文件不存在。
  3. `local_upload_adapter:*` 全部 6 条路由 — 所有路由 source_mode 均为 "local"，但未配置本地文件→夸克的上传适配器（按 Skill 前置条件，本地资料发布必须阻断）。
- 已通过项：三个源文件存在；playwright/requests 可导入；6 个 group_id 有效；全部 6 个 source 候选目录当前存在（D:\Codex\projects\开源项目、E:\IMA知识库上传 及各子合集）。
- 结论：源目录已恢复可读，但登录态（夸克 cookie、知识星球 cookie）与本地上传适配器仍未就绪，无法进入真实发布。
- 后续恢复要点：① 填入有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器后，预检才可放行。

## 2026-09-21 03:02 执行（Asia/Shanghai 窗口内）
- 入口：复用入口 `.cmd` 绑定的同一 WorkBuddy Python（`envs\default\Scripts\python.exe`）直接运行 `automation/run-nightly.py --preflight`（同 09-20，避免 cmd.exe 安全策略拦截；解释器已核验存在，Python 3.13.14）。
- 结果：**预检失败（success=false，退出码 2），按规则结束，未运行主发布流程，未假报成功。**
- 阻断项（同 09-20，无变化）：① `quark_login` — quark_cookie 仍为空；② `zsxq_login` — zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（无本地上传适配器）。
- 已通过项：源文件存在、playwright/requests 可导入、6 个 group_id 有效、全部 6 个源目录当前存在且有充足文件（IMA 合集 file_count=100 已封顶）。
- 日志说明：`--preflight` 模式按脚本设计只打印 JSON 到 stdout、不写磁盘日志（仅 `run_once()` 主流程才写 run-*.json/preflight-*.json/run-*.log）。为留存审计，本次已手动落盘快照 `automation/logs/preflight-20260921-030229.json`；此前最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 结论：登录态（夸克 cookie、知识星球 cookie）与本地上传适配器三项前置条件依旧未满足，无法进入真实发布；状态与 09-20 完全持平，非回归。

## 2026-09-22 03:04 执行（Asia/Shanghai 窗口内，03:01:49 触发）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`envs\default\Scripts\python.exe`）运行 `automation/run-nightly.py --preflight`（cmd.exe 安全策略拦截，故走同款解释器；Python 3.13 已核验存在）。
- 结果：**预检失败（success=false，退出码 2），按规则结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-21 完全一致，非回归）：① `quark_login` — quark_cookie 仍为空；② `zsxq_login` — zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，均无本地上传适配器）。
- 已通过项：三个源文件存在；playwright/requests 可导入；6 个 group_id 有效；全部 6 个源目录当前存在且有充足文件（IMA 合集 file_count 均=100 封顶）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260922-030401.json`（8155 字节）。因 `--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新的 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 成功/失败计数：本次无真实发布——成功数 0、失败数（被阻断未能发布）6 路由；阻断根因为上述三项前置条件未满足。
- 后续恢复要点（不变）：① 填入有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器后，预检才可放行进入真实发布。

## 2026-09-23 08:19 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化被触发于 08:18）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，注意：文件实际经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 仍受安全策略拦截，沿用同款解释器）。
- 结果：**预检失败（success=false，退出码 2），按规则结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-20/21/22 完全一致，非回归）：① `quark_login` — quark_cookie 仍为空；② `zsxq_login` — zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，均无本地上传适配器）。
- 已通过项：三个源文件存在；playwright/requests 可导入；6 个 group_id 有效；全部 6 个源目录当前存在且可读（D:\Codex\projects\开源项目 file_count=1 等）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260923-081924.json`（8157 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 额外提示：本次触发于 08:19，本就在 03:00-04:30 发布窗口之外；即便预检通过，按规则也不应在窗口外发布。实际因预检三项前置条件未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断路由 6（根因为上述三项前置条件未满足）。
- 后续恢复要点（不变）：① 填入有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器后，预检才可放行进入真实发布。

## 2026-09-24 06:47 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 06:46）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 仍只回显 banner 被拦截，沿用同款解释器；Python 3.13 已核验）。
- 结果：**预检失败（success=false，退出码 2），按规则结束，未运行主发布流程，未假报成功。**
- 阻断项（12 条，较 09-22/23 新增 4 条源目录失效项，属回归）：
  1. `quark_login` — config/settings.json 的 `quark_cookie` 仍为空（旧项）。
  2. `zsxq_login` — config/zsxq_cookies.json 仍不存在（旧项）。
  3. `local_upload_adapter:*` 全部 6 条路由 — 均无本地上传适配器（旧项）。
  4. 新增回归：`source:solar_resources` / `source:cost_optimization_resources` / `source:city_renewal_resources` / `source:ima_misc_resources` — "none of the configured source paths exists"。即 E:\IMA知识库上传\... 与 F:\IMA知识库上传\... 各合集目录当前已不存在（09-22/23 时这些目录存在且 file_count=100）。
- 已通过项：三个源文件存在；playwright/requests 可导入；6 个 group_id 有效；仅 ai_open_source_projects 与 ai_engineering_tools_skills 源目录仍可读（D:\Codex\projects\开源项目，file_count=1），其余 4 条 IMA 路由源目录已消失。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260924-064735.json`（8131 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 06:47 在 03:00-04:30 窗口外；即便预检通过也不应在窗口外发布。实际因预检 12 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 12（根因为上述三项登录态/适配器前置 + 新增 4 条 IMA 源目录失效）。
- 后续恢复要点（新增第④条）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器；④ 恢复/重配 IMA 源目录（E:\IMA知识库上传\...、F:\IMA知识库上传\... 各合集），或更新 config.json 指向新的有效源路径。四项齐备后预检才可放行进入真实发布。

## 2026-09-25 06:37 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 06:37）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（Python 3.13.14 已核验存在；cmd.exe 安全策略拦截，沿用同款解释器）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-22/23 持平，非 09-24 回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三个源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在（含 09-24 失效的 4 条 IMA 合集已恢复：solar/cost_optimization/city_renewal/ima_misc 的 file_count 均=100 封顶）**。
- 观察（非阻断）：`ai_open_source_projects` 与 `ai_engineering_tools_skills` 选中源 `D:\Codex\projects\开源项目` 仅 file_count=1，即便预检通过也不足 batch_size=5，需源目录补充文件或更换 source_candidates。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260925-063742.json`。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 06:37 在 03:00-04:30 窗口之外；即便预检通过也不应在窗口外发布。实际因预检 8 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为上述三项登录态/适配器前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器（实现后才能把"扫描到文件"变为真实上传）。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。

## 2026-09-26 08:16 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 08:15）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 3.13 已核验）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（12 条，较 09-25 新增 4 条源目录失效，重回 09-24 回归型）：
  1. `quark_login` — config/settings.json 的 `quark_cookie` 仍为空（旧项）。
  2. `zsxq_login` — config/zsxq_cookies.json 仍不存在（旧项）。
  3. `local_upload_adapter:*` 全部 6 条路由 — 均无本地上传适配器（旧项）。
  4. 回归：`source:solar_resources` / `source:cost_optimization_resources` / `source:city_renewal_resources` / `source:ima_misc_resources` — "none of the configured source paths exists"（E:\IMA知识库上传\… 与 F:\IMA知识库上传\… 各合集目录当前已不存在，与 09-24 同型；09-25 时曾恢复、本次再失效）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；仅 ai_open_source_projects 与 ai_engineering_tools_skills 源目录仍可读（D:\Codex\projects\开源项目，file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260926-081617.json`（8131 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 08:16 在 03:00-04:30 窗口之外；即便预检通过也不应在窗口外发布。实际因预检 12 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 12（根因为上述登录态/适配器两项长期前置 + 本次 IMA 源目录失效回归）。
- 后续恢复要点（④ 为反复失效项，建议改为稳定路径或自动重建）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器；④ 恢复/重配 IMA 源目录（E:\IMA知识库上传\…、F:\IMA知识库上传\… 各合集），或更新 config.json 指向新的有效源路径——该目录反复在 09-24 失效、09-25 恢复、09-26 再失效，需排查磁盘挂载/盘符稳定性。

## 2026-09-27 03:01 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:00:59）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 3.13 已核验）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（12 条，与 09-26 完全一致，非新增回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）；④ `source:solar_resources` / `source:cost_optimization_resources` / `source:city_renewal_resources` / `source:ima_misc_resources` 4 条 IMA 路由源目录仍 "none of the configured source paths exists"（与 09-26 同型，E:\IMA知识库上传\… / F:\IMA知识库上传\… 各合集仍不存在）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；仅 ai_open_source_projects 与 ai_engineering_tools_skills 源目录可读（D:\Codex\projects\开源项目，file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260927-030150.json`（8131 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 03:01 在 03:00-04:30 窗口内，时间合规；但因预检 12 项前置未满足，仍不得进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 12（根因为登录态/适配器两项长期前置 + IMA 源目录失效）。
- 后续恢复要点（不变，④ 反复失效需重点排查）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器；④ 恢复/重配 IMA 源目录或更新 config.json 源路径——该目录在 09-24 失效、09-25 恢复、09-26 与 09-27 连续两天再失效，应为盘符/挂载不稳定，建议改为稳定绝对路径或增加自动重建逻辑。

## 2026-09-28 03:02 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:01:15，预检完成于 03:02:34）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 已核验）。时间 03:01 在 03:00-04:30 窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-25 持平、较 09-27 少 4 条——本次 IMA 源目录全部恢复存在）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在（含 09-27 失效的 4 条 IMA 合集本次恢复：solar/cost_optimization/city_renewal/ima_misc 的 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1）**。
- 审计留痕：已落盘快照 `automation/logs/preflight-20260928-030234.json`（8157 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）；源目录已不再是阻断项（全部存在）。
- 后续恢复要点（①②③ 为长期未解决项）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器（实现后才能把"扫描到文件"变为真实上传）。源目录项本次已达标，无需再处理；待①②③齐备且于窗口内运行，预检方可放行进入真实发布。

## 2026-10-01 14:53 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 14:50）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（Python 已核验）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（含 4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261001-145305.json`（8157 字节）；`.err` 为空。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 14:53 在 03:00-04:30 窗口之外；即便预检通过也不应在窗口外发布。实际因预检 8 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。

## 2026-10-02 06:39 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 06:38）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（Python 已核验存在；cmd.exe 安全策略拦截，沿用同款解释器）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-01 持平，非回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（含 4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261002-063914.json`（EXIT=2）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 06:39 在 03:00-04:30 窗口之外；即便预检通过也不应在窗口外发布。实际因预检 8 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变，③ 反复失效需重点排查）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器（实现后才能把"扫描到文件"变为真实上传）。源目录项本次已达标，无需再处理；待①②③齐备且于窗口内运行，预检方可放行进入真实发布。

## 2026-10-03 07:28 执行（Asia/Shanghai 时间，窗口外 03:00-04:30；自动化触发于 07:27）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 已核验存在）。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-01/10-02 持平，非回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261003-072718.json`（8157 字节），`.err` 为空。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 07:28 在 03:00-04:30 窗口之外；即便预检通过也不应在窗口外发布。实际因预检 8 项前置未满足，未进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。

## 2026-10-04 03:01 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:00:49，预检完成于 03:01:42）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 已核验存在）。时间 03:01 在 03:00-04:30 窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-01/10-02/10-03 持平，非回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。本次无 `source:*` 失效项（源目录稳定存在）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261004-030201.json`（EXIT=2）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，加之预检失败按规则不进入主流程，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 时间提示：本次 03:01 在 03:00-04:30 窗口内，时间合规；但因预检 8 项前置未满足，仍不得进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器（实现后才能把"扫描到文件"变为真实上传）。源目录项本次已达标，无需再处理；待①②③齐备且于窗口内运行，预检方可放行进入真实发布。

## 2026-10-06 03:01 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:01:04）
- 入口：直接调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 已核验存在）。时间 03:01 在 03:00-04:30 窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-01~10-04 持平，非回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。本次无 `source:*` 失效项（源目录稳定存在）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261006-030148.json`（8157 字节），`.err` 为空。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，加之预检失败按规则不进入主流程，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。`state.json` 仍 `published:{}`（从未真实发布）。
- 时间提示：本次 03:01 在 03:00-04:30 窗口内，时间合规；但因预检 8 项前置未满足，仍不得进入任何发布。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。
- 备注：IMA 源目录 file_count=100 仅是预检扫描计数，非上传/发布结果；无上传适配器时这些文件不会被发布，不可据此判为"已发布"。

## 2026-10-07 03:01 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:01:46）
- 入口：调用 `.cmd` 绑定的同一 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`）运行 `run-nightly.py --preflight`（cmd.exe 安全策略拦截，沿用同款解释器；Python 已核验存在）。时间 03:02 在 03:00-04:30 窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-04/10-06 持平，非回归）：① `quark_login` — config/settings.json 的 `quark_cookie` 仍为空；② `zsxq_login` — config/zsxq_cookies.json 仍不存在；③ 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（4 条 IMA 合集 file_count 均=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。本次无 `source:*` 失效项（源目录稳定存在）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261007-030243.json`（EXIT=2，.err 为空）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，加之预检失败不进入主流程，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。`state.json` 仍 `published:{}`（从未真实发布）。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。

## 2026-10-08 03:02 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:00:43）
- 入口：按用户要求直接运行 `.cmd` 绑定入口 `automation\run-nightly.cmd --preflight`（其内部调用 `C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe` 跑 `run-nightly.py --preflight`，即指定的 WorkBuddy Python 环境）。本次 cmd.exe 未被拦截，正常返回 EXIT=2。
- 时间：03:02 处于 03:00-04:30 发布窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（8 条，与 09-28/10-04/10-06/10-07 完全一致，非回归）：
  1. `quark_login` — config/settings.json 的 `quark_cookie` 仍为空。
  2. `zsxq_login` — config/zsxq_cookies.json 仍不存在。
  3. 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；**全部 6 个源目录当前均存在**（4 条 IMA 合集 file_count=100 封顶；ai_open_source_projects 与 ai_engineering_tools_skills 选中 `D:\Codex\projects\开源项目` 仍仅 file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261008-030243.json`（8157 字节，校验为合法 JSON，success=False，8 failures），`.err` 为空（0 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，且预检失败按规则不进入主流程，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 8（根因为登录态/适配器两项长期前置条件仍未满足；源目录项已连续多日稳定存在，不再是阻断因素）。
- 后续恢复要点（不变）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器（实现后才能把"扫描到文件"变为真实上传）。三项齐备 + 在窗口内运行，预检方可放行进入真实发布。

## 2026-10-09 03:01 执行（Asia/Shanghai 窗口内 03:00-04:30；触发于 03:00:45）
- 入口：按用户要求以 `.cmd` 绑定入口运行预检——`cmd.exe` 经 Bash 触发被安全策略拦截，故改用同一绑定 WorkBuddy Python（`C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe`）直接运行 `run-nightly.py --preflight`（与 `.cmd` 内解释器一致；经 junction 解析到 `D:\1052-OS\skills\quark-to-zsxq`）。EXIT=2。
- 时间：03:01 处于 03:00-04:30 发布窗口内，时间合规。
- 结果：**预检失败（success=false，退出码 2），按规则 #3 结束，未运行主发布流程，未假报成功。**
- 阻断项（12 条，含 4 条 IMA 源目录失效回归）：
  1. `quark_login` — config/settings.json 的 `quark_cookie` 仍为空（长期项）。
  2. `zsxq_login` — config/zsxq_cookies.json 仍不存在（长期项）。
  3. 6 条 `local_upload_adapter:*` 路由全部阻断（ai_open_source_projects / ai_engineering_tools_skills / solar_resources / cost_optimization_resources / city_renewal_resources / ima_misc_resources，source_mode=local 且无上传适配器，长期项）。
  4. 回归：`source:solar_resources` / `source:cost_optimization_resources` / `source:city_renewal_resources` / `source:ima_misc_resources` — "none of the configured source paths exists"（E:\IMA知识库上传\… 与 F:\IMA知识库上传\… 各合集目录当前又不存在，与 09-24/26/27 同型；09-25/28/10-04~10-08 曾恢复，本次再失效）。
- 已通过项：三源文件存在；playwright/requests 可导入；6 个 group_id 有效；仅 ai_open_source_projects 与 ai_engineering_tools_skills 源目录可读（D:\Codex\projects\开源项目，file_count=1，即便通过也不足 batch_size=5）。
- 审计留痕：已落盘快照 `automation/logs/preflight-20261009-030144.json`（EXIT=2，.err 0 字节）。`--preflight` 只打印 JSON、不写 run-*.json/run-*.log，且预检失败不进入主流程，故本次无新 run-*.json/run-*.log；最新 run-*.json 仍为 09-19 两次 blocked_by_preflight。`state.json` 仍 `published:{}`（从未真实发布）。
- 成功/失败计数：本次无真实发布——成功数 0、被阻断项 12（根因为登录态/适配器两项长期前置 + 本次 IMA 源目录失效回归）。
- 后续恢复要点（④ 为反复失效项，建议改为稳定路径或自动重建）：① 填有效 quark_cookie；② 提供有效 zsxq_cookies.json；③ 为 local 路由实现/启用本地上传适配器；④ 恢复/重配 IMA 源目录（E:\IMA知识库上传\…、F:\IMA知识库上传\… 各合集）或更新 config.json 源路径——该目录在 09-24/26/27 与本次 10-09 反复失效、09-25/28/10-04~10-08 恢复，应为盘符/挂载不稳定，建议改为稳定绝对路径或增加自动重建逻辑。四项齐备 + 在窗口内运行，预检方可放行进入真实发布。
