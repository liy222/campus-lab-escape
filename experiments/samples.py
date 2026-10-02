"""Offline-only fixture builder. Never imported by paid request construction."""
from copy import deepcopy
from uuid import uuid5, NAMESPACE_URL

from .common import BASELINE, HOME, ROOT, baseline_binding, load, sha, write_new


def build_samples():
    baseline_binding()  # Validate bytes before importing trusted level code.
    from backend.app.domain.models import GameState
    from backend.app.domain.rules import apply_action, visible_state
    generation = str(uuid5(NAMESPACE_URL, "E1/baseline-v1/synthetic-generation"))
    state = GameState(generation=generation)
    history = []
    public, private = {}, {}

    def action(tool, **arguments):
        nonlocal state
        state, result = apply_action(state, tool, arguments)
        history.append({"kind": "action", "tool": tool, "arguments": arguments,
                        "observation": result["observation"], "new_clue_ids": result["new_clue_ids"],
                        "revision": state.revision, "generation": generation,
                        "outcome": "success", "message": result["message"]})

    def checkpoint(number, candidates, required=()):
        sample_id = f"C{number:02d}"
        # Fixed repeated public read records; no puzzle or knowledge mutation.
        action("get_inventory")
        action("get_inventory")
        sample = {"sample_id": sample_id, "commit": BASELINE, "level_version": "1.0.0",
                  "schema_version": "1.0.0", "source": "frozen rules legal prefix; synthetic IDs; no HTTP",
                  "message": "请根据我已知的信息建议一个有用的下一步动作，不执行。",
                  "visible_state": visible_state("E1-synthetic", state), "visible_history": deepcopy(history)}
        public[sample_id] = sample
        private[sample_id] = {"sample_id": sample_id, "state": state.model_dump(), "acceptable_actions": candidates,
                              "required_code_refs": list(required), "public_sample_hash": sha(sample),
                              "source": "offline level rules and docs/level_design.md; never model input"}

    def candidate(tool, **arguments):
        return {"tool": tool, "arguments": arguments}

    checkpoint(1, [candidate("inspect", object_id="r1_note"), candidate("inspect", object_id="r1_cabinet")])
    action("inspect", object_id="r1_note")
    checkpoint(2, [candidate("inspect", object_id="r1_cabinet")])
    action("inspect", object_id="r1_cabinet")
    checkpoint(3, [candidate("submit_code", target_id="r1_cabinet", code="382")], ("r1_note_clue", "r1_cabinet_clue"))
    action("submit_code", target_id="r1_cabinet", code="382")
    checkpoint(4, [candidate("take", item_id="access_card")])
    action("take", item_id="access_card")
    checkpoint(5, [candidate("use_item", item_id="access_card", target_id="r1_door")])
    action("use_item", item_id="access_card", target_id="r1_door")
    action("move", destination_id="R2")
    checkpoint(6, [candidate("take", item_id="fuse"), candidate("inspect", object_id="r2_drawer")])
    action("take", item_id="fuse")
    action("use_item", item_id="fuse", target_id="r2_powerbox")
    checkpoint(7, [candidate("inspect", object_id="r2_monitor"), candidate("inspect", object_id="r2_drawer")])
    action("inspect", object_id="r2_monitor")
    action("inspect", object_id="r2_drawer")
    checkpoint(8, [candidate("submit_code", target_id="r2_drawer", code="724")], ("r2_monitor_clue", "r2_drawer_clue"))
    action("submit_code", target_id="r2_drawer", code="724")
    checkpoint(9, [candidate("take", item_id="emergency_key")])
    action("take", item_id="emergency_key")
    checkpoint(10, [candidate("use_item", item_id="emergency_key", target_id="r2_door")])
    action("use_item", item_id="emergency_key", target_id="r2_door")
    action("move", destination_id="R3")
    action("inspect", object_id="r3_checklist")
    checkpoint(11, [candidate("inspect", object_id="r3_panel")])
    action("inspect", object_id="r3_panel")
    checkpoint(12, [candidate("submit_code", target_id="r3_panel", code="231")], ("r3_checklist_clue", "r3_panel_clue"))
    return public, private


def main():
    public, private = build_samples()
    tools = load(ROOT / "contracts/tools.json")
    refs = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
    choices = []
    for tool in tools:
        function = tool["function"]
        choices.append({"type": "object", "additionalProperties": False,
                        "required": ["tool", "arguments", "clue_refs", "summary"],
                        "properties": {"tool": {"const": function["name"]}, "arguments": function["parameters"],
                                       "clue_refs": refs, "summary": {"type": "string", "minLength": 1, "maxLength": 4000}}})
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "additionalProperties": False,
              "required": ["answer", "clue_refs", "next_action"], "properties": {
                  "answer": {"type": "string", "minLength": 1, "maxLength": 4000}, "clue_refs": refs,
                  "next_action": {"oneOf": [{"type": "null"}] + choices}}}
    write_new(HOME / "schema.json", schema)
    for sample_id in public:
        write_new(HOME / "fixtures" / (sample_id + ".json"), public[sample_id])
        write_new(HOME / "ground_truth" / (sample_id + ".json"), private[sample_id])
    write_new(HOME / "fixtures/index.json", {"samples": {key: sha(value) for key, value in public.items()},
                                             "commit": BASELINE, "ground_truth_sent": False})


if __name__ == "__main__":
    main()
