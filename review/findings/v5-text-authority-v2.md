# 生成文案权威 v2：独立 AI QA

2026-10-26。**有限合成专项联合通过；不是单次全绿，也没有 v2 真实模型质量样本。** 执行者为独立 AI QA 智能体，没有真人或教师试玩/签字。旧 BP-REAL-NARRATIVE-01 仍 OPEN，旧文本不自动修复。

实际只执行两条正式命令（解释器均为 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8`）：

| 命令尾部 | 实际结果 |
| --- | --- |
| `evidence/upgrade/v5.0/text-authority-v2/qa/run_targeted.py --candidate evidence/upgrade/v5.0/text-authority-v2/candidate.json --output evidence/upgrade/v5.0/text-authority-v2/qa/run1` | `f81c39` exit1；79项：48通过、30失败、1错误；JUnit5.431秒。 |
| 同runner，`--candidate evidence/upgrade/v5.0/text-authority-v2/candidate-qa-fixed.json --output evidence/upgrade/v5.0/text-authority-v2/qa/run2 --nodes-file evidence/upgrade/v5.0/text-authority-v2/qa/run1-failed-nodeids.json` | `0913ae` exit0；仅真实失败/错误31项通过，JUnit5.848秒；不重复48项。 |

首次错误来自QA脚本误挡Windows asyncio标准库socketpair内部连接，API错误为连带事件环失败。原日志/JUnit/guard及exit1完整保留。只修runner：线程局部标志仅包围原socketpair、finally恢复，仅其内部127.0.0.1/::1连接可用；其他socket/真实HTTP/config/非TEMP DB门保留。窄补实际禁止边界尝试0、标准库内部IPC连接141，后者不是外网/provider调用；原guard31不能解释为31次外部请求。无产品修复、无真实付费。

两个来源epoch产品完全相同。当前固定候选420输入 bundle `15e9e46eca8db586e7b5225be8c2138ed8563e92c03b14100e2bd4cd9abfaa89` 全匹配；首次419与之仅QA runner不同，并新增冻结的31节点列表。两次各自before/after匹配。完整输入表在候选文件，不复制到报告。

TXT-C1–C5有限覆盖：18合同×两组受控参数纯schema/组装/派生等价，v1历史结构/Schema保留；有效v2基线后验证错版本、额外description、typed/raw坏例拒绝且不进v1 helper。两族角色/四机制/三配方、改名+旧槽诱饵及40字名称检查；两族未观察/已观察/部分/完整资料四阶段保持原发现门，无提前答案/后房物件。两个代表场景经真实ProductionService+MockTransport、原API准入/witness到EXIT、隔离存档/重开恢复与owner边界；每请求一次、Key/profile/cap及坏回复/超限/异常保护保留。旧完整v1定义的文字/hash恢复reload不调用内容服务，坏hash拒且状态不覆写。18纯矩阵未重复solver，未做无关经典/伙伴/jobs全套或UI/build/eval。

完整请求计量（3/hard，原cap0.20元）：

| 家族 | 6字短主题 | 2000个四字节字符 |
| --- | ---: | ---: |
| position_v1 | 0.133464元 | 0.197320元 |
| mapping_v1 | 0.157200元 | 0.221056元，超cap |

上表来自纯计量，不是账单。另在窄补的现有provider测试中，合法分支只经MockTransport发一次，mapping超cap在预占/发送前拒绝且fake ledger不变；没有提高上限或声称所有合法长度主题均可付费发送。

原v1直接测试、runtime禁用fixture及onecall/Key/budget断言保留，GenerationService非prompt AST只归一化精确两处模块import。旧报告/seal/log字节不改；旧item-context seal16包含的测试源码条目属于历史epoch，当前获准v2适配后不能宣称它仍等于current。9eea893的Gitblob精确匹配其旧raw SHA `51c667b4…`，不作换行转换；其余公开旧证据及53注册来源匹配。注册评价不因此覆盖新v2模块。新跨namespace观测仅写获准全新子目录，归本候选；未覆盖旧观测。

封存前metadata审计 `de128c` exit1为上述历史源码被误作current的断言错误，写入前停止，非第三次测试失败；`63ff55`/`44f54e` exit0定位并证明历史raw，原件未改。其他命令/哈希与有限日志隐私检查见integrity.json；末次封存命令exit0。四份raw输出/JUnit有限凭据模式检查0（公开合成CANARY除外），不读取实际Key做比较，不保证所有编码。原失败输出不打印、不改写，无需脱敏副本。

本轮仅合成TEMP DB/ledger与注入传输，未读取真实私有raw-sensitive/投影、玩家DB、配置Key或实时账本；真实provider/外网/付费0。模型名称、故事、房间氛围仍可误导，Host说明的有限检查不保证任意主题语义、真人难度或实际生成可靠性。新报告/result/seal SOURCE STOP，不提交、不推送、不提出付费复测。
