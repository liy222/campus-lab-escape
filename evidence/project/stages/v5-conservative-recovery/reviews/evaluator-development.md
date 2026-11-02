# 受控评价恢复：Owner开发记录

2026-11-02。本轮普通实现已完成，Evaluator实现Owner SOURCE STOP，待集中独立QA；不是正式QA、核账完成或语义PASS。用户确认接管成功不包含改账或付费授权，当前没有本轮付费gate。

## 文件与行为

- `evaluation/v5.py`新增受控paid入口及纯绑定/wire函数；原REGISTRATION_RAW_SHA256、16项INSTALLATION_PINS、load/precheck/semantic及校准helper保持。原provider/engine/reader/CLI、产品71来源和旧报告未改。
- 新`scripts/preview_v5_evaluation.py`只读取当前登记与已有证据，借原Evaluator与明确mock CaptureProvider构造三份真实engine消息。捕获回复仅为Synthetic IE，不是语义判断；脚本不读gate、Key或ledger，不发HTTP。
- paid报告直接写固定阶段`evaluation/paid-<UTC微秒>-<uuid>/report.json`；非paid沿原历史输出位置。免费preview写`evaluation/preview-<UTC微秒>-<uuid>/preview.json`，不接受target指定输出路径。

paid绑定覆盖active registration raw SHA和20项评价来源身份：原installation16+loader/CLI2+trusted/root-config+本preview脚本。paid-gates文件不进入绑定，避免Main将待批准hash写回gate造成循环；运行期另锁定所选gate和gate文件raw hash。原注册sources和pin不用更新。

读取顺序为：证据身份READY及三项覆盖complete→固定Main gate（唯一approval_id、purpose=claims、绑定、有效期、原Provider配置/限额、max_calls≤3）→ExistingLedger.assert_ready→每条dispatch前再次核验以上条件、wire上界与已用gate额度→lazy PaidProvider。Provider自身的原子reserve/全scope unknown/reserved/frozen/10元cap/有限授权金额保护原样保留。已用完的gate也在Key访问前停止。没有有效批准或证据不就绪，不实例化真实PaidProvider、不读环境凭据、不打开ledger。

每次返回后再核验来源、批准、ledger；IE、invalid输出、Provider异常、中断、身份漂移或新unknown停止余项，0重试。合法FAIL保留，其他固定Claim可继续。Provider元数据按每次attempt保存call_id、usage、wire hash/大小、费用上界和error code；下一次guard失败不会复用上一条元数据。paid/network计数来自Provider的actual_network_call/call_id，而非恒定0；这些是发送attempt，不能当作供应商已收到或已回包的证明。

入口异常/中断会保留已经发生的attempt并输出纯code停止报告，未执行余项为IE；原始异常文字不写报告。身份最终变化使判断失效。若文件系统无法创建/写入报告目录，任何程序都无法保证落盘，本实现不把这种失败当作可恢复付费授权。未更改Provider模型allowlist或费率。

## 最终接口与QA隔离接点

- `paid_input_binding() -> dict`：binding_version、registration_raw_sha256、evaluator_sources、input_sha256；不读gate/ledger/env。
- `paid_wire_bytes(messages, *, max_tokens=1000) -> bytes`：与PaidProvider相同字段及UTF-8紧凑序列化。
- `require_paid_evidence(tools, context, *, expected_binding=None) -> binding`：纯身份及coverage门。
- `fixed_paid_gate(approval_id, input_hash) -> (gate, gate_file_raw_sha256)`：仅固定`evaluation/trusted/paid-gates.json`，无自选路径或旧gate豁免。
- `prepare_paid_provider(tools, context, approval_id, report) -> GuardedV5PaidProvider`：先纯门与ExistingLedger readiness；真实PaidProvider仍lazy。
- `evaluate_paid_claims(files, tools, context, approval_id, report) -> exit_code`：最多原三项、停止余项、合法FAIL保留。
- preview `build_preview(*, max_tokens=1000, timeout_seconds=20) -> dict`：PREVIEW_ONLY、三claim的wire_sha256/wire_bytes/input_token_bound/output_token_cap/cost_upper_units、total/peak cost、绑定/profile及明确Synthetic/真实访问0。

QA应在`evaluation.v5`命名空间patch ExistingLedger/PaidProvider/fixed_paid_gate/paid_input_binding，或明确TEMP路径的既有FakePaidProvider。ledger fake需assert_ready返回remaining_units，并提供仅查询同approval allowance的_connect（或用TEMP ExistingLedger._fake_path）；禁止调用默认真实ledger构造。report最少初始化paid_attempts=[]/credentials_accessed=false/ledger_opened=false。不得把内存Synthetic gate字典写入真实批准文件。

## 实际检查与退出

- ab4bf7、25e6dc、72efce均exit0：只读计划、Provider、CLI、engine/reader和根配置。首次误读`evaluation/root-config.json`产生非终止找不到文件提示，随后定位正确的`evaluation/trusted/root-config.json`；没有读取批准内容或真实ledger。
- 中断恢复49f53c exit0：确认中断前两个文件确已落盘；此前没有Owner测试或SOURCE STOP结果，不假定完成。
- 37981a exit0（1.2381486秒）：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -`运行有限内存fake开发检查。包括缺批准/坏证据先停、max4/过期/错绑定拒绝、lazy provider、后续unknown与元数据清空、已用完gate在凭据前拒绝、合法FAIL保留、IE后0余项调用、unexpected paid异常在自有TEMP写停止报告，以及Synthetic capture/wire/原pin与旧helper AST检查。所有批准数据只在内存，所有ledger/provider均替身；无真实数据库构造、环境凭据读取或网络。TEMP合成异常报告自身exit2是预期停止结果，不是实际paid运行。
- 800201 exit0（0.4014954秒）：最后只做语法/静态身份核对，active registration pin仍匹配原值、16项安装raw均匹配，CLI raw与此前实际报告绑定相同；新paid目录带uuid。目录接线在fake开发组之后按Main要求调整，没有重复整组检查。

实际结果：`automated/evaluator-owner-development.json`、`automated/evaluator-owner-static.json`。Owner未运行正式QA、原C1-C3节点、build/browser、实际precheck/deterministic CLI或免费preview主程序；没有真实Key、ledger写入、付费gate或模型请求。

## 待完成与限制

QA接必要隔离验证，Main在稳定复核后只执行一次真实只读dry-run与免费preview。具体apply差异和新付费次数/总额须随后交本人明确批准；本轮没有授权执行。preview按现有锁定峰值费率输出保守上界，不是账单。登记READY不自动批准付费，接管成功不豁免费用/unknown/批准门，也不证明新付费路径已真实成功。

本轮没有验证`EVALUATION_MODEL_API_KEY`是否存在，没有读取.env或任何实际Key。未来只有具体批准、证据和账本均就绪后才进入原Provider的凭据读取；若变量缺失，原`MISSING_EVALUATOR_CREDENTIALS`在本地停止，不发请求、不承诺真实评价必然能发出。没有新增凭据路径或修改冻结Provider。
