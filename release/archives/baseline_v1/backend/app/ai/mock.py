"""Deterministic visible-information-only provider; never reports paid usage."""
from __future__ import annotations

import json
import re

from .provider import CallLimits, ProviderError, ProviderResult, strict_json, _validate_messages, _validate_tools


def infer_code(clues: list[dict], target_id: str) -> tuple[str, list[str]] | None:
    """Read number mappings and an ordered list from discovered clue text."""
    for mapping in clues:
        pairs = re.findall(r"([\u4e00-\u9fff]+?)(?:记为|对应)?([0-9]+)", mapping["text"])
        values = {name.removesuffix("色"): number for name, number in pairs}
        if not values:
            continue
        for ordering in clues:
            if target_id not in {mapping["object_id"], ordering["object_id"]}:
                continue
            text = ordering["text"]
            if not any(word in text for word in ("从左到右", "依次")) or "：" not in text:
                continue
            names = [s.strip(" 。；;\n").removesuffix("色") for s in text.split("：", 1)[1].split("、")]
            if len(names) > 1 and all(name in values for name in names):
                code = "".join(values[name] for name in names)
                if 1 <= len(code) <= 16:
                    return code, list(dict.fromkeys((mapping["clue_id"], ordering["clue_id"])))
    return None


class DeterministicMockProvider:
    provider_name = "mock"
    model_name = "deterministic-visible-v1"

    async def complete(self, messages, tools, limits=CallLimits(), *, scope="game", tool_choice="auto"):
        limits.validate()
        _validate_messages(messages, _validate_tools(tools))
        context = next((strict_json(m["content"]) for m in messages if m["role"] == "user"), None)
        if not isinstance(context, dict) or "visible_state" not in context:
            raise ProviderError("MODEL_INVALID_OUTPUT")
        state = context["visible_state"]
        inspected = set()
        candidate = None
        for message in messages:
            if message["role"] == "tool":
                result = strict_json(message["content"])
                state = result.get("visible_state", state)
                if result.get("tool") == "inspect":
                    inspected.add(result["arguments"]["object_id"])
                if result.get("candidate"):
                    candidate = result["candidate"]
        if candidate:
            return self._final(candidate["summary"], candidate["clue_refs"], candidate)
        clues = state["clues"]
        # Interface-supplied legal item targets and exposed action templates only.
        for item in state["inventory"]:
            for target in item["usable_targets"]:
                target_id = target.get("target_id") if isinstance(target, dict) else target
                if isinstance(target_id, str):
                    return self._proposal("use_item", {"item_id": item["item_id"], "target_id": target_id}, [], "可以使用已持有的道具；请确认后执行。")
        for obj in state["objects"]:
            for action in obj["actions"]:
                if action["tool"] == "take":
                    return self._proposal("take", action["arguments"], [], "可以领取当前可见的物品；请确认后执行。")
                if action["tool"] == "submit_code":
                    inferred = infer_code(clues, action["arguments"]["target_id"])
                    if inferred:
                        code, refs = inferred
                        return self._proposal("submit_code", {**action["arguments"], "code": code}, refs, "依据已发现线索中的数字与顺序，可以提交推导的密码；请确认。")
        # Explore only exposed inspect actions, without a private clue/object map.
        known_objects = {clue["object_id"] for clue in clues}
        calls = []
        for obj in state["objects"]:
            if obj["object_id"] not in known_objects | inspected and any(a["tool"] == "inspect" for a in obj["actions"]):
                calls.append({"id": f"mock_inspect_{len(inspected) + len(calls)}", "type": "function", "function": {"name": "inspect", "arguments": json.dumps({"object_id": obj["object_id"]})}})
        if calls:
            return ProviderResult(None, tuple(calls[:5]), None, self.provider_name, self.model_name, self.model_name, "tool_calls")
        # Advance toward a later room only when the public exit is unlocked.
        order = {"R1": 0, "R2": 1, "R3": 2, "EXIT": 3}
        for exit_ in state["exits"]:
            if exit_["unlocked"] and order.get(exit_["destination_id"], -1) > order.get(state["room"]["room_id"], -1):
                return self._proposal("move", {"destination_id": exit_["destination_id"]}, [], "当前出口允许通行，可以移动；请确认后执行。")
        return self._final("目前没有足够的已发现信息形成可执行建议，请查看可见对象或补充线索。", [], None)

    def _proposal(self, tool, arguments, refs, summary):
        return self._final(summary, refs, {"tool": tool, "arguments": arguments, "clue_refs": refs, "summary": summary})

    def _final(self, answer, refs, proposal):
        return ProviderResult(json.dumps({"answer": answer, "clue_refs": refs, "proposal": proposal}, ensure_ascii=False), (), None, self.provider_name, self.model_name, self.model_name, "stop")
