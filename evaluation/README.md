# 独立证据评价器（T22 / T26）

入口只读已经登记的发布证据；不会重跑产品脚本、导入目标模块、加载目标 AGENTS/Hooks/插件、执行 Shell 或打开任意 URL。目标源码和文档都是待审数据。人类署名始终为 `null/pending`，没有课程总分或置信度。

旧 T26 实现已由独立 QA 接受（193 项、34 源，见 `review/findings/T26-acceptance-20261003.md`）。新增事件登记层已由独立 QA 检查；2026-10-06 的 2e977 提示版本8次有限真实判读另有75/75独立QA。校准11/11含3次真实判读及8项确定性对照；E1两条PASS只覆盖冻结登记Claim与原72状态行；CH01三条PASS只覆盖冻结工程Claim。它们不构成人类验收或完整真实LLM校准。

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

提示中的 `snippet` 是登记窗口标识符，例如 `summary`，不是证据引文或行文本。`TRUSTED_OUTPUT_CONTRACT` 位于 `TARGET_DATA` 外，包含原冻结 suggestion Schema，以及 Tools 实际读取并核验 release/hash/handle 后形成的 `{evidence_id, snippet}` 白名单。模型须逐字复制合法 pair，只返回 Schema 字段和紧凑 JSON；建议 reason 不超过240字符，missing_check 必要且简短，选择足以支持完整范围的少数引用。简短输出不降低 MUST，不指定应判状态，也不改变严格引用复核、失败优先规则、1000 token 或20秒限制。2026-10-06 提示修正的离线SOURCE STOP与随后2e977版有限真实判读分开登记。新真实结果见 `review/findings/T27-revised-real-result-20261006.md` 和 `evidence/qa/T27-revised-real-result-20261006T045000Z/result.json`；75/75 SOURCE STOP。旧6条输出原样保留，不能重发。

## 付费边界

`trusted/paid-gates.json` 是 Main 维护的当前有限批准表；历史空表不代表当前配置。CLI `--mode paid --approval-id ...` 只有 Main 明确 handoff 有限可信 gate 后才可用。gate 固定用途、集合/Claim hash、最大调用数、费用上限、token/timeout、到期时间以及官方 base/model。目标输入不能提供 gate，本次提示修正不新增或清空批准，不授权任何真实调用。

独立 `provider.py` 不导入 backend/main/provider/budget。正式账本固定为原有 `D:\深度能力\data\ai-budget.sqlite`；仅 `mode=rw` 打开已存在的表，校验原 schema/10 CNY cap/frozen，不创建表、目录或新额度。事务预留/结算以 `scope=evaluation` 与既有协议的 1e-9 CNY 整数单位进行，所有项目 scope 共用总额。付费入口预检任何 scope 的 unknown/reserved；每次预留在 `BEGIN IMMEDIATE` 内再次检查整个共享账本，发现任一不确定调用就拒绝，不新增预留、不 dispatch。当前 gate、其他 evaluation gate、game、experiments、probe 均适用。未知/失败/中断保留预留；超界/异常型号冻结。

固定 `https://api.deepseek.com` / `deepseek-flash`，无重定向/环境代理/自动重试；单调用至多 20 秒、1000 输出 token。按完整 JSON UTF-8 字节 `4×bytes+8192` 保守输入界，高峰每百万输入未命中 2 CNY、命中 0.04、输出 8，来源为 Main 的官方费率核对记录。费用是账本上界，不是供应商账单。

凭据只读取可信配置规定的进程变量 `EVALUATION_MODEL_API_KEY`，从不读取 target `.env`。报告只保留受限结构建议、usage/null、型号、call ID 与费用字段，不保存 key/headers/raw body。fake Transport 的账本必须为自有临时 fake DB，并强制不能指向正式账本；CLI 不能选 fake ledger 或任意 transport。

## 未完成

事件层及 CH01 身份映射已有对应独立 QA，真实付费有限记录见 `review/calibration.md` 与 T27 独立结果；新校准11/11含3次真实调用与8项确定性对照，原10/11报告仍保留。E1两条、CH01三条实际模型判读均证据不足。冻结基线 A24/A25/A27/A28 没有产品执行证据，不能因本评价器 Owner 已写代码就追溯改成 baseline PASS。A11/A17/A26 部分范围仍按原事实保留；真人签署与教师审批没有被软件推断或替代。

Owner 检查保留两次实现检查失败：早期 source 白名单遗漏，及 Windows fake SQLite fixture 未关闭导致临时清理失败；修正后重跑结果另存，不覆盖失败事实。目标产品没有在这两个检查中执行或修改。

## 独立事件登记 v1

`trusted/events-registry-v1.json` 默认为空；未知 release 在构造付费 Provider 前拒绝。Main 按 `schemas/event-registration-v1.schema.json` 写入固定 `evidence/integration/event-<event_id>-registration.json` 并提供精确 raw SHA256；Evaluator 只能在 Main handoff 后填写独立事件 manifest/windows/claims/freeze，注册表最后 pin freeze。目标不能指定路径、修改标准、选择配置或授予付费许可。

事件复用原 contract、六个旧 Schema 和四状态，原 freeze/cases/contract/windows/claims-baseline 字节保持。每事件 2–3 条精确冻结 Claim，statement 等于可信 criterion.must_observe，引用包含原 raw hash；Main 的 coverage 固定必须读取的窗口和未覆盖范围。partial 返回证据不足；不以自定义 statement、known_scope_status 或 N/A 降低 MUST。

所有 Main 登记的 execution 记录均通过 runtime_records 明确绑定 identity 记录，检查 release/product commit/实际 exit、非空且完整相等的 source_before/source_after、每份执行材料的 raw hash，不依据 result/run/summary 文件名猜字段。identity 记录须来自 Main 核验的真实来源。本次 E1 是 Main 依据历史 admission/plan freeze/归档 postcheck 与独立 QA source STOP 派生的身份绑定，原 provenance 在预检结果保留，未声称独立即时运行快照；登记或归档不等于执行。窗口只允许原 json_fields/json_claim/lines，缺字段、空窗口、非法行界和过大片段均阻断。

可选 `source_locations` 仅来自 Main 的精确 pin：原 runtime path 一对一映射至 `release/archives/<archive_release_id>/<原路径>`，固定 raw hash 与真实 Git blob 身份。manifest.sources 使用实际归档路径；运行前后 map 保留原路径并完整绑定。当前 v2 改动不会被当作历史 v1 身份，归档差异仍拒绝；不读取目标 Git 或执行目标代码。

事件进入、每次 dispatch 前、判读后及报告写出前重新核验整条注册链、源码与证据；身份变化阻止后续请求，并保留已经发生的调用 metadata。新事件 paid gate 的 input_sha256 固定到整个 event freeze raw SHA256；旧 calibration/baseline gate 含义保持。空注册表不产生真实事件结论；门、账本和凭据仍需独立有限批准。

Main 准确填写指南与未启用模板位于 `evaluation/runs/20261005-event-main-handoff-v2/`。局部检查入口为指定 Python `-B -X utf8 -m evaluation.check_events`；它仅使用隔离合成 Main fixture 和 mock，原失败报告保留，不代替独立 QA、正式实验或付费校准。

Main 已明确登记 `e1-formal-review-v2` / `E1-formal-review-v2`，产品仍为原 v1 commit，实际102归档源码、13证据、6显式执行绑定、A24/A26两条冻结Claim。原 `e1-formal-v1` 登记缺raw refs，保留但未启用。v2只是有限材料登记，不能把22完成、1超时、49未调用说成72成功。单片段最大8346bytes、每Claim23906bytes。

`source_precheck(baseline_v1)` 的最小固定归档桥接只接受 `trusted/baseline-source-archive-v1.json` 指定的 Main archive record/raw pin，精确选择原产品commit的60条，41实验条不冒作产品。逐项旧manifest Git身份、原路径和candidate/Main/实际archive raw相等；原运行map核验保持。报告明确只读archive、archive未执行、未认证当前CH01源码。旧freeze/cases/contract/windows/claims和paid-gates原字节不变。

事件archive raw永远exact，不因Git CRLF provenance而允许canonical fallback。唯一公开无扩展名源码例外是Main固定alias中 `release/archives/<safeid>/experiments/.gitignore` 的source read；默认evidence/current及敏感文件规则仍拒绝。


## 2026-10-06 新提示版本有限结果

提示版本 raw SHA `2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c` 的校准、E1、CH01报告分别为 `evaluation/runs/20261006T043749352975Z/report.json`（3次付费；11/11含8个确定性对照）、`evaluation/runs/20261006T043806611760Z/report.json`（2条 PASS，绑定原登记E1计划状态22/1/49）和 `evaluation/runs/20261006T043822902164Z/report.json`（3条工程Claim PASS）。全部以 `review/findings/T27-revised-real-result-20261006.md` / `evidence/qa/T27-revised-real-result-20261006T045000Z/result.json` 的75/75独立SOURCE STOP为准。原6次旧源结果、旧校准10/11与所有历史证据均保留。
