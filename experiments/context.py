"""Experiment-local exact reversible column layout; baseline AI is untouched."""
from copy import deepcopy

VERSION = "e1-columns-v1"
VARIANTS = ("full_history", "structured_summary")
FIELD_ORDER = ("kind", "tool", "arguments", "observation", "new_clue_ids", "revision",
               "generation", "outcome", "message", "answer", "clue_refs")


def pack(history):
    groups = {}
    for index, entry in enumerate(history):
        if not isinstance(entry, dict) or set(entry) - set(FIELD_ORDER):
            raise ValueError("UNAUTHORIZED_HISTORY_FIELDS")
        fields = tuple(key for key in FIELD_ORDER if key in entry)
        group = groups.setdefault(fields, {"fields": list(fields), "indices": [], "rows": []})
        group["indices"].append(index)
        group["rows"].append([deepcopy(entry[key]) for key in fields])
    return {"encoding": VERSION, "record_count": len(history), "groups": list(groups.values())}


def unpack(summary):
    if summary.get("encoding") != VERSION or type(summary.get("record_count")) is not int or summary["record_count"] < 0:
        raise ValueError("INVALID_SUMMARY")
    output = [None] * summary["record_count"]
    for group in summary["groups"]:
        fields = group["fields"]
        if len(set(fields)) != len(fields) or set(fields) - set(FIELD_ORDER) or len(group["indices"]) != len(group["rows"]):
            raise ValueError("INVALID_SUMMARY")
        for index, values in zip(group["indices"], group["rows"]):
            if type(index) is not int or not 0 <= index < len(output) or output[index] is not None or len(values) != len(fields):
                raise ValueError("INVALID_SUMMARY")
            output[index] = dict(zip(fields, deepcopy(values)))
    if any(row is None for row in output):
        raise ValueError("INCOMPLETE_SUMMARY")
    return output


def build(sample, variant):
    if variant not in VARIANTS:
        raise ValueError("INVALID_VARIANT")
    result = {"visible_state": deepcopy(sample["visible_state"]), "message": sample["message"]}
    if variant == "full_history":
        result["visible_history"] = deepcopy(sample["visible_history"])
    else:
        result["visible_history_summary"] = pack(sample["visible_history"])
    return result


def facts(context):
    history = context.get("visible_history")
    if history is None:
        history = unpack(context["visible_history_summary"])
    return {"visible_state": deepcopy(context["visible_state"]), "message": context["message"],
            "visible_history": deepcopy(history)}
