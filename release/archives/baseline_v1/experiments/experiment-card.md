# E1 预注册候选卡

问题：相同可见事实下，可逆结构化历史是否减少输入 token，同时保持下一步建议质量？允许 B 没有优势。冻结值见 config.json、prompt.txt、schema.json 及每个 plan.freeze 指纹。

固定游戏 baseline_v1；12点为 C01初始/C02便签/C03两R1线索/C04柜开无卡/C05持卡门闭/C06R2无电无保险丝/C07有电但两R2线索未发现/C08两R2线索/C09抽屉开无钥匙/C10持钥匙R3门闭/C11只读R3检查单/C12两R3线索。每点可接受动作与引用依据提前冻结在独立 ground_truth，绝不发给模型。

主指标分别为 correct/planned、correct/completed、legal/completed、reference_valid/completed；代码依据充分性另报。completed 指可解析 schema 输出，不代表动作正确、引用有效或已执行。无 action 的合法 JSON 是 completed，但 legal/correct=false。解析失败时 judgement 为 null；空引用的存在性可以成立，不能冒充代码依据充分。费用只称账本上界，非供应商实际账单。

配对控制同一prompt/question/current-state/tool-schema/model/options，只有历史表示不同。同样的输入在3次重复中不强制供应商采样独立；缓存与时间影响须保留观察。token优势使用可信 usage，未知样本不填0；另报所有 payload 字节数、保守 reservation。延迟p95依样本数有限，不宣称稳定尾部估计。

预试为6次单请求，另建run；正式为72条提前登记的计划，失败/超时/not_called均保留，禁止替换。正式预算未批准，真实实验未执行。价格证据是Main于2026-10-02T12:00Z核对的历史资料，真实执行须另绑定新鲜核对，不把历史余额当即时余额。

Main提出T21实施GO只授权本地确定性/mock工作。未来真实pilot和formal各须有限GO及复核，本卡不是付费授权。真人课程确认不属于本实验判定。
