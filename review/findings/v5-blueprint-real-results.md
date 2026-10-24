# v5 蓝图生成：两份真实样本的独立结果复核

日期：2026-10-24。结论：**两份有限真实样本的准入与 HTTP witness 技术链通过；存在未关闭的叙述误导，不能称叙事质量或真人体验通过。** 本报告仅属于当前 411 来源 epoch，不混写任何未来修复或复测。

## 实际执行与来源

用户实际批准引用为 `call_8533192c1d7a4aee9fe2d26bc11d3133 item0`，最多 2 次 / 0.40 元。Main 在独占授权记录后，只执行已审查的 `real-samples/run.py --execute` 一次；实际进程返回 exit 0。QA 等到明确 terminal GO 后才读取产物，没有启动、恢复或重复该执行。

当前 runner SHA256 为 `31d72c5cf6e84cde83d371a3849a4793896758e4d87c0d7b2148fe1fcb1781f0`；预览 SHA256 为 `fec5789db9d55f76928ba68902d85655cfb6cca1ed5537315ed9d4fb51151d95`。411 来源 bundle `207b07f44f5070ae499f892c4ff2ca49c9cc89f8de3604571d0cc35bbad415b3` 与预览、实际 `source_after`、当前文件全部一致。授权文件原字节哈希与 authorization binding、独占 marker 相同；批准时间早于 marker 和首次 before-dispatch 日志。

原 409 产品候选、63 份旧 QA 证据、12 份预检封存材料及旧评价登记 53 来源均保持原字节。QA 未改产品、原稿、运行记录或旧报告。

## 两份实际结果

| 项目 | G2 | G3 |
| --- | --- | --- |
| 请求 | 2 房 / normal；天文社资料交接 | 3 房 / hard；生态标本交接 |
| 披露的 Host 选择 | seed 0；position_v1 | seed 1；mapping_v1 |
| 实际模型调用 | 1 次 | 1 次 |
| 请求 / 返回型号 | deepseek-flash / deepseek-flash | deepseek-flash / deepseek-flash |
| 输入 / 输出 tokens | 1410 / 581 | 2661 / 1023 |
| 结束原因 | stop | stop |
| 原 API 准入 | ready | ready |
| 已记录真实 HTTP witness | 24 动作、全部 200、显式 EXIT / won | 33 动作、全部 200、显式 EXIT / won |
| usage 保守费用上界 | 0.007468 元 | 0.01325512 元 |

两份模型原稿哈希均与 `content_raw_sha256` 相符，未发生 redaction 改变内容、修复、替代、fixture 回退或自动重试。原稿内容经确定性 assemble 与原 compiler 的静态部分重建，和保存的完整定义精确相等。这里 QA 使用 `prove=False`，没有新规划搜索；真实准入和求解证明属于 Main 已完成的原运行。

派发 journal 恰为 G2 before / after、G3 before / after 四条，provider call ID 两个且不同。保存的账本摘要从 calls 142 → 144、charged upper 1072378880 → 1093102000 units，差额 **0.02072312 元**，与两份实际 usage 按原输入 miss / hit、输出费用独立重算的和完全相等。预占请求上界合计 0.259424 元，授权上限 0.40 元；它们都不是外部账单。

原三条 unknown 的数量与身份哈希 `b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e` 不变；pending 0、frozen false。QA 仅读取已保存的摘要，没有打开 canonical ledger。两次名额均已消耗，**没有剩余付费授权**。

## 原稿、定义与动作链的独立一致性

QA 在本地内存读取实际原稿及六份仅本地私有材料，使用既有规则解释保存的 witness；没有新 HTTP、模型或数据库调用：

- 原稿 assemble 后经原 compiler 静态校验的 `private_dump` 与保存定义完全相同；定义 hash、witness hash / 动作数均匹配。
- G2 的 24 / 24、G3 的 33 / 33 每步 `visible_state_sha256` 均精确重现；初始投影哈希及最终完整投影也精确一致。
- 比较时仅重用产物内的 generation、started / finished 时间、session / level ID 和 save 投影，以排除随机元数据差异；不把它们伪称新执行或真人耗时。
- 每步 `api_result_sha256` 只保存 opaque hash，没有原始完整响应及随机 event ID，故无法独立重建该完整 API body hash。已保存 HTTP 200 状态与每步规则状态 hash 链一致；本报告不扩大为所有原始响应字节均可独立复算。

六个 `*-private-definition-local.json`、`*-witness-local.json`、`*-api-replay-local.json` **不得发布或发送模型**。公开 seal 仅绑定路径与原始哈希，正文不输出完整定义、witness、typed 参数或答案；本地有原件可复核。

## 未关闭叙述 finding

**[P2] G3 最后交接箱引导使用不存在的物品。** 实际原稿 `objects.obj_puzzle_6.description` 写“空交接箱需放入指定的标本资料袋，完成离楼最后一项。”，但 Host 定义的必需物品是已有的“标本柜钥匙”，全定义没有“资料袋”物件。该文字原样保留到关卡定义；与实际 `use_item` 规则冲突。自动 witness 根据服务器权威答案和合法动作成功，不证明玩家按此叙述能自然完成。当前实际 epoch 内该问题未修，不能标为已关闭或用未来源码重新解释原样本。

“旧设备清单按字母序记着几种维护设备”也有术语歧义：实际 source 符号确为字母升序，经过 `device_map` 后设备序列并非字母升序。符号层按字母序成立，映射层则应按权威对应关系处理，因此不将它夸大为已经证明的密码 / 设备答案错误；但文字混称符号和设备，会产生按设备名称自行排序的误读风险。

G2 的最终箱子文字包含正确的“交接钥匙”，仍把动作描述为“放回钥匙等物品并确认清单”，比实际非消耗 `use_item` 含义更丰富。两份主题大体贴合，不足以推出所有局部操作叙述正确、自然或有趣。本次没有真人试玩、体验评分或教师接受。

## QA 实际命令、证据与限制

解释器为 `C:\Users\liyh\.conda\envs\1\python.exe`。本次只读 / 内存审计使用 `python -X utf8 -`，完整命令见会话工具记录；没有运行 pytest、build、浏览器、evaluation、prepare 或 execute。

| 实际审计 | exit | 新证据 |
| --- | ---: | --- |
| 读取已终止产物、原稿叙述与实际授权 / journal | 0 | 工具记录 `b9b121`、`c99fdc` |
| 本地比较描述、required item 与排列层次 | 0 | 工具记录 `eb5f02`；仅输出有限叙述与布尔判断 |
| 原稿重组及已存 witness 内存状态 hash 解释 | 0 | `qa-actual-review-memory-v1.json`，记录 `17896f` |
| 411 来源、真实授权、payload、usage 与保存账本摘要闭合 | 0 | `qa-actual-review-bindings-v1.json`，记录 `5d0688` |
| 13 份公开终端证据的有限秘密模式检查 | 0 | `qa-actual-review-privacy-v1.json`，记录 `4253c0` |

有限隐私模式命中 0，未打印凭据值，所有原始文件前后 hash 相同；QA 未读取真实 Key，不能把模式检查夸大为识别一切秘密格式。review 仅增加本报告与 `qa-actual-review*.json`。

实际两次生成不能推出总体成功率、任意主题可靠或任意新结构。真实调用使用受控 Host 骨架族，不是模型自行创造拓扑。自动回放的亚秒时长、S 评级均是程序运行数据，不能当作真人难度 / 时长 / 可玩性接受。本轮未真实验证 save / restore、伙伴或 evaluator；原历史失败、旧 unknown 和评价缺证保持原样。

QA 新实际结果报告与 seal **SOURCE STOP**。结论仅为有限技术链通过并保留上述叙述 finding；Main 的整体接受和后续任务另行记录。本报告不授权新收费、提交、推送或发布。
