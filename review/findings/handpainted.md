# 手绘素材接入独立 QA

状态：独立联合范围验收通过，SOURCE STOP。候选为 `evidence/integration/handpainted/candidate.json`，raw SHA256 `e7341a6d778c0af4295c791946ec92633347287e1ae4a4d8813af3c58ab39f81`，242 个产品/规格/PNG/元数据文件。未发现需要产品修复的阻塞项。

正式静态核验 `20261009T045232371706-static/run.json` exit 0：85 个新接入 PNG 全部对应 canonical 原始字节，尺寸/alpha>16 或全幅 bbox 一致；242 候选与389 不变量均吻合。

唯一独立构建 `20261009T045244235346-build/run.json` exit 0：实际 `npm.cmd run build`，52 modules、Vite 2.98 秒；保留既有 Phaser 1.388 MB 大包提示。构建前后242源码 raw 一致。

浏览器结果按独立范围保留，不合计为单轮总数，也不称单轮完整全绿：

| 实际运行 | exit / 记录数 | 可复用范围与边界 |
|---|---|---|
| `20261009T045300333Z-browser` | 1 / 201 | 真实 UI R1全部、R2全部、R3早期及刷卡接受；44 个截图 checkpoint、精确已知线索、三个特写隔离、375/812电路与顺序热点不重叠及每房375边缘 mouse/touch 正确归属、PNG实际abort5次/阻断/retry、首屏lazy、所选纸条存档恢复/cancel/reload、唯一实际后端进程重启。最后QA未取消仍选中的可重复门禁卡，把合法 use_item409误当inspect200；是新adapter失败，原证据不改。 |
| `20261009T045643974Z-browser` | 0 / 101 | 其中62条明确为新会话公开API前置fixture，准备至CARD_ACCEPTED，不计真实UI路线。真实UI只续验 FINAL_CHECK→设备草稿→passed→UNLOCKED→OPEN→EXIT，375/812草稿布局、权威结算6字段、末段五时刻列表中的初始/已取保险丝/Win选择恢复/cancel及Win重载。旧201范围、构建、重启、缺图和lazy不重复。 |
| `20261009T050000993Z-browser` | 0 / 75 | 公开API fixture准备至Win；仅补过渡完成后的真实桌面Victory PNG和两个原生按钮78×44。第二次桌面PNG拍到既有渐入暗幕，保留该图作为历史时机记录；最终使用本次 `Victory-desktop-settled.png`。不再验路线、存档、构建、重启、缺图或lazy。 |

所有正式运行 candidate242 和 immutable389 前后一致。旧测试与旧证据未修改；没有完整127后端suite或真实模型调用。本轮隔离SQLite只用于QA新会话，session/key/token未写入执行证据。

正式PNG实际查看17张，具体路径/hash在 `evidence/integration/handpainted/qa/result.json`：三房总览；R1钟面、记录、显微视野、柜内/标签；R2通电总览与375电路/login；R3对应表、早期375面板、375最终草稿、OPEN门；手机Victory、历史暗幕桌面Victory及最后settled桌面Victory。没有声称逐85张审美认证。已观察精确规则文本可读；所查物件没有独立重复或拉伸，实际绘制frame检查统一缩放且source frame等于元数据。

非阻塞视觉限制：R3总览背景墙管在终检台右上方悬挂，与物件自带管口略错位；没有影响热点或路线。钟面纸纹补片有可辨接缝。均作为画面组合/生成材质限制记录，未扩展为本轮源修改。手机特写保持完整stage紧凑布局，表单控件可滚动；测试没有覆盖所有物件每一个边缘、所有浏览器/设备或人类完成时间。

主结果与逐文件artifact rawhash：`evidence/integration/handpainted/qa/result.json`、`artifacts.json`。以下准备记录与修正说明保留为历史，不替代以上实际执行结果。

仅新增 `tests/handpainted/` 与本报告、本轮 QA 证据。旧测试、素材包、游戏源与旧执行证据保持不变。

预定正式范围：一次前端构建；真实 Canvas/触摸/键盘 R1→R2→R3→EXIT；设备全状态及已观察精确线索；图片与热点、透明边界和等比显示；特写背景输入隔离；研究纸条早显四设备并保留服务端提交门槛；回退/恢复通断电；375 竖屏与 812 横屏 44px；多时刻存档/选择恢复/重载/一次实际后端进程重启；真实 PNG 缺图阻断与重试、首屏懒加载和结算权威字段。

准备脚本沿用已封存成功的 closeup QA Canvas 坐标输入与电路公共端口推导，正式执行使用新的独立输出目录。失败 adapter 时代将保留，重复范围不相加，不把公共 API fixture 称为真实 UI 路线。

素材包已有 84 映射+5 净背景，其中正式新接入为 80 对应PNG+5 净背景。4 张既有全景样稿不作为互动分层背景。静态核验会对 85 实际副本与元数据的尺寸、SHA256、alpha>16 可见 bbox 和来源映射逐项读取；catalog 标为 closeup、净背景及无 alpha 的图片按既定全幅约定计算。

正式执行前修正：Main 审阅指出初版脚本采用非零 alpha 而非 Owner 的 alpha>16，可能错误拒绝极淡投影边界。原未执行 adapter/协议保留在本轮 QA `preparation-epochs/`；修正没有弱化源副本 SHA、尺寸或存在性检查，不是产品缺陷或正式执行失败。当前已读 `GameCanvas` 中 `data-paint-frame=bbox-contain-v1` 和已知当前视图线索 ID 标记，并绑定显式预期；仍需 Owner SOURCE STOP/Main GO。

正式执行前增强：Main 在未封存产品中指出手机小游戏热点扩展可能重叠，已由 Frontend 处理绘制与输入坐标。新 QA 将在每个实际截图 checkpoint 核对所有电路模块/顺序设备的 DOM 实际矩形两两不相交，浮点容差 0.05 CSS px，并在 375px 每房间至少一个热点的内部边缘执行真实 mouse 和 touch：R1 检查观察回执 object_id，R2 检查旋转回执 module_id 与实际旋转量，R3 检查设备草稿归属且服务端状态不变。原中心路线与前一准备版本保留；尚未运行产品正式测试。

限制：代表 PNG 必须在正式执行后实际查看，自动状态属性不能代替视觉验收；无真实模型/密钥/付费调用，无历史用户数据库、root CMD 交互启动或人类完成时间声明。冻结后若出现产品缺陷须 Owner 修复和 Main 新冻结，QA 不编辑产品源。
