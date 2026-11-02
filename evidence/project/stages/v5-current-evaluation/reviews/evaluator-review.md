# 当前有限评价登记：独立只读复核

2026-11-02。本轮由既有Backend临时承担独立Evaluator角色；未制作新proof、登记或pin，也未运行产品、测试、评价CLI、模型或账本。QA执行者与Main规范化职责按实际记录保留；不推断恢复后的运行型号。

## 登记前判断

**可以由Main将当前提案原字节填入固定登记，并仅更新REGISTRATION_RAW_SHA256行；本次未发现阻断缺陷。** 这是证据身份、来源、有限覆盖与窗口的复核结论，不是模型语义PASS、全版本通过或真人接受。提案为`evaluation/current-registration/registration.proposed.json`，raw SHA256为`ee7b394208c5e1c5e8df107c053692db322b23bec1801d1e372bd63e6f55c7de`。

实际观察来自唯一运行`automated/current-evidence-20261102T064847Z-6770f20d/result.json`：2026-11-02T06:48:47.493168Z至06:48:53.178208Z，四个原定节点，pytest及runner均exit0。Evaluator只读了已存在结果与形成这些观察的测试源码，没有重跑它们。C1输入与fixture账号是Synthetic；当前编译器、规则、鉴权API与存储的执行是真实发生的，不能把这两层混为虚构产品执行或真实AI生成质量。

## 已核对内容

- 三份Main-derived proof的checks来自四份实际观察，逐数组/逐行相等。C1包含9个不同房数/难度的实际准入与正步数EXIT回放，以及20个不同坏例；reference/dependency/semantic/layout各5。逐case的输入hash与冻结输入相同；原测试将`semantics`标签投影为`semantic`，Main没有再造行或改分类。
- C2的owner/intruder不同，11个请求逐行复制，包含read/restore，全部404且目标状态前后hash相同。C3包含3个不同moment_id及不同saved_state hash，恢复hash等于保存hash、定义hash相同；一个checksum坏档409拒绝且当前状态hash不变。坏档观察整行保留。
- 实际source_before/source_after各71项，含字节数的原列表相同、无重复；规范化为字典后恰等提案sources及三份proof前后字典。逐文件读取当前raw SHA256及字节数相同，不采用换行归一替代raw身份。
- 四份实际helper JSON与固定入口副本逐字节相同。9项登记涵盖三proof、实际result、四观察与原输入；各文件raw hash与proof provenance一致。来源声明区分QA实际执行、Main规范化、Synthetic输入与未测试的真实AI质量；源码被绑定不等于每个模块的行为被测试。
- installation恰等加载器的16项INSTALLATION_PINS，当前raw全部相同；没有将带登记pin的evaluation/v5.py或registration本身纳入自引用。登记前时点，旧活动登记与原字节归档及旧pin相同，旧loader raw hash也仍与上下文记录相同。本轮不改旧合同或安装固定项。

按`reader.read_evidence`实际`json.dumps(..., ensure_ascii=False, sort_keys=True, allow_nan=False)`方式计算UTF-8窗口：

|窗口|字节|
|---|---:|
|V5-C1 proof|9465|
|V5-C2 proof|5941|
|V5-C3 proof|5020|
|RAW1 result|1373|
|RAW2 C1观察|6567|
|RAW3 C2观察|2825|
|RAW4 checksum观察|434|
|RAW5 moments观察|1356|
|RAW6 原输入首行|2|

全部不超过16384字节，文件均小于10MiB，每claim只引用一个proof窗口、合计小于64KiB。原输入的两字节窗口只是已绑定文件的身份入口，不作为合成输入全量内容的语义证明。三claim均通过json_fields选择claim_id/checks/provenance/release/candidate/exit；来源前后字典由precheck在模型窗口外读取。

## 评价器与限制

加载器/engine源码表明：READY只检查固定身份与覆盖；没有provider的deterministic评估不会给语义PASS，缺少批准的LLM证据解释仍须保留INSUFFICIENT_EVIDENCE；实际失败不能被覆盖。paid路径先停止于PRIOR_CALL_UNKNOWN_STOP，不打开ledger、读Key、创建PaidProvider或发送请求。本次只读源码确认，没有调用该路径探测、读取或改动任何真实账本。

有限C1-C3不覆盖任意生成、36结构变体、UI、普遍安全、真实模型质量或真人难度。没有新付费批准、模型判断、同伴/教师结论或真人接管事实；本人接管仍待实际进行。独立复核未将规划或“继续”写为完成。

## 实际只读命令

下列编号是本轮工具实际结果标识；读取与纯数据比较均未导入目标产品或评价器模块。

- 866d2f exit0：读取计划、README、proof.template及文件清单。误尝试不存在的`evaluation/v5/schema.json`产生PowerShell非终止读错误；随后以正确的`registration.schema.json`完成读取，无文件修改。
- d29455、092ed1、eefd31均exit0：Get-Content/rg读取登记schema、合同、加载器/reader/engine、旧登记与旧proof格式，核对原窗口和门控实现。
- 58b7d9 exit0：读取实际runner源码、result和规范化摘要；长输出展示被截断，后续按字段解析核对。
- 96a885 exit0：`python -B -X utf8 -`仅解析三proof元数据和提案各窗口/安装项。
- d11327 exit0：Get-Content/rg只读四个既有测试如何形成观察与归档目录，不执行测试。
- bb94d7 exit0：标准库只读逐行相等性与旧pin上下文，输出字段名/布尔值，不导出账号或私有状态值。
- d0bf2c exit0（0.4677617秒）：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -`进行一次纯数据比较与schema验证：71当前raw身份、4副本、3proof、9登记/窗口、16安装项及旧archive/active/pin；issues为空。未运行pytest或evaluation.cli，也不生成新的测试观察。

## Main最终执行结果

Main已将提案原字节写入active registration，raw SHA与登记前审核提案相同。当前pin与该raw SHA一致；把loader的唯一pin字面值替换回旧值后，其原字节SHA恰等旧loader上下文及activation.loader_raw_before，证明除该字面值外没有改加载/门控逻辑。16个安装固定项未变，旧登记原件仍可追溯。此结论来自字节比较，不是再次执行评价器或paid探针。

|Main实际命令|实际退出/状态|只读复核|
|---|---|---|
|`python -B -X utf8 -m evaluation.cli precheck --release v5.0-engineering`|exit0，READY，issues=[]|71源码、3条运行绑定及评价器前后身份稳定|
|`python -B -X utf8 -m evaluation.cli evaluate --release v5.0-engineering --mode deterministic`|exit2，三项INSUFFICIENT_EVIDENCE|初末precheck均READY，deterministic findings为空|

两个原始报告分别来自`evidence/upgrade/v5.0/evaluator-owner/runs/20261102T065647753871Z/report.json`、`20261102T065648260580Z/report.json`，固定入口[current-precheck.json](../evaluation/current-precheck.json)、[current-deterministic.json](../evaluation/current-deterministic.json)均逐字节等于原件。具体命令/归档出处见[cli-results.json](../evaluation/current-registration/cli-results.json)。71项当前源码、9项登记证据以及评价器报告前后身份的当前raw SHA全部一致。

三项实际IE原因均为`LLM evidence interpretation not run.`，唯一missing_check为`Run approved LLM judgement; no model was called.`。三项audit均`execution_evidence_found=true`、`failures=[]`、`issues=[]`；因此本次不是源码漂移、缺少9/20或恢复行、合成输入被错当虚构观察，也没有检测到实际失败。它仍缺批准的LLM证据解释，不能写为语义PASS。每项实际model请求为0，两次报告均paid/network0、credentials_accessed=false、ledger_opened=false；真人与教师结论仍未发生。

最终只读命令：ae5b1f exit0读取activation/CLI出处和README；606e69 exit0（0.29354秒）以`python -B -X utf8 -`比较active/proposal、唯一pin字面值、旧loader、当前71/9身份、两原报告/归档字节及三项真实缺证原因，issues=[]。未导入产品或评价模块，未运行CLI、测试、模型、Key或账本。

文档收尾ef15b7 exit0（0.2546038秒）：仅用标准库核对本轮两份文档的16个本地链接，缺失0，不执行产品或评价器。

Main另授权更新`evaluation/v5/README.md`当前状态、旧登记归档和本轮报告链接；该README不在登记sources或INSTALLATION_PINS，不需更改pin。旧Oct27/Oct28记录明确标为历史并保留数据。**本阶段Evaluator工作SOURCE STOP**；完成当前有限登记复核，真实语义判断与本人接管仍待，未作整体接受声明。
