# A28 新目录真实段独立只读结果 — 阻塞，SOURCE STOP

本次真实段没有开始，不能写通过。Main实际命令（handoff原文）`Python -B -X utf8 evidence/integration/run_a28_fresh_real.py`，工具块c4f09f、exit1。实际记录atUTC2026-10-06T04:28:35.359022+00:00，process_started=false、actual_paid_calls=0；创建runtime文件symlink失败，relay在凭据加载和子进程启动前返回。error_type=OSError，安全错误类别为Runtime file symlink privilege unavailable；原始errno未保存，QA不臆造1314等具体系统错误。

固定candidate833aafb09ad20dc1ba82cfed198485ce13300067 / clean115741未改变。Main执行前11个文件hash均与封存readiness的Root/clean/materalization绑定相同。relay80305b8955f0426d87577d086fd603ed72f2d2d04fddc8ada485095177698a01、准备报告7dd6d3e30700789a61fe23e4f4baaa2a9581cd7cc7ab94f5c6ac063557a0b7a5保持原pin。本次仅查看4份记录SHA前后不变，并核对11个保存的source绑定；没有重复27文件/全量回归。

Main失败process.json实际SHA d0963248437b1ebb9d5c46377be8498c3c61c487d1f947644c9b76bffd8d5a85。clean/data/ai-budget.sqlite metadata显示exists=false、is_symlink=false；没有创建/复制预算或账本。本QA没有打开账本/费用调查/读取.env；Main确认没有凭据注入。未生成新的m3-real子进程run、真实tool result、proposal、confirm或重放证据。人工签署仍NULL/pending；A28真实段状态为证据不足，而不是FAIL的模型能力判断或PASS。

实际QA只读检查：05fae9 exit0（旧relay/report pin与安全状态）；fe24f0 exit0（安全失败记录、link metadata、11保存的source对checkpoint）。四记录实际before/after与11绑定见evidence/qa/A28-real-result-20261006T043101848502Z/result.json。本次没有调用模型/网络、执行relay、改Owner源码/Git/原ledger/env或新增回归。没有新8评价审批或真实评价结果。

Main提出的替代是全新workspace同833 archive/pins材料化，仅新workspace/data目录Junction指向Root现存data，并验证resolve/samefile原ledger；这是尚未执行/验收的准备。需要先检查归档data源叶与路径别名的相容性，保留旧clean、旧0-call marker及失败证据；不得移动/删旧data或复制/初始化预算。新relay/记录须只读快审后再经具体执行审批，不能把本阻塞结果当作provider retry或自动付费授权。

文件：只新增本报告与evidence/qa/A28-real-result-20261006T043101848502Z，未添加不必要测试helper。result.json SHA 07d9e4b68a03e54a71205e58aa338e590170ed70ec37ce4958627a046ae120f5。准备检查已封存，当前0-call阻塞结论SOURCE STOP；替代方案另等Main稳定文件后只读快审。
