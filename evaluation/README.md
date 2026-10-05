# 独立证据评价器（T22 / T26）

入口只读已经登记的发布证据；不会重跑产品脚本、导入目标模块、加载目标 AGENTS/Hooks/插件、执行 Shell 或打开任意 URL。目标源码和文档都是待审数据。人类署名始终为 `null/pending`，没有课程总分或置信度。

此实现为 Evaluator Owner 工程候选。mock 校准与 fake 协议检查不构成真实 LLM 校准、独立 QA 或人类验收。正式 E1 审查须另行登记冻结证据并获得 Main 的有限付费 GO。

## 已批准版本和输入

- 产品 `baseline_v1`：`7821af4efe0613c20a80ea164c1dab1c0f288bab`。
- 原始 Main manifest SHA-256：`9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`。
- Main 身份附录 SHA-256：`0b181dda973d62cb3c212b4a85766fe576851f6afd98f19c8e5284e38c87ca53`。
- 正式 Claim 使用修正事实 `baseline_v1:ADD001` / `acceptance-M3-v2.json`。旧 `E012` 保留为 superseded，不能用于一致通过判定。
- `REV001–004` 是 Main 明确批准的身份复核注册记录；初审与修正审查各自保持原貌。身份核验不是产品重跑。
- 契约 `campus-lab-engineering/1.0.0` 保留 R01–R18、A01–A28。目标不能自降 MUST 或自行声明 N/A。K6 的 `NA-DEMO` 只适用于合成校准，不能免除任何实际项目或真人要求。
- `trusted/freeze.json` 固定输入、Schema、11 个 K1–K6 子案例的 SHA-256 和冻结时间；expected 不送模型。`fixtures/cases.json` 集合 hash 为 `58423418e0f336899fbeffc1439f007f73bd4206d54f09e10121235dc56fabe1`。

K1 使用已存在的真实 build/check 证据，判读仍为 mock 时必须标明 mock。K2/K4 是明确标注的合成失败，K3 仅自称完成；K5 包含错 ID、release、contract/version、hash；K6 包含有批准与无批准的 N/A。不得将合成证据写成项目实际执行。

## 使用

在 `D:\深度能力` 使用现有指定解释器，无需安装环境或更改目标依赖：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m evaluation.cli precheck --release baseline_v1
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m evaluation.cli calibrate --fixture-set k1-k6-v1 --mode mock
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m evaluation.cli evaluate --release baseline_v1 --mode deterministic
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m evaluation.check
```

`deterministic` 是默认模式。缺少 LLM 判读时保存确定性结果及最小补查，不替代语义通过判定。明确失败仍为 FAIL；可信 N/A 可按批准依据输出。mock 正式 Claim 默认请求真实判读，不伪装通过。

报告追加到 `evaluation/runs/<UTC run_id>/`。退出码：0 为预检无缺口或校准实际匹配冻结预期；1 为明确失败/校准不匹配；2 为材料不足或批准门拒绝。PowerShell 的外层执行工具有时将非零原生退出映射为 1，应同时查看报告中程序自己的 `exit_code`，不能将两者混写。

## 只读工具和身份

`get_approved_contract(contract_id, version)` 只返回登记契约；`list_evidence(target_release)` 只列该版本；`read_evidence(evidence_id, snippet)` 只读登记的字段或行窗口。没有任意路径、JSON Pointer、URL、Shell 参数。

单文件最多 10 MiB、单片段 16 KiB、单 Claim 总量 64 KiB。完整文件先 hash，再提供有限片段。拒绝穿越、UNC/device/ADS、敏感目录、数据库及未登记证据；所有 symlink/junction/reparse point 均拒绝。Windows 打开时不共享写/删除，复核实际 handle 路径、类型和大小，防止组件检查与打开之间的路径替换越界。

runtime raw SHA-256 从不重写。只有 Main 明确登记 `approved_crlf_to_lf_only` 时才采用 strict UTF-8、仅 CRLF→LF 的 `utf8-lf-v1` 身份；保留 BOM、EOF 和所有其他字节，并报告 `raw_equal=false`。目标不能自选 normalization。60 个源码身份、3 个未提交 runtime 构建产物和 6 个历史 harness 未绑定记录分别保留；历史不匹配不被冒充当前源码通过。

模型引用必须是实际读取的 ID、snippet、release 与 hash；返回前重新打开核验。未知/跨版本/未读取引用拒绝。四状态输出经严格 Schema 验证。K4 会进入 mock/fake/以后获准的 paid 判读路径，报告同时保存模型建议和最终判定；确定性 FAIL 不能被模型 PASS 覆盖。

模型建议通过 Schema、文本和引用检查后才进入 `audit.raw_suggestion`。不合法响应只保存 SHA-256、字节数和受限错误码，不保存其原始内容、未知字段或不合法字段值；合法 K4 的原 PASS 建议与最终 FAIL 均保留。

## 付费边界

`trusted/paid-gates.json` 当前是空批准表。CLI `--mode paid --approval-id ...` 只有 Main 明确 handoff 有限可信 gate 后才可用。gate 固定用途、集合/Claim hash、最大调用数、费用上限、token/timeout、到期时间以及官方 base/model。未来 gate 由 Main 审批并维护可信评价器根配置，目标输入不能提供 gate。

独立 `provider.py` 不导入 backend/main/provider/budget。正式账本固定为原有 `D:\深度能力\data\ai-budget.sqlite`；仅 `mode=rw` 打开已存在的表，校验原 schema/10 CNY cap/frozen，不创建表、目录或新额度。事务预留/结算以 `scope=evaluation` 与既有协议的 1e-9 CNY 整数单位进行，所有项目 scope 共用总额。付费入口预检任何 scope 的 unknown/reserved；每次预留在 `BEGIN IMMEDIATE` 内再次检查整个共享账本，发现任一不确定调用就拒绝，不新增预留、不 dispatch。当前 gate、其他 evaluation gate、game、experiments、probe 均适用。未知/失败/中断保留预留；超界/异常型号冻结。

固定 `https://api.deepseek.com` / `deepseek-flash`，无重定向/环境代理/自动重试；单调用至多 20 秒、1000 输出 token。按完整 JSON UTF-8 字节 `4×bytes+8192` 保守输入界，高峰每百万输入未命中 2 CNY、命中 0.04、输出 8，来源为 Main 的官方费率核对记录。费用是账本上界，不是供应商账单。

凭据只读取可信配置规定的进程变量 `EVALUATION_MODEL_API_KEY`，从不读取 target `.env`。报告只保留受限结构建议、usage/null、型号、call ID 与费用字段，不保存 key/headers/raw body。fake Transport 的账本必须为自有临时 fake DB，并强制不能指向正式账本；CLI 不能选 fake ledger 或任意 transport。

## 未完成

独立 QA、真实 paid K1–K6 校准、E1 正式材料判读尚未完成。冻结基线 A24/A25/A27/A28 没有产品执行证据，不能因本评价器 Owner 已写代码就追溯改成 baseline PASS。A11/A17/A26 部分范围仍按原事实保留；真人签署与教师审批没有被软件推断或替代。

Owner 检查保留两次实现检查失败：早期 source 白名单遗漏，及 Windows fake SQLite fixture 未关闭导致临时清理失败；修正后重跑结果另存，不覆盖失败事实。目标产品没有在这两个检查中执行或修改。
