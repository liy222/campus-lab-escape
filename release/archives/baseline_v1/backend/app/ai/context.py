"""Comparable context layouts retaining the same authorized visible facts."""
from __future__ import annotations

import copy

CONTEXT_MODES = {"full_history", "structured_summary"}
HISTORY_FIELDS = {"kind", "tool", "arguments", "observation", "new_clue_ids", "revision", "generation", "outcome", "message", "answer", "clue_refs"}


def build_context(visible_state: dict, visible_history: list[dict], message: str, mode: str = "full_history") -> dict:
    """Summary groups lossless records by tool, with original chronological index.

    Both modes preserve every already-authorized history field and value; this is
    a layout comparison, not an invented or model-generated knowledge summary.
    Callers must supply sanitized public projections/history (Runtime validates).
    """
    if mode not in CONTEXT_MODES:
        raise ValueError("Invalid context mode")
    context = {"visible_state": copy.deepcopy(visible_state), "message": message, "context_mode": mode}
    if mode == "full_history":
        context["visible_history"] = copy.deepcopy(visible_history)
    else:
        groups = {}
        for ordinal, entry in enumerate(visible_history):
            group = entry["kind"] + (":" + entry["tool"] if entry["kind"] == "action" else "")
            groups.setdefault(group, []).append({"history_index": ordinal, **copy.deepcopy(entry)})
        context["visible_history_summary"] = {"record_count": len(visible_history), "records_by_tool": groups}
    return context
