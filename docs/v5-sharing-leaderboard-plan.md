# 关卡共享与通关排行榜实施规格（2026-11-04）

用户明确批准实施本对话完整构建计划。开发基线为8bd46aa；本文件为执行范围与跨模块约定，不是已执行或已验收的证据。

## 目标与边界

复用V5已有生成定义、规则、账号、存档、AI与五主题美术，新增本地登录账号之间的共享大厅和逐关卡通关排行榜。作者主动发布；作者可参榜并标记身份；每账号取最快成绩。允许免费提示和伙伴，并标注使用情况。连续服务端计时包含离线/读档/退出/重启；本轮读档不回退计时，跨轮读档转练习。只有真实行动通关可产生一次成绩。原私人、经典会话及旧快照不变。本轮真实模型/付费/新美术0，不部署公网。

SHARE-01发布/取消与固定定义；SHARE-02独立进度和私有资源隔离；SHARE-03取消后阻止新加入且保留已参与入口；RANK-01服务端连续计时与原子结算；RANK-02个人最佳/作者标记/稳定排序；RANK-03本轮读档、跨轮练习和辅助累计；COMPAT-01旧账户/私人/经典/存档兼容。实际验证和剩余限制随执行保存。

## 接口约定

所有路径位于/api/v2；认证、CSRF、身份上下文、错误封装保持现有体系。后台时间使用UTC，duration为非负整数毫秒。

- `SharingState = {share_id:string|null,published:boolean,revision:number,published_at:string|null}`。本人levels/level元数据新增sharing（尚未发布默认null/false/0/null）。
- `POST /levels/{lid}/sharing`，body为`{published:boolean,revision:number}`，response.data为`{sharing:SharingState}`。仅作者可改，revision作比较并更新；版本冲突409/STALE_SHARING，前端刷新状态。首次发布revision=0。重发不创建另一共享关卡，取消/再发布保留榜单。
- `SharedLevel`包含原Level展示字段（原level_id/title/story/theme/room_count/difficulty/created_at/definition_hash等），及`share_id,author_username,is_author,published,sharing_revision,published_at,session_id:string|null,status:playing|won|null,challenge_status:active|practice|finished|null`。
- `GET /shared-levels?view=hall|joined&page=1`，data为`{shared_levels:SharedLevel[],page,page_size:20,total}`；hall仅已发布，joined仅本人已加入，包含已取消共享。稳定按首次发布时间倒序、share_id排序。
- `GET /shared-levels/{share_id}`，data为`{shared_level:SharedLevel}`；已发布或本人已加入/作者可读，否则404。
- `POST /shared-levels/{share_id}/sessions`，body为`{request_id:string}`，response复用session_response，data额外含share_id。首次201，复用200；同账号同关卡只建一个共享会话，重开使用reset开启新轮次。已取消时仅原参与者可继续。
- 所有共享会话对外仍`mode=generated,level_id=原关卡ID`，新增`share_id`标识来源；内部会话模式可用shared以与作者私人会话区分。sessions列表及state/session_response一致映射。私人POST /sessions仍只接收classic/generated，不能用原level_id绕过共享加入检查。
- `Challenge = {attempt_id,status:active|practice|finished,started_at,finished_at:string|null,elapsed_ms:number|null,hint_count,companion_count,is_author}`，仅共享state新增share_id和challenge。实时计时由前端按started_at显示，正式结算仅用服务端elapsed_ms。
- `LeaderboardEntry = {rank,attempt_id,username,is_author,elapsed_ms,finished_at,hint_count,companion_count}`。
- `GET /shared-levels/{share_id}/leaderboard`，data为`{share_id,entries:LeaderboardEntry[],own_entry:LeaderboardEntry|null,total_players}`。前50名，own_entry始终包含本人最佳/名次（若有）。访问规则同共享详情。每玩家按elapsed_ms/finished_at/attempt_id取最佳，再按相同键整体排序，rank从1起。

合同生成源与schema/routes同步；前端额外字段均可从现有Level/Run/GeneratedState扩展。保留原创建时间和level_id，确保跨账号场景选图一致。

## 存储与事务

新增共享发布、共享会话关联、挑战轮次、存档轮次关联四类表及必要索引；排行榜直接查询有效完成轮次，不设可独立编辑的成绩副本。固定引用已保存定义及摘要，不复制生成任务或重新请求AI。先验证会话本人归属，再通过明确共享关联加载原定义；私人levels接口保持作者限制。

在原Store事务内增加默认无行为的窄扩展点，V5共享BoundStore接入action/reset与archive create/restore/delete及旧单槽save/restore的轮次关联。行动通关、轮次完成和幂等receipt同事务；重放不重复处理。只有action的playing→won记分，restore/GET不得记分。reset使未完成轮次结束并创建新轮次。finished成绩不可由后续读档修改。

存档轮次关联独立于快照JSON。本轮未完成挑战的playing存档恢复可继续计时；跨轮/已完成轮次存档或won存档恢复后转练习，不撤销原已完成成绩。坏档恢复失败不修改资格。练习仅由reset新开完整挑战恢复参榜。

成功的有效免费提示累计hint_count，成功伙伴回复累计companion_count；失败、未知结果、重放均不增。计数不随读档回退，并仅影响对应当前轮次。AI旧安全与费用体系保持。

增量升级前为已有V5数据库创建本地SQLite一致性备份，新空库不备份；备份在该数据库父目录backups内（玩家库为ignored data/backups）。数据库版本仍5，以独立共享迁移标记保证幂等；不改旧状态/定义/存档JSON，不触碰canonical预算库。

## 责任与执行节奏

Main：本文件、AGENTS/PLAN/STATUS/DECISIONS、固定证据索引与真人交付、Git；现有Backend临时拥有storage/v5.py、新sharing helper、必要sqlite.py/saves.py窄hook、api/v5.py与contracts/v2合同源及产物。现有Frontend拥有frontend/共享大厅/状态/榜单与样式类型；不改素材。现有QA拥有新增共享API/浏览器测试/fixture与本阶段结果。代理不提交、不再派生代理。

先实现完整后端/合同和前端，QA可提前准备但稳定后才集中正式验证。只做受影响必要回归、一次必要V5构建、两桌面浏览器与独立复核；失败保留，只补受影响范围。开发持续记录，不逐小步审批。完整功能集中一次liy222提交/推送，不改历史评价原件/pin或伪称旧PASS适用新源码。

## 验收与交付

隔离TEMP数据库、可控时间、Synthetic伙伴：共享定义/选图一致，A/B/C独立进度/存档和越权404；发布取消/原参与继续；作者独立私人及共享会话；连续计时/进程重开；本轮/跨轮/坏档/won档；重放/回滚/最佳/同耗时稳定排序；免费提示与伙伴成功/失败/重放；旧经典/私人/旧档兼容。前端1280×720和1920×1080覆盖完整发布→加入→存读档→通关→榜单→作者→重开→取消流程。

证据：evidence/project/stages/v5-sharing-leaderboard/；本人实际反馈：evidence/project/human-reviews/v5-sharing-leaderboard/round-01/。技术完成后状态为待本人检查，提供效果入口和简短步骤；未发生的本人/同伴核验不预填。
