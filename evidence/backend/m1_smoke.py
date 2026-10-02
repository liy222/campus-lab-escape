"""Backend owner's local smoke; independent formal QA lives under tests/."""
import json
import sqlite3
import tempfile
import argparse
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def main(output="evidence/backend/m1_smoke_result.json"):
    checks = []
    with tempfile.TemporaryDirectory(prefix="campus-backend-") as folder:
        db_path = Path(folder) / "smoke.sqlite"
        with TestClient(create_app(sqlite_path=db_path)) as client:
            def check(name, condition):
                assert condition, name
                checks.append(name)

            check("health", client.get("/api/health").status_code == 200)
            check("create strict body", client.post("/api/sessions", json={"won": True}).status_code == 422)
            first = client.post("/api/sessions", json={})
            check("create status", first.status_code == 201)
            one = first.json()["data"]
            two = client.post("/api/sessions", json={}).json()["data"]
            sid, token, state = one["session_id"], one["token"], one["visible_state"]
            headers = {"X-Session-Token": token}
            prefix = "/api/sessions/" + sid
            check("initial visibility", state["revision"] == 0 and state["clues"] == [] and state["inventory"] == [] and len(state["objects"]) == 3)
            check("initial no answer", "382" not in json.dumps(state) and "r1_note_clue" not in json.dumps(state))
            forbidden = client.get("/api/sessions/" + two["session_id"] + "/state", headers=headers)
            check("cross-session forbidden", forbidden.status_code == 403 and forbidden.json()["visible_state"] is None)
            check("missing token forbidden", client.get(prefix + "/state").status_code == 403)
            counter = 0
            def act(tool, arguments, request_id=None, override=None):
                nonlocal counter, state
                counter += 1
                request = {"request_id": request_id or f"smoke_{counter}", "revision": state["revision"], "generation": state["generation"], "tool": tool, "arguments": arguments}
                if override:
                    request.update(override)
                result = client.post(prefix + "/actions", json=request, headers=headers)
                payload = result.json()
                next_state = payload["data"]["visible_state"] if payload["ok"] else payload["visible_state"]
                if next_state:
                    state = next_state
                return result, request
            result, _ = act("take", {"item_id": "access_card"})
            check("hidden card denied", result.json()["error"]["code"] == "NOT_VISIBLE" and state["revision"] == 0)
            result, _ = act("use_item", {"item_id": "access_card", "target_id": "r1_door"})
            check("missing card denied", result.json()["error"]["code"] == "PRECONDITION_FAILED" and state["revision"] == 0)
            result, bad_request = act("submit_code", {"target_id": "r1_cabinet", "code": "000"}, request_id="wrong")
            check("wrong code no progress", result.json()["error"]["code"] == "WRONG_CODE" and state["revision"] == 0 and "382" not in result.text)
            repeated = client.post(prefix + "/actions", json=bad_request, headers=headers)
            check("failure replay immutable", repeated.json()["event_id"] == result.json()["event_id"])
            for label, tool, arguments, override in [
                ("extra result rejected", "inspect", {"object_id": "r1_note"}, {"won": True}),
                ("extra argument rejected", "inspect", {"object_id": "r1_note", "flags": {}}, None),
                ("boolean revision rejected", "inspect", {"object_id": "r1_note"}, {"revision": False}),
                ("integer code rejected", "submit_code", {"target_id": "r1_cabinet", "code": 382}, None),
                ("unknown tool rejected", "shell", {}, None),
            ]:
                result, _ = act(tool, arguments, override=override)
                check(label, result.status_code == 422 and state["revision"] == 0)
            result, request = act("inspect", {"object_id": "r1_note"}, request_id="read_note")
            check("first inspect revision", state["revision"] == 1 and state["clues"][0]["clue_id"] == "r1_note_clue")
            replay = client.post(prefix + "/actions", json=request, headers=headers)
            check("success replay", replay.json()["data"]["replayed"] and replay.json()["data"]["receipt"] == result.json()["data"]["receipt"] and state["revision"] == 1)
            changed_request = dict(request, arguments={"object_id": "r1_cabinet"})
            check("same id conflict", client.post(prefix + "/actions", json=changed_request, headers=headers).json()["error"]["code"] == "REQUEST_ID_CONFLICT")
            result, _ = act("inspect", {"object_id": "r1_cabinet"}, override={"revision": 0})
            check("stale version denied", result.json()["error"]["code"] == "STALE_STATE" and state["revision"] == 1)
            act("inspect", {"object_id": "r1_note"})
            check("repeat inspect unchanged", state["revision"] == 1)
            act("inspect", {"object_id": "r1_cabinet"})
            act("submit_code", {"target_id": "r1_cabinet", "code": "382"})
            check("open cabinet card visible", "access_card" in [obj["object_id"] for obj in state["objects"]])
            act("take", {"item_id": "access_card"})
            result, _ = act("take", {"item_id": "access_card"})
            check("duplicate card denied", result.json()["error"]["code"] == "ALREADY_TAKEN" and len(state["inventory"]) == 1)
            act("use_item", {"item_id": "access_card", "target_id": "r1_door"})
            act("move", {"destination_id": "R2"})
            check("R1 completed intermediate R2", state["room"]["room_id"] == "R2" and state["revision"] == 6 and state["objects"] == [])
            result, _ = act("take", {"item_id": "fuse"})
            check("M1 later actions denied", result.json()["error"]["code"] == "NOT_VISIBLE")
            other = client.get("/api/sessions/" + two["session_id"] + "/state", headers={"X-Session-Token": two["token"]}).json()["data"]["visible_state"]
            check("second session isolated", other["revision"] == 0 and not other["clues"] and not other["inventory"])
            with closing(sqlite3.connect(db_path)) as connection:
                events = connection.execute("SELECT result_json,request_json FROM events").fetchall()
                text = json.dumps(events)
                check("no capability persisted in events", token not in text and two["token"] not in text)
                check("six state-changing commits", connection.execute("SELECT count(*) FROM events WHERE session_id=? AND outcome='committed' AND revision_after>revision_before", (sid,)).fetchone()[0] == 6)
            with TestClient(create_app(sqlite_path=db_path)) as restored_client:
                persisted = restored_client.get(prefix + "/state", headers=headers).json()["data"]["visible_state"]
            check("SQLite survives app recreation", persisted == state)
        result = {"scope": "Backend owner local M1 smoke, not independent QA", "checks": checks, "passed": len(checks), "limitations": ["R2 is an intermediate scene; T09 gameplay, controls, saves and AI pending", "No browser acceptance or real model calls performed"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/backend/m1_smoke_result.json")
    main(parser.parse_args().output)
