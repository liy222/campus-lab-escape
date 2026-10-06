"""Versioned device rules sharing the existing Store, receipts and AI boundary."""
from copy import deepcopy

from . import rules as legacy
from .models import RuleError
from .upgrade_models import DeviceStates, TOOL_MODELS_UPGRADE, UpgradeState

SCHEMA_VERSION = "1.1.0"
LEVEL_VERSION = "3.1.0"
state_model = UpgradeState
tool_models = TOOL_MODELS_UPGRADE
game_fields = set(UpgradeState.model_fields) - {"revision", "generation"}
DEVICE_IDS = {"r1_cabinet": "cabinet", "r2_powerbox": "powerbox", "r2_monitor": "computer", "exit_door": "exit"}
OBJECT_IDS = {"r1_note", "r1_cabinet", "r1_door", "access_card", "r2_fuse", "r2_powerbox", "r2_monitor", "r2_drawer", "r2_door", "emergency_key", "r3_checklist", "r3_panel", "exit_door"}
CLUES = deepcopy(legacy.CLUES)
for object_id in OBJECT_IDS:
    CLUES[object_id + "_observation"] = {"clue_id": object_id + "_observation", "object_id": object_id, "title": "现场观察", "text": ""}
# Login information is visible on the powered login screen, before authentication.
CLUES["r2_monitor_clue"]["text"] += " 登录数字键旁的标签是：青、橙、紫。"
DESCRIPTIONS = {
    "cabinet": {"LOCKED": "柜门紧闭，数字锁下贴着几何标签。", "CODE_ACCEPTED": "绿灯亮起，门闩发出一声轻响，柜门仍合着。", "OPEN": "柜门敞开，内侧放着一张磨损的卡片。", "ITEM_TAKEN": "柜门敞开，卡片原来所在的位置已空。"},
    "powerbox": {"CLOSED": "金属箱盖紧闭，外侧有一个搭扣。", "OPEN": "箱盖已打开，里面的触点被一块小护板挡着。", "MISSING_FUSE": "护板已移开，两枚触点之间的窄槽空着。", "FUSE_INSTALLED": "玻璃管已经卡在触点之间，总闸仍抬着。", "CIRCUIT_READY": "连接指示窗亮起绿标，总闸仍抬着。", "POWER_ON": "总闸已合上，设备的电源灯亮着。"},
    "computer": {"OFF": "显示器漆黑，机身上有一个启动按钮。", "BOOTING": "启动灯闪烁，屏幕显示启动进度，等待确认继续。", "LOGIN_LOCKED": "屏幕亮起登录数字键与几枚颜色标记。", "UNLOCKED": "登录已通过，屏幕上出现一份待读取的研究记录。", "DATA_READ": "研究记录已经打开，桌下抽屉的电子锁恢复响应。"},
    "exit": {"LOCKED": "出口门紧闭，旁边有一道读卡槽和暗着的状态灯。", "CARD_ACCEPTED": "读卡灯已亮，终检开关等待启动。", "FINAL_CHECK": "终检灯亮起，出口仍锁着。", "UNLOCKED": "出口锁舌已经收回，门仍合着。", "OPEN": "出口门已经打开，外面的走廊映入眼前。"},
}


def initial_state(revision=0):
    return UpgradeState(level_version=LEVEL_VERSION, revision=revision,
                        device_states=DeviceStates(cabinet="LOCKED", powerbox="CLOSED", computer="OFF", exit="LOCKED"),
                        observed_object_ids=[], taken_item_ids=[], consumed_item_ids=[])


def affordance(tool, label, **arguments):
    return {"tool": tool, "label": label, "arguments": arguments, "requires_code": tool == "submit_code"}


def visible_objects(state):
    d = state.device_states
    entries = []
    if state.room_id == "R1":
        entries = [("r1_note", "值班便签", "clue", "桌上有一张值班便签。"), ("r1_cabinet", "值班柜", "container", DESCRIPTIONS["cabinet"][d.cabinet]), ("r1_door", "设备间门", "door", "门侧有读卡槽。" if not state.flags["r2_unlocked"] else "门已解锁。")]
        if d.cabinet == "OPEN":
            entries.append(("access_card", "门卡", "item", "柜内有一张磨损的卡片。"))
    elif state.room_id == "R2":
        entries = [("r2_powerbox", "电源箱", "device", DESCRIPTIONS["powerbox"][d.powerbox]), ("r2_monitor", "电脑", "device", DESCRIPTIONS["computer"][d.computer]), ("r2_drawer", "抽屉", "container", "抽屉已打开。" if "r2_drawer" in state.opened_containers else "抽屉的数字键旁有颜色标签。"), ("r2_door", "控制室门", "door", "门已解锁。" if state.flags["r3_unlocked"] else "门把手下有一个窄锁孔。")]
        if "fuse" not in state.taken_item_ids:
            entries.insert(0, ("r2_fuse", "备用保险丝", "item", "桌上放着一个细长玻璃管。"))
        if "r2_drawer" in state.opened_containers and "emergency_key" not in state.taken_item_ids:
            entries.append(("emergency_key", "应急钥匙", "item", "抽屉内有一把黄铜钥匙。"))
    elif state.room_id == "R3":
        entries = [("r3_checklist", "出口检查单", "clue", "出口旁贴着一张检查单。"), ("r3_panel", "检查面板", "device", "检查完成，确认灯亮着。" if state.flags["check_done"] else "面板上有设备标签和数字键。"), ("exit_door", "实验室出口", "door", DESCRIPTIONS["exit"][d.exit])]
    objects = []
    for object_id, name, kind, description in entries:
        actions = [affordance("inspect", "观察", object_id=object_id)]
        if object_id in state.observed_object_ids and state.status == "playing":
            if kind == "item":
                item_id = next(item for item, obj in legacy.ITEM_OBJECTS.items() if obj == object_id)
                actions.append(affordance("take", "拿起物品", item_id=item_id))
            elif object_id == "r1_cabinet":
                if d.cabinet == "LOCKED":
                    actions.append(affordance("submit_code", "操作数字锁", target_id=object_id))
                elif d.cabinet == "CODE_ACCEPTED":
                    actions.append(affordance("interact", "拉开柜门", target_id=object_id))
            elif object_id == "r2_powerbox" and d.powerbox != "POWER_ON":
                labels = {"CLOSED": "打开箱盖", "OPEN": "移开护板", "FUSE_INSTALLED": "检查接合", "CIRCUIT_READY": "合上总闸"}
                if d.powerbox in labels:
                    actions.append(affordance("interact", labels[d.powerbox], target_id=object_id))
            elif object_id == "r2_monitor":
                if d.computer == "LOGIN_LOCKED":
                    actions.append(affordance("submit_code", "登录终端", target_id=object_id))
                elif state.flags["power_on"] and d.computer in {"OFF", "BOOTING", "UNLOCKED"}:
                    actions.append(affordance("interact", {"OFF": "按下启动键", "BOOTING": "继续启动", "UNLOCKED": "读取记录"}[d.computer], target_id=object_id))
            elif object_id == "r2_drawer" and d.computer == "DATA_READ" and "r2_drawer" not in state.opened_containers:
                actions.append(affordance("submit_code", "操作数字锁", target_id=object_id))
            elif object_id == "r3_panel" and d.exit == "FINAL_CHECK" and not state.flags["check_done"]:
                actions.append(affordance("submit_code", "操作检查面板", target_id=object_id))
            elif object_id == "exit_door":
                labels = {"CARD_ACCEPTED": "启动终检", "FINAL_CHECK": "释放门锁", "UNLOCKED": "推开出口"}
                if d.exit in labels and (d.exit != "FINAL_CHECK" or state.flags["check_done"]):
                    actions.append(affordance("interact", labels[d.exit], target_id=object_id))
        objects.append({"object_id": object_id, "name": name, "kind": kind, "description": description, "actions": actions})
    return objects


def visible_state(session_id, state, save=None):
    exits = {"R1": [("R2", state.flags["r2_unlocked"])], "R2": [("R1", True), ("R3", state.flags["r3_unlocked"])], "R3": [("R2", True), ("EXIT", state.device_states.exit == "OPEN")], "EXIT": []}[state.room_id]
    return {"schema_version": SCHEMA_VERSION, "level_version": LEVEL_VERSION, "session_id": session_id, "revision": state.revision, "generation": state.generation, "status": state.status, "room": {"room_id": state.room_id, "name": legacy.ROOMS[state.room_id][0], "description": legacy.ROOMS[state.room_id][1]}, "objects": visible_objects(state), "inventory": [{**deepcopy(legacy.ITEMS[item]), "usable_targets": []} for item in state.inventory], "clues": [deepcopy(CLUES[clue]) if not clue.endswith("_observation") else {**deepcopy(CLUES[clue]), "text": observation_text(clue.removesuffix("_observation"), state, historical=True)} for clue in state.discovered_clue_ids], "exits": [{"destination_id": dest, "name": legacy.ROOMS[dest][0], "unlocked": unlocked} for dest, unlocked in exits], "progress": {"power_on": state.flags["power_on"], "check_done": state.flags["check_done"]}, "save": save, "device_states": state.device_states.model_dump(), "observed_object_ids": list(state.observed_object_ids)}


def observation_text(object_id, state, historical=False):
    # Notebook observations retain neutral exterior facts, not future device states.
    neutral = {"r1_door": "门侧有一道磨损的读卡槽。", "r2_door": "门把手下有一个窄锁孔。", "exit_door": "出口门旁有一道读卡槽和终检装置。", "r2_monitor": "机身上有启动按钮，显示器旁有颜色标记。", "r2_powerbox": "箱盖带搭扣，里面有金属触点和总闸。"}
    if object_id in DEVICE_IDS and not historical:
        return DESCRIPTIONS[DEVICE_IDS[object_id]][getattr(state.device_states, DEVICE_IDS[object_id])]
    if object_id in neutral:
        return neutral[object_id]
    item = next((item for item, obj in legacy.ITEM_OBJECTS.items() if obj == object_id), None)
    return legacy.ITEMS[item]["description"] if item else "已观察到这里的外观。"


def validate_invariants(state):
    d, flags = state.device_states, state.flags
    if state.level_version != LEVEL_VERSION or set(flags) != {"r2_unlocked", "power_on", "r3_unlocked", "check_done"} or any(type(v) is not bool for v in flags.values()):
        raise ValueError("Invalid level or flags")
    allowed_lists = [(state.inventory, set(legacy.ITEMS)), (state.taken_item_ids, set(legacy.ITEMS)), (state.consumed_item_ids, {"fuse", "emergency_key"}), (state.discovered_clue_ids, set(CLUES)), (state.observed_object_ids, OBJECT_IDS), (state.opened_containers, {"r1_cabinet", "r2_drawer"})]
    if any(len(values) != len(set(values)) or not set(values) <= allowed for values, allowed in allowed_lists):
        raise ValueError("Invalid identifiers")
    if set(state.inventory) != set(state.taken_item_ids) - set(state.consumed_item_ids) or not set(state.consumed_item_ids) <= set(state.taken_item_ids):
        raise ValueError("Invalid item lifecycle")
    if any(CLUES[clue]["object_id"] not in state.observed_object_ids for clue in state.discovered_clue_ids):
        raise ValueError("Clue requires observation")
    if set(state.observed_object_ids) != {CLUES[clue]["object_id"] for clue in state.discovered_clue_ids}:
        raise ValueError("Observation requires notebook record")
    for clue_id, clue in legacy.CLUES.items():
        # The monitor can first be observed before its powered clue is available.
        # Other clue-bearing objects always register their canonical clue.
        if clue["object_id"] != "r2_monitor" and clue["object_id"] in state.observed_object_ids and clue_id not in state.discovered_clue_ids:
            raise ValueError("Observed clue object requires its clue record")
    for flag, target in (("r2_unlocked", "r1_door"), ("r3_unlocked", "r2_door"), ("check_done", "r3_panel")):
        if flags[flag] and target not in state.observed_object_ids:
            raise ValueError("Committed progress requires target observation")
    for object_id, field in DEVICE_IDS.items():
        initial = {"cabinet": "LOCKED", "powerbox": "CLOSED", "computer": "OFF", "exit": "LOCKED"}[field]
        if getattr(d, field) != initial and object_id not in state.observed_object_ids:
            raise ValueError("Device progression requires observation")
    if any(legacy.ITEM_OBJECTS[item] not in state.observed_object_ids for item in state.taken_item_ids):
        raise ValueError("Taking requires observation")
    if "access_card" in state.observed_object_ids and d.cabinet not in {"OPEN", "ITEM_TAKEN"}:
        raise ValueError("Card observation requires open cabinet")
    if "emergency_key" in state.observed_object_ids and "r2_drawer" not in state.opened_containers:
        raise ValueError("Key observation requires open drawer")
    if "r2_drawer" in state.opened_containers and "r2_drawer" not in state.observed_object_ids:
        raise ValueError("Drawer opening requires observation")
    if (d.cabinet in {"OPEN", "ITEM_TAKEN"}) != ("r1_cabinet" in state.opened_containers) or (d.cabinet == "ITEM_TAKEN") != ("access_card" in state.taken_item_ids):
        raise ValueError("Invalid cabinet lifecycle")
    if flags["r2_unlocked"] and "access_card" not in state.inventory:
        raise ValueError("First door requires retained card")
    if state.room_id != "R1" and not flags["r2_unlocked"]:
        raise ValueError("Room requires first door")
    equipment = d.powerbox != "CLOSED" or d.computer != "OFF" or "fuse" in state.taken_item_ids or any(obj.startswith("r2_") or obj == "emergency_key" for obj in state.observed_object_ids)
    if equipment and not flags["r2_unlocked"]:
        raise ValueError("Equipment requires first door")
    if (d.powerbox in {"FUSE_INSTALLED", "CIRCUIT_READY", "POWER_ON"}) != ("fuse" in state.consumed_item_ids) or flags["power_on"] != (d.powerbox == "POWER_ON"):
        raise ValueError("Invalid electrical state")
    if d.computer != "OFF" and not flags["power_on"]:
        raise ValueError("Computer requires power")
    if "r2_monitor_clue" in state.discovered_clue_ids and d.computer in {"OFF", "BOOTING"}:
        raise ValueError("Login clue requires booted screen")
    if ("r2_drawer" in state.opened_containers or "emergency_key" in state.taken_item_ids or flags["r3_unlocked"]) and d.computer != "DATA_READ":
        raise ValueError("Drawer requires data read")
    if "emergency_key" in state.taken_item_ids and "r2_drawer" not in state.opened_containers:
        raise ValueError("Key requires open drawer")
    if flags["r3_unlocked"] != ("emergency_key" in state.consumed_item_ids):
        raise ValueError("Invalid second door lifecycle")
    if (state.room_id in {"R3", "EXIT"} or d.exit != "LOCKED" or flags["check_done"] or any(obj.startswith("r3_") or obj == "exit_door" for obj in state.observed_object_ids)) and not flags["r3_unlocked"]:
        raise ValueError("Exit progress requires second door")
    if d.exit != "LOCKED" and "access_card" not in state.inventory:
        raise ValueError("Exit requires retained card")
    if flags["check_done"] and d.exit not in {"FINAL_CHECK", "UNLOCKED", "OPEN"} or d.exit in {"UNLOCKED", "OPEN"} and not flags["check_done"]:
        raise ValueError("Invalid final check")
    if (state.status == "won") != (state.room_id == "EXIT") or state.room_id == "EXIT" and d.exit != "OPEN":
        raise ValueError("Invalid finish")


def apply_action(original, tool, arguments):
    state = original.model_copy(deep=True)
    before = state.model_dump()
    observation, new_clues, consumed = None, [], []
    objects = {obj["object_id"]: obj for obj in visible_objects(state)}
    d = state.device_states
    if state.status == "won" and tool not in {"inspect", "get_inventory"}:
        raise RuleError("GAME_FINISHED", "游戏已通关，请重新开始。")

    def require(condition, message="当前装置没有响应，请观察它的状态。"):
        if not condition:
            raise RuleError("PRECONDITION_FAILED", message)

    def visible(target):
        if target not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该对象。")

    def observed(target):
        visible(target)
        require(target in state.observed_object_ids, "还没有仔细观察这件装置。")

    message = "操作完成。"
    if tool == "inspect":
        target = arguments["object_id"]
        visible(target)
        clue_id = next((cid for cid, clue in legacy.CLUES.items() if clue["object_id"] == target), None)
        if target == "r2_monitor" and d.computer in {"OFF", "BOOTING"}:
            clue_id = None
        if clue_id:
            observation = CLUES[clue_id]["text"]
            if target in DEVICE_IDS:
                observation += " " + observation_text(target, state)
            if target == "r2_drawer" and "r2_drawer" in state.opened_containers:
                observation += " 抽屉已开。" + ("钥匙已使用。" if "emergency_key" in state.consumed_item_ids else "物品已领取。" if "emergency_key" in state.taken_item_ids else "内有一把黄铜钥匙。")
        else:
            clue_id = target + "_observation"
            observation = observation_text(target, state)
        if target not in state.observed_object_ids:
            state.observed_object_ids.append(target)
        if clue_id not in state.discovered_clue_ids:
            state.discovered_clue_ids.append(clue_id)
            new_clues.append(clue_id)
        message = "已观察。"
    elif tool == "get_inventory":
        observation = "背包：" + ("、".join(legacy.ITEMS[item]["name"] for item in state.inventory) or "空")
        message = "已读取背包。"
    elif tool == "take":
        item = arguments["item_id"]
        if item in state.taken_item_ids:
            raise RuleError("ALREADY_TAKEN", "该物品已领取。")
        target = legacy.ITEM_OBJECTS.get(item)
        observed(target)
        state.inventory.append(item)
        state.taken_item_ids.append(item)
        if item == "access_card":
            d.cabinet = "ITEM_TAKEN"
        message = "已拿起" + legacy.ITEMS[item]["name"] + "。"
    elif tool == "use_item":
        item, target = arguments["item_id"], arguments["target_id"]
        observed(target)
        require(item in state.inventory, "手中没有这件物品。")
        if (item, target) == ("access_card", "r1_door"):
            state.flags["r2_unlocked"] = True
            message = "读卡灯亮起，设备间门已解锁。"
        elif (item, target) == ("fuse", "r2_powerbox"):
            require(d.powerbox == "MISSING_FUSE", "箱内的触点还无法接合。")
            d.powerbox = "FUSE_INSTALLED"
            consumed.append(item)
            message = "玻璃管已卡入触点之间，总闸仍抬着。"
        elif (item, target) == ("emergency_key", "r2_door"):
            require(d.computer == "DATA_READ")
            state.flags["r3_unlocked"] = True
            consumed.append(item)
            message = "控制室门已解锁，应急钥匙已消耗。"
        elif (item, target) == ("access_card", "exit_door"):
            if d.exit == "LOCKED":
                d.exit = "CARD_ACCEPTED"
            message = "读卡装置已经响应，出口门仍保持当前状态。"
        else:
            raise RuleError("PRECONDITION_FAILED", "物品与装置无法接合，没有出现变化。")
        for item in consumed:
            state.inventory.remove(item)
            state.consumed_item_ids.append(item)
    elif tool == "submit_code":
        target = arguments["target_id"]
        observed(target)
        require(target in {"r1_cabinet", "r2_monitor", "r2_drawer", "r3_panel"}, "这里没有可操作的数字键。")
        if target == "r2_monitor":
            require(d.computer == "LOGIN_LOCKED", "终端当前没有等待登录。")
        elif target == "r2_drawer":
            require(d.computer == "DATA_READ", "抽屉数字键尚未响应。")
        elif target == "r3_panel":
            require(d.exit == "FINAL_CHECK", "检查面板尚未进入终检。")
        expected = legacy.CODES.get(target) if target != "r2_monitor" else legacy.CODES["r2_drawer"]
        if arguments["code"] != expected:
            raise RuleError("WRONG_CODE", "装置没有接受这组数字，请核对已发现的线索。")
        if target == "r1_cabinet":
            if d.cabinet == "LOCKED":
                d.cabinet = "CODE_ACCEPTED"
            message = "数字锁已接受输入，柜门仍保持当前状态。"
        elif target == "r2_monitor":
            d.computer = "UNLOCKED"
            message = "终端登录已通过，研究记录等待读取。"
        elif target == "r2_drawer":
            if target not in state.opened_containers:
                state.opened_containers.append(target)
            message = "抽屉已打开。"
        else:
            state.flags["check_done"] = True
            message = "终检已完成，出口仍等待释放门锁。"
    elif tool == "interact":
        target = arguments["target_id"]
        observed(target)
        if target == "r1_cabinet":
            require(d.cabinet == "CODE_ACCEPTED", "柜门当前无法拉开。")
            d.cabinet = "OPEN"
            state.opened_containers.append(target)
        elif target == "r2_powerbox":
            transitions = {"CLOSED": "OPEN", "OPEN": "MISSING_FUSE", "FUSE_INSTALLED": "CIRCUIT_READY", "CIRCUIT_READY": "POWER_ON"}
            require(d.powerbox in transitions, "触点之间还没有可靠的连接。")
            d.powerbox = transitions[d.powerbox]
            state.flags["power_on"] = d.powerbox == "POWER_ON"
        elif target == "r2_monitor":
            require(state.flags["power_on"], "按下按钮后没有反应，启动灯仍暗着。")
            transitions = {"OFF": "BOOTING", "BOOTING": "LOGIN_LOCKED", "UNLOCKED": "DATA_READ"}
            require(d.computer in transitions, "终端正在等待另一种操作。")
            d.computer = transitions[d.computer]
        elif target == "exit_door":
            transitions = {"CARD_ACCEPTED": "FINAL_CHECK", "FINAL_CHECK": "UNLOCKED", "UNLOCKED": "OPEN"}
            require(d.exit in transitions)
            if d.exit == "FINAL_CHECK":
                require(state.flags["check_done"], "终检尚未完成，门锁仍扣着。")
            d.exit = transitions[d.exit]
        else:
            raise RuleError("PRECONDITION_FAILED", "轻触之后没有出现变化。")
        message = DESCRIPTIONS[DEVICE_IDS[target]][getattr(d, DEVICE_IDS[target])]
    elif tool == "move":
        destination = arguments["destination_id"]
        exits = {exit_["destination_id"]: exit_["unlocked"] for exit_ in visible_state("", state)["exits"]}
        require(exits.get(destination, False), "门还无法通行。")
        state.room_id = destination
        if destination == "EXIT":
            state.status = "won"
        message = "已进入" + legacy.ROOMS[destination][0] + "。"
    else:
        raise RuleError("INVALID_TOOL", "工具不在允许列表中。")
    changed = state.model_dump() != before
    if changed:
        state.revision += 1
    validate_invariants(state)
    return state, {"changed": changed, "message": message, "observation": observation, "new_clue_ids": new_clues, "consumed_item_ids": consumed}
