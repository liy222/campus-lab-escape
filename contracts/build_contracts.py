"""Rebuild the public v1 schemas. Contains no puzzle answers or private state."""
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).parent
BASE = "https://campus-lab-escape.local/contracts/"

def obj(properties, required=None):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required, "additionalProperties": False}

def arr(items, **kw):
    return {"type": "array", "items": items, **kw}

def enum(*values):
    return {"enum": list(values)}

def ref(name):
    return {"$ref": "#/$defs/" + name}

def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}

def document(filename, definitions, root):
    value = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": BASE + filename, **root, "$defs": definitions}
    (ROOT / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ID = {"type": "string", "minLength": 1, "maxLength": 100, "pattern": "^[A-Za-z0-9_-]+$"}
GEN = {"type": "string", "format": "uuid"}
REV = {"type": "integer", "minimum": 0}
TEXT = {"type": "string", "maxLength": 4000}
TIME = {"type": "string", "format": "date-time"}
ROOM = enum("R1", "R2", "R3", "EXIT")
args = {
    "inspect": obj({"object_id": ID}),
    "get_inventory": obj({}),
    "take": obj({"item_id": ID}),
    "use_item": obj({"item_id": ID, "target_id": ID}),
    "submit_code": obj({"target_id": ID, "code": {"type": "string", "minLength": 1, "maxLength": 16, "pattern": "^[0-9]+$"}}),
    "move": obj({"destination_id": ROOM}),
}

def invocation(names):
    return {"oneOf": [obj({"tool": {"const": name}, "arguments": args[name]}) for name in names]}

TOOLS = list(args)
PROGRESS = ["take", "use_item", "submit_code", "move"]
document("tools.schema.json", args, invocation(TOOLS))
(ROOT / "tools.json").write_text(json.dumps([{"type": "function", "function": {"name": name, "description": {"inspect": "Inspect a currently visible object; discover its currently available clue. This cannot advance a puzzle.", "get_inventory": "Read the current inventory.", "take": "Propose taking a currently visible item; player confirmation required.", "use_item": "Propose using a held item on a visible target; player confirmation required.", "submit_code": "Propose submitting a numeric code inferred from discovered clues; player confirmation required.", "move": "Propose moving to an adjacent unlocked room or valid exit; player confirmation required."}[name], "strict": True, "parameters": args[name]}} for name in TOOLS], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

affordances = []
for name in TOOLS:
    template_args = args[name] if name != "submit_code" else obj({"target_id": ID})
    affordances.append(obj({"tool": {"const": name}, "label": TEXT, "arguments": template_args, "requires_code": {"const": name == "submit_code"}}))

D = {
    "tool_call": invocation(TOOLS),
    "progress_call": invocation(PROGRESS),
    "affordance": {"oneOf": affordances},
    "clue": obj({"clue_id": ID, "object_id": ID, "title": TEXT, "text": TEXT}),
    "item": obj({"item_id": ID, "name": TEXT, "description": TEXT, "usable_targets": arr(ID, uniqueItems=True)}),
    "visible_object": obj({"object_id": ID, "name": TEXT, "kind": enum("clue", "container", "door", "device", "item"), "description": TEXT, "actions": arr(ref("affordance"))}),
    "exit": obj({"destination_id": ROOM, "name": TEXT, "unlocked": {"type": "boolean"}}),
    "save_metadata": obj({"schema_version": {"const": "1.0.0"}, "level_version": enum("1.0.0", "2.0.0"), "saved_at": TIME, "source_revision": REV, "source_generation": GEN}),
}
D["visible_state"] = obj({"schema_version": {"const": "1.0.0"}, "level_version": enum("1.0.0", "2.0.0"), "session_id": ID, "revision": REV, "generation": GEN, "status": enum("playing", "won"), "room": obj({"room_id": ROOM, "name": TEXT, "description": TEXT}), "objects": arr(ref("visible_object")), "inventory": arr(ref("item")), "clues": arr(ref("clue")), "exits": arr(ref("exit")), "progress": obj({"power_on": {"type": "boolean"}, "check_done": {"type": "boolean"}}), "save": nullable(ref("save_metadata"))})
D["proposal"] = {"oneOf": [obj({"proposal_id": ID, "tool": {"const": name}, "arguments": args[name], "revision": REV, "generation": GEN, "expires_at": TIME, "status": enum("pending", "committed", "cancelled", "expired", "invalidated", "rejected"), "clue_refs": arr(ID, uniqueItems=True), "summary": TEXT}) for name in PROGRESS]}
D["receipt"] = {"oneOf": [obj({"request_id": ID, "event_id": ID, "tool": {"const": name}, "arguments": args[name], "generation": GEN, "revision_before": REV, "revision_after": REV, "changed": {"type": "boolean"}, "message": TEXT, "observation": nullable(TEXT), "new_clue_ids": arr(ID, uniqueItems=True), "consumed_item_ids": arr(ID, uniqueItems=True)}) for name in TOOLS]}
CONTROL = obj({"request_id": ID, "revision": REV, "generation": GEN})
D["version_request"] = CONTROL
D["action_request"] = {"oneOf": [obj({**CONTROL["properties"], "tool": {"const": name}, "arguments": args[name]}) for name in TOOLS]}
D["ai_turn_request"] = obj({**CONTROL["properties"], "message": {"type": "string", "minLength": 1, "maxLength": 2000}})
D["empty_request"] = obj({})
D["create_data"] = obj({"session_id": ID, "token": {"type": "string", "minLength": 32, "maxLength": 256}, "visible_state": ref("visible_state")})
D["state_data"] = obj({"visible_state": ref("visible_state")})
D["action_data"] = obj({"receipt": ref("receipt"), "replayed": {"type": "boolean"}, "proposal": nullable(ref("proposal")), "visible_state": ref("visible_state")})
D["control_data"] = obj({"request_id": ID, "replayed": {"type": "boolean"}, "message": TEXT, "visible_state": ref("visible_state")})
D["cancel_data"] = obj({"proposal": ref("proposal"), "visible_state": ref("visible_state")})
D["ai_turn_data"] = obj({"turn_id": ID, "answer": TEXT, "clue_refs": arr(ID, uniqueItems=True), "proposal": nullable(ref("proposal")), "status": enum("completed", "no_suggestion", "stopped"), "stop_reason": nullable(enum("MODEL_TIMEOUT", "MODEL_UNAVAILABLE", "MODEL_INVALID_OUTPUT", "AI_LIMIT_REACHED", "STALE_STATE")), "usage": obj({"provider": ID, "model": nullable(TEXT), "input_tokens": nullable(REV), "output_tokens": nullable(REV), "model_calls": REV, "read_tool_calls": REV}), "visible_state": ref("visible_state")})
ERRORS = {"BAD_ARGUMENT": 422, "INVALID_TOOL": 422, "FORBIDDEN_SESSION": 403, "NOT_VISIBLE": 409, "PRECONDITION_FAILED": 409, "WRONG_CODE": 409, "ALREADY_TAKEN": 409, "GAME_FINISHED": 409, "STALE_STATE": 409, "STALE_GENERATION": 409, "REQUEST_ID_CONFLICT": 409, "PROPOSAL_NOT_FOUND": 404, "PROPOSAL_EXPIRED": 409, "PROPOSAL_CANCELLED": 409, "PROPOSAL_INVALIDATED": 409, "PROPOSAL_REJECTED": 409, "SAVE_NOT_FOUND": 404, "INVALID_SNAPSHOT": 409, "SNAPSHOT_VERSION_MISMATCH": 409, "MODEL_UNAVAILABLE": 503, "MODEL_TIMEOUT": 504, "MODEL_INVALID_OUTPUT": 502, "AI_LIMIT_REACHED": 429, "INTERNAL_ERROR": 500}
D["error_response"] = obj({"ok": {"const": False}, "event_id": ID, "error": obj({"code": enum(*ERRORS), "message": TEXT}), "visible_state": nullable(ref("visible_state"))})
for name in ["create", "state", "action", "control", "cancel", "ai_turn"]:
    D[name + "_response"] = obj({"ok": {"const": True}, "event_id": ID, "data": ref(name + "_data")})

# Keep the legacy projection strict and describe upgrade as a separate branch.
# Provider tools remain the original six; interact is a manual-only operation.
INTERACT_ARGS = obj({"target_id": ID})
D["upgrade_affordance"] = deepcopy(D["affordance"])
D["upgrade_affordance"]["oneOf"].append(obj({"tool": {"const": "interact"}, "label": TEXT, "arguments": INTERACT_ARGS, "requires_code": {"const": False}}))
D["upgrade_visible_object"] = deepcopy(D["visible_object"])
D["upgrade_visible_object"]["properties"]["actions"] = arr(ref("upgrade_affordance"))
D["legacy_save_metadata"] = deepcopy(D["save_metadata"])
D["upgrade_save_metadata"] = deepcopy(D["save_metadata"])
D["upgrade_save_metadata"]["properties"]["schema_version"] = {"const": "1.1.0"}
D["upgrade_save_metadata"]["properties"]["level_version"] = {"const": "3.1.0"}
D["save_metadata"] = {"oneOf": [ref("legacy_save_metadata"), ref("upgrade_save_metadata")]}
D["legacy_visible_state"] = deepcopy(D["visible_state"])
D["legacy_visible_state"]["properties"]["save"] = nullable(ref("legacy_save_metadata"))
D["upgrade_visible_state"] = deepcopy(D["visible_state"])
upgrade_properties = D["upgrade_visible_state"]["properties"]
upgrade_properties["schema_version"] = {"const": "1.1.0"}
upgrade_properties["level_version"] = {"const": "3.1.0"}
upgrade_properties["objects"] = arr(ref("upgrade_visible_object"))
upgrade_properties["save"] = nullable(ref("upgrade_save_metadata"))
upgrade_properties["device_states"] = obj({
    "cabinet": enum("LOCKED", "CODE_ACCEPTED", "OPEN", "ITEM_TAKEN"),
    "powerbox": enum("CLOSED", "OPEN", "MISSING_FUSE", "FUSE_INSTALLED", "CIRCUIT_READY", "POWER_ON"),
    "computer": enum("OFF", "BOOTING", "LOGIN_LOCKED", "UNLOCKED", "DATA_READ"),
    "exit": enum("LOCKED", "CARD_ACCEPTED", "FINAL_CHECK", "UNLOCKED", "OPEN"),
})
upgrade_properties["observed_object_ids"] = arr(ID, uniqueItems=True)
D["upgrade_visible_state"]["required"] = list(upgrade_properties)
D["visible_state"] = {"oneOf": [ref("legacy_visible_state"), ref("upgrade_visible_state")]}
D["action_request"]["oneOf"].append(obj({**CONTROL["properties"], "tool": {"const": "interact"}, "arguments": INTERACT_ARGS}))
manual_receipt = deepcopy(D["receipt"]["oneOf"][0])
manual_receipt["properties"]["tool"] = {"const": "interact"}
manual_receipt["properties"]["arguments"] = INTERACT_ARGS
D["receipt"]["oneOf"].append(manual_receipt)

# v3.2 is another strict projection. Login is manual-only, never a provider tool.
LOGIN_ARGS = obj({"target_id": ID, "username": {"type": "string", "minLength": 1, "maxLength": 64, "pattern": "^[A-Za-z0-9_-]+$"}, "password": {"type": "string", "minLength": 1, "maxLength": 16, "pattern": "^[0-9]+$"}})
D["puzzle_affordance"] = deepcopy(D["upgrade_affordance"])
D["puzzle_affordance"]["oneOf"].append(obj({"tool": {"const": "submit_login"}, "label": TEXT, "arguments": obj({"target_id": ID}), "requires_code": {"const": False}}))
D["puzzle_visible_object"] = deepcopy(D["upgrade_visible_object"])
D["puzzle_visible_object"]["properties"]["actions"] = arr(ref("puzzle_affordance"))
D["puzzle_save_metadata"] = deepcopy(D["upgrade_save_metadata"])
D["puzzle_save_metadata"]["properties"]["schema_version"] = {"const": "1.2.0"}
D["puzzle_save_metadata"]["properties"]["level_version"] = {"const": "3.2.0"}
D["save_metadata"]["oneOf"].append(ref("puzzle_save_metadata"))
D["puzzle_visible_state"] = deepcopy(D["upgrade_visible_state"])
puzzle_properties = D["puzzle_visible_state"]["properties"]
puzzle_properties["schema_version"] = {"const": "1.2.0"}
puzzle_properties["level_version"] = {"const": "3.2.0"}
puzzle_properties["objects"] = arr(ref("puzzle_visible_object"))
puzzle_properties["save"] = nullable(ref("puzzle_save_metadata"))
puzzle_properties["puzzle_states"] = obj({"microscope": enum("EMPTY", "SLIDE_PLACED"), "panel": enum("EMPTY", "STRIP_INSERTED")})
D["puzzle_visible_state"]["required"] = list(puzzle_properties)
D["visible_state"]["oneOf"].append(ref("puzzle_visible_state"))
D["action_request"]["oneOf"].append(obj({**CONTROL["properties"], "tool": {"const": "submit_login"}, "arguments": LOGIN_ARGS}))
login_receipt = deepcopy(manual_receipt)
login_receipt["properties"]["tool"] = {"const": "submit_login"}
login_receipt["properties"]["arguments"] = LOGIN_ARGS
D["receipt"]["oneOf"].append(login_receipt)

# v3.3 exposes manual minigames only in the current physically prepared room.
MODULE = enum(*[f"c{row}{column}" for row in range(3) for column in range(3)])
DEVICE = enum("cooling", "lighting", "safety", "ventilation")
ROTATE_ARGS = obj({"target_id": {"const": "r2_powerbox"}, "module_id": MODULE})
CIRCUIT_ARGS = obj({"target_id": {"const": "r2_powerbox"}})
SEQUENCE_ARGS = obj({"target_id": {"const": "r3_panel"}, "device_ids": arr(DEVICE, minItems=4, maxItems=4, uniqueItems=True)})
MINI_ARGS = {"rotate_circuit": ROTATE_ARGS, "submit_circuit": CIRCUIT_ARGS, "submit_sequence": SEQUENCE_ARGS}
D["mini_affordance"] = deepcopy(D["puzzle_affordance"])
for name, parameters in MINI_ARGS.items():
    template = obj({"target_id": parameters["properties"]["target_id"]}) if name == "submit_sequence" else parameters
    D["mini_affordance"]["oneOf"].append(obj({"tool": {"const": name}, "label": TEXT, "arguments": template, "requires_code": {"const": False}}))
    D["action_request"]["oneOf"].append(obj({**CONTROL["properties"], "tool": {"const": name}, "arguments": parameters}))
    receipt = deepcopy(manual_receipt)
    receipt["properties"]["tool"] = {"const": name}
    receipt["properties"]["arguments"] = parameters
    D["receipt"]["oneOf"].append(receipt)
D["mini_visible_object"] = deepcopy(D["puzzle_visible_object"])
D["mini_visible_object"]["properties"]["actions"] = arr(ref("mini_affordance"))
D["mini_save_metadata"] = deepcopy(D["puzzle_save_metadata"])
D["mini_save_metadata"]["properties"]["schema_version"] = {"const": "1.3.0"}
D["mini_save_metadata"]["properties"]["level_version"] = {"const": "3.3.0"}
D["save_metadata"]["oneOf"].append(ref("mini_save_metadata"))
D["mini_visible_state"] = deepcopy(D["puzzle_visible_state"])
mini_properties = D["mini_visible_state"]["properties"]
mini_properties["schema_version"] = {"const": "1.3.0"}
mini_properties["level_version"] = {"const": "3.3.0"}
mini_properties["objects"] = arr(ref("mini_visible_object"))
mini_properties["save"] = nullable(ref("mini_save_metadata"))
ENDPOINT = obj({"module_id": MODULE, "side": enum("N", "E", "S", "W")})
COORDINATE = {"type": "integer", "minimum": 0, "maximum": 2}
MODULE_STATE = obj({"module_id": MODULE, "row": COORDINATE, "column": COORDINATE,
                    "shape": enum("I", "L"), "rotation": {"type": "integer", "minimum": 0, "maximum": 3}})
CIRCUIT = obj({"target_id": {"const": "r2_powerbox"}, "rows": {"const": 3}, "columns": {"const": 3},
               "source": ENDPOINT, "sink": ENDPOINT, "modules": arr(MODULE_STATE, minItems=9, maxItems=9),
               "status": enum("editing", "completed")})
SEQUENCE = obj({"target_id": {"const": "r3_panel"},
                "devices": arr(obj({"device_id": DEVICE, "label": TEXT, "symbol": enum("▲", "★", "●", "■")}), minItems=4, maxItems=4),
                "length": {"const": 4}, "status": enum("editing", "completed")})
mini_properties["minigames"] = obj({"circuit": nullable(CIRCUIT), "sequence": nullable(SEQUENCE)})
D["mini_visible_state"]["required"] = list(mini_properties)
D["visible_state"]["oneOf"].append(ref("mini_visible_state"))
document("api.schema.json", D, {"oneOf": [ref(name + "_response") for name in ["create", "state", "action", "control", "cancel", "ai_turn"]] + [ref("error_response")]})
ROUTES = [
    ("POST", "/api/sessions", "empty_request", "create_response", 201, False),
    ("GET", "/api/sessions/{id}/state", None, "state_response", 200, True),
    ("POST", "/api/sessions/{id}/actions", "action_request", "action_response", 200, True),
    ("POST", "/api/sessions/{id}/reset", "version_request", "control_response", 200, True),
    ("POST", "/api/sessions/{id}/save", "version_request", "control_response", 200, True),
    ("POST", "/api/sessions/{id}/restore", "version_request", "control_response", 200, True),
    ("POST", "/api/sessions/{id}/ai/turns", "ai_turn_request", "ai_turn_response", 200, True),
    ("POST", "/api/sessions/{id}/proposals/{pid}/confirm", "empty_request", "action_response", 200, True),
    ("POST", "/api/sessions/{id}/proposals/{pid}/cancel", "empty_request", "cancel_response", 200, True),
]
(ROOT / "routes.json").write_text(json.dumps({"contract_version": "1.3.0", "schema": "api.schema.json", "routes": [{"method": m, "path": p, "request": r, "response": s, "success_status": h, "requires_session_token": a} for m,p,r,s,h,a in ROUTES], "error_statuses": ERRORS}, indent=2) + "\n", encoding="utf-8")
