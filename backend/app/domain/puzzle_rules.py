"""Three-room v3.2 clue network, using the shared Store and device stages."""
from copy import deepcopy

from .device_flow import DEVICE_IDS, advance, initial_devices, validate_observed_devices
from .models import RuleError
from .puzzle_models import PuzzleState, PuzzleStates, TOOL_MODELS_PUZZLE
from .upgrade_rules import DESCRIPTIONS as DEVICE_DESCRIPTIONS

SCHEMA_VERSION = "1.2.0"
LEVEL_VERSION = "3.2.0"
state_model = PuzzleState
tool_models = TOOL_MODELS_PUZZLE
game_fields = set(PuzzleState.model_fields) - {"revision", "generation"}
ROOMS = {"R1": ("实验准备室", "月光落在实验桌上，墙钟的指针停在深夜。"), "R2": ("设备实验室", "仪器沿墙排列，安静的屏幕映着房间里的微光。"), "R3": ("出口控制室", "控制台旁有一张设备对应表，出口门立在走廊尽头。"), "EXIT": ("实验室出口", "已离开实验室。")}
ITEMS = {
    "sample_slide": {"item_id": "sample_slide", "name": "样本玻片", "description": "一块薄薄的玻璃片，中央封着一小点淡色样本。"},
    "fuse": {"item_id": "fuse", "name": "保险丝", "description": "细长玻璃管里有一根完整金属丝，两端包着金属帽。"},
    "research_strip": {"item_id": "research_strip", "name": "研究纸条", "description": "一条窄纸，边缘有整齐的定位孔，字迹保存完好。"},
    "access_card": {"item_id": "access_card", "name": "门禁卡", "description": "一张磨损的塑料卡片，边角留下了反复使用的痕迹。"},
}
ITEM_OBJECTS = {"sample_slide": "sample_slide", "fuse": "r1_fuse", "research_strip": "research_strip", "access_card": "access_card"}
CLUES = {
    "r1_clock_clue": {"clue_id": "r1_clock_clue", "object_id": "r1_clock", "title": "实验开始时间", "text": "墙钟停在21:17，钟下的小牌写着“实验开始”。"},
    "r1_record_clue": {"clue_id": "r1_record_clue", "object_id": "r1_record", "title": "样本编号规则", "text": "样本索引的前两位是样本编号，最后两位采用实验开始时间的分钟数。"},
    "r1_plaque_clue": {"clue_id": "r1_plaque_clue", "object_id": "r1_plaque", "title": "实验室铭牌", "text": "门边的旧铭牌写着：LAB-42。"},
    "r1_sample_clue": {"clue_id": "r1_sample_clue", "object_id": "r1_microscope", "title": "显微镜下的标记", "text": "在放大视野里，样本标记可以辨认为：LAB SAMPLE 42。"},
    "r1_symbols_clue": {"clue_id": "r1_symbols_clue", "object_id": "r1_symbols", "title": "旧批次源序", "text": "柜内旧标签写着“批次源序”，从左到右为：▲ ● ■ ★。"},
    "r2_maintenance_clue": {"clue_id": "r2_maintenance_clue", "object_id": "r2_maintenance", "title": "终端维护说明", "text": "USER使用实验室的完整编号；PASS采用实验开始时间，格式为HHMM，不包含冒号。"},
    "r2_indices_clue": {"clue_id": "r2_indices_clue", "object_id": "research_strip", "title": "转录读取位置", "text": "研究纸条：按源序中的第3、第1、第4、第2位依次读取。纸边有定位孔，末端印着四个空白方格。"},
    "r3_legend_clue": {"clue_id": "r3_legend_clue", "object_id": "r3_legend", "title": "设备对应表", "text": "■ 通风对应4；▲ 冷却对应7；★ 照明对应9；● 安全对应2。终检按转录后的顺序录入设备数字。"},
}
CANONICAL = {clue["object_id"]: cid for cid, clue in CLUES.items() if cid != "r1_sample_clue"}
DESCRIPTIONS = deepcopy(DEVICE_DESCRIPTIONS)
DESCRIPTIONS["cabinet"].update(LOCKED="柜门紧闭，四位数字锁旁刻着“样本索引”。", OPEN="柜门敞开，里面有一个玻璃管和一张旧标签。", ITEM_TAKEN="玻璃管原来所在的位置已空，旧标签仍贴在柜内。")
DESCRIPTIONS["computer"].update(LOGIN_LOCKED="登录界面亮着，等待输入USER和PASS。", UNLOCKED="登录已通过，一份封存研究记录等待读取。", DATA_READ="研究记录已经打开，侧边的小托盘里露出窄纸和塑料卡片。")
OBJECTS = {
    "R1": [("r1_clock", "墙钟", "clue", "墙上挂着一只停走的钟。"), ("r1_record", "实验记录", "clue", "实验桌上摊着一份旧记录。"), ("r1_plaque", "实验室铭牌", "clue", "门旁钉着一块磨损铭牌。"), ("r1_microscope", "显微镜", "device", "实验桌上的显微镜带着玻片夹。"), ("sample_slide", "样本玻片", "item", "桌边的小盒里放着一块薄玻璃片。"), ("r1_cabinet", "储物柜", "container", ""), ("r1_door", "设备间门", "door", "门把手旁有一道普通门闩。")],
    "R2": [("r2_powerbox", "电源箱", "device", ""), ("r2_monitor", "电脑", "device", ""), ("r2_maintenance", "维护说明", "clue", "机身旁贴着一张维护说明。"), ("r2_door", "控制室门", "door", "门把手旁有一道普通门闩。")],
    "R3": [("r3_legend", "设备对应表", "clue", "控制台旁印着一张设备对应表。"), ("r3_panel", "终检控制台", "device", ""), ("exit_door", "实验室出口", "door", "")],
    "EXIT": [],
}
OBJECT_IDS = {entry[0] for entries in OBJECTS.values() for entry in entries} | {"r1_fuse", "r1_symbols", "research_strip", "access_card"}
# Trusted answers are never included in the public projection or affordances.
CABINET_CODE = "4217"
LOGIN_USERNAME, LOGIN_PASSWORD = "LAB-42", "2117"
FINAL_CODE = "4792"


def initial_state(revision=0):
    return PuzzleState(level_version=LEVEL_VERSION, revision=revision, device_states=initial_devices(), puzzle_states=PuzzleStates(microscope="EMPTY", panel="EMPTY"), observed_object_ids=[], taken_item_ids=[], consumed_item_ids=[])


def affordance(tool, label, **args):
    return {"tool": tool, "label": label, "arguments": args, "requires_code": tool == "submit_code"}


def current_description(object_id, state, fallback=""):
    if object_id in DEVICE_IDS:
        field = DEVICE_IDS[object_id]
        return DESCRIPTIONS[field][getattr(state.device_states, field)]
    if object_id == "r1_microscope":
        if "r1_sample_clue" in state.discovered_clue_ids:
            return "载物台上的玻片保持原位，样本标记已经读过。"
        return {"EMPTY": "玻片夹空着，目镜下只有模糊光影。", "SLIDE_PLACED": "玻片已固定在载物台上，目镜等待读取。"}[state.puzzle_states.microscope]
    if object_id == "r3_panel":
        if state.flags["check_done"]:
            return "转录顺序已经通过终检，确认灯亮着。"
        return {"EMPTY": "控制台旁有一条带定位齿的窄纸槽，数字键仍暗着。", "STRIP_INSERTED": "窄纸已沿定位齿插好，控制台等待终检录入。"}[state.puzzle_states.panel]
    if object_id == "r1_door" and state.flags["r2_unlocked"] or object_id == "r2_door" and state.flags["r3_unlocked"]:
        return "门闩已拉开，可以通行。"
    return fallback


def visible_objects(state):
    d, p = state.device_states, state.puzzle_states
    entries = [entry for entry in OBJECTS[state.room_id] if entry[0] != "sample_slide" or "sample_slide" not in state.taken_item_ids]
    if state.room_id == "R1" and d.cabinet in {"OPEN", "ITEM_TAKEN"}:
        entries.append(("r1_symbols", "柜内旧标签", "clue", "柜内壁上贴着一张旧批次标签。"))
        if "fuse" not in state.taken_item_ids:
            entries.append(("r1_fuse", "保险丝", "item", "柜内有一个两端包着金属帽的玻璃管。"))
    if state.room_id == "R2" and d.computer == "DATA_READ":
        for item in ("research_strip", "access_card"):
            if item not in state.taken_item_ids:
                entries.append((item, ITEMS[item]["name"], "item", "托盘里露出一条窄纸。" if item == "research_strip" else "托盘里有一张磨损塑料卡片。"))
    result = []
    for object_id, name, kind, fallback in entries:
        actions = [affordance("inspect", "观察", object_id=object_id)]
        if object_id in state.observed_object_ids and state.status == "playing":
            if kind == "item":
                item = next(item for item, obj in ITEM_OBJECTS.items() if obj == object_id)
                actions.append(affordance("take", "拿起物品", item_id=item))
            elif object_id in {"r1_door", "r2_door"}:
                flag = "r2_unlocked" if object_id == "r1_door" else "r3_unlocked"
                if not state.flags[flag]:
                    actions.append(affordance("interact", "拉开门闩", target_id=object_id))
            elif object_id == "r1_cabinet":
                if d.cabinet == "LOCKED":
                    actions.append(affordance("submit_code", "操作数字锁", target_id=object_id))
                elif d.cabinet == "CODE_ACCEPTED":
                    actions.append(affordance("interact", "拉开柜门", target_id=object_id))
            elif object_id == "r2_powerbox":
                labels = {"CLOSED": "打开箱盖", "OPEN": "移开护板", "FUSE_INSTALLED": "检查接合", "CIRCUIT_READY": "合上总闸"}
                if d.powerbox in labels:
                    actions.append(affordance("interact", labels[d.powerbox], target_id=object_id))
            elif object_id == "r2_monitor":
                if d.computer == "LOGIN_LOCKED":
                    actions.append(affordance("submit_login", "登录终端", target_id=object_id))
                elif state.flags["power_on"] and d.computer in {"OFF", "BOOTING", "UNLOCKED"}:
                    actions.append(affordance("interact", {"OFF": "按下启动键", "BOOTING": "继续启动", "UNLOCKED": "读取记录"}[d.computer], target_id=object_id))
            elif object_id == "r3_panel" and p.panel == "STRIP_INSERTED" and d.exit == "FINAL_CHECK" and not state.flags["check_done"]:
                actions.append(affordance("submit_code", "录入设备数字", target_id=object_id))
            elif object_id == "exit_door":
                labels = {"CARD_ACCEPTED": "启动终检", "FINAL_CHECK": "释放门锁", "UNLOCKED": "推开出口"}
                if d.exit in labels and (d.exit != "FINAL_CHECK" or state.flags["check_done"]):
                    actions.append(affordance("interact", labels[d.exit], target_id=object_id))
        result.append({"object_id": object_id, "name": name, "kind": kind, "description": current_description(object_id, state, fallback), "actions": actions})
    return result


def visible_state(session_id, state, save=None):
    exits = {"R1": [("R2", state.flags["r2_unlocked"])], "R2": [("R1", True), ("R3", state.flags["r3_unlocked"])], "R3": [("R2", True), ("EXIT", state.device_states.exit == "OPEN")], "EXIT": []}[state.room_id]
    return {"schema_version": SCHEMA_VERSION, "level_version": LEVEL_VERSION, "session_id": session_id, "revision": state.revision, "generation": state.generation, "status": state.status, "room": {"room_id": state.room_id, "name": ROOMS[state.room_id][0], "description": ROOMS[state.room_id][1]}, "objects": visible_objects(state), "inventory": [{**deepcopy(ITEMS[item]), "usable_targets": []} for item in state.inventory], "clues": [deepcopy(CLUES[cid]) for cid in state.discovered_clue_ids], "exits": [{"destination_id": dest, "name": ROOMS[dest][0], "unlocked": unlocked} for dest, unlocked in exits], "progress": {"power_on": state.flags["power_on"], "check_done": state.flags["check_done"]}, "save": save, "device_states": state.device_states.model_dump(), "observed_object_ids": list(state.observed_object_ids), "puzzle_states": state.puzzle_states.model_dump()}


def validate_invariants(state):
    d, p, flags = state.device_states, state.puzzle_states, state.flags
    if state.level_version != LEVEL_VERSION or set(flags) != {"r2_unlocked", "r3_unlocked", "power_on", "check_done"} or any(type(value) is not bool for value in flags.values()):
        raise ValueError("Invalid flags or level")
    for values, allowed in ((state.inventory, set(ITEMS)), (state.taken_item_ids, set(ITEMS)), (state.consumed_item_ids, {"sample_slide", "fuse", "research_strip"}), (state.observed_object_ids, OBJECT_IDS), (state.discovered_clue_ids, set(CLUES)), (state.opened_containers, {"r1_cabinet"})):
        if len(values) != len(set(values)) or not set(values) <= allowed:
            raise ValueError("Invalid state identifiers")
    if set(state.inventory) != set(state.taken_item_ids) - set(state.consumed_item_ids) or not set(state.consumed_item_ids) <= set(state.taken_item_ids):
        raise ValueError("Invalid item lifecycle")
    if any(ITEM_OBJECTS[item] not in state.observed_object_ids for item in state.taken_item_ids):
        raise ValueError("Taken item requires observation")
    if any(CLUES[cid]["object_id"] not in state.observed_object_ids for cid in state.discovered_clue_ids):
        raise ValueError("Clue requires object observation")
    if any(object_id in state.observed_object_ids and cid not in state.discovered_clue_ids for object_id, cid in CANONICAL.items()):
        raise ValueError("Observed clue requires canonical record")
    validate_observed_devices(d, state.observed_object_ids)
    for flag, target in (("r2_unlocked", "r1_door"), ("r3_unlocked", "r2_door"), ("check_done", "r3_panel")):
        if flags[flag] and target not in state.observed_object_ids:
            raise ValueError("Committed progress requires observed target")
    if (d.cabinet in {"OPEN", "ITEM_TAKEN"}) != ("r1_cabinet" in state.opened_containers) or (d.cabinet == "ITEM_TAKEN") != ("fuse" in state.taken_item_ids):
        raise ValueError("Invalid cabinet lifecycle")
    if ("fuse" in state.taken_item_ids or "r1_fuse" in state.observed_object_ids or "r1_symbols" in state.observed_object_ids) and d.cabinet not in {"OPEN", "ITEM_TAKEN"}:
        raise ValueError("Cabinet contents require open cabinet")
    if (p.microscope != "EMPTY") != ("sample_slide" in state.consumed_item_ids) or p.microscope != "EMPTY" and "r1_microscope" not in state.observed_object_ids:
        raise ValueError("Invalid microscope installation")
    if "r1_sample_clue" in state.discovered_clue_ids and p.microscope != "SLIDE_PLACED":
        raise ValueError("Sample reading requires installed slide and discovered record")
    if (d.powerbox in {"FUSE_INSTALLED", "CIRCUIT_READY", "POWER_ON"}) != ("fuse" in state.consumed_item_ids) or flags["power_on"] != (d.powerbox == "POWER_ON"):
        raise ValueError("Invalid electrical progression")
    if d.computer != "OFF" and not flags["power_on"]:
        raise ValueError("Computer requires power")
    if any(item in state.taken_item_ids or ITEM_OBJECTS[item] in state.observed_object_ids for item in ("research_strip", "access_card")) and d.computer != "DATA_READ":
        raise ValueError("Terminal contents require data read")
    if (p.panel != "EMPTY") != ("research_strip" in state.consumed_item_ids) or p.panel != "EMPTY" and "r3_panel" not in state.observed_object_ids:
        raise ValueError("Invalid paper installation")
    if flags["check_done"] and p.panel != "STRIP_INSERTED":
        raise ValueError("Panel verification requires actual check")
    if d.exit != "LOCKED" and "access_card" not in state.inventory:
        raise ValueError("Exit activation requires retained card")
    if flags["check_done"] and d.exit not in {"FINAL_CHECK", "UNLOCKED", "OPEN"} or d.exit in {"UNLOCKED", "OPEN"} and not flags["check_done"]:
        raise ValueError("Invalid exit final check")
    if state.room_id != "R1" and not flags["r2_unlocked"] or (state.room_id in {"R3", "EXIT"} or flags["r3_unlocked"]) and not flags["r2_unlocked"]:
        raise ValueError("Room requires first door")
    if (state.room_id in {"R3", "EXIT"} or any(obj in state.observed_object_ids for obj in ("r3_legend", "r3_panel", "exit_door"))) and not flags["r3_unlocked"]:
        raise ValueError("Third room requires door")
    if any(obj.startswith("r2_") for obj in state.observed_object_ids) and not flags["r2_unlocked"]:
        raise ValueError("Second room observations require first door")
    if (state.status == "won") != (state.room_id == "EXIT") or state.room_id == "EXIT" and d.exit != "OPEN":
        raise ValueError("Invalid finished state")


def apply_action(original, tool, arguments):
    state = original.model_copy(deep=True)
    before = state.model_dump()
    d, p = state.device_states, state.puzzle_states
    objects = {obj["object_id"]: obj for obj in visible_objects(state)}
    observation, new_clues, consumed = None, [], []
    message = "操作完成。"
    if state.status == "won" and tool not in {"inspect", "get_inventory"}:
        raise RuleError("GAME_FINISHED", "游戏已通关，请重新开始。")

    def require(condition, text="装置没有响应，请观察当前状态。"):
        if not condition:
            raise RuleError("PRECONDITION_FAILED", text)

    def visible(target):
        if target not in objects:
            raise RuleError("NOT_VISIBLE", "当前无法操作该对象。")

    def observed(target):
        visible(target)
        require(target in state.observed_object_ids, "还没有仔细观察这件装置。")

    if tool == "inspect":
        target = arguments["object_id"]
        visible(target)
        if target not in state.observed_object_ids:
            state.observed_object_ids.append(target)
        cid = CANONICAL.get(target)
        if target == "r1_microscope" and p.microscope != "EMPTY":
            cid = "r1_sample_clue"
        observation = CLUES[cid]["text"] if cid else next((ITEMS[item]["description"] for item, obj in ITEM_OBJECTS.items() if obj == target), objects[target]["description"])
        if cid and cid not in state.discovered_clue_ids:
            state.discovered_clue_ids.append(cid)
            new_clues.append(cid)
        message = "已观察。"
    elif tool == "get_inventory":
        observation = "背包：" + ("、".join(ITEMS[item]["name"] for item in state.inventory) or "空")
        message = "已读取背包。"
    elif tool == "take":
        item = arguments["item_id"]
        if item in state.taken_item_ids:
            raise RuleError("ALREADY_TAKEN", "该物品已领取。")
        observed(ITEM_OBJECTS.get(item))
        state.inventory.append(item)
        state.taken_item_ids.append(item)
        if item == "fuse":
            d.cabinet = "ITEM_TAKEN"
        message = "已拿起" + ITEMS[item]["name"] + "。"
    elif tool == "use_item":
        item, target = arguments["item_id"], arguments["target_id"]
        observed(target)
        require(item in state.inventory, "手中没有这件物品。")
        if (item, target) == ("sample_slide", "r1_microscope"):
            require(p.microscope == "EMPTY")
            p.microscope = "SLIDE_PLACED"
            consumed.append(item)
            message = "玻片已固定在载物台上，目镜等待读取。"
        elif (item, target) == ("fuse", "r2_powerbox"):
            require(d.powerbox == "MISSING_FUSE", "触点之间还无法接合。")
            d.powerbox = "FUSE_INSTALLED"
            consumed.append(item)
            message = "玻璃管已卡入触点之间，总闸仍抬着。"
        elif (item, target) == ("research_strip", "r3_panel"):
            require(p.panel == "EMPTY")
            p.panel = "STRIP_INSERTED"
            consumed.append(item)
            message = "窄纸已经沿定位齿插好，控制台等待终检录入。"
        elif (item, target) == ("access_card", "exit_door"):
            if d.exit == "LOCKED":
                d.exit = "CARD_ACCEPTED"
            message = "读卡灯已经亮起，出口仍保持当前状态。"
        else:
            raise RuleError("PRECONDITION_FAILED", "物品与装置无法接合，没有出现变化。")
        for item in consumed:
            state.inventory.remove(item)
            state.consumed_item_ids.append(item)
    elif tool == "submit_login":
        target = arguments["target_id"]
        observed(target)
        require(target == "r2_monitor" and d.computer == "LOGIN_LOCKED", "终端当前没有等待登录。")
        if arguments["username"] != LOGIN_USERNAME or arguments["password"] != LOGIN_PASSWORD:
            raise RuleError("WRONG_CODE", "终端没有接受这组登录信息，请核对已发现资料。")
        d.computer = "UNLOCKED"
        message = "登录已通过，研究记录等待读取。"
    elif tool == "submit_code":
        target = arguments["target_id"]
        observed(target)
        require(target in {"r1_cabinet", "r3_panel"}, "这里没有等待这类数字输入。")
        if target == "r3_panel":
            require(p.panel != "EMPTY" and d.exit == "FINAL_CHECK", "终检装置尚未准备好录入。")
        if arguments["code"] != (CABINET_CODE if target == "r1_cabinet" else FINAL_CODE):
            raise RuleError("WRONG_CODE", "装置没有接受这组数字，请核对已发现资料。")
        if target == "r1_cabinet":
            if d.cabinet == "LOCKED":
                d.cabinet = "CODE_ACCEPTED"
            message = "数字锁已接受输入，柜门仍保持当前状态。"
        else:
            state.flags["check_done"] = True
            message = "终检已完成，出口仍等待释放门锁。"
    elif tool == "interact":
        target = arguments["target_id"]
        observed(target)
        if target in {"r1_door", "r2_door"}:
            state.flags["r2_unlocked" if target == "r1_door" else "r3_unlocked"] = True
            message = "门闩已拉开，可以通行。"
        else:
            require(target in DEVICE_IDS, "轻触之后没有出现变化。")
            field = DEVICE_IDS[target]
            if field == "computer":
                require(state.flags["power_on"], "按下按钮后没有反应，启动灯仍暗着。")
            if field == "exit" and d.exit == "FINAL_CHECK":
                require(state.flags["check_done"], "终检尚未完成，门锁仍扣着。")
            advance(d, field)
            if field == "powerbox":
                state.flags["power_on"] = d.powerbox == "POWER_ON"
            if field == "cabinet":
                state.opened_containers.append(target)
            message = DESCRIPTIONS[field][getattr(d, field)]
    elif tool == "move":
        destination = arguments["destination_id"]
        exits = {exit_["destination_id"]: exit_["unlocked"] for exit_ in visible_state("", state)["exits"]}
        require(exits.get(destination, False), "门还无法通行。")
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
    return state, {"changed": changed, "message": message, "observation": observation, "new_clue_ids": new_clues, "consumed_item_ids": consumed}
