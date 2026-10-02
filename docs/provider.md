# T04 独立 Provider 与共用预算

已实现可替换 MockProvider 与 DeepSeekProvider，尚未接入游戏轮次、可见上下文或确认事务。T14/T15须等M2手动门通过后另行派发。本地开发检查与合成真实探针不能证明游戏AI验收通过。

用户选择 DeepSeek-V4.1-Flash，授权全项目 API 共用人民币10元（接入/游戏/实验/评价合计）。正式model=deepseek-flash，base_url=https://api.deepseek.com。2026-10-02直连[官方价格页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)和[更新日志](https://api-docs.deepseek.com/updates/)确认名称；批量实验前须重新核对价格。

## 配置与调用接口

根目录本地.env使用MODEL_API_KEY、MODEL_NAME=deepseek-flash、MODEL_BASE_URL=https://api.deepseek.com。DeepSeekConfig.from_environment()只读取这三个键，进程环境优先；密钥不打印、不写证据或账本。空密钥返回MISSING_CREDENTIALS，无付费请求。密钥与数据库必须持续Git忽略；本任务未改依赖、锁文件或环境。

```python
from backend.app.ai.provider import (
    DeepSeekConfig, DeepSeekProvider, CallLimits,
    tool_result_message, validate_final_content,
)

provider = DeepSeekProvider(DeepSeekConfig.from_environment())
result = await provider.complete(
    messages, tools, CallLimits(max_tokens=1000, timeout_seconds=20),
    scope="game", tool_choice="auto",
)
# 只使用已验证的tool_calls；适配器不执行工具。
messages.append(result.assistant_message())
for call in result.tool_calls:
    messages.append(tool_result_message(call["id"], trusted_tool_result))
# 轮次工具探索结束后再获取最终content；T14须另行控制总请求数。
result = await provider.complete(messages, tools, scope="game", tool_choice="none")
final = validate_final_content(result.content, discovered_clue_ids, tools)
```

result含content、tool_calls、usage、provider、requested_model、reported_model、finish_reason、call_id、cost_upper_cny。无usage返回null并保留预留额。MockProvider接受脚本ProviderResult或ProviderError列表，接口相同，usage保持null，不填假token。

根据[Chat Completions官方文档](https://api-docs.deepseek.com/api/create-chat-completion/)发送thinking={"type":"disabled"}、stream=false、max_tokens<=1000。单请求总截止最多20秒，没有自动重试。3次模型/5个只读工具/45秒总轮次限制由未来T14执行。

按[官方Tool Calls指南](https://api-docs.deepseek.com/guides/tool_calls/)回传assistant tool_calls，再传role=tool、匹配tool_call_id与JSON字符串content。strict=true要求Beta地址且不支持契约minLength/maxLength；正式地址只移除wire strict字段，完整Draft2020-12参数契约在本地严格校验。拒绝未知工具、额外参数、错误类型、重复JSON键、截断及未知线索引用。

实际非流式API多返回tool_call.index，前两次真实探针因此被拒绝；第二次仅形状诊断记录了该字段。兼容后只接受匹配序号的非负整数，规范化history省略index，没有放宽参数/引用校验。最终JSON精确含answer、clue_refs、proposal；proposal为null或tool/arguments/clue_refs/summary。有proposal必须传完整tools校验参数。这里只验结构与引用，动态可见性、前置、版本及玩家确认仍由T15/后端负责。

## 共用预算接口

BudgetLedger正式路径固定为项目根data/ai-budget.sqlite。游戏/实验/评价必须共用它；真实DeepSeekProvider拒绝自选账本。临时账本仅用于MockTransport局部检查。BEGIN IMMEDIATE事务串行化预留与结算，费用使用十亿分之一元整数；首次预算配置不可静默提高/重置。pending/crashed记录继续计入总预算。

```python
from backend.app.ai.budget import BudgetLedger, cost_units
ledger = BudgetLedger()
call_id = ledger.reserve("experiments", maximum_units)
ledger.settle(call_id, prompt_tokens=p, completion_tokens=c,
              cache_hit_tokens=h)  # 只使用可信完整usage
# 对超时/失败/未知usage：保留全部预留，不假装0费用。
ledger.retain(call_id, "MODEL_TIMEOUT")
summary = ledger.snapshot()
```

其他Provider复用者须核对各自费率并保守预留；cost_units只对应当前Flash费率。scope建议probe/game/experiments/evaluation，不切割项目总额。重复call_id拒绝，重复同值结算无副作用、冲突结算拒绝。snapshot含charged_upper_cny、remaining_cny、unknown_or_pending_calls、frozen。不能删除数据库恢复预算。

按高峰百万token缓存未命中输入2元、命中0.04元、输出8元。请求前将完整发送JSON（包括Schema与合法可见历史）的UTF-8字节数乘4，加8192 framing token余量，输入全按未命中率预留，输出按max_tokens预留。只支持文字输入，保守输入token界不得超过1M。这个界是工程保守估计，不是官方tokenizer证明；usage超token界/费用预留界、返回其他模型时冻结后续付费调用，须核对后处理。可信cache hit usage按高峰费率结算，未知usage保留最大额。probe另有事务累计0.20元与单请求0.10元预留上限，每次运行最多两请求，不自动付费重试。

## 实际验证与证据

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m backend.app.ai.provider_check --output evidence/provider
# 可选：凭据/预算满足才发起真实合成探针，不作无界重复测试。
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m backend.app.ai.provider_check --real --official-docs --output evidence/provider
```

每次新增时间戳目录，失败证据不覆盖。不保存原始API body、headers、任意异常或凭据；只存合成检查、固定字段形状、usage、模型与费用上界。新报告分别标明local_checks_passed、real_probe_passed、overall_passed；早期passed仅指局部检查，不能误读为真实探针成功。

以下目录均在evidence/provider/，日期2026-10-02：

- adapter-20261002T062843343708Z/report.json：18项局部检查通过，真实响应index被拒绝，exit1；四官方页HTTP200和SHA256。真实失败已按usage结算，没有当0费用。
- adapter-20261002T063050346163Z/report.json：18项通过，真实仍失败，脱敏形状明确index，exit1。
- adapter-20261002T063154317917Z/report.json：index兼容后18项通过；真实两请求完成get_inventory及回传，exit0。reported_model均deepseek-flash；usage分别prompt282/completion17/cache_hit128与prompt71/completion44/cache_hit0，本次上界0.00094312元。
- adapter-20261002T063537034325Z/report.json：新增probe子预算与报告标志后19项局部检查通过，exit0；没有真实请求。实际两个Python进程以game/experiments scope竞争同账本，仅一个预留成功。

截至成功报告共有4次真实HTTP请求（失败2、成功2），共用账本结算上界0.00230824元，剩余9.99769176元，未知usage 0。未查实际供应商账单，不能称此为账单金额。仅发送合成空背包探针，未读游戏秘密/会话/关卡答案。独立QA、游戏AI端点、六工具动态约束、玩家轮次、实验/评价真实调用未验收。修复前运行未记录源码hash，此缺口不能补称为已记录；最终hash及交接事实另存追加handoff证据。
