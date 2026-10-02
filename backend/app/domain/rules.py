"""M1 trusted rules. Secret values stay exclusively in this server module."""
from copy import deepcopy

from .models import GameState, RuleError

SCHEMA_VERSION = LEVEL_VERSION = "1.0.0"
CLUES = {
    "r1_note_clue": {"clue_id": "r1_note_clue", "object_id": "r1_note", "title": "值班便签", "text": "三角记为3，圆记为8，方记为2。"},
    "r1_cabinet_clue": {"clue_id": "r1_cabinet_clue", "object_id": "r1_cabinet", "title": "柜门顺序", "text": "柜门标签从左到右是：三角、圆、方。"},
}
ITEMS = {"access_card": {"item_id": "access_card", "name": "门卡", "description": "设备间门卡"}}


def action(tool: str, label: str, **arguments) -> dict:
    return {"tool": tool, "label": label, "arguments": arguments, "requires_code": tool == "submit_code"}


def visible_objects(state: GameState) -> list[dict]:
    if state.room_id != "R1":
        return []
    opened = "r1_cabinet" in state.opened_containers
    objects = [
        {"object_id": "r1_note", "name": "值班便签", "kind": "clue", "description": "桌上有一张值班便签。", "actions": [action("inspect", "查看", object_id="r1_note")]},
        {"object_id": "r1_cabinet", "name": "值班柜", "kind": "container", "description": "值班柜已打开。" if opened else "带数字锁的值班柜，门上贴着形状标签。", "actions": [action("inspect", "查看", object_id="r1_cabinet")] + ([] if opened else [action("submit_code", "输入密码", target_id="r1_cabinet")])},
        {"object_id": "r1_door", "name": "设备间刷卡门", "kind": "door", "description": "刷卡门已解锁。" if state.flags["r2_unlocked"] else "通向设备间的刷卡门。", "actions": [action("inspect", "查看", object_id="r1_door")]},
    ]
    if opened and "access_card" not in state.inventory:
        objects.append({"object_id": "access_card", "name": "门卡", "kind": "item", "description": "柜内有一张门卡。", "actions": [action("inspect", "查看", object_id="access_card"), action("take", "拾取", item_id="access_card")]})
    return objects


def visible_state(session_id: str, state: GameState, save=None) -> dict:
    rooms = {
        "R1": ("值班室", "夜间断电了，先寻找通往设备间的门卡。"),
        "R2": ("设备间", "已完成值班室原型。设备间玩法将在下一阶段开放；可以返回值班室。"),
        "R3": ("出口控制室", "出口控制室。"), "EXIT": ("实验室出口", "已离开实验室。"),
    }
    exits = []
    if state.room_id == "R1":
        exits = [{"destination_id": "R2", "name": "设备间", "unlocked": state.flags["r2_unlocked"]}]
    elif state.room_id == "R2":
        exits = [{"destination_id": "R1", "name": "值班室", "unlocked": True}]
    inventory = []
    for item_id in state.inventory:
        item = deepcopy(ITEMS[item_id])
        item["usable_targets"] = ["r1_door"] if state.room_id == "R1" and not state.flags["r2_unlocked"] else []
        inventory.append(item)
    name, description = rooms[state.room_id]
    return {"schema_version": SCHEMA_VERSION, "level_version": LEVEL_VERSION,
            "session_id": session_id, "revision": state.revision, "generation": state.generation,
            "status": state.status, "room": {"room_id": state.room_id, "name": name, "description": description},
            "objects": visible_objects(state), "inventory": inventory,
            "clues": [deepcopy(CLUES[clue_id]) for clue_id in state.discovered_clue_ids],
            "exits": exits, "progress": {"power_on": state.flags["power_on"], "check_done": state.flags["check_done"]}, "save": save}


def validate_invariants(state: GameState) -> None:
    if set(state.flags) != {"r2_unlocked", "power_on", "r3_unlocked", "check_done"}:
        raise ValueError("Invalid flags")
    for values, allowed in ((state.inventory, set(ITEMS)), (state.discovered_clue_ids, set(CLUES)), (state.opened_containers, {"r1_cabinet"})):
        if len(values) != len(set(values)) or not set(values) <= allowed:
            raise ValueError("Invalid state identifiers")
    if "access_card" in state.inventory and "r1_cabinet" not in state.opened_containers:
        raise ValueError("Card requires open cabinet")
    if state.room_id != "R1" and not state.flags["r2_unlocked"]:
        raise ValueError("Room requires unlock")
    if state.room_id not in {"R1", "R2"} or state.status != "playing" or any(state.flags[k] for k in ("power_on", "r3_unlocked", "check_done")):
        raise ValueError("M1 room boundary")


def apply_action(original: GameState, tool: str, arguments: dict) -> tuple[GameState, dict]:
    state = original.model_copy(deep=True)
    before = state.model_dump()
    observed = None
    new_clues = []
    message = "操作完成。"
    objects = {obj["object_id"] for obj in visible_objects(state)}
    if state.status == "won" and tool not in {"inspect", "get_inventory"}:
        raise RuleError("GAME_FINISHED", "游戏已通关，请重新开始。")
    if tool == "inspect":
        object_id = arguments["object_id"]
        if object_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法查看该对象。")
        clue_id = {"r1_note": "r1_note_clue", "r1_cabinet": "r1_cabinet_clue"}.get(object_id)
        if clue_id:
            observed = CLUES[clue_id]["text"]
            if clue_id not in state.discovered_clue_ids:
                state.discovered_clue_ids.append(clue_id)
                new_clues.append(clue_id)
            if object_id == "r1_cabinet" and "r1_cabinet" in state.opened_containers:
                observed += " 柜子已打开。" + ("柜内有门卡。" if "access_card" not in state.inventory else "门卡已领取。")
        else:
            observed = "设备间门卡" if object_id == "access_card" else ("刷卡门已解锁" if state.flags["r2_unlocked"] else "需要门卡解锁；刷卡门")
        message = "已查看。"
    elif tool == "get_inventory":
        observed = "背包：" + ("、".join(ITEMS[item]["name"] for item in state.inventory) or "空")
        message = "已读取背包。"
    elif tool == "take":
        item_id = arguments["item_id"]
        if item_id in state.inventory:
            raise RuleError("ALREADY_TAKEN", "该道具已领取。")
        if item_id != "access_card" or item_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法拾取该道具。")
        state.inventory.append(item_id)
        message = "已拾取门卡。"
    elif tool == "use_item":
        item_id, target_id = arguments["item_id"], arguments["target_id"]
        if target_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该目标。")
        if (item_id, target_id) != ("access_card", "r1_door"):
            raise RuleError("PRECONDITION_FAILED", "该道具不能用于此目标。")
        if not state.flags["r2_unlocked"] and item_id not in state.inventory:
            raise RuleError("PRECONDITION_FAILED", "需要先取得门卡。")
        state.flags["r2_unlocked"] = True
        message = "设备间刷卡门已解锁。"
    elif tool == "submit_code":
        target_id = arguments["target_id"]
        if target_id not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该目标。")
        if target_id != "r1_cabinet":
            raise RuleError("PRECONDITION_FAILED", "该目标不接受密码。")
        if arguments["code"] != "382":
            raise RuleError("WRONG_CODE", "密码不正确，请重新核对已发现线索。")
        if target_id not in state.opened_containers:
            state.opened_containers.append(target_id)
        message = "值班柜已打开。"
    elif tool == "move":
        destination = arguments["destination_id"]
        if (state.room_id, destination) not in {("R1", "R2"), ("R2", "R1")}:
            raise RuleError("PRECONDITION_FAILED", "当前无法前往该房间。")
        if not state.flags["r2_unlocked"]:
            raise RuleError("PRECONDITION_FAILED", "房门尚未解锁。")
        state.room_id = destination
        message = "已进入设备间。" if destination == "R2" else "已返回值班室。"
    else:
        raise RuleError("INVALID_TOOL", "工具不在允许列表中。")
    changed = state.model_dump() != before
    if changed:
        state.revision += 1
    validate_invariants(state)
    return state, {"changed": changed, "message": message, "observation": observed, "new_clue_ids": new_clues, "consumed_item_ids": []}
