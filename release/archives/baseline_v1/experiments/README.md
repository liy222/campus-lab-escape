# E1 上下文与下一步建议实验

状态：T22 候选实现；T23/T24 真实实验未执行，须独立 QA 和 Main 的有限 GO。游戏基线 commit 为 `7821af4efe0613c20a80ea164c1dab1c0f288bab`；Main 清单 raw SHA256 为 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`。当前 HEAD 不是冒称的被测游戏版本。

以项目根为工作目录，使用既有 Python，不安装或更改环境：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.runner check
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.runner plan --phase formal
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.runner plan --phase pilot
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.runner mock --phase pilot --scenario mixed
```

所有输出在 `experiments/runs/<独立时间戳目录>/` 追加，已有输出拒绝覆盖。check 是 Owner 本地检查，不能当作独立 QA。mixed mock 显式注入格式失败、超时和未知引用，既不联系模型，也不填写假 token/费用。`plan`、`check`、`summarize`、mock 不读取 `.env`、不构造 DeepSeekProvider。样本生成模块仅用于离线重建，现有样本重复生成会拒绝覆盖。

`fixtures/` 是合法动作前缀产生的公开状态及白名单历史；`ground_truth/` 是离线私有 state 和可接受动作。生成器和判定器可以读秘密关卡，但模型请求构造器不能加载 ground_truth。请求仅含同一系统提示、公开 context 和六工具 schema。每点两次固定背包读取保留重复历史。正确密码只在已发现必要线索的合法历史动作中出现。合成 session/generation 是固定的无鉴权能力标识。

A 为完整历史；B 为可逆字段列布局，保留缺失/null/顺序/重复。两组系统提示相同，同时解释两种表示；当前状态、问题、工具和模型选项相同。调用前验证事实一致性与输入指纹。没有修改游戏原 summary（它是无损分组，不是本实验压缩器）。B 不保证少 token，短历史可能更长。温度和 seed 均未发送；供应商默认值未经独立证明。

每条建议只做一个 generic Provider 请求，tool_choice=none，输出最多1000 token/20秒，thinking disabled，stream=false；不执行模型工具、不会自动通关、不会纠正或替换失败。自有 schema 允许六工具下一步。代码建议引用充分性与引用存在性分开；动作正确性是冻结集合匹配，合法性是私有深拷贝规则执行。自由文本无幻觉不由该判定器全面证明。

正式计划固定72行（12×2×3），配对先后整体18AB/18BA；预试 C02/C06/C12 各两方案，共6行，独立于正式结果。`raw.jsonl` 每个计划行保留一次实际终态；plan.json 保留全部原始未调用行；journal.jsonl 在调用前 fsync。中断时 raw 可能只有前缀，reconcile 生成新的完整72/6行副本，绝不补打调用。原始错误及历史证据保留。

真实调用入口为 `pilot --mode real` 或 `run --phase formal --mode real`，均需要 Main 在 `experiments/authorizations/` 提供单独授权文件及其 raw SHA256。未提供时会在读取凭据前 exit1。授权精确绑定 phase、plan_hash、freeze_hash、max_calls（6/72）、additional_upper_cap_units、到期时间、24小时内重新核对的价格证据及 SHA。正式 GO 还绑定已完成的真实 pilot summary 与 Main 的复核；这些字段只是执行门，没有自动生成或宣称 Main 已批准。一次授权 ID 只可使用一次，失败不得重用补打。

唯一真实账本为原根 `data/ai-budget.sqlite`，scope=experiments，共享 probe/game/evaluation 的 CNY10 总额；不创建新 allowance 或生产账本。每次完整 payload 按 UTF8字节×4+8192输入 token 界与1000输出保守预留，同时满足真实共享剩额和 Main 的更严格 phase 上限。未知 usage、超时、模型/界异常立刻停止；已知费用的其他失败连续2次停止，剩余计划行标为 not_called。缓存用量真实取得才结算，否则保留最大预留。

所有模式使用进程锁，崩溃自动释放 OS 锁。真实调用前记录既有 experiments 账本 IDs。`reconcile --run-dir <目录>` 只读原账本：唯一新增 reservation 可证明付费尝试，上游是否收到仍未知；不能唯一关联则 called/call_id 保持 null。尚有未知关联的中断阻断后续真实运行。不要用成功重试填平失败，或把预写 journal 当 HTTP 已发出的证据。synthetic-real-recovery 是明确标注的本地注入 fixture，不是账本/模型事实。

汇总由逐行数据生成，包括 planned、确证付费尝试及未知数、收到响应、completed、legal、correct、ref-valid 的计数及对应分母；mock 的 paid 分母为0，completed/paid 比率为 null。用量/费用覆盖率与 null 保留，延迟报告中位数与 nearest-rank p95。pilot 与 formal、mock 与 real 不混合。结论只适用于本固定关卡下一步建议，小样本不证明总体智能或自主通关。

HTTP响应由实验层安全transport observer观察，仅保存状态码与true/false/null：已收到401/403/429/503或格式错误200仍为true；连接错误、超时及未完成的付费调用为null；明确未调用为false。模型标准化回复另记normalized_response_received，不用metadata缺失推断未收到HTTP。汇总responses_received是确证下界，responses_unknown显式列出未知，responses_not_received列出确证未调用；投递同样三态。Observer在冻结Provider正常构造后安装，生产仍检查原canonical账本，只接受官方单一endpoint；仅MockTransport可使用明确的本地合成账本。

可信基线检验保留全部60源码、14证据 binding，以及3个 runtime-only构建文件和6条旧QA未绑定记录。canonical CRLF→LF 认同由 Main 清单授权，不冒称所有 raw 相同或独立重验 Git。旧QA文件未绑定的局限原样带入 run 与 summary。
