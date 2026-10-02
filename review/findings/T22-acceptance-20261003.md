# T22 独立 QA 验收恢复

结论：T22 的实验工程与预试门检查通过；T22-EXP-001 关闭。此结论不代表真实 E1 调用或付费实验已执行。

既有完整独立结果 `evidence/qa/T22-experiments-20261002T130448812384Z/result.json`：764 项全部通过、83 条源记录 before=after；恢复读取时当前文件哈希也全部相符。旧结果缺少保存的进程退出码，未把按源码推断的 exit 当成历史执行事实。Main 因此明确授权一次完整重跑补全真实进程证据，原通过与原失败结果均保留。

真实命令：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_e1`；真实进程 exit **0**（工具 session 66992，完成 chunk `b866cf`）。新完整结果 `evidence/qa/T22-experiments-20261002T164754631028Z/result.json`：764 项、0 失败、passed=true；83 条源记录 before=after，完成后再核对当前源无差异。`process-result.json` 单独记录实际命令、真实 exit 与工具完成记录。

新旧 `result.json` raw SHA256 均为 `54d730377941179358ee439d73f1214fbdcbb634d2a628f2ba41e43fd303587b`，因为结果载荷和源快照完全相同；它们来自各自独立目录，重跑的逐次合成数据另存于新目录。QA harness `tests/review_e1.py` raw SHA256 `b98c23b80313c21232d3ae5c1435bbd5d08b550714d055df3f9b1b771e56fbc2`，本次未改动。

验收范围：12 个检查点的合法前缀、A/B 可见事实一致及结构摘要无损往返、离线参考答案不进入请求；72 行正式计划与6行预试独立；六工具严格参数、合法性/正确性/引用充分性区分；逐行身份与分母、失败保留、崩溃预留和不重打；共享额度、pending/unknown/frozen 拒绝；调用前 journal、真实线传内容哈希；401/403/429/503/malformed200 的响应确证与 ConnectError/ReadTimeout 的响应未知三态。全部传输为 `httpx.MockTransport`，账本由 QA 独立创建；实际网络、付费调用均 0，凭据与原账本没有访问。

源绑定：`experiments/runner.py` = `a46368a2a20c819fc21f9d29ea57c90bfb80189e9383f9c0c383cfec6847df19`；`experiments/transport.py` = `a0d6bc454c058957cd35802c64660667c7a283b1ef6330a948626aa5755b8a01`；`experiments/summarize.py` = `717c2f02f07fdc2bdb02f10a70a6ed3b80175c0926166958ff42b1e210f10ee7`。完整83条绑定见结果文件。产品 v1 manifest raw 仍为 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`；本角色没有修改实现、manifest 或 Git。

限制：本次只证明固定实验输入、工程门与合成失败路径；真实模型、真实费用、真实方案优劣均尚未因此被验证。真实 pilot/formal 仍需 Main 单独有限批准，不能使用合成 gate 作为预算授权。人类签署未提供。
