# Backend Owner 开发交接（2026-11-04）

状态：SOURCE STOP，开发检查完成，待独立QA及本人核验。本文件不是正式QA或真人验收记录。基线8bd46aa；按docs/v5-sharing-leaderboard-plan.md实现，无真实模型/付费。

## 交付文件与行为

- backend/app/storage/sharing.py：四类增量表、已有V5迁移前SQLite一致性备份、共享状态/列表/加入、独立挑战轮次及个人最佳排行榜。
- backend/app/storage/v5.py：先校验本人会话归属，再由明确共享关联读取作者冻结定义；内部shared映射公开generated，私人levels仍作者限定；投影挑战和累计辅助。
- backend/app/storage/sqlite.py、saves.py：仅增加默认noop事务扩展点after_mutation，合法action/control/archive成功后、投影和receipt前调用。BoundStore接入共享轮次、计分和存档来源，重放不再次处理。
- backend/app/api/v5.py：新增五条认证接口；沿用CSRF/身份context/Origin/封装。公开schema与routes仅更新contracts/v2/build_contracts.py、api.schema.json、routes.json；未写level-draft.schema.json或经典合同。
- 本目录automated/backend/dev_check.py、dev_ai_bad_save.py及实际JSON：仅Owner开发入口和结果，TEMP数据库、合成定义/账号/Synthetic伙伴，无网络或账本。

## 接口与关键语义

五条新增接口：POST /api/v2/levels/{lid}/sharing；GET /api/v2/shared-levels；GET /api/v2/shared-levels/{share_id}；POST /api/v2/shared-levels/{share_id}/sessions；GET /api/v2/shared-levels/{share_id}/leaderboard。

封装和字段与实施规格一致。levels/level新增必填sharing；shared列表data为shared_levels/page/page_size/total，详情为shared_level。共享join仍返回session_response，并增加share_id；mode始终generated，level_id和created_at沿用作者原定义。共享state新增配对share_id/challenge，sessions摘要增加share_id/challenge_status；私人/经典不增加这两个来源字段。

首次发布从revision0变1；已有共享每次合法修改revision+1，取消再发保持share_id、首次published_at和榜单。不曾发布时取消为revision0的稳定无操作。hall仅公开，joined仅本人参与且包含取消共享。total_players为有有效成绩的独立玩家数；前50名外仍提供本人最佳与真实名次。

只有当前active轮次的合法action由playing变won才完成计分；完成、state、receipt同事务。完成成绩不因restore/reset改变。本轮active的playing档恢复保留attempt_id/started_at/累计辅助；跨轮或won档转practice；已finished后恢复创建新practice而保留原成绩。reset重新开active，未完成旧轮结束为practice。旧单槽及新档案来源单独关联，快照JSON/规则版本不变。坏档先失败，不改变资格。

有效免费提示累计hint_count；通过Storeguard的伙伴回复累计companion_count。失败、未知、重放不计。显式本地count_hint=false且usage.model_calls=0提醒不计；有效回复不以可省略的model_calls=1作为唯一条件。shared伙伴辅助有变化时即使count_hint=false也增加state.revision；前端以返回state为准。读档不回退累计数。

## 迁移、时钟与安全观测

新增shared_levels、shared_sessions、challenge_attempts、shared_save_origins。v5_metadata的sharing_schema_version=1保证幂等，database_version仍5。已有未迁移V5数据库启动写入前在同父backups创建<stem>-sharing-v1-<UTC>-<uuid>.sqlite一致性备份；新空库无备份。非V5仍拒绝。未触碰玩家数据库，实际迁移仅TEMP开发检查。

sharing.now_ms为挑战计时统一接点；UTC字符串由同毫秒值派生。计时包含停启/离线，finished.elapsed_ms非负整数；active/practice.elapsed_ms为null。排行榜直接查询finished轮次，按elapsed_ms/finished_at/attempt_id选个人最佳并稳定全局排序，不设成绩副本。

原events表同事务记录sharing_publish/unpublish/join、challenge_start/practice/finish/assistance，仅安全ID、状态、耗时与辅助计数；不写凭据、请求头、答案或定义。操作请求仍用原Store事件/receipt体系。迁移服务日志仅固定安全事件码。

## 实际开发执行

1. 完整规格/现状读取：d54a58、49c023、afde2c、768698等，exit0。
2. 核心开发命令：C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/project/stages/v5-sharing-leaderboard/automated/backend/dev_check.py。
   - 首次36c1d4启动、6a6ce6结束，exit1。到TEMP清理阶段因开发脚本使用sqlite连接上下文未close导致Windows文件锁；原dev-result-20261104T162327722850.json保留。未将这次写成完整通过。
   - 将开发脚本连接改用closing，第二次71e22d exit0，dev-result-20261104T162359868928.json：65个检查记录（包含逐行动作步骤，不能称65个独立测试）。覆盖发布/越权/独立会话/同轮读档/提示/真实领域witness EXIT/重放/最佳/跨轮练习/finished不可变/事务回滚/取消及再发/重启/备份幂等。该命令同时仅重建api.schema.json与routes.json并校验所用公开响应。
3. 窄补命令：C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/project/stages/v5-sharing-leaderboard/automated/backend/dev_ai_bad_save.py，6aa3c2 exit0；ai-bad-save-20261104T162558434095.json，12条记录。Synthetic回复count_hint=false/省略usage仍计伙伴并增加revision、重放不重复、无效/超时/local提醒不计，坏档保持完整state和challenge。
4. git diff --check -- backend/app/storage/v5.py backend/app/storage/sqlite.py backend/app/storage/saves.py backend/app/api/v5.py contracts/v2/build_contracts.py contracts/v2/api.schema.json contracts/v2/routes.json，f1cf24 exit0。Git提示部分文件后续会转CRLF，未因此重新改写历史文件；新未跟踪文件不在该git diff检查范围。

## 独立验证接点与限制

QA可patch sharing.now_ms控制时间，patch BoundStore.after_mutation或sharing.after_mutation/audit注入事务异常。原CompanionService依旧可注入；Owner的Synthetic仅在TEMP检查中替换app.state.companion_service，不是产品fallback。

未运行正式QA、浏览器、前端构建、旧全套、真实provider、费用预检或玩家库测试；未提交/推送或派生代理。旧经典/旧档完整兼容矩阵、稳定同耗时/前50外本人排名、并发、跨进程真实浏览器与两桌面等由独立QA针对规格验证。现有TestClient httpx弃用提示保留，未更换依赖。服务端时间依赖本机系统时钟；向后调整时最终耗时下界为0。当前只在本地账号间共享，不做公网部署。

## 独立QA首轮后的窄合同修复（2026-11-04）

实际只读api-run1/output.txt和junit.xml：17项，11通过/6失败，其中generated旧单槽恢复200的slot未被save_slot.oneOf接纳为真实合同缺口；其余新测试适配由QA处理，Owner未更改测试或重跑API。

仅改contracts/v2/build_contracts.py及api.schema.json：复制原3.4经典legacy严格分支，仅替换schema_version=2.0.0、level_version=5.0.0后追加generated legacy分支。保留save_id/name/kind常量、room_id/status/clues_found必须null、必填字段和additionalProperties=false。原有全部分支逐项相等，完整JSON差异仅此一分支。

实际命令5a0082：Python -B -X utf8 stdin构建/比较合同、检查实际失败slot形状及经典正例、非null房间/混合版本/任意legacy ID反例，并仅写api.schema.json；随后git diff --check -- contracts/v2/build_contracts.py contracts/v2/api.schema.json，exit0。routes.json、level-draft.schema.json、经典合同原字节未改。机械结果automated/backend/legacy-contract-fix.json（8条合同检查，非API复测）。未打开数据库、模型/账本/网络；后端产品/私有快照/权限规则未改。再次SOURCE STOP，独立QA按Main要求仅重失败6项。
