"""Actual local adapter checks and optional two-request synthetic real probe.

Development verification only; does not exercise game endpoints or claim QA.
Evidence deliberately excludes credentials, raw exception text and raw API bodies.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import httpx

from .budget import BudgetError, BudgetLedger, PROJECT_ROOT, cost_units
from .provider import CallLimits, DeepSeekConfig, DeepSeekProvider, MockProvider, ProviderError, ProviderResult, tool_result_message, validate_final_content

TOOLS = [{"type":"function","function":{"name":"get_inventory","description":"Read a fictional probe inventory.","strict":True,"parameters":{"type":"object","properties":{},"required":[],"additionalProperties":False}}}]
MESSAGE = [{"role":"user","content":"This is a synthetic API probe with no game or private data. Call get_inventory once."}]
CALL = {"id":"call_probe_1","type":"function","function":{"name":"get_inventory","arguments":"{}"}}


def response(*, calls=None, usage=True, content="Synthetic inventory is empty.", finish=None):
    calls = calls or []
    body = {"model":"deepseek-flash","choices":[{"finish_reason":finish or ("tool_calls" if calls else "stop"),"message":{"role":"assistant","content":None if calls else content,"tool_calls":calls}}]}
    if usage:
        body["usage"] = {"prompt_tokens":100,"completion_tokens":20,"total_tokens":120,"prompt_cache_hit_tokens":10,"prompt_cache_miss_tokens":90}
    return body


async def local_checks() -> list[dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="provider-local-") as temp:
        root = Path(temp)
        for name, expected in [("normal","COMPLETED"),("timeout","MODEL_TIMEOUT"),("auth","MODEL_AUTH_ERROR"),("service","MODEL_UNAVAILABLE"),("rate_limit","MODEL_RATE_LIMIT"),("malformed","MODEL_INVALID_OUTPUT"),("invalid_tool","MODEL_INVALID_OUTPUT"),("extra_arguments","MODEL_INVALID_OUTPUT"),("duplicate_arguments","MODEL_INVALID_OUTPUT"),("truncated","MODEL_INVALID_OUTPUT"),("missing_usage","COMPLETED"),("missing_credential","MISSING_CREDENTIALS"),("model_mismatch","UNAPPROVED_REPORTED_MODEL"),("token_overrun","TOKEN_BOUND_EXCEEDED")]:
            ledger = BudgetLedger(root / (name + ".sqlite"))
            requests = []
            async def handler(request):
                payload = json.loads(request.content)
                assert payload["thinking"] == {"type":"disabled"} and payload["stream"] is False and payload["max_tokens"] <= 1000
                assert "strict" not in payload["tools"][0]["function"]
                requests.append(payload)
                if name == "timeout":
                    await asyncio.sleep(0.1)
                if name in {"auth","service","rate_limit"}:
                    return httpx.Response({"auth":401,"service":503,"rate_limit":429}[name],json={"error":"synthetic_error_do_not_log"})
                if name == "malformed":
                    return httpx.Response(200,content=b"not JSON")
                if name == "normal":
                    if len(requests) == 1:
                        return httpx.Response(200,json=response(calls=[{**CALL,"index":0}]))
                    assert payload["messages"][-2]["tool_calls"][0]["id"] == payload["messages"][-1]["tool_call_id"]
                    assert payload["messages"][-1]["content"] == '{"inventory":[]}'
                body = response(usage=name != "missing_usage",finish="length" if name == "truncated" else None)
                if name in {"invalid_tool","extra_arguments","duplicate_arguments"}:
                    call = json.loads(json.dumps(CALL))
                    if name == "invalid_tool": call["function"]["name"] = "shell"
                    if name == "extra_arguments": call["function"]["arguments"] = '{"extra":true}'
                    if name == "duplicate_arguments": call["function"]["arguments"] = '{"x":1,"x":2}'
                    body = response(calls=[call])
                if name == "model_mismatch": body["model"] = "deepseek-v4-pro"
                if name == "token_overrun": body["usage"].update(completion_tokens=33,total_tokens=133)
                return httpx.Response(200,json=body)
            provider = DeepSeekProvider(DeepSeekConfig("" if name == "missing_credential" else "synthetic-key"),ledger,transport=httpx.MockTransport(handler))
            try:
                result = await provider.complete(MESSAGE,TOOLS,CallLimits(32,0.02 if name == "timeout" else 1),scope="local_check")
                if name == "normal":
                    messages = MESSAGE + [result.assistant_message(), tool_result_message(result.tool_calls[0]["id"],{"inventory":[]})]
                    result = await provider.complete(messages,TOOLS,CallLimits(32,1),scope="local_check",tool_choice="none")
                actual = "COMPLETED"
                if name == "missing_usage": assert result.usage is None
            except ProviderError as error:
                actual = error.code
            snapshot = ledger.snapshot()
            passed = actual == expected
            if name in {"timeout","auth","service","rate_limit","malformed","missing_usage"}:
                passed = passed and snapshot["unknown_or_pending_calls"] == 1 and snapshot["charged_upper_cny"] > 0
            if name in {"model_mismatch","token_overrun"}: passed = passed and snapshot["frozen"]
            if name == "missing_credential": passed = passed and snapshot["calls"] == 0
            results.append({"scenario":name,"expected":expected,"actual":actual,"http_requests":len(requests),"ledger":snapshot,"passed":passed,"real_api_called":False})
        # Two truly separate Python processes contend for the same final budget.
        dbpath = root / "concurrency.sqlite"
        code = "from pathlib import Path; import sys; from backend.app.ai.budget import BudgetLedger,BudgetError; b=BudgetLedger(Path(sys.argv[1]),cap_units=1000);\ntry: b.reserve(sys.argv[2],600); print('RESERVED')\nexcept BudgetError as e: print(e.code)"
        procs = [subprocess.Popen([sys.executable,"-B","-X","utf8","-c",code,str(dbpath),scope],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=PROJECT_ROOT) for scope in ("game","experiments")]
        outputs = [p.communicate(timeout=20) for p in procs]
        statuses = sorted(o[0].strip() for o in outputs)
        snap = BudgetLedger(dbpath,cap_units=1000).snapshot()
        results.append({"scenario":"cross_process_budget","actual":statuses,"exit_codes":[p.returncode for p in procs],"ledger":snap,"passed":statuses == ["AI_BUDGET_EXHAUSTED","RESERVED"] and all(p.returncode == 0 and not o[1] for p,o in zip(procs,outputs))})
        ledger = BudgetLedger(root / "idempotence.sqlite")
        ident = ledger.reserve("game",1000,call_id="stable_call")
        ledger.settle(ident,prompt_tokens=0,completion_tokens=0)
        ledger.settle(ident,prompt_tokens=0,completion_tokens=0)
        try: ledger.reserve("game",1000,call_id="stable_call")
        except BudgetError as error: duplicate = error.code
        results.append({"scenario":"settlement_and_call_id","passed":duplicate == "DUPLICATE_CALL_ID" and ledger.snapshot()["calls"] == 1})
        pending = ledger.reserve("experiments",1000)
        reopened = BudgetLedger(root / "idempotence.sqlite")
        results.append({"scenario":"crash_pending_reservation","passed":reopened.snapshot()["unknown_or_pending_calls"] == 1 and reopened.snapshot()["charged_upper_cny"] == 0.000001})
        probe_budget = BudgetLedger(root / "probe_cap.sqlite")
        probe_budget.reserve("probe",100_000_000)
        probe_budget.reserve("probe",100_000_000)
        try: probe_budget.reserve("probe",1)
        except BudgetError as error: probe_limit = error.code
        results.append({"scenario":"probe_sub_budget","passed":probe_limit == "PROBE_BUDGET_EXHAUSTED" and probe_budget.snapshot()["charged_upper_cny"] == 0.2})
        final = '{"answer":"Inspect a visible object.","clue_refs":[],"proposal":null}'
        validate_final_content(final,set())
        try: validate_final_content('{"answer":"x","clue_refs":["unknown"],"proposal":null}',set())
        except ProviderError as error: invalid = error.code
        mock = MockProvider([ProviderResult(final,(),None,"mock","scripted-fixture","scripted-fixture","stop")])
        mock_result = await mock.complete(MESSAGE,TOOLS)
        results.append({"scenario":"replaceable_mock_and_final_refs","passed":mock_result.usage is None and invalid == "MODEL_INVALID_OUTPUT"})
    return results


class PublicText(HTMLParser):
    def __init__(self):
        super().__init__(); self.items = []
    def handle_data(self, data): self.items.append(data)


def official_sources() -> list[dict]:
    urls = ["https://api-docs.deepseek.com/zh-cn/quick_start/pricing/","https://api-docs.deepseek.com/api/create-chat-completion","https://api-docs.deepseek.com/guides/tool_calls","https://api-docs.deepseek.com/updates"]
    checks = [["deepseek-flash","DeepSeek-V4.1-Flash","2元","8元"],["thinking","disabled","tool_call_id","prompt_cache_hit_tokens"],["https://api.deepseek.com/beta","minLength","maxLength"],["V4.1","Flash"]]
    output = []
    for url, markers in zip(urls,checks):
        try:
            fetched = httpx.get(url,timeout=20,follow_redirects=True)
            parsed = PublicText(); parsed.feed(fetched.text)
            text = " ".join(parsed.items)
            output.append({"url":url,"final_url":str(fetched.url),"http_status":fetched.status_code,"sha256":hashlib.sha256(fetched.content).hexdigest(),"markers_found":{m:m in text for m in markers},"fetched_at":datetime.now(timezone.utc).isoformat()})
        except httpx.HTTPError:
            output.append({"url":url,"status":"PUBLIC_DOCUMENT_FETCH_FAILED"})
    return output


async def real_probe() -> dict:
    config = DeepSeekConfig.from_environment()
    if not config.api_key.strip():
        return {"status":"blocked","reason":"MISSING_CREDENTIALS","real_api_called":False,"calls":[],"usage":None,"cost_upper_cny":None}
    ledger = BudgetLedger()
    before = ledger.snapshot()
    provider = DeepSeekProvider(config,ledger)
    calls = []
    messages = MESSAGE
    # Each request reserves < CNY .1; max two calls, no paid retries.
    for index in range(2):
        if ledger.snapshot()["charged_upper_cny"] - before["charged_upper_cny"] >= 0.1:
            return {"status":"stopped","reason":"PROBE_SUB_BUDGET","real_api_called":bool(calls),"calls":calls,"ledger":ledger.snapshot()}
        try:
            result = await provider.complete(messages,TOOLS,CallLimits(128,20),scope="probe",tool_choice={"type":"function","function":{"name":"get_inventory"}} if index == 0 else "none")
            calls.append({"ordinal":index+1,"provider":result.provider,"requested_model":result.requested_model,"reported_model":result.reported_model,"finish_reason":result.finish_reason,"usage":result.usage,"cost_upper_cny":result.cost_upper_cny,"tool_names":[c["function"]["name"] for c in result.tool_calls],"call_id":result.call_id})
            if index == 0:
                if len(result.tool_calls) != 1:
                    raise ProviderError("MODEL_INVALID_OUTPUT")
                messages = messages + [result.assistant_message(),tool_result_message(result.tool_calls[0]["id"],{"inventory":[],"source":"synthetic_fixture"})]
        except ProviderError as error:
            return {"status":"failed","reason":error.code,"real_api_called":bool(calls) or error.call_id is not None,"calls":calls,"sanitized_response_metadata":provider.last_response_metadata,"ledger":ledger.snapshot(),"billing_verified":False}
    return {"status":"completed","real_api_called":True,"calls":calls,"ledger":ledger.snapshot(),"incremental_cost_upper_cny":ledger.snapshot()["charged_upper_cny"]-before["charged_upper_cny"],"billing_verified":False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real",action="store_true",help="One synthetic two-request probe; credentials and approved budget required.")
    parser.add_argument("--official-docs",action="store_true")
    parser.add_argument("--output",type=Path,default=Path("evidence/provider"))
    args = parser.parse_args()
    report = {"task":"T04","scope":"isolated provider development checks; no game integration or independent QA","executed_at":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),"executable":sys.executable,"local_checks":asyncio.run(local_checks())}
    if args.official_docs: report["official_sources"] = official_sources()
    report["real_probe"] = asyncio.run(real_probe()) if args.real else {"status":"not_requested","real_api_called":False}
    report["local_checks_passed"] = all(r["passed"] for r in report["local_checks"])
    report["real_probe_passed"] = report["real_probe"]["status"] == "completed" if args.real else None
    report["overall_passed"] = report["local_checks_passed"] and report["real_probe_passed"] if args.real else report["local_checks_passed"]
    code = 0 if report["overall_passed"] else 1
    report["exit_code"] = code
    run = args.output / datetime.now(timezone.utc).strftime("adapter-%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True,exist_ok=False)
    (run / "report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines = [f"{r['scenario']}: passed={r['passed']}" for r in report["local_checks"]]
    lines.extend(["real_probe="+report["real_probe"]["status"],f"exit_code={code}",f"evidence={run / 'report.json'}"])
    output = "\n".join(lines)+"\n"
    (run / "output.txt").write_text(output,encoding="utf-8")
    print(output,end="")
    return code


if __name__ == "__main__": raise SystemExit(main())
