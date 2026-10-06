"""Trusted CH01 level rules; secret answers stay on the server."""
from copy import deepcopy

from .models import GameState, RuleError

SCHEMA_VERSION = "1.0.0"
LEVEL_VERSION = "2.0.0"
CLUES = {
    "r1_note_clue": {"clue_id": "r1_note_clue", "object_id": "r1_note", "title": "值班便签", "text": "三角记为3，圆记为8，方记为2。"},
    "r1_cabinet_clue": {"clue_id": "r1_cabinet_clue", "object_id": "r1_cabinet", "title": "柜门顺序", "text": "柜门标签从左到右是：三角、圆、方。"},
    "r2_monitor_clue": {"clue_id": "r2_monitor_clue", "object_id": "r2_monitor", "title": "屏幕读数", "text": "青色7、橙色2、紫色4。"},
    "r2_drawer_clue": {"clue_id": "r2_drawer_clue", "object_id": "r2_drawer", "title": "抽屉顺序", "text": "抽屉标签从左到右是：青、橙、紫。"},
    "r3_checklist_clue": {"clue_id": "r3_checklist_clue", "object_id": "r3_checklist", "title": "出口检查顺序", "text": "依次确认：冷却、通风、照明。"},
    "r3_panel_clue": {"clue_id": "r3_panel_clue", "object_id": "r3_panel", "title": "设备标签", "text": "冷却对应2，通风对应3，照明对应1。"},
}
ITEMS = {
    "access_card": {"item_id": "access_card", "name": "门卡", "description": "一张边角磨损的塑料卡片，印字已经模糊。"},
    "fuse": {"item_id": "fuse", "name": "保险丝", "description": "细长的玻璃管里有一根完好的金属丝，两端包着金属帽。"},
    "emergency_key": {"item_id": "emergency_key", "name": "应急钥匙", "description": "一把老旧的黄铜钥匙，标签已经脱落，齿槽有使用痕迹。"},
}
ROOMS = {
    "R1": ("值班室", "夜色透过窗户，桌面与柜门隐在昏暗的光线里。"),
    "R2": ("设备间", "室内安静得只剩脚步声，几台设备的指示灯都没有亮。"),
    "R3": ("出口控制室", "控制台旁贴着旧纸张，厚重的出口门立在房间尽头。"),
    "EXIT": ("实验室出口", "已离开实验室。"),
}
ITEM_OBJECTS = {"access_card": "access_card", "fuse": "r2_fuse", "emergency_key": "emergency_key"}
PAIRS = {("access_card", "r1_door"): "r2_unlocked", ("fuse", "r2_powerbox"): "power_on", ("emergency_key", "r2_door"): "r3_unlocked"}
CODES = {"r1_cabinet": "382", "r2_drawer": "724", "r3_panel": "231"}


def action(tool: str, label: str, **arguments) -> dict:
    return {"tool": tool, "label": label, "arguments": arguments, "requires_code": tool == "submit_code"}


def visible_objects(state: GameState) -> list[dict]:
    def obj(object_id, name, kind, description, locked=False, item_id=None):
        actions = [action("inspect", "观察", object_id=object_id)]
        if locked:
            actions.append(action("submit_code", "互动", target_id=object_id))
        if item_id:
            actions.append(action("take", "互动", item_id=item_id))
        return {"object_id": object_id, "name": name, "kind": kind, "description": description, "actions": actions}

    if state.room_id == "R1":
        opened = "r1_cabinet" in state.opened_containers
        objects = [
            obj("r1_note", "值班便签", "clue", "桌上有一张值班便签。"),
            obj("r1_cabinet", "值班柜", "container", "值班柜已打开。" if opened else "带数字锁的值班柜，门上贴着形状标签。", not opened),
            obj("r1_door", "设备间刷卡门", "door", "刷卡门已解锁。" if state.flags["r2_unlocked"] else "通向设备间的刷卡门。"),
        ]
        if opened and "access_card" not in state.inventory:
            objects.append(obj("access_card", "门卡", "item", "柜内有一张门卡。", item_id="access_card"))
        return objects
    if state.room_id == "R2":
        opened = "r2_drawer" in state.opened_containers
        objects = []
        if "fuse" not in state.inventory and not state.flags["power_on"]:
            objects.append(obj("r2_fuse", "备用保险丝", "item", "桌上放着备用保险丝。", item_id="fuse"))
        objects.extend([
            obj("r2_powerbox", "电源箱", "device", "电源已恢复。" if state.flags["power_on"] else "电源箱有空置保险丝槽。"),
            obj("r2_monitor", "屏幕", "clue", "电源箱旁有一块屏幕。"),
            obj("r2_drawer", "抽屉", "container", "抽屉已打开。" if opened else "带数字锁的抽屉上有颜色标签。", not opened),
            obj("r2_door", "出口控制室钥匙门", "door", "门已解锁。" if state.flags["r3_unlocked"] else "通向出口控制室的钥匙门。"),
        ])
        if opened and "emergency_key" not in state.inventory and not state.flags["r3_unlocked"]:
            objects.append(obj("emergency_key", "应急钥匙", "item", "抽屉内有一把应急钥匙。", item_id="emergency_key"))
        return objects
    if state.room_id == "R3":
        return [
            obj("r3_checklist", "出口检查单", "clue", "出口旁贴着一张检查单。"),
            obj("r3_panel", "检查面板", "device", "检查面板上有设备标签和数字键。", not state.flags["check_done"]),
            obj("exit_door", "实验室出口", "door", "出口检查已完成。" if state.flags["check_done"] else "实验室出口等待检查完成。"),
        ]
    return []


def visible_state(session_id: str, state: GameState, save=None) -> dict:
    exits = []
    if state.room_id == "R1":
        exits = [("R2", state.flags["r2_unlocked"])]
    elif state.room_id == "R2":
        exits = [("R1", True), ("R3", state.flags["r3_unlocked"])]
    elif state.room_id == "R3":
        exits = [("R2", True), ("EXIT", state.flags["power_on"] and state.flags["check_done"])]
    objects = visible_objects(state)
    object_ids = {obj["object_id"] for obj in objects}
    inventory = []
    for item_id in state.inventory:
        item = deepcopy(ITEMS[item_id])
        item["usable_targets"] = [target for (required, target), flag in PAIRS.items() if required == item_id and target in object_ids and not state.flags[flag]]
        inventory.append(item)
    name, description = ROOMS[state.room_id]
    return {"schema_version": SCHEMA_VERSION, "level_version": LEVEL_VERSION,
            "session_id": session_id, "revision": state.revision, "generation": state.generation,
            "status": state.status, "room": {"room_id": state.room_id, "name": name, "description": description},
            "objects": objects, "inventory": inventory,
            "clues": [deepcopy(CLUES[clue_id]) for clue_id in state.discovered_clue_ids],
            "exits": [{"destination_id": destination, "name": ROOMS[destination][0], "unlocked": unlocked} for destination, unlocked in exits],
            "progress": {"power_on": state.flags["power_on"], "check_done": state.flags["check_done"]}, "save": save}


def validate_invariants(state: GameState) -> None:
    flags = state.flags
    if set(flags) != {"r2_unlocked", "power_on", "r3_unlocked", "check_done"} or any(type(value) is not bool for value in flags.values()):
        raise ValueError("Invalid flags")
    for values, allowed in ((state.inventory, set(ITEMS)), (state.discovered_clue_ids, set(CLUES)), (state.opened_containers, {"r1_cabinet", "r2_drawer"})):
        if len(values) != len(set(values)) or not set(values) <= allowed:
            raise ValueError("Invalid state identifiers")
    if "access_card" in state.inventory and "r1_cabinet" not in state.opened_containers:
        raise ValueError("Card requires open cabinet")
    if "emergency_key" in state.inventory and "r2_drawer" not in state.opened_containers:
        raise ValueError("Key requires open drawer")
    if state.room_id != "R1" and not flags["r2_unlocked"]:
        raise ValueError("Room requires unlock")
    if state.room_id in {"R3", "EXIT"} and not flags["r3_unlocked"]:
        raise ValueError("Room requires second unlock")
    if flags["r3_unlocked"] and (not flags["power_on"] or "r2_drawer" not in state.opened_containers or "emergency_key" in state.inventory):
        raise ValueError("Unlocked door requires power, open drawer and consumed key")
    if flags["r2_unlocked"] and "access_card" not in state.inventory:
        raise ValueError("Baseline door requires retained card")
    if (flags["power_on"] or "fuse" in state.inventory or any(clue.startswith("r2_") for clue in state.discovered_clue_ids)) and not flags["r2_unlocked"]:
        raise ValueError("Equipment progress requires first unlock")
    if (flags["check_done"] or any(clue.startswith("r3_") for clue in state.discovered_clue_ids)) and not flags["r3_unlocked"]:
        raise ValueError("Exit progress requires second unlock")
    if flags["power_on"] and "fuse" in state.inventory:
        raise ValueError("Installed fuse cannot be held")
    if (flags["check_done"] or "r2_drawer" in state.opened_containers or "r2_monitor_clue" in state.discovered_clue_ids) and not flags["power_on"]:
        raise ValueError("Operation requires power")
    is_won = state.room_id == "EXIT" and flags["power_on"] and flags["check_done"]
    if (state.status == "won") != is_won or (state.room_id == "EXIT" and not is_won):
        raise ValueError("Invalid finished state")


def apply_action(original: GameState, tool: str, arguments: dict) -> tuple[GameState, dict]:
    state = original.model_copy(deep=True)
    before = state.model_dump()
    observed, new_clues, consumed = None, [], []
    message = "操作完成。"
    objects = {obj["object_id"] for obj in visible_objects(state)}
    if state.status == "won" and tool not in {"inspect", "get_inventory"}:
        raise RuleError("GAME_FINISHED", "游戏已通关，请重新开始。")
    if tool == "inspect":
        object_id = arguments["object_id"]
        if object_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法查看该对象。")
        clue_id = next((key for key, clue in CLUES.items() if clue["object_id"] == object_id), None)
        if object_id == "r2_monitor" and not state.flags["power_on"]:
            clue_id, observed = None, "当前无显示"
        if clue_id:
            observed = CLUES[clue_id]["text"]
            if clue_id not in state.discovered_clue_ids:
                state.discovered_clue_ids.append(clue_id)
                new_clues.append(clue_id)
            container_item = {"r1_cabinet": "access_card", "r2_drawer": "emergency_key"}.get(object_id)
            if container_item and object_id in state.opened_containers:
                if container_item == "emergency_key" and state.flags["r3_unlocked"]:
                    contents = "应急钥匙已使用。"
                else:
                    contents = "道具已领取。" if container_item in state.inventory else "内有" + ITEMS[container_item]["name"] + "。"
                observed += " 容器已打开。" + contents
        elif observed is None:
            observed = {
                "r1_door": "刷卡门已解锁" if state.flags["r2_unlocked"] else "门侧有一条磨损的读卡槽，门锁没有松动。",
                "r2_door": "门已解锁" if state.flags["r3_unlocked"] else "门把手下有一个窄锁孔，转动把手时门仍紧闭。",
                "r2_powerbox": "电源已恢复" if state.flags["power_on"] else "箱内两枚金属触点之间空着，指示灯没有亮。",
                "exit_door": "出口检查已完成" if state.flags["check_done"] else "出口门紧闭，旁边的状态灯仍亮着。",
                **{object_id: ITEMS[item_id]["description"] for item_id, object_id in ITEM_OBJECTS.items()},
            }[object_id]
        message = "已查看。"
    elif tool == "get_inventory":
        observed = "背包：" + ("、".join(ITEMS[item]["name"] for item in state.inventory) or "空")
        message = "已读取背包。"
    elif tool == "take":
        item_id = arguments["item_id"]
        if item_id in state.inventory or (item_id == "fuse" and state.flags["power_on"]) or (item_id == "emergency_key" and state.flags["r3_unlocked"]):
            raise RuleError("ALREADY_TAKEN", "该道具已领取。")
        if ITEM_OBJECTS.get(item_id) not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法拾取该道具。")
        state.inventory.append(item_id)
        message = "已拾取" + ITEMS[item_id]["name"] + "。"
    elif tool == "use_item":
        item_id, target_id = arguments["item_id"], arguments["target_id"]
        if target_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该目标。")
        flag = PAIRS.get((item_id, target_id))
        if flag is None:
            feedback = {
                "r1_door": "门侧的装置没有反应，物品与槽口似乎不相合。",
                "r2_door": "物品无法与锁孔嵌合，门锁没有松动。",
                "r2_powerbox": "物品与箱内触点无法接合，指示灯没有亮。",
                "r1_cabinet": "物品碰到柜门，锁上的数字没有变化。",
                "r2_drawer": "抽屉仍停在原处，物品没有使锁产生反应。",
                "r3_panel": "面板没有响应，显示仍与刚才相同。",
                "exit_door": "出口装置没有响应，门仍保持原来的状态。",
            }.get(target_id, "物品轻触表面，没有出现任何变化。")
            raise RuleError("PRECONDITION_FAILED", feedback)
        if not state.flags[flag]:
            if item_id not in state.inventory or (target_id == "r2_door" and not state.flags["power_on"]):
                raise RuleError("PRECONDITION_FAILED", "需要先取得相应道具并满足设备条件。")
            state.flags[flag] = True
            if item_id in {"fuse", "emergency_key"}:
                state.inventory.remove(item_id)
                consumed.append(item_id)
        message = {"r1_door": "设备间刷卡门已解锁。", "r2_powerbox": "电源已恢复。", "r2_door": "出口控制室门已解锁。"}[target_id]
        if "emergency_key" in consumed:
            message += "应急钥匙已消耗。"
    elif tool == "submit_code":
        target_id = arguments["target_id"]
        if target_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该目标。")
        if target_id not in CODES:
            raise RuleError("PRECONDITION_FAILED", "该目标不接受密码。")
        if target_id != "r1_cabinet" and not state.flags["power_on"]:
            raise RuleError("PRECONDITION_FAILED", "需要先恢复供电。")
        if arguments["code"] != CODES[target_id]:
            raise RuleError("WRONG_CODE", "密码不正确，请重新核对已发现线索。")
        if target_id == "r3_panel":
            state.flags["check_done"] = True
        elif target_id not in state.opened_containers:
            state.opened_containers.append(target_id)
        message = {"r1_cabinet": "值班柜已打开。", "r2_drawer": "抽屉已打开。", "r3_panel": "出口检查已完成。"}[target_id]
    elif tool == "move":
        destination = arguments["destination_id"]
        exits = {exit_["destination_id"]: exit_["unlocked"] for exit_ in visible_state("", state)["exits"]}
        if destination not in exits or not exits[destination]:
            raise RuleError("PRECONDITION_FAILED", "当前无法前往该房间，请先解锁或完成出口检查。")
        state.room_id = destination
        if destination == "EXIT":
            state.status = "won"
        message = "已进入" + ROOMS[destination][0] + "。"
    else:
        raise RuleError("INVALID_TOOL", "工具不在允许列表中。")
    changed = state.model_dump() != before
    if changed:
        state.revision += 1
    validate_invariants(state)
    return state, {"changed": changed, "message": message, "observation": observed, "new_clue_ids": new_clues, "consumed_item_ids": consumed}

