# Main 事件登记 handoff v2（实际登记 + 后续模板）

当前只登记 Main 批准的 e1-formal-review-v2 / E1-formal-review-v2，产品版本仍为 7821af4efe0613c20a80ea164c1dab1c0f288bab；旧 e1-formal-v1 未登记。这里只提供 Main 后续实际填充方式；模板中的 null、设计缺口、假设 ID/字段不能直接注册。新入口的 Schema 位于 evaluation/schemas/event-registration-v1.schema.json、events-registry-v1.schema.json、event-freeze-v1.schema.json、event-windows-v1.schema.json。旧六个 Schema 保持原字节，manifest 与 Claim 同时经原严格 Schema 校验。

## 顺序与实际字段

1. Main 完成真实事件的只读 QA 后，确定 event_id、release_id、产品 commit。产品 commit 是运行所用版本，不等于当前仓库 HEAD、Evaluator commit 或 QA 工具 commit。现有计划/Runner 的 baseline 绑定及逐行 commit 必须核对，不能靠模板补写实际身份。
2. 选择 2–3 条 Claim，保留原 criterion.must_observe 全文和 declared_na=false。模板示例两条均映射 A24，另可采用 A26；这是方案，Main 需按实际材料定稿。claim_id 不同、同一 criterion 可以重复审查不同关系，但每条 PASS 仍要求该 criterion 完整必要观察，不因 declared_scope 较窄自动通过。
3. Main 列固定 Evidence ID/path/精确 raw SHA256/artifact_binding。每条 Claim evidence_refs 必须写 expected_raw_sha256，并精确等于对应 Evidence 的 artifact_raw_sha256；coverage.required_refs 只含 evidence_id/snippet。每个 ID 必须以 release_id+冒号开头，且不与旧基线/校准或其它事件重名。支持资料角色 support，实际执行材料 execution，Main 核验固定的身份资料 identity；roles 必须覆盖全部证据。每条 execution 必须恰有一条 runtime_records，不能改成 support 跳过运行身份。
4. runtime_records 指定已登记 identity_evidence_id 和六类真实顶层字段：release_id_field、commit_field、exit_code_field、source_before_field、source_after_field、artifact_hashes_field。字段名都是精确顶层 ASCII 名称，不支持任意 JSON Pointer、代码或递归查询；这些选择器必须彼此不同。source_paths 列该运行身份 map 的完整原路径集合。
5. 本次实际 E1 identity 由 Main 依据 formal admission/原 plan freeze/归档 postcheck，以及独立 T25 experiment map/QA source STOP/归档核对派生。其原 provenance 随 pin 固定，并在预检报告 identity_provenance / identity_derived_by 保留；并非独立即时 runtime 前后快照，也不证明归档曾执行。identity 的实际数据必须包含：固定 release、真实产品 commit、int 型 exit（bool 拒绝）、非空完整 before/after（原路径→64位小写 raw SHA256）、以及 artifact_hashes（execution Evidence ID→该执行材料 raw SHA256）。before 必须与 after 相等并与已登记 source_paths 集合完全一致。identity 文件必须已经有真实来源且自身 raw 被登记；若原运行未捕获 source before/after，不可后补伪造，需另行说明缺口并获得真实 QA 身份复核材料。不能将当前源码快照伪装为过去运行前后捕获。
6. manifest.sources 的每个条目沿旧 Schema，必须有 candidate_runtime_raw_sha256、git_blob_sha256、git_blob_oid（真实40位 Git blob OID）、utf8_lf_v1_sha256、binding、evidence。这些身份由 Main 真实读取并提供；Evaluator 不调用 Git，不能用零值、任意文本哈希或临时 OID 伪造项目提交。
7. 若后续 CH01 改当前源码，Main 可制作 release/archives/baseline_v1/<原路径> 不可变 raw 副本，并添加 source_locations：原路径→{archive_release_id,archive_path,raw_sha256}。实际 archive_path 强制等于 release/archives/<archive_release_id>/<原路径>。manifest.sources 的键改为实际 archive_path，Git blob 与 raw 身份仍对应真实 v1 原字节。mapping 一对一、完整覆盖 sources 和所有运行 source_paths；每个 archive raw 与原 runtime raw 完全相等。binding 保留 Main 实际 Git provenance，可为 raw_equal 或 approved_crlf_to_lf_only；归档实际 raw 校验独立于 Git CRLF binding，绝不采用 canonical fallback。不读当前 v2 原路径、不将复制日期或归档声明当执行证据。若任一原路径/hash 无法匹配，保留差异并暂缓注册，不静默省略。
8. windows 只允许 json_fields、json_claim、lines。json_fields 必须所有字段实际存在；json_claim 必须恰有一个匹配 acceptance_id；lines 的 start/count 为正整数且整段存在（最大 count=200）。每片段≤16 KiB，每 Claim≤64 KiB。identity 的完整 source map 在确定性预检读取，不受模型窗口限制。
9. coverage 对每条 Claim 固定 criterion_id、status full/partial、gaps 和 required_refs。required_refs 必须是 Claim 引用的子集；require_execution 的 Claim 至少有已绑定 execution 证据。partial 必须给具体缺口，阻止模型 PASS；full 只能在实际覆盖 criterion 必要观察后填写，不能代表 72 次成功、教师批准或真人签署。coverage、roles、runtime_records、aliases 全部随 Main 文件 raw pin 固定。
10. Main 按新 Schema 写裸 registration 对象至固定 evidence/integration/event-<event_id>-registration.json（模板外层说明不写入真实登记）。计算实际 raw SHA256，明确 handoff 给 Evaluator。Evaluator 才能写 trusted/events/<event_id>/{manifest,windows,claims}.json，严格投影等于 Main 对象，计算三个 raw hashes并写独立 freeze。freeze 包含 Main path/raw pin、固定 event/release/product commit、原 contract raw、六个旧 Schema raw、三个新输入 raw hashes、Claim/Evidence ID 集合、frozen_at、frozen_before_calls=true；签署保持 null。注册表最后填写 event_freeze_raw_sha256。修正另建版本与新 pin，旧原始证据不覆盖。

## E1 窗口建议与结论限制

当前 Main 报告 formal 因 unknown 调用停止，不能把计划72写为完成72。summary 窗口可选现有 by_variant/row_count/phase/mode/run_id/limits；raw.jsonl 另登记固定代表行窗口，覆盖成功、超时、未调用，以及全部计划分母的独立 QA 汇总；formal plan、已发送 inputs 和 source freeze 另按 Main 精确 path/hash 作为 support。地面判定资料不必全文送判读模型，采用真实隔离检查的 QA 结论与有限字段。

模板 summary 只作为一个执行记录示例，不能仅凭这一个窗口满足两条 A24：Main 应补充实际 raw/plan/inputs/QA 窗口和所有 Claim 必读引用。如果现有 run.json/summary.json 没有统一顶层身份/exit/beforeafter，不猜字段；让真实 QA 身份记录绑定它们的原 raw。所有 execution 材料都登记 runtime_records，不依赖文件后缀推断。

报告必须区分计划分母、实际调用、完成、失败、未调用及 unknown usage/预算，允许停止、不优势或证据不足。工程上可审查是否保留分母、是否地面资料隔离、是否有可核对身份；不能因此证明自然自主整局通关、总体智能、未发生的重试成功或真实课程批准。

## 入口与付费边界

同一窄 CLI 使用 precheck/evaluate --release <已注册 release_id>；不能传 root、manifest、contract、windows、aliases 或任意路径。空表/未知 release/无完整身份在付费 Provider 构造前拒绝。注册后的源码、Main、freeze、Schema、窗口或证据发生变化，停止后续请求并保留实际已发生调用 metadata。

新事件 purpose=claims gate 的 input_sha256 等于整个该事件 freeze 文件 raw SHA256，覆盖 Claim/windows/Main pin 链；旧 calibration/baseline gate 含义不变。登记不授予 paid 权限。原共享账本任何 scope 的 unknown/reserved 都阻断所有新 paid，当前不得真实运行。后续只有独立 QA、有限 Main gate 与安全进程变量映射全部满足，才能单独恢复批准范围；本模板未给预算、凭据或任何真实执行授权。

## 本次固定归档桥接与拒绝记录

legacy source_precheck(baseline_v1) 仅使用安装内 trusted/baseline-source-archive-v1.json 的字面固定指针：evidence/integration/E1-source-archive-20261005.json，raw 0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6。101 Main entries 精确分为60产品与41实验；只60产品旧 manifest paths参与legacy源码核验，Git来源逐项匹配。archive实际raw必须与旧candidate及Mainraw都相等；不认证当前CH01工作区，也不把归档当执行。旧 runtime source map 原路径核验和旧17输入原字节仍保留。

E1 v2 Main固定登记raw 8d60abed1e4746939576e2351f9dbdac055fbbcad91e49d06cedd2b6eb04fef3，102sources（新增1份实际QA harness归档）、13evidence、6execution bindings、2claims。每Claim窗口23906bytes，最大单片段8346bytes。freeze仅声明先于Evaluator判读调用冻结，不声称先于历史实验。原v1缺Claim raw refs不启用，原v2首次预检拒绝公开归档.gitignore记录保留registration-owner-report.json。最小 source=True 例外仅Main固定source alias的release/archives/<safeid>/experiments/.gitignore；默认 evidence/current .gitignore以及.env/secret/binary仍拒绝，路径与handle防护未放宽。

当前不授予paid。原校准与event检查只offline/mock，独立QA仍待稳定候选正式审查。formal22completed/1timeout/49notcalled仅固定材料范围，coveragefull不代表72success或人类签署。

E1 QA窗口的failures字段是检查失败名称list，并非旧tests_run/failures/errors/skipped四int形状。新event仅完整四字段时复用计数算术/类型检查；完整非法记录仍拒绝，非零显式event exit仍主导FAIL。旧baseline/calibration sparse-count检查保持原义。首次mock因此0requests不足结果保留，不视为真实模型或付费失败。
