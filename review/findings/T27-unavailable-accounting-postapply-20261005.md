# T27 新 unavailable 核账实际 apply 后独立只读复核

结论：95/95 检查通过，全部原 83 行逐列对照；仅指定请求的 state/reason 改变，其他 82 行完全相同。原 preapply 130/130 的 result 和 unknown 快照保留，不重写为当前结论。此次 QA 没有 apply 或付费调用；实际更新由 Main 执行。

实际命令：

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T27-unavailable-accounting-application-20261005T121200Z/review.py
```

工作目录 `D:\深度能力`，actual exit 0/chunk 042ae4。原共享账本只以 SQLite mode=ro 读取两次，postapply 快照稳定，之后停止读取。Main supplied actual apply exit 0/chunk 9eb52f；QA 独立核对实际 applied record 与原账本后状态，不声称观察了 Main 进程现场。

目标 `6dfc591c79c54544afe6d70eec6d697b` 精确由 unknown/MODEL_UNAVAILABLE 更新为 settled/HUMAN_FEE_REPORTED_UPPER_RETAINED。scope、时间戳、reserved/charged 94,536,000 units 和三列 NULL token 均保留。83 个 ID、10 列完整 tuple 逐行与原 preQA snapshot 比较；其他 82 行没有任何变化。总 charged upper 448,961,840 units（0.44896184 元），cap 10,000,000,000、frozen=0，当前 83 settled/pending 0。trigger 列表也保持。

Main applied record 的 before/after 精确对应独立快照与唯一允许的改动；人工费用 90,000,000 units 仍不回收 full upper 差额，没有 token 重建、HTTP 回包恢复、重复记账或补请求。记录声明 provider_usage_known=false、provider_invoice_independently_verified=false。旧 timeout helper、旧 dryrun/applied 费用记录、旧 formal raw/summary 原始字节仍匹配 preQA 保存值。

实际 applied record `evidence/integration/unavailable-human-fee-20261005-applied.json` 原始 SHA256 `cd3a9dfe4fd93ae3882020abb9a67c48eeb2701e70d82f03f3adc9fd9dbfe011`；helper 与 preQA pin 精确相等：`151b30144e1f440e3abb8c7901d3e27c180601d742fcfcb24f15d7e5989175b8`。独立 postapply result `68d412e9d81ae4c396b9527dc8d714f8c2b0c202de1953bb7c4c4472b5ca63c5`，review.py `7f8c31bcad05b84092036133bb64e888ab531814ec71749c5cae53c97bac47e1`。

新增证据根 `evidence/qa/T27-unavailable-accounting-application-20261005T121200Z` 保存 review.py、checks/result/process-result/source-stop/artifact-sha256；preQA 130 项证据仍在 `evidence/qa/T27-unavailable-accounting-20261005T120700Z`。此后不再读账本。人工“0.09”不是独立供应商 invoice，原实验 unavailable/NULL 与完整预留上限永久保留。无真实环境文件、网络、Git、付费请求或 QA 原账本写入。SOURCE STOP；本核账本身不授予新增调用。
