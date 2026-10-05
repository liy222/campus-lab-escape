# Main 事件登记 handoff v1（未启用模板）

当前生产注册表为空。这里只提供 Main 实际填充方式；模板中的 null、设计缺口、假设 ID/字段不能直接注册。新入口的 Schema 位于 evaluation/schemas/event-registration-v1.schema.json、events-registry-v1.schema.json、event-freeze-v1.schema.json、event-windows-v1.schema.json。旧六个 Schema 保持原字节，manifest 与 Claim 同时经原严格 Schema 校验。

## 顺序与实际字段

1. Main 完成真实事件的只读 QA 后，确定 event_id、release_id、产品 commit。产品 commit 是运行所用版本，不等于当前仓库 HEAD、Evaluator commit 或 QA 工具 commit。现有计划/Runner 的 baseline 绑定及逐行 commit 必须核对，不能靠模板补写实际身份。
2. 选择 2–3 条 Claim，保留原 criterion.must_observe 全文和 declared_na=false。模板示例两条均映射 A24，另可采用 A26；这是方案，Main 需按实际材料定稿。claim_id 不同、同一 criterion 可以重复审查不同关系，但每条 PASS 仍要求该 criterion 完整必要观察，不因 declared_scope 较窄自动通过。
3. Main 列固定 Evidence ID/path/精确 raw SHA256/artifact_binding。每个 ID 必须以 release_id+冒号开头，且不与旧基线/校准或其它事件重名。支持资料角色 support，实际执行材料 execution，真实捕获的身份资料 identity；roles 必须覆盖全部证据。每条 execution 必须恰有一条 runtime_records，不能改成 support 跳过运行身份。
4. runtime_records 指定已登记 identity_evidence_id 和六类真实顶层字段：release_id_field、commit_field、exit_code_field、source_before_field、source_after_field、artifact_hashes_field。字段名都是精确顶层 ASCII 名称，不支持任意 JSON Pointer、代码或递归查询；这些选择器必须彼此不同。source_paths 列该运行捕获 map 的完整原路径集合。
5. identity 的实际数据必须包含：固定 release、真实产品 commit、int 型 exit（bool 拒绝）、非空完整 before/after（原路径→64位小写 raw SHA256）、以及 artifact_hashes（execution Evidence ID→该执行材料 raw SHA256）。before 必须与 after 相等并与已登记 source_paths 集合完全一致。identity 文件必须已经有真实来源且自身 raw 被登记；若原运行未捕获 source before/after，不可后补伪造，需另行说明缺口并获得真实 QA 身份复核材料。不能将当前源码快照伪装为过去运行前后捕获。
6. manifest.sources 的每个条目沿旧 Schema，必须有 candidate_runtime_raw_sha256、git_blob_sha256、git_blob_oid（真实40位 Git blob OID）、utf8_lf_v1_sha256、binding、evidence。这些身份由 Main 真实读取并提供；Evaluator 不调用 Git，不能用零值、任意文本哈希或临时 OID 伪造项目提交。
7. 若后续 CH01 改当前源码，Main 可制作 release/archives/baseline_v1/<原路径> 不可变 raw 副本，并添加 source_locations：原路径→{archive_release_id,archive_path,raw_sha256}。实际 archive_path 强制等于 release/archives/<archive_release_id>/<原路径>。manifest.sources 的键改为实际 archive_path，Git blob 与 raw 身份仍对应真实 v1 原字节。mapping 一对一、完整覆盖 sources 和所有运行 source_paths；每个 archive raw 与捕获的原 runtime raw 完全相等，binding=raw_equal。不读当前 v2 原路径、不将复制日期或归档声明当执行证据。若任一原路径/hash 无法匹配，保留差异并暂缓注册，不静默省略。
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
