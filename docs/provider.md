# T04 Provider 接入状态

当前仅完成独立离线 mock 探针，未实现游戏 AI 接入或真实 Provider。探针不读取环境变量、凭据、秘密关卡、会话或数据库，不发送网络请求，不执行进度动作。

运行入口（在项目根目录）：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -m backend.app.ai.provider_probe --output evidence/provider
```

每次运行写入新的时间戳目录，保留 `report.json` 及 `output.txt`。输出包含实际 Python 版本、指定解释器路径、停止原因、模拟调用次数、只读次数和断言结果。模拟响应不是模型输出；usage 和 cost 为 null，不能用于实验成本估算。

探针覆盖正常工具结果回传、超时、畸形响应、模拟鉴权失败、服务错误、只读循环、请求限额和非法工具。探针只允许模拟 `get_inventory`。独立验证使用短超时加速，不宣称验证了生产轮次的 20 秒单请求/45 秒总截止；生产限制与正式六工具契约将在 T14/T15 接入。

无需新增 Python 依赖。T04 本地开发检查不替代独立 QA，不证明 A15/A16 游戏接口验收。

真实供应商、模型 ID、版本、凭据和批准预算均未确定；真实调用未验证。未查询价格或官方 API 文档，因此无单价或成本估算依据。后续选定 Provider 后须依据其官方文档实现并记录结构、工具结果回传、用量字段和有效限制；不能将开发 Agent 模型当成游戏 API 模型。M1/M2 手动玩法不依赖这一配置。

待主 Agent 在手动基线完成后派发 T14/T15，并以冻结 `contracts/` 与 `visible_state` 为输入继续实现。
