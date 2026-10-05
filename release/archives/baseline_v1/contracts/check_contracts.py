"""Dependency-free structural review; does not replace JSON Schema validation or QA."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
results = []

def visit(value, definitions, filename):
    if isinstance(value, dict):
        if "$ref" in value:
            target = value["$ref"]
            assert target.startswith("#/$defs/"), (filename, target)
            assert target.removeprefix("#/$defs/") in definitions, (filename, target)
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False, filename
            assert set(value.get("required", [])) == set(value["properties"]), filename
        for child in value.values():
            visit(child, definitions, filename)
    elif isinstance(value, list):
        for child in value:
            visit(child, definitions, filename)

for path in sorted(ROOT.glob("*.schema.json")):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    visit(schema, schema["$defs"], path.name)
    results.append({"file": path.name, "json_parse": "PASS", "local_refs": "PASS", "strict_objects": "PASS"})

tools = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
assert [tool["function"]["name"] for tool in tools] == ["inspect", "get_inventory", "take", "use_item", "submit_code", "move"]
for tool in tools:
    assert tool["function"]["strict"] is True
    visit(tool["function"]["parameters"], {}, "tools.json")
routes = json.loads((ROOT / "routes.json").read_text(encoding="utf-8"))
api = json.loads((ROOT / "api.schema.json").read_text(encoding="utf-8"))
assert len(routes["routes"]) == 9
assert len({(r["method"], r["path"]) for r in routes["routes"]}) == 9
for route in routes["routes"]:
    assert route["request"] is None or route["request"] in api["$defs"]
    assert route["response"] in api["$defs"]
for filename in ["api.schema.json", "tools.schema.json", "tools.json", "routes.json"]:
    value = (ROOT / filename).read_text(encoding="utf-8")
    assert not any(secret in value for secret in ['"382"', '"724"', '"231"']), filename
report = {"command": "C:\\Users\\liyh\\.conda\\envs\\1\\python.exe contracts/check_contracts.py", "exit_code": 0, "checks": results, "tool_count": len(tools), "route_count": len(routes["routes"]), "route_refs": "PASS", "public_answer_literals": "ABSENT", "limitations": ["jsonschema is unavailable in the specified interpreter; no dependencies installed", "This is structural review, not full Draft2020-12 instance validation", "No game implementation, formal QA, real model calls, or course approvals verified"]}
(ROOT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
