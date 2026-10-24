# v5 Host 骨架 / AI 内容生成：独立定向 QA

日期：2026-10-24。结论：**本次有限离线范围联合通过；无产品 finding**。这是新内部生成合同的工程验证，不是实际模型生成成功、叙事质量、真人试玩或 v5 整体发布验收。

## 来源与执行边界

首候选为 `v5.0-blueprint-8dde2fe2604a5bfd`，文件 `evidence/upgrade/v5.0/blueprint-generation/candidate.json`，409 来源。首次 QA 发现两项测试协议错误后，Main 仅重新冻结一个 QA 文件，形成 `v5.0-blueprint-qa-fixed-ba75ae39ab3302c5`，文件 `candidate-qa-fixed.json`，409 来源。产品字节没有修正。所有正式命令各自记录了候选、实际命令、退出码与来源前后哈希。

新测试独立编写，生产实现与此 QA 分属不同 Owner。QA 仅改分配的测试、报告及本 epoch QA 证据；未改产品、旧测试装置、旧报告或评价登记。正式运行发生在 Owner SOURCE STOP 与 Main freeze/GO 后。全部账户、数据库、费用账本和供应商响应为隔离合成输入；生产 `GenerationService` 与 `DeepSeekProvider` 通过 HTTPX MockTransport 工作，未发送真实供应商请求。

## 实际命令与结果

解释器均为 `C:\Users\liyh\.conda\envs\1\python.exe`。以下证据目录相对于 `evidence/upgrade/v5.0/blueprint-generation/qa/`。

| 实际命令 | 结果 | 证据 |
| --- | --- | --- |
| `python tests/v5/test_blueprint_generation.py --candidate .../candidate.json --output .../qa/api-run1` | exit 1；pytest 86 passed、1 failed、2 errors，12.99 秒。JUnit 88 个 testcase；两个 error 是同一 testcase 的 setup / teardown 阶段。 | `api-run1/run.json`、`output.txt`、`junit.xml`、`observations/` |
| 同一 runner，候选改 `candidate-qa-fixed.json`，仅 `--scope "raw-size65537 or test_internal_schema_is_reproducible_and_public_contracts_keep_their_roles"` | exit 0；精确 2 items，0.622 秒。未重跑其余 86 项。 | `api-qa-fixed-run1/` |
| `python contracts/v2/build_generation_content.py --check` | exit 0；18 个当前内部合同与源码一致。 | `contracts-run1/internal-output.txt` |
| `python contracts/v2/check_contracts.py --output .../qa/contracts-run1/v2-result.json` | exit 0；当前 v2 合同检查。未重跑原 classic checker。 | `contracts-run1/run.json`、`v2-result.json` |
| `python tests/v5/run_build.py --candidate .../candidate-qa-fixed.json --output .../qa/build-run1` | exit 0；本 epoch 唯一一次构建，保留超过 500 kB 的 chunk 警告。 | `build-run1/` |
| `node .../qa/run_creation_ui.mjs --candidate .../candidate-qa-fixed.json --output .../qa/ui-run1` | exit 0；30 条记录、issues `[]`、生成提交 0。 | `ui-run1/run.json` 与三张 PNG |

首次失败没有产品原因：一项把 65537 空格直接用作 pytest 自动测试 ID，触发 Windows 环境变量 32767 字符上限，故该 size case 尚未执行；另一项误将不变的 classic 合同路由数写成 8，实际原合同一直为 13。QA 只增加简短显式 ID、修正该事实预期，原输入与产品约束不变。首轮原输出与 exit 1 完整保留。**结论联合复用了首轮 86 项及窄验 2 项，不能称某一次完整套件全绿，也不将重复范围累加。**

## 已实际覆盖

- 两个版本化骨架族 `position_v1` / `mapping_v1` 的 9 种房数、难度组合。每种结构采用两组独立合成参数，经原编译器与真实规则动作 witness 回放到显式 EXIT。独立答案 oracle 核对数值、位置读取、映射及设备顺序，参数改变实际答案；额外 code / sequence 参数只改变对应题目。
- 独立核对谜题数、每房不超过 8 物件、道具上限、normal / hard 组合数、hard 依赖深度和真实跨房材料 / 道具引用。单房 hard 实为 4 puzzle + 1 item + 3 clue，总计 8。四机制在足够题数的定义中实际存在。
- 缺字段、额外字段、缺 / 多槽位、错误蓝图、错误类型、布尔 / 浮点冒充整数、越界排列、重复设备与错误映射均拒绝；重复 JSON 键、非有限数、深度、raw 大小、危险文本与根形状均覆盖。非法输入没有修改或修复。压缩 `$defs` / 本地 `$ref` 的 exact-slot 与名称 / 叙述限制另经独立静态核对。
- 原生产 service + provider 通过一次模拟响应，实际走原 API 准入、worker ready、真实 API witness、早期存档、恢复与应用工厂重开。两房 normal、三房 hard 均覆盖；换账号读取私人任务、关卡、会话及档案为 404，Owner 状态不变。
- 生产生成只选择一次骨架、发送一次；重复 request ID 沿用原任务。无效响应为 `MODEL_INVALID_OUTPUT`，worker 拒绝且无可玩关卡。测试期间禁止生产调用 `make_fixture`；旧完整 Draft 只作为明确标识的 QA 历史格式设置，旧定义 / 旧档恢复不选择新骨架、不调用 provider。
- 临时合成 Key 仅在允许的认证传输中；主题误粘贴被清除，模型请求内容、关卡 DB、合成费用 DB 与错误未泄漏该值。无 Key / 错 Key 在骨架选择和 provider 构造前拒绝。受影响旧测试的预算、一次发送、未知收费与 profile 断言保留，`wire_body` 未修改。
- 完整实际请求计量维持 6000 tokens、60 秒、0.20 元 cap。2000 个四字节字符主题：position 上界 187568000 units，模拟发送一次；mapping 上界 211304000 units，在 reservation / send 前拒绝、两者增量均 0。额外 provider-level 超限输入也实际验证先拒绝；它明确超出 API 主题上限，不冒充合法 API 请求。
- 创建页以实际 v5 构建登录临时本地账户，检查 1280×720、390×844、812×375。文案说明程序结构、AI 内容与校验；换行无横向溢出，表单控件仍满足 44 CSS px。QA 实际查看三张截图，无新的可见问题；没有提交生成，也没有重新跑完整游戏路线。

## 来源、隐私与恢复复核

`qa/static-audit.json` 的只读恢复审计 exit 0：当前 409 来源与固定候选全部匹配；基线 403 中仅 AI generation、Workspace 文案及两份获准测试共 4 路径改变，399 旧来源 raw 不变，另增 5 core 来源及一个显式 UI runner。原 compiler、API、Store、provider、资产均未改；原 25000 状态 / 5 秒 proof 门槛没有提高。AI 模块除 generation prompt / service 外的顶层 AST 与基线一致。

原评价登记的 53 个 sources raw 全匹配，未改 registration、pin 或旧证据。该历史有限 Claim **不覆盖新内部生成路径**，本报告不把它重标为新路径 PASS。

`qa/privacy-review.json` 有限扫描首轮失败 `output.txt` / `junit.xml`：Cookie、session / anon、Authorization、Key、CSRF / auth-context 值模式命中 0，合成 Canary 出现 0；未打印值，原件前后哈希相等。此为有限模式检查，不宣称能识别所有秘密格式。

暂停前一次只读审计命令被中断且没有留下审计文件；用户明确继续后只恢复该静态审计和报告，未重跑任何测试、构建、UI 或模型。一次只读汇总因 GBK 控制台打印构建符号而 exit 1，后续 UTF-8 只读打印 exit 0；这不是构建重跑。最初默认执行器在 prelaunch 初始化失败，实际工作使用获准的明确目的执行方式；不将未启动命令当作执行证据。

## 限制与 SOURCE STOP

本 epoch 实际付费调用 0，真实供应商网络调用 0，没有读取真实 Key 或 canonical ledger，没有清账或环境 / 数据库删除。未重跑无关 API / legacy / 游戏全路线 / evaluator。原真实失败样本、历史 unknown 和有限真实质量缺口保持原状。

验证只覆盖当前两个骨架族及受控合成内容，不能推出任意新结构、任意主题可靠、叙事贴合、有趣或真人难度。浏览器为视口模拟，不是物理手机或真人体验。恢复验证是应用工厂重开，不是 OS 重启；未交互运行根 CMD。既有 Starlette 弃用和构建 chunk 警告保留。

QA 源码、正式执行输出、结果及本报告 **SOURCE STOP**。后续 Main 接受、文档交付与 Git 属 Main / Delivery 范围；此 QA 不提交、不推送、不宣称整体发布完成。
