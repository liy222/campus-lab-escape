"""Strict data I/O and the Main-approved baseline binding."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "experiments"
BASELINE = "7821af4efe0613c20a80ea164c1dab1c0f288bab"
MANIFEST_SHA = "9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1"


def strict_load(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def load(path):
    return strict_load(Path(path).read_text(encoding="utf-8"))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def inside(path):
    path = Path(path).resolve()
    if not path.is_relative_to(HOME.resolve()):
        raise ValueError("OUTPUT_OUTSIDE_EXPERIMENTS")
    return path


def write_new(path, value):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encoded(value) + b"\n")


def canonical(data):
    return data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def baseline_binding():
    path = ROOT / "evidence/integration/baseline_v1-manifest.json"
    raw = path.read_bytes()
    if sha(raw) != MANIFEST_SHA:
        raise ValueError("UNTRUSTED_BASELINE_MANIFEST")
    manifest = strict_load(raw.decode("utf-8"))
    if manifest["commit"] != BASELINE:
        raise ValueError("BASELINE_COMMIT_MISMATCH")
    observed = {}
    for rel, record in manifest["sources"].items():
        data = (ROOT / rel).read_bytes()
        if sha(canonical(data)) != record["utf8_lf_v1_sha256"]:
            raise ValueError("BASELINE_SOURCE_CHANGED:" + rel)
        observed[rel] = {"raw_sha256": sha(data), "canonical_sha256": sha(canonical(data)),
                         "git_blob_oid": record["git_blob_oid"], "binding": record["binding"]}
    artifacts = []
    for record in manifest["evidence"]:
        data = (ROOT / record["path"]).read_bytes()
        if sha(canonical(data)) != record["artifact_utf8_lf_v1_sha256"]:
            raise ValueError("BASELINE_EVIDENCE_CHANGED:" + record["path"])
        artifacts.append({"path": record["path"], "raw_sha256": sha(data),
                          "canonical_sha256": sha(canonical(data))})
    return {"commit": BASELINE, "manifest_raw_sha256": MANIFEST_SHA, "sources": observed,
            "artifacts": artifacts, "generated_runtime_only": manifest["generated_artifacts"],
            "unbound_prior_source_records": manifest["unbound_prior_source_records"],
            "limitations": manifest["limitations"],
            "binding_method": "Main-approved manifest plus current raw/canonical hashes; no new Git verification"}


def experiment_hashes():
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p.read_bytes())
            for p in sorted(HOME.rglob("*")) if p.is_file()
            and not any(part in {"runs", "__pycache__", ".runtime", "authorizations"} for part in p.relative_to(HOME).parts)}
