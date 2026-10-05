# 离线关卡设计与确定性判定资料

版本：基线 level `1.0.0`；契约 `1.0.0`。Main 于 2026-10-01 审查批准冻结。本文件含秘密答案与完整解法，仅供服务端规则和离线验证，禁止送入前端构建、模型上下文或公开 HTTP。内容是设计，不是通关事实。

## 内部真值

game_fields 为 room_id、inventory（唯一 item ID 有序数组）、discovered_clue_ids（首次发现顺序唯一数组）、flags、opened_containers（唯一 ID 数组）、status。flags 固定为 r2_unlocked、power_on、r3_unlocked、check_done 四 boolean。opened_containers 只允许 r1_cabinet/r2_drawer；room 为 R1/R2/R3/EXIT；status playing/won。新局全 false、空数组、R1/playing。revision/generation 是当前会话的版本元数据，不从快照恢复。

不变量：R2/R3/EXIT 必须已有 r2_unlocked；R3/EXIT 必须已有 r3_unlocked；r3_unlocked 必须 power_on；check_done 必须 power_on；won 等价于 room=EXIT 且 power_on/check_done；access_card 需要 r1_cabinet 已开；emergency_key 需要 r2_drawer 已开；power_on 时 fuse 已安装且不在 inventory。屏幕 clue 需要 power_on。包含未开放容器的拾取记录、未知 IDs、重复 IDs、类型错误、不一致 room/status 均拒绝快照。基线 r3_unlocked 仍需持有 emergency_key；v2 可已消耗。允许已发现线索跨房间保留；线索不是通关的强制先决，玩家可自行推理/试码，后端精确校验仍是真值。

## 房间、对象与线索正文

| 房间 | object_id | 场景公开外观（未查看时） | inspect 的当前观察/发现 |
|---|---|---|---|
| R1 值班室 | r1_note | 桌上有一张值班便签。 | clue r1_note_clue：值班便签；“三角记为3，圆记为8，方记为2。” |
| R1 | r1_cabinet | 带数字锁的值班柜，门上贴着形状标签。 | clue r1_cabinet_clue：柜门顺序；“柜门标签从左到右是：三角、圆、方。”；打开后还描述门卡 |
| R1 | r1_door | 通向设备间的刷卡门。 | “需要门卡解锁；刷卡门”或“刷卡门已解锁”，无 clue |
| R1 柜开后 | access_card | 柜内有一张门卡。 | “设备间门卡”，无 clue |
| R2 设备间 | r2_fuse | 桌上放着备用保险丝。 | “可装入电源箱的保险丝”，无 clue |
| R2 | r2_powerbox | 电源箱有空置保险丝槽。 | “尚未安装保险丝”或“电源已恢复”，无 clue |
| R2 | r2_monitor | 电源箱旁有一块屏幕。 | 未通电“当前无显示”，无 clue；通电后 clue r2_monitor_clue：屏幕读数；“青色7、橙色2、紫色4。” |
| R2 | r2_drawer | 带数字锁的抽屉上有颜色标签。 | clue r2_drawer_clue：抽屉顺序；“抽屉标签从左到右是：青、橙、紫。”；打开后还描述钥匙 |
| R2 | r2_door | 通向出口控制室的钥匙门。 | “需要应急钥匙解锁”或“门已解锁”，无 clue |
| R2 抽屉开后 | emergency_key | 抽屉内有一把应急钥匙。 | “出口控制室的应急钥匙”，无 clue |
| R3 出口控制室 | r3_checklist | 出口旁贴着一张检查单。 | clue r3_checklist_clue：出口检查顺序；“依次确认：冷却、通风、照明。” |
| R3 | r3_panel | 检查面板上有设备标签和数字键。 | clue r3_panel_clue：设备标签；“冷却对应2，通风对应3，照明对应1。” |
| R3 | exit_door | 实验室出口等待检查完成。 | “尚未完成出口检查”或“出口检查已完成”，无 clue |

R2 的 r2_fuse 是对象 ID，take 参数 item_id=fuse。其他两物品的 object_id 与 item_id 相同。保险丝领取后 r2_fuse 不再可见；物品已领取后不再出现在 objects。容器、门、设备持续可见。EXIT objects/inventory 可显示已持有物品，objects/exits 均为空；inspect 无可见目标，get_inventory 仍可用。clues 跨房间保存。

房间邻接：R1↔R2 经 r1_door，R2↔R3 经 r2_door，R3→EXIT 经 exit_door；无其他移动。r1_door 解锁 flag=r2_unlocked；r2_door 解锁 flag=r3_unlocked；出口 unlocked=power_on && check_done。R2/R3 返回前房间始终可以，门永久解锁；不需重复用钥匙或卡。

## 秘密规则表

| 动作 | 前置 | 成功转换 | 秘密判定 |
|---|---|---|---|
| submit_code r1_cabinet | R1，柜可见 | opened_containers 增 r1_cabinet | 精确 code="382" |
| take access_card | R1，柜已开，未领取 | inventory 增 access_card | 无 |
| use_item access_card,r1_door | R1，持卡 | r2_unlocked=true，保留卡 | 无 |
| move R2 | R1，r2_unlocked | room=R2 | 无 |
| take fuse | R2，未领取且未安装 | inventory 增 fuse | object r2_fuse |
| use_item fuse,r2_powerbox | R2，持 fuse | 移除 fuse，power_on=true | 安装保险丝消耗物品 |
| submit_code r2_drawer | R2，power_on | opened_containers 增 r2_drawer | 精确 code="724" |
| take emergency_key | R2，抽屉已开，未领取 | inventory 增 emergency_key | 无 |
| use_item emergency_key,r2_door | R2，power_on，持钥匙 | r3_unlocked=true，基线保留钥匙 | CH01 修改见下 |
| move R3 | R2，r3_unlocked | room=R3 | 无 |
| submit_code r3_panel | R3，power_on | check_done=true | 精确 code="231" |
| move EXIT | R3，power_on && check_done | room=EXIT,status=won | 无 |

已成功打开柜/抽屉或完成检查时同目标重复 submit_code：当前可见且 playing 时可返回 changed=false，无再次副作用。错误输入仍可 WRONG_CODE（实现统一采用仍校验 code 后返回不变成功）。重复已解锁门 use_item 可不要求已消耗钥匙；仍校验合法 item/target 配对、当前目标可见。重复电源箱 use_item fuse 在安装后可 changed=false（不要求背包中不存在的 fuse）；不能返还物品。已经领取物品重复 take 返回 ALREADY_TAKEN；隐藏未领取返回 NOT_VISIBLE。必须保留领取事实：access_card/emergency_key 通过 inventory 或 v2 门消耗判定；fuse 通过 inventory 或 power_on 判定。

## 完整标准手动路线与版本

新建 R1/revision0。每行使用当前服务端 revision/generation 和新 request_id；inspect 新 clue 或成功进度各 +1：

1. inspect r1_note → r1_note_clue（rev1）。
2. inspect r1_cabinet → r1_cabinet_clue（rev2）。
3. submit_code {target_id:r1_cabinet,code:"382"} → 开柜（rev3）。
4. take access_card → 门卡（rev4）。
5. use_item access_card,r1_door → R2 解锁（rev5）。
6. move R2 → 设备间（rev6）。
7. take fuse → 保险丝（rev7）。
8. use_item fuse,r2_powerbox → 供电，保险丝消耗（rev8）。
9. inspect r2_monitor → r2_monitor_clue（rev9）。
10. inspect r2_drawer → r2_drawer_clue（rev10）。
11. submit_code r2_drawer,"724" → 开抽屉（rev11）。
12. take emergency_key → 钥匙（rev12）。
13. use_item emergency_key,r2_door → R3 解锁，基线钥匙保留（rev13）。
14. move R3（rev14）。
15. inspect r3_checklist → r3_checklist_clue（rev15）。
16. inspect r3_panel → r3_panel_clue（rev16）。
17. submit_code r3_panel,"231" → check_done（rev17）。
18. move EXIT → won（rev18）。

期间保存不增 revision；额外重复查看不增；reset/restore 会改变 generation 并增加当前 revision，使此示例版本序列不再适用。AI 路径允许 inspect 自动登记线索，但进度步骤全部先 proposal、再玩家 confirm，提案不增 revision。

## CH01 预留影响（尚非批准或执行事实）

level `2.0.0` 只改变：首次成功 use_item emergency_key,r2_door 解锁时移除 emergency_key，receipt.consumed_item_ids=[emergency_key]。失败、重放、已开门重用不消耗；门永久解锁，往返无需钥匙。公共 API schema 仍为 `1.0.0`。快照 level 版本不一致拒绝。v1 基线数据独立保存；实现前 Main 登记变更理由/批准来源/验收。A27 须验证首次开门、重放、重复使用、再进入、保存恢复及旧快照拒绝。
