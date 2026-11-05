# 共享与排行榜独立 QA（2026-11-04）

结论：本阶段定向技术范围联合通过，待用户本人检查。执行者是独立 AI QA 智能体，尚无真人或同伴验收。项目真实模型/付费调用0；全部使用自有TEMP、Synthetic定义/伙伴和可控时间，未触碰玩家8001服务、玩家库、Key或预算账本。

覆盖共享固定定义及原level_id/创建时间/选图、A/B/C进度与私人存档隔离、作者私人/共享会话并存、发布取消与原参与继续、CSRF/认证、连续计时和重开、同轮/跨轮/finished/won/坏档、通关事务回滚及幂等、个人最佳/同耗时排序/作者、前50外本人排名、提示/伙伴成功失败未知与重放、旧经典/私人/旧policy09和迁移前一致性备份幂等。一个实际子进程继续原attempt/started，真实最后action结算654321ms且不调用生成。

## 实际执行、问题与窄补

| 命令与证据（均在本阶段automated下） | 实际结果 |
|---|---|
| `python -B -X utf8 -m pytest -q --tb=short` 新共享12项+旧5节点；完整argv见`api-run1/run.json` | f3ea1f/36fd7b exit1，17项11通过/6失败，18.647s；原日志/JUnit保留 |
| 仅原失败6节点，`api-failed6-run1/run.json` | fca100 exit1，5通过/1失败，7.058s |
| 仅辅助计数方法，`api-assists-run1/run.json` | cbe20f exit0，1通过，2.667s |
| 仅实际child-reopen，`api-child-reopen1/run.json` | 4f9ce7 exit0，1通过，3.248s |
| `frontend: npm run build`，VITE_GAMEPLAY_VERSION=v5、CAMPUS_BACKEND_URL=http://127.0.0.1:8001；`build-run1/` | 81a137/b3f84f exit0，一次构建10.967s；在后端合同窄修等待期间完成，前端源码持续STOP，未重建 |
| `node tests/v5/run_sharing_browser.mjs`，后续`--after-key-check` | 首3个控制器定位失败保留（目录13-45-35/13-46-45/13-48-03），只完成注册/Key等准备；末e863eb/9f5e23 exit0，102条观察、issues[]、17.327s，目录`browser-2026-11-04T13-49-27-940Z-831e772c/` |
| `node tests/v5/run_sharing_browser.mjs --cover-only --resume-from ...831e772c/result.json` | ae9f4b exit0，4条观察；目录`browser-cover-2026-11-04T13-54-10-571Z-7fce3dab/` |

唯一实际产品问题是V5 generated旧单槽恢复返回200但slot不在公开save_slot合同分支。Backend仅追加严格2.0.0/5.0.0 legacy分支，保留经典分支与null/常量限制；受影响测试窄补通过。其余API失败为新QA的query路由匹配、422/504/503预期、Synthetic mock调用计数和sqlite.Row表示适配，未削弱原安全/幂等断言。浏览器首3次为新控制器嵌套label定位失败，未发起共享主链；修正为真实表单select及实际值断言。原非零退出和全部原件保留，不累加成单轮全绿。

## 实际界面与效果入口

1280×720及1920×1080均真实点击发布、加入、保存/确认读取、最终出口通关、排行榜、重开与取消。旧谜题控件未改，其前置由隔离API witness准备，不能称整条旧谜题UI重通。共享前填Synthetic Key切大厅后已清空；另一账号的进度、作者/本人榜单标记无残留。首轮Key记录复用，不重复当新范围。

末主链12张截图包括`published-{1280,1920}.png`、`hall-*`、`challenge-restored-*`、`author-finished-*`、`leaderboard-*`和`cancelled-joined-*`。独立QA实际查看leaderboard1280、hall1920、challenge-restored1920，未见新布局或操作阻挡。Main发现首hall封面抓图过早；仅复用同TEMP的“我的参与”卡片加载复核（与大厅同SharedLibrary/同URL），实际PNG HTTP200、2445959bytes、1672×941解码成功，`shared-cover-loaded-1280.png`已显示封面。未改产品或重跑主链。

源文件：新`tests/v5/test_sharing.py`、`test_sharing_reopen.py`、`sharing_fixture_server.py`、`run_sharing_browser.mjs`；只做这些新QA文件的适配。语法检查实际exit0；末UI结果记录实际来源及dist入口摘要。新结果/日志有限凭据模式扫描未发现匹配，自有服务均已停止；没有新增封条。

限制：前50窗口测试使用51条受控SQL成绩夹具，只证明查询窗口与本人名次，不冒充51次实际通关。浏览器毫秒成绩是自动化运行，非人类难度或用时；真实伙伴质量/全部主题/并发压力/跨机器时钟未验证，服务端计时依赖本机系统时钟。本轮技术结果不更新旧评价pin，也不把旧C1-C3 PASS扩展为新源码评价。

请本人在当前预览用两个账号验证：作者发布→另一账号加入并存读档→通关看本人/作者榜单→重开→作者取消后原参与仍可继续、新账号不可加入。核验前保持待本人检查。
