# T27 独立评价器事件登记、固定归档与 Main 进程转交复核

结论：本次稳定候选的独立检查通过，范围仅为离线结构、读取边界、冻结绑定与合成协议行为。没有未闭合实现 Finding。未执行真实模型请求、目标源码、归档源码、HTTP、Git、原账本访问或真实环境文件读取；此结论不构成新的付费授权，也不是真实语义评价结果。

## 实际执行与失败历史

工作目录 `D:\深度能力`。最终实际命令：

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_evaluation_events.py --output evidence/qa/T27-evaluation-events-20261005T105300Z
```

实际 exit 0，session 41908，输出 chunk 443744，完成 chunk eefc04：新增 168/168 检查通过，必要旧回归 114/114 通过，旧 11 个案例另外实际经过 MockProvider，其中 K1/K2/K4 的模型模拟调用与 audit 原建议保留，K4 由真实确定性失败覆盖模拟 PASS。未重复旧 T26 全量 193 项。首次完整运行 165/165 与 114/114、exit 0（session 10570/chunk 45abeb）也保留；最终增加归档连接目录和声明总读取量边界后再完整复跑。

先前两个 QA 自身失败均保留且不算通过：`T27-evaluation-events-20261005T100300Z` exit 1/chunk 848877，过早的网络阻断器阻止 Windows asyncio 本地唤醒 socketpair，执行检查数为 0；`T27-evaluation-events-20261005T100600Z` exit 1/chunk 61347b，隔离 SQLite 连接循环使 Windows 临时文件清理失败，未达到旧 114 回归。只修正 QA 阻断器安装时机及隔离连接关闭/回收；没有修改候选实现。第二次失败留下的临时目录只有人工构造的标记和假账本，不能作为生产证据或随成果提交。

## 主要覆盖与事实边界

真实 E1 已注册事件的 102 个源文件、13 份证据、6 个逐执行身份绑定通过独立只读预检。每个执行记录绑定 release、原 product commit、非布尔 exit、完整相等的 before/after 映射及本执行原始文件哈希。A24/A26 保留原完整 MUST、无 N/A；窗口逐项与声明总读取量在限制内。Main 派生的来源说明保留，不将其改称即时独立快照。RT06 的真实结构读取结果为 INSUFFICIENT_EVIDENCE；CLI 使用两个明确的模型模拟请求，实际 paid 0，结论仍 INSUFFICIENT_EVIDENCE，没有事件自证 PASS。

独立合成反例覆盖：空/未知事件、固定 Main 路径和原始 pin、主记录/冻结/窗口漂移、假 execution/support 角色绕过、漏映射/选择器别名、源集合缺失/外来/变化、错误 release/commit、布尔 exit、未绑定 execution 原始哈希、低 MUST/N/A、虚假证据/片段/哈希/required ref、窗口不存在/越界/超过 16384、声明累计读取超过 65536、失败事实、评价过程中的证据漂移。注入文字加模拟 PASS 仍由确定性失败覆盖；模拟模型虚假引用和未批准 N/A 不能 PASS。该合成语言覆盖不证明一般自然语言抗注入能力。

旧 baseline 仅使用固定 Main 归档映射读取原 60 个源文件，排除 41 个实验源。6 个历史未绑定记录与 3 个生成期 runtime-only 范围继续披露。当前 CH01 路径内容漂移不会静默改为当前版本认证；归档不执行。合成归档测试验证同一冻结原始字节、拒绝 CRLF→LF canonical fallback、任意 alias、目标路径与 Windows reparse/junction；后者即使目的文件内容哈希相同也拒绝，目的文件保留。

Main 转交 utility 只在独立临时根调用函数，`.env` 全为人工构造值，child subprocess 全为 stub，SQLite 全为假账本。16 类情形覆盖：成功单次进程转交、unknown/reserved hold、已用 gate、已有 started/output、缺 gate/错 purpose、冻结/错 cap、重复/空/错引号环境数据、child 非零退出、源变化、child 中断。验证每次假账本原字节未变、凭据值不写记录、父环境 KEY/TOKEN/提供商字段被过滤、只传进程环境单次启动无重试、失败 exit 保留、源变化导致拒绝成功、中断留下不可重发标记。事件付费 gate 绑定完整 event freeze 原始哈希，单 claimsHash 被拒绝；未知 release 在 gate/provider 构建前被拒绝。原账本 RO 行为由隔离 fake SQLite 和实现审阅验证，未重新读取原账本。本次不认证凭据有效性或真实 child/provider 通信。

## 稳定源与证据

48 文件 Main map 原始 SHA256：`4bc47615092cb6dbd7acd9c64b81ab583adae63bcc7f4964044cd6f3954b3f38`；最终 handoff：`7f1459e16e2212b4ccc75243291d9e13866e05e96d2c6c46832ba40e21d4b143`。代码完整 before/after 相等，最终再次逐文件核验；原冻结链共 17 文件（16 个 inputs 加 freeze 本身），16 项仍逐项等于既有 freeze。证据整理器首次将链文件数误作 inputs 项数，exit 1/chunk aa8efe；该 QA 整理错误与修正另存 failed-finalization-process.json，不改变已实际通过的 168/168 检查。

真实事件 Main 注册 pin：`8d60abed1e4746939576e2351f9dbdac055fbbcad91e49d06cedd2b6eb04fef3`；事件 freeze：`6ac8f14b3b8f4abf38fcc1e60327062540fc1678c9feb04546c34f61fd918a84`；旧归档 Main pin：`0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6`。

独立新增文件：`tests/review_evaluation_events.py`、本报告及 `evidence/qa/T27-evaluation-events-*` 新目录。最终证据根 `evidence/qa/T27-evaluation-events-20261005T105300Z`：`checks.json`、`result.json`、`process-result.json`、`real-structural.json`、`legacy-mock11.json`、`event-counterexamples.json`、`relay-counterexamples.json`、`legacy114/owner-check.json`、`cli-isolated-output/2/report.json`、`source-stop.json`、`artifact-sha256.json`。后两文件给出 QA/utility/原冻结输入源 pin 和全部最终证据原始哈希。命令解释器实际 `-B -X utf8` 记录在 process-result；原报告的 sys.argv 未包含解释器 flags，原样保留并明确解释。

证据整理实际命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T27-evaluation-events-20261005T105300Z/finalize.py` 最终 exit 0/chunk 6184ca，索引记录 917 份证据文件（索引本身不自引用）。最终原始 SHA256：result `a5e5b418895c7597932b9792199a9f73b09cc37baf57784825c39c9aab6188d9`；process `0b90d2d10ccf291475c907541df64d9e01b25843d0894c70b76947fd57ab4830`；source-stop `20befc0b94e49ce6bba69d125e03c68bb3801e37ee6c4bf7463d6ab408a1c8ca`；artifact-index `39fb5df7cba5185e74c9939aea144263f51bca471f947c1511f32c8d93331c77`；QA harness `2e48d442a463557f59ba6cce4bd177b6b1064b473b2f1fa8986754afe1acc329`；Main relay `a1561ac38f8756856642a1d7e991d9545d04c5afa591b71d281987f3ab6ebd41`。

本次已 SOURCE STOP。T25 原始 timeout unknown 历史、T27 人工会计核清与 full upper bound 事实均不重写；没有独立供应商账单证明、即时快照、教师签署或人工验收被虚构。
