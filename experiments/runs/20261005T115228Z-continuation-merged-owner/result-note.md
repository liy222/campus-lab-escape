# E1 追加续跑结果说明（Owner整理，待独立QA）

72个冻结计划单元的首个实际尝试已追加合并，终态为 **69 completed、1 timeout、1 failed、1 not_called**。也就是71次确证付费尝试、69次确证响应、2次响应/用量未知、1条未调用；不是72次回复。原run72行、原summary和续run49行均未改。

| 方案 | planned | 付费确证 | 完成 | 正确/完成 | 正确/planned | usage覆盖 | 服务失败 | 未调用 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A完整历史 | 36 | 36 | 34 | 26/34 | 26/36 | 34/36 | 1原timeout+1续failed | 0 |
| B结构摘要 | 36 | 35 | 35 | 29/35 | 29/36 | 35/36 | 0 | 1 |

两方案已完成动作均合法且引用有效/充分（A34/34、B35/35）；动作正确性不等于自由文本全部无幻觉。69条完成中有14条合法但不在冻结正确下一步集合内，这些偏差未被替换。36个计划配对只有34个双响应完整；C12 repeat1的A原超时保留，C04 repeat3的A失败/B未调用。原23条付费尝试的完整行对象及22条响应UTF8内容逐条相等，详情在evidence-index.json。

原第23行formal-C12-full_history-1超时的HTTP/model/usage仍null，账本上界0.16292元保留；用户曾向Main确认费用0.05元是独立的人工费用事实，不能补出模型token或改写raw。续跑第71行formal-C04-full_history-3发生MODEL_UNAVAILABLE，call_id=6dfc591c79c54544afe6d70eec6d697b，HTTP/model/usage/投递仍未知，fullupper0.094536元；第72行B未调用。新失败不能推定上游没收到请求。所有付费操作暂停，由Main另行核清。

正式两个批次合计费用保守上界0.40885584元，其中已知usage结算0.15139984元、两条unknown usage预留上界0.257456元；不含独立pilot和此前游戏/探针费用。续跑单批上界0.17135888元，已知结算0.07682288元、未知预留0.094536元。原总项目账本交接事实为83条调用、总上界0.44896184元，Owner只读当前快照另存accounting-notes.json；账本状态核清与实验未知状态分别记录，不回收/猜测费用。

summary.csv为T24附件，沿原summary分母补列timeout/failed/not_called及known settled/unknown retained upper费用。raw.jsonl等于merged.jsonl完整72行；lineage.json逐单元说明原not_called→首次实际尝试或仍未调用。原23条结果保持原样，没有选择最好结果、补打旧失败或把pilot并入正式。

延迟和缓存按批次分列于latency-by-phase.csv、usage-cache-by-phase.csv。原批记录的是旧进程内判定结束前后的latency_seconds，续批端到端包含独立v1判定子进程，另有provider_latency_seconds；不能把混合延迟当同一测量边界。续跑相隔约六小时，vendor时间/负载、缓存命中和顺序连续性改变；仅请求值、字节指纹、原相对顺序及v1判定保持一致。原温度/seed未发送。原v1的6条未绑定旧QA源记录/3项runtime-only构建局限仍适用。不能声称B优越、成本优势、总体智能、自主通关、人测或课程签署。

source-map.json分别注明original41 before来自原plan.freeze源图、new5 before来自真实续run记录，after为本次实际raw哈希读取；不是事后制造前快照。归档v1 aliases和canonical付费client明确分开，currentv2规则没有进入续跑判定。稳定executor和原始数据均未修改。当前报告仅Owner整理；Main交接和独立QA复核尚待进行。
