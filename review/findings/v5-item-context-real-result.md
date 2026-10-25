# 单 G3 真实复测：独立 AI QA 结果复核

日期：2026-10-25。结论：**本次真实样本因遗漏四个必需物件槽位被严格拒绝，未形成可玩关卡。** 执行器实际 exit 1；独立只读诊断 exit 0 表示成功查明原因，不是把真实失败改判为通过。原 G3 叙述 finding 保持 OPEN。

本复核由独立 AI QA 智能体执行，不是真人试玩、教师审查、签字或产品接受。用户确实批准了这一次有限调用；该批准不等于确认结果质量。

## 实际执行与首拒原因

用户批准引用为 `call_816b3ba868734520b192ddddab3fdeeb item0`，最多 1 次 / 0.20 元。Main 仅运行封存 runner `--execute` 一次，工具记录 `7ad987`：exit 1，8.02 秒，无重试。实际请求与已批准预览完全一致，G3 / 三房 / hard / mapping_v1 / 内部 seed 1，主题与旧实际 G3 相同。

模型返回完整可解析 JSON，`finish_reason=stop`，输出 641 tokens，低于 6000 上限。原稿 SHA256 与保存的 `content_raw_sha256` 相同；没有改值、补项、替代或回退。未观察到输出截断，不能把本次缺项归因为截断或据此要求放宽上限。

独立诊断直接对保存原稿运行原严格 parser、当前 exact Schema 和生产 `assemble_draft`，不修补、不调用 compiler / planner。首拒发生在 **精确内容合同校验，尚未构造 Draft**：

| 必需而遗漏的 objects 槽位 |
| --- |
| `obj_extra_code_a` |
| `obj_extra_code_b` |
| `obj_extra_devices_a` |
| `obj_extra_devices_b` |

实际仅返回 10 个物件槽位，合同要求 14 个。实际校验恰有以上四项 `required` 错误，未观察到额外槽位或其他 Schema 错误；原 JSON / 安全文本检查通过。生产组装器报 `GENERATION_CONTENT_INVALID`，对应真实任务 `rejected / MODEL_INVALID_OUTPUT`，`level_id=null`。

这是模型输出未满足合同，**不是准入程序把坏关卡放行的缺陷**。没有 ready 定义、proof、公开游戏投影、HTTP witness 或存档恢复证据；`raw-sensitive/` 不存在，不能声称完成了这些阶段。没有修复一个假想草稿后再编译或回放。

## 有限文字观察

真实原稿把物件命名为“标本柜铜钥匙”，最后装置叙述为“标本暂存柜的检修锁孔与铜钥匙匹配，是离楼前的最后一步。”

- “铜钥匙”与该物件在意义上可辨认，但没有按新提示精确引用完整 `objects[slot].name`。“大体提到钥匙”不能当成严格同名要求已满足。
- 本原稿未再出现“资料袋”；最后装置没有归还、放回、消耗或额外清单操作。不过也没有明确说明使用后保留。只能记录未观察到相反文字，不能验证实际 `use_item` 非消耗行为，因为关卡未准入。
- 房间描述含“交接清单”，属于场景陈述；最后装置没有要求玩家额外执行清单操作，不能把提到清单直接判成新增必需步骤。
- 设备登记文字没有再声称按字母序处理。相关 typed 参数通过当前排列 / 映射合同，但由于缺物件而没有实际游戏投影或交互，不能据此声称设备 / 符号叙述与玩家推理体验全部一致。

这些是未准入原稿的局部观察，不是可玩叙事质量通过。旧样本中的错误资料袋文字、原成功准入和 witness 原件均不改写；本次没有关闭旧 finding，也不与旧样本合并成新源码成功率。

## 授权、费用与来源闭合

当前 runner SHA256 为 `eed8325b4cff57668eb36ec5d3584b1ef270080b59f69755a946f7190d2b38cf`。预览、实际 `source_after`、当前文件的 412 来源完全一致，bundle 为 `6232d032655ecf5a894dd60e82cb782fd175ebe71c1d01194a2941ff9b14672d`。实际授权绑定精确预览、来源、G3 scope / 1 次 / 200000000 units；授权时间早于独占 marker 和首次派发。

派发 journal 恰有一次 before / after，返回型号与请求型号均为 `deepseek-flash`。实际 usage 为 prompt 2729、completion 641、cache hit 0，合计 3370 tokens。独立按原费用单位重算为 **0.010586 元保守费用上界**，与保存账本摘要 calls 144 → 145、charged upper 1093102000 → 1103688000 units 的差额完全一致。发送前预占上界为 0.150816 元，授权上限 0.20 元；它们不是外部账单。

原三条 unknown 身份哈希 `b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e` 不变，pending 0、frozen false，`finalization_failures=[]`。本次失败已消费唯一调用名额，**无剩余付费授权**。QA 仅读取保存的摘要，未打开当前 canonical ledger 或真实 Key / 配置。

原 QA 63 / 16、预检 12 / 8、旧实际公开 17 / 本地私有 6 的原哈希及旧登记 53 来源均保持；没有修改产品、旧报告或任何真实原稿。私有旧材料只核对哈希，不复制、不发布或发送模型。

## 实际 QA 命令与限制

解释器为 `C:\Users\liyh\.conda\envs\1\python.exe`。以下命令均在 Main 明确 terminal GO 后执行：

| 实际命令 / 范围 | exit | 新证据 |
| --- | ---: | --- |
| `python -X utf8 -`，读取真实拒绝结果、原稿叙述与保存摘要，记录 `448620` | 0 | 原件只读，未改写 |
| `python -X utf8 -`，生产严格组装器离线诊断，记录 `5835e6` | 0 | `qa-actual-diagnosis-v1.json` |
| `python -X utf8 -`，授权 / payload / 412 来源 / usage / 保存账本与有限秘密模式核对，记录 `e641c8` | 0 | `qa-actual-bindings-v1.json`、`qa-actual-privacy-v1.json` |

纯诊断没有导入 provider 或 application main，没有打开 DB / canonical ledger，没有新模型或 API 请求，没有编译、规划、witness、旧测试、构建、UI、evaluation、prepare 或 execute。10 份公开实际证据的有限秘密格式检查命中 0，原件哈希前后不变；未读取真实 Key，因此不宣称能识别所有秘密格式。

本报告只能说明这一份真实输出被正确拒绝、失败原因及有限文本观察，不能证明新提示保证遵守、模型总体可靠或真人体验合格。任何未来修改属于新 epoch，不得重写本次失败或称已真实复测。

本次新实际复核报告与 `qa-actual-*` 证据 **SOURCE STOP**。不修产品，不提出新收费执行，不提交或推送。
