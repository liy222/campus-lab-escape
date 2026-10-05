# T27 / E1–E3 独立事件登记设计 v1

状态：设计和未启用模板。Main 已原则同意独立登记层；尚未收到编码 GO、事件精确 pin 或真实付费 GO。本目录不被现有 CLI 加载，不代表事件登记完成、测试通过或课程批准。

## 旧边界与事实

本次只读核对独立 QA 的 193 项、0 失败和 34 条 source_before/source_after；当前 34 源 raw hash 匹配。旧 Owner 114 项、mock 11 案例、baseline precheck exit 0 是局部历史结果。独立 QA 验收在 review/findings/T26-acceptance-20261003.md，不能等同真实 LLM 校准。

旧 trusted/freeze.json、fixtures/cases.json、contract/windows/claims-baseline 及所有旧 Schema 保持原字节。旧 baseline_v1 A24/A25/A27/A28 的 NOT_RUN 和 A11/A17/A26 的 PARTIAL_SCOPE 不追溯改写。原 10 CNY 共享账本、Provider 和有限门协议保持既有边界；本次未打开账本或凭据。

## 可信登记链

新增 evaluator 安装内 trusted/events-registry-v1.json。注册表只列 Main 明确 handoff 的事件 ID、release_id、product_commit、固定 Main integration 登记路径和精确 raw SHA256，以及该事件 freeze 路径和精确 raw SHA256。只有安装内固定注册表可选择登记记录；CLI 只接受已登记 ID/release，不接受 manifest/contract/windows/claims 路径、URL、自由归一化或目标配置。

每事件新增 trusted/events/<event-id>/{freeze,manifest,windows,claims}.json。Main integration 原始登记记录为 authority 输入，需先 exact raw hash，后 strict JSON，再严格字段与跨文件身份校验。manifest 是 Main 登记材料的受限投影，沿用旧 manifest.schema；claim 项沿用旧 claim.schema，判读及报告沿用旧 suggestion/output.schema。不从目标自声明导入证据、不 glob 外部目录、不运行目标任何代码。Main 登记内容即使经过批准，也不能视作事件实际验证结论。

每事件 freeze 固定 Main raw pin、release/product commit、旧 contract raw hash、旧 Schema raw hashes、新 manifest/windows/claims raw hashes、固定 Claim ID 与 evidence ID。先写输入，确认实际字节，再形成 freeze；注册表最后 pin freeze。禁止零 hash/占位 SHA/空 sources 被伪装成真实身份；缺字段拒绝，模板 null 不激活。不可在冻结之后重写输入：修正另立版本和新 pin，原文件及历史结果保留。

事件 release ID 不与 baseline/calibration 或其他事件重复；证据 ID 全局唯一，引用与 release 一致。注册表、Main 登记、freeze、manifest、claims 的 event/release/product commit 必须完全一致。manifest commit 是产品 commit，不混成 evaluator/QA 提交；其它代码身份由来源记录精确区分。

## 运行身份与读取前后绑定

登记明确哪些 Evidence ID 是运行记录，以及每条记录的 release/commit/source_before/source_after 字段选择器。选择器是实现支持的固定顶层字段名，不提供任意 JSON Pointer。source_precheck 目前仅对 run.json/summary.json 自动核对运行 map，新增事件不得用文件名决定是否校验；result.json 和其它登记运行记录同样必须检查。

必须读整份已登记运行记录并 exact raw hash，校验非空 before/after dict、合法相对源码路径、64位小写 raw hash、before==after，逐项绑定 manifest.sources.candidate_runtime_raw_sha256 与固定提交。Main 若提供不同字段名，先明确映射并冻结；未提供不猜测字段。若运行期间源码未变但不等于注册身份，同样拒绝。旧 manifest source Schema 还要求 git_blob_sha256/git_blob_oid/utf8_lf_v1_sha256/binding/evidence：只有 Main 可提供真实值，Evaluator 不调用 Git 或捏造 OID。

默认事件 artifact_binding/source binding 为 raw_equal；任何 CRLF→LF 例外必须由 Main 显式 pin，保留原 raw hash 与 raw_equal=false，不能自动清理 BOM/EOF。源码与证据仍使用既有 safe_read，拒绝重解析点、敏感路径、越界、二进制/数据库；文件/片段/Claim 限额仍为 10 MiB/16 KiB/64 KiB。

在预检、每次模型 dispatch 之前、结果写出之前重核 registry/Main/freeze/输入身份及 source/evidence；模型引用仍以实际读出的有限 snippet ID/hash 为依据，重新读取比较。变化后输出证据不足并停止剩余调用，保留实际已发生调用的 metadata，不报 0 掩盖消耗。付费 provider 的 reserved/unknown 阻断和费用事务不绕过。

## Claim 与范围

每事件 2–3 条固定 Claim。建议 E1 为 A24、A26；E2 为 A27、A13；E3 为 A17、A21、A23。这只是候选选择，Main 可按实际事件材料冻结；没有材料不能登记为通过。E1 只支持固定检查点下一步建议，不证明整局自主通关或总体智能；E2/E3 无教师批准时只能工程预演，不能产出课程批准。每条 statement 保留旧可信 criterion.must_observe，declared_scope 写实际执行范围，declared_na=false。

Main 登记需逐 Claim 固定 scope_limits/coverage_gaps 和最小必读 evidence/snippets。目标 known_scope_status 不作为可信通过依据。部分范围不满足 full criterion 时，工程局部事实可以保留，四状态仍为 INSUFFICIENT_EVIDENCE；不能通过自缩 statement、删 MUST、宣称 NA 或把 Main pin 当执行证据取得 PASS。相邻事件可各有 Claim，不通过合并身份伪造覆盖。同一 release 的证据缺口不能靠别的 release 引用补足。

窗口仅允许旧 json_fields/json_claim/lines 三种固定配置。字段、行起点、行数、criterion、必读 snippet 由 Main 登记后 pin；严格验证未知 kind/字段/负数/bool 当整数/重复 ID/空选择器。运行前后源码 map 的完整确定性核对不受模型片段截断影响。registration-template.json 和 event-input-template.json 的 null 均是待 Main 填充项，不是 active Schema 输入。

## 编码和有限运行门

编码 GO 后拟新增 evaluation/events.py，窄改 trust.py/cli.py/engine.py 的事件加载与身份检查；旧 freeze/cases/contract/windows/claims-baseline/Schema/provider 不改。新 event registry/schema 若需增加，独立版本化，不混进旧 freeze。README 和 review/calibration.md 只有明确 handoff 后更新准确状态。Owner 只做本地协议检查；稳定候选再交独立 QA，不自署正式 QA。

先登记和 deterministic precheck；unknown event、hash mismatch、跨版本/重复引用、缺 before/after、source/commit 变化、target 自改标准和过大窗口均应在 provider 构造前拒绝。模板、注册或预检都不授予付费权限。真实 K 校准只准 frozen 11 case set；只有 K1/K2/K4 进入模型路径共 3 请求，其余 8 为 deterministic。Main 已给预算上界 219496000 单位（0.219496 CNY），本次未重新实测或声称发生费用。

随后 Main 提供有限 calibration gate 与进程凭据映射才能执行真实校准。事件判读另需 purpose=claims 且 input_sha256 固定到该事件 freeze（包含 Claims 与整条身份链）的独立有限门；最大请求数按实际 2–3 Claims，预算仍从原唯一账本扣除，绝无新增额度。若设计选择改用 claims raw hash，必须同时 gate 绑定完整 event freeze，避免同 Claim 被重定向至不同证据。任何 credentials/unknown/reserved/expiry/fee 异常停止，不自动重试或补跑。

## 尚缺 Main 输入

编码 GO；注册表实际安装路径和版本 pin；每事件 ID/release/product commit；Main integration 固定路径/精确 raw hash；sources 真实 raw/Git identity；运行记录字段及 before/after map；证据 ID/路径/hash；2–3 Claim 和范围限制；固定 snippets；独立 QA 门；随后有限真实校准门和安全进程密钥映射。当前无真实校准、事件判读、人类签署或教师批准。
