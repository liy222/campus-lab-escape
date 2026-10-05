"""Isolated, read-only v1 judge. No Provider, ledger or arbitrary path input."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "release/archives/baseline_v1"
INDEX = ROOT / "evidence/integration/E1-source-archive-20261005.json"
INDEX_SHA = "0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6"
MODULES = ["backend/__init__.py", "backend/app/__init__.py", "backend/app/domain/__init__.py",
           "backend/app/domain/models.py", "backend/app/domain/rules.py", "experiments/__init__.py",
           "experiments/common.py", "experiments/judger.py"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_KEY")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE")))


def main():
    if len(sys.argv) != 1:
        raise ValueError("WORKER_ARGUMENTS_FORBIDDEN")
    data = sys.stdin.read(1_000_001)
    if len(data.encode("utf8")) > 1_000_000:
        raise ValueError("WORKER_INPUT_LIMIT")
    request = strict(data)
    if not isinstance(request, dict) or set(request) != {"requests"} or not isinstance(request["requests"], list) or not 1 <= len(request["requests"]) <= 72:
        raise ValueError("WORKER_SHAPE")
    samples = {"C10"}  # Fixed in-memory v1 key-retention dependency probe.
    for item in request["requests"]:
        if not isinstance(item, dict) or set(item) != {"sample_id", "content"} or item["sample_id"] not in {f"C{n:02d}" for n in range(1, 13)} or not isinstance(item["content"], str) or len(item["content"].encode("utf8")) > 100_000:
            raise ValueError("WORKER_ITEM")
        samples.add(item["sample_id"])
    if digest(INDEX) != INDEX_SHA:
        raise ValueError("ARCHIVE_INDEX_CHANGED")
    records = strict(INDEX.read_text(encoding="utf8"))["sources"]
    dependencies = MODULES + ["experiments/schema.json"]
    for sample in sorted(samples):
        dependencies += [f"experiments/fixtures/{sample}.json", f"experiments/ground_truth/{sample}.json"]
    allowed, verified = {Path(__file__).resolve()}, {}
    for rel in dependencies:
        record = records[rel]
        path = (ROOT / record["archive_path"]).resolve()
        if path != (ARCHIVE / rel).resolve() or not path.is_relative_to(ARCHIVE.resolve()) or digest(path) != record["raw_sha256"]:
            raise ValueError("ARCHIVE_DEPENDENCY_CHANGED")
        allowed.add(path)
        verified[rel] = {"path": str(path), "raw_sha256": digest(path)}
    sys.dont_write_bytecode = True
    sys.path = [str(ARCHIVE)] + [p for p in sys.path if p and not Path(p).resolve().is_relative_to(ROOT)]

    def audit(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system"}:
            raise PermissionError("WORKER_EXTERNAL_ACTION_FORBIDDEN")
        if event == "open" and isinstance(args[0], str):
            path = Path(args[0]).resolve()
            mode, flags = args[1], args[2] if len(args) > 2 else 0
            if isinstance(mode, str) and any(c in mode for c in "wax+") or isinstance(flags, int) and flags & (1 | 2 | 64 | 512 | 1024):
                raise PermissionError("WORKER_WRITE_FORBIDDEN")
            if path.is_relative_to(ROOT) and path not in allowed:
                raise PermissionError("WORKER_REPOSITORY_READ_FORBIDDEN")
    sys.addaudithook(audit)
    from experiments.judger import judge
    from experiments.common import load
    from backend.app.domain import models, rules
    import experiments.judger as judger
    import experiments.common as common
    module_facts = {}
    for name, module, rel in [("models", models, "backend/app/domain/models.py"), ("rules", rules, "backend/app/domain/rules.py"),
                              ("judger", judger, "experiments/judger.py"), ("common", common, "experiments/common.py")]:
        path = Path(module.__file__).resolve()
        if path != (ARCHIVE / rel).resolve() or digest(path) != records[rel]["raw_sha256"]:
            raise ValueError("WORKER_IMPORT_CONTAMINATION")
        module_facts[name] = {"file": str(path), "raw_sha256": digest(path)}
    if rules.LEVEL_VERSION != "1.0.0" or common.ROOT.resolve() != ARCHIVE.resolve():
        raise ValueError("WORKER_NOT_V1")
    if any(name.startswith("backend.app.ai") for name in sys.modules):
        raise ValueError("WORKER_AI_IMPORT_FORBIDDEN")
    truth = load(ARCHIVE / "experiments/ground_truth/C10.json")
    probe_state = models.GameState.model_validate(truth["state"])
    advanced, _ = rules.apply_action(probe_state.model_copy(deep=True), "use_item", {"item_id": "emergency_key", "target_id": "r2_door"})
    if "emergency_key" not in advanced.inventory or not advanced.flags["r3_unlocked"]:
        raise ValueError("WORKER_V1_KEY_SEMANTICS_CHANGED")
    results = [judge(item["content"], load(ARCHIVE / "experiments/fixtures" / (item["sample_id"] + ".json"))) for item in request["requests"]]
    print(json.dumps({"results": results, "dependencies": verified, "modules": module_facts, "level_version": rules.LEVEL_VERSION,
                      "provider_imported": False, "canonical_product_imported": False, "ledger_accessed": False,
                      "v1_key_retention_probe": True, "probe_only_memory_state": True},
                     ensure_ascii=False, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        raise SystemExit(1)
