"""Finite paired plans; constructing inputs never reads private truth or .env."""
from copy import deepcopy

from .common import BASELINE, HOME, ROOT, encoded, experiment_hashes, load, sha
from .context import VERSION, VARIANTS, build, facts


def input_for(sample, variant):
    tools = load(ROOT / "contracts/tools.json")
    messages = [{"role": "system", "content": (HOME / "prompt.txt").read_text(encoding="utf-8")},
                {"role": "user", "content": encoded(build(sample, variant)).decode("utf-8")}]
    config = load(HOME / "config.json")
    wire_tools = deepcopy(tools)
    for tool in wire_tools:
        tool["function"].pop("strict", None)
    payload = {"model": config["model"], "messages": messages,
               "max_tokens": 1000, "thinking": {"type": "disabled"}, "stream": False}
    payload.update(tools=wire_tools, tool_choice="none")
    # Match the exact Provider wire serializer (insertion order, not sorted).
    import json
    wire_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    bound = len(wire_bytes) * 4 + 8192
    return messages, tools, {"input_hash": sha(wire_bytes), "payload_utf8_bytes": len(wire_bytes),
                             "input_token_bound": bound, "reservation_units": bound * 2000 + 1000 * 8000,
                             "visible_facts_hash": sha(facts(build(sample, variant)))}


def frozen():
    config = load(HOME / "config.json")
    expected = {"provider": "deepseek", "model": "deepseek-flash", "base_url": "https://api.deepseek.com",
                "max_tokens": 1000, "timeout_seconds": 20, "tool_choice": "none",
                "thinking": {"type": "disabled"}, "stream": False, "formal_repeats": 3,
                "temperature": {"sent": False, "value": None}, "seed": {"sent": False, "value": None},
                "pilot_samples": ["C02", "C06", "C12"], "context_version": VERSION,
                "max_consecutive_failures": 2, "prompt_version": "e1-next-action-v1", "judger_version": "e1-judger-v1"}
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("UNFROZEN_OR_UNAPPROVED_CONFIG")
    return {"config": config, "source_hashes": experiment_hashes(), "config_hash": sha(config),
            "prompt_hash": sha((HOME / "prompt.txt").read_bytes()), "schema_hash": sha((HOME / "schema.json").read_bytes()),
            "tools_hash": sha((ROOT / "contracts/tools.json").read_bytes())}


def make_plan(phase):
    if phase not in {"pilot", "formal"}:
        raise ValueError("INVALID_PHASE")
    freeze = frozen()
    config = freeze["config"]
    rows = []
    repeats = 1 if phase == "pilot" else 3
    for repeat in range(1, repeats + 1):
        samples = config["pilot_samples"] if phase == "pilot" else [f"C{n:02d}" for n in range(1, 13)]
        if repeat == 2:
            samples = list(reversed(samples))
        elif repeat == 3:
            samples = samples[4:] + samples[:4]
        for sample_id in samples:
            sample = load(HOME / "fixtures" / (sample_id + ".json"))
            variants = VARIANTS if (int(sample_id[1:]) + repeat) % 2 else tuple(reversed(VARIANTS))
            for variant in variants:
                _, _, hashes = input_for(sample, variant)
                rows.append({"row_id": f"{phase}-{sample_id}-{variant}-{repeat}", "sample_id": sample_id,
                             "phase": phase, "variant": variant, "repeat": repeat, "order": len(rows) + 1,
                             "commit": BASELINE, "level_version": sample["level_version"], "schema_version": sample["schema_version"],
                             "model": config["model"], "provider": config["provider"], "base_url": config["base_url"],
                             "requested_model": config["model"], "reported_model": None,
                             "prompt_version": config["prompt_version"], "judger_version": config["judger_version"],
                             "context_version": VERSION, **hashes, "status": "not_called", "error": "PLANNED_ONLY",
                             "start_time": None, "end_time": None, "latency_seconds": None,
                             "response": None, "tool_proposal": None, "usage": None, "usage_known": False,
                             "call_id": None, "actually_called": False, "provider_invoked": False,
                             "response_received": False, "upstream_delivery_known": False, "local_attempted": False,
                             "http_status_code": None, "normalized_response_received": False,
                             "charged_upper_cny": None, "legal": None, "correct": None,
                             "reference_valid": None, "reference_sufficient": None})
    return {"phase": phase, "planned": len(rows), "freeze": freeze, "rows": rows,
            "controls": {"temperature": config["temperature"], "seed": config["seed"],
                         "paid_attempt_definition": "A shared-ledger reservation; upstream delivery is separate",
                         "retry": False, "suggestions_executed": False}}
