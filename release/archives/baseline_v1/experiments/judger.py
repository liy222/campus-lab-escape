"""Offline deepcopy judger, separate from request building and generation."""
from copy import deepcopy

from jsonschema import Draft202012Validator

from .common import HOME, ROOT, load, sha, strict_load

VERSION = "e1-judger-v1"


def judge(content, sample):
    result = {"parse_valid": False, "legal": None, "correct": None, "reference_valid": None,
              "reference_sufficient": None, "judger_version": VERSION, "reason": None, "next_action": None}
    try:
        value = strict_load(content or "")
        Draft202012Validator(load(HOME / "schema.json")).validate(value)
    except Exception:
        result["reason"] = "INVALID_OUTPUT_SCHEMA"
        return result
    result["parse_valid"] = True
    proposed = value["next_action"]
    known = {clue["clue_id"] for clue in sample["visible_state"]["clues"]}
    references = value["clue_refs"] + (proposed["clue_refs"] if proposed else [])
    result["reference_valid"] = all(ref in known for ref in references)
    truth = load(HOME / "ground_truth" / (sample["sample_id"] + ".json"))
    if truth["public_sample_hash"] != sha(sample):
        raise ValueError("GROUND_TRUTH_SAMPLE_MISMATCH")
    if proposed is None:
        result.update(legal=False, correct=False, reference_sufficient=False, reason="NO_ACTION")
        return result
    result["next_action"] = deepcopy(proposed)
    from backend.app.domain.models import GameState, RuleError
    from backend.app.domain.rules import apply_action
    state = GameState.model_validate(deepcopy(truth["state"]))
    before = state.model_dump()
    try:
        apply_action(state.model_copy(deep=True), proposed["tool"], deepcopy(proposed["arguments"]))
        result["legal"] = True
    except RuleError as error:
        result.update(legal=False, reason=error.code)
    if before != state.model_dump():
        raise ValueError("JUDGER_MUTATED_SAMPLE")
    action = {"tool": proposed["tool"], "arguments": proposed["arguments"]}
    result["correct"] = bool(result["legal"] and action in truth["acceptable_actions"])
    required = set(truth["required_code_refs"]) if proposed["tool"] == "submit_code" else set()
    result["reference_sufficient"] = result["reference_valid"] and required <= set(proposed["clue_refs"])
    if not result["correct"] and result["reason"] is None:
        result["reason"] = "LEGAL_BUT_NOT_USEFUL_NEXT_ACTION"
    return result
