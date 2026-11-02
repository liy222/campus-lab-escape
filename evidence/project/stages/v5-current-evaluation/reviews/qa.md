# 当前 V5 C1–C3 定向证据复核

日期：2026-11-02。基线产品为 f0be900；本阶段只重跑计划指定的四个 pytest 节点，未运行全套、构建、浏览器、真实模型、账本或玩家数据库检查。

## 实际命令与结果

外层实际命令：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 tests/v5/run_current_evidence.py --execute
```

外层 runner 退出码 **0**；内层 pytest 退出码 **0**，`4 passed, 1 warning in 3.87s`。警告为现有 Starlette TestClient 使用 httpx 的弃用提醒。操作者角色记录为 Independent AI QA agent `/root/passage_qa_exec_luna`；记录中的 `host_account=liyh` 仅是本机执行账户，不作为真人签字。

精确执行节点：

```text
tests/v5/test_planner_fixed.py::test_affected_nine_and_twenty_original_inputs
tests/v5/test_security.py::test_all_private_ids_read_write_denied_without_owner_change
tests/v5/test_integration.py::test_three_archives_restore_delete_reset_relogin_reopen
tests/v5/test_integration.py::test_bad_definition_or_archive_does_not_overwrite[checksum]
```

本轮 JSON 结果、脱敏 pytest 输出及来源映射：[run result](../automated/current-evidence-20261102T064847Z-6770f20d/result.json)、[pytest 摘要](../automated/current-evidence-20261102T064847Z-6770f20d/pytest-output-redacted.log)。前后共绑定71个产品、合同、测试、夹具及资源元数据文件，逐文件 bytes/SHA 一致。

## 从实际观察派生的范围

四个既有 `observed_output` JSON 由本次测试实际生成，先写入其路径约束允许的新子目录，再逐字节复制到固定阶段。原始旧路径输出、当前阶段副本和字节/摘要对应关系见结果文件的 `raw_observed_files`；所有四份副本均逐字节相同。派生摘要在 [derived observations](../automated/current-evidence-20261102T064847Z-6770f20d/derived-observations.json)，由这些实际文件计算，没有预填预期值：

- **C1：**9/9 合法输入由当前 compiler/`GeneratedRules` 实际编译，并逐步回放至 EXIT；20/20 原冻结坏例被拒绝。冻结输入摘要与既有 `INPUTS` 指纹一致。这是 Synthetic 输入对当前产品代码的实际执行，不是伪造回放，也不代表真实 AI 质量。
- **C2：**另一 Synthetic 账户发出的11个资源读取/写入请求均为404；每次前后目标状态哈希不变。凭据 Cookie/token 不在公开结果中；原观察 JSON 含 Synthetic 资源标识，仅保留在本次观察原件/逐字节副本中。
- **C3：**三个时刻均实际恢复成功，保存与恢复状态哈希及定义哈希匹配；checksum 损坏的恢复被409拒绝，观察到的当前游戏字段前后哈希一致。测试还实际断言原始状态 JSON未被改写、损坏档仍存在。

## 隔离与日志边界

测试使用 `FixtureGenerator` 和独立 TEMP：runner 为导入期 SQLite 路径及 pytest `--basetemp` 预设当前运行专用目录；既有 `conftest.py` 另创建自己的临时导入目录，实际 app 测试数据库由 pytest `tmp_path` 提供。生产数据未访问或改写。真实模型调用、付费调用、玩家数据库访问均为0。

公开阶段只保存脱敏 pytest 日志和观察 JSON；测试原始 stdout 的 SHA 记录在结果中，原始日志保存在本机 TEMP 的 `raw-pytest-sensitive.log`，不复制到证据目录或 Git，可能含 Synthetic 凭据/token信息。不要把该本地日志当作公开证据或真人记录。

## 限制

这次只绑定和执行四个既定节点，不表示整个 V5 测试套件或所有产品源码都通过；扩大到 `backend/app/**/*.py` 的源码映射是当前候选身份绑定，不是全后端覆盖声明。C1使用冻结离线 Synthetic 输入，不衡量模型内容质量；C2/C3只覆盖指定双账户资源与档案路径。未更新可信评价登记或 loader/pin，也没有评价 PASS、真人接管、同伴/教师核验或整版接受结论；这些由 Main/独立 Evaluator 按计划另行处理。
