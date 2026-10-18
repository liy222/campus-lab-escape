"""Isolated text-only Provider adapter. It never loads game state or executes tools."""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx
from jsonschema import Draft202012Validator

from .budget import BudgetError, BudgetLedger, PROJECT_ROOT, cost_units


class ProviderError(Exception):
    def __init__(self, code: str, *, call_id: str | None = None):
        self.code, self.call_id = code, call_id
        super().__init__(code)


def strict_json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))


@dataclass(frozen=True)
class CallLimits:
    max_tokens: int = 1000
    timeout_seconds: float = 20.0
    json_mode: bool = False

    def validate(self):
        if type(self.json_mode) is not bool or type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 1000 or not 0 < self.timeout_seconds <= 20:
            raise ProviderError("INVALID_CALL_LIMITS")


@dataclass(frozen=True)
class ProviderResult:
    content: str | None
    tool_calls: tuple[dict, ...]
    usage: dict | None
    provider: str
    requested_model: str
    reported_model: str
    finish_reason: str
    call_id: str | None = None
    cost_upper_cny: float | None = None

    def assistant_message(self) -> dict:
        message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = copy.deepcopy(list(self.tool_calls))
        return message


class Provider(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict], limits: CallLimits = CallLimits(), *, scope: str = "game", tool_choice: str | dict = "auto") -> ProviderResult: ...


def tool_result_message(tool_call_id: str, result: dict) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", tool_call_id) or not isinstance(result, dict):
        raise ProviderError("INVALID_TOOL_RESULT")
    return {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)}


def _validate_tools(tools: list[dict]) -> dict[str, dict]:
    if not isinstance(tools, list) or len(tools) > 6:
        raise ProviderError("INVALID_TOOLS")
    schemas = {}
    for tool in tools:
        if not isinstance(tool, dict) or set(tool) != {"type", "function"} or tool["type"] != "function":
            raise ProviderError("INVALID_TOOLS")
        f = tool["function"]
        if not isinstance(f, dict) or set(f) - {"name", "description", "parameters", "strict"} or not {"name", "parameters"} <= set(f):
            raise ProviderError("INVALID_TOOLS")
        name = f["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", name) or name in schemas:
            raise ProviderError("INVALID_TOOLS")
        try:
            Draft202012Validator.check_schema(f["parameters"])
        except Exception:
            raise ProviderError("INVALID_TOOLS") from None
        schemas[name] = f["parameters"]
    return schemas


def _validate_messages(messages: list[dict], schemas: dict[str, dict]) -> None:
    if not isinstance(messages, list) or not 1 <= len(messages) <= 100:
        raise ProviderError("INVALID_MESSAGES")
    pending = set()
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant", "tool"}:
            raise ProviderError("INVALID_MESSAGES")
        role = message["role"]
        allowed = {"role", "content"} | ({"tool_calls"} if role == "assistant" else {"tool_call_id"} if role == "tool" else set())
        if set(message) - allowed or "content" not in message or not (isinstance(message["content"], str) or role == "assistant" and message["content"] is None):
            raise ProviderError("INVALID_MESSAGES")
        if role == "tool":
            ident = message.get("tool_call_id")
            if not isinstance(ident, str):
                raise ProviderError("INVALID_MESSAGES")
            if ident not in pending:
                raise ProviderError("INVALID_MESSAGES")
            pending.remove(ident)
        else:
            if pending:
                raise ProviderError("INVALID_MESSAGES")
            if message.get("tool_calls"):
                pending = {t["id"] for t in _validate_calls(message["tool_calls"], schemas)}
    if pending:
        raise ProviderError("MISSING_TOOL_RESULT")


def _validate_calls(calls: Any, schemas: dict[str, dict]) -> tuple[dict, ...]:
    if not isinstance(calls, list) or len(calls) > 6:
        raise ProviderError("MODEL_INVALID_OUTPUT")
    ids = set()
    for ordinal, call in enumerate(calls):
        if not isinstance(call, dict) or not {"id", "type", "function"} <= set(call) or set(call) - {"id", "type", "function", "index"} or call["type"] != "function":
            raise ProviderError("MODEL_INVALID_OUTPUT")
        # Observed official non-stream response includes the documented stream
        # index too. Validate it, then omit it from normalized history.
        if "index" in call and (type(call["index"]) is not int or call["index"] != ordinal):
            raise ProviderError("MODEL_INVALID_OUTPUT")
        ident, f = call["id"], call["function"]
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", ident) or ident in ids or not isinstance(f, dict) or set(f) != {"name", "arguments"}:
            raise ProviderError("MODEL_INVALID_OUTPUT")
        ids.add(ident)
        if not isinstance(f["name"], str) or f["name"] not in schemas or not isinstance(f["arguments"], str) or len(f["arguments"].encode("utf-8")) > 16384:
            raise ProviderError("MODEL_INVALID_OUTPUT")
        try:
            arguments = strict_json(f["arguments"])
            Draft202012Validator(schemas[f["name"]]).validate(arguments)
        except Exception:
            raise ProviderError("MODEL_INVALID_OUTPUT") from None
    normalized = copy.deepcopy(calls)
    for call in normalized:
        call.pop("index", None)
    return tuple(normalized)


def validate_final_content(content: str | None, discovered_clue_ids: set[str], tools: list[dict] | None = None) -> dict:
    """T14 may use this only after tools end; no dynamic action authorization here."""
    try:
        value = strict_json(content or "")
        if not isinstance(value, dict) or set(value) != {"answer", "clue_refs", "proposal"}:
            raise ValueError()
        if not isinstance(value["answer"], str) or not 1 <= len(value["answer"]) <= 4000 or not isinstance(value["clue_refs"], list):
            raise ValueError()
        refs = value["clue_refs"]
        if any(not isinstance(r, str) or r not in discovered_clue_ids for r in refs) or len(refs) != len(set(refs)):
            raise ValueError()
        proposal = value["proposal"]
        if proposal is not None:
            if not isinstance(proposal, dict) or set(proposal) != {"tool", "arguments", "clue_refs", "summary"} or proposal["tool"] not in {"take", "use_item", "submit_code", "move"} or not isinstance(proposal["arguments"], dict) or not isinstance(proposal["clue_refs"], list) or any(not isinstance(r, str) or r not in discovered_clue_ids for r in proposal["clue_refs"]) or not isinstance(proposal["summary"], str) or not 1 <= len(proposal["summary"]) <= 4000:
                raise ValueError()
            schemas = _validate_tools(tools or [])
            if proposal["tool"] not in schemas:
                raise ValueError()
            Draft202012Validator(schemas[proposal["tool"]]).validate(proposal["arguments"])
            if len(proposal["clue_refs"]) != len(set(proposal["clue_refs"])):
                raise ValueError()
        return value
    except Exception:
        raise ProviderError("MODEL_INVALID_OUTPUT") from None


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str = field(repr=False)
    model: str = "deepseek-flash"
    base_url: str = "https://api.deepseek.com"

    @classmethod
    def from_environment(cls, env_file: Path = PROJECT_ROOT / ".env"):
        values = {}
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8-sig").splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip() in {"MODEL_API_KEY", "MODEL_NAME", "MODEL_BASE_URL"}:
                    values[key.strip()] = value.strip().strip("\"'")
        for name in ("MODEL_API_KEY", "MODEL_NAME", "MODEL_BASE_URL"):
            if name in os.environ:
                values[name] = os.environ[name]
        return cls(values.get("MODEL_API_KEY", ""), values.get("MODEL_NAME") or "deepseek-flash", values.get("MODEL_BASE_URL") or "https://api.deepseek.com")


class DeepSeekProvider:
    def __init__(self, config: DeepSeekConfig, ledger: BudgetLedger | None = None, *, transport: httpx.AsyncBaseTransport | None = None):
        if config.model != "deepseek-flash" or config.base_url.rstrip("/") != "https://api.deepseek.com":
            raise ProviderError("UNAPPROVED_PROVIDER_CONFIG")
        self.config, self.ledger, self.transport = config, ledger or BudgetLedger(), transport
        self.last_response_metadata = None
        # Production calls cannot choose a fresh or less restrictive ledger.
        if transport is None and self.ledger.path != (PROJECT_ROOT / "data" / "ai-budget.sqlite").resolve():
            raise ProviderError("UNAPPROVED_BUDGET_LEDGER")

    async def complete(self, messages, tools, limits=CallLimits(), *, scope="game", tool_choice="auto"):
        self.last_response_metadata = None
        limits.validate()
        if not self.config.api_key.strip():
            raise ProviderError("MISSING_CREDENTIALS")
        schemas = _validate_tools(tools)
        _validate_messages(messages, schemas)
        if tool_choice not in ("auto", "none", "required"):
            if not isinstance(tool_choice, dict) or tool_choice.get("type") != "function" or set(tool_choice) != {"type", "function"} or not isinstance(tool_choice["function"], dict) or set(tool_choice["function"]) != {"name"} or tool_choice["function"]["name"] not in schemas:
                raise ProviderError("INVALID_TOOL_CHOICE")
        # strict:true requires /beta and a restricted schema subset. Keep the
        # approved stable URL and enforce the FULL contract locally instead.
        wire_tools = copy.deepcopy(tools)
        for tool in wire_tools:
            tool["function"].pop("strict", None)
        payload = {"model": self.config.model, "messages": copy.deepcopy(messages), "max_tokens": limits.max_tokens, "thinking": {"type": "disabled"}, "stream": False}
        if limits.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if wire_tools:
            payload.update(tools=wire_tools, tool_choice=tool_choice)
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        # Text-only UTF-8 byte bound with 4x safety factor plus 8192 framing
        # tokens; full outgoing schemas/history included, never hidden data.
        input_bound = len(encoded) * 4 + 8192
        if input_bound > 1_000_000:
            raise ProviderError("INPUT_TOO_LARGE")
        try:
            call_id = self.ledger.reserve(scope, cost_units(input_bound, limits.max_tokens))
        except BudgetError as error:
            raise ProviderError(error.code) from None
        settled = False
        try:
            async with httpx.AsyncClient(transport=self.transport, follow_redirects=False, timeout=limits.timeout_seconds, trust_env=False) as client:
                async with asyncio.timeout(limits.timeout_seconds):
                    response = await client.post(self.config.base_url.rstrip("/") + "/chat/completions", content=encoded, headers={"Authorization": "Bearer " + self.config.api_key, "Content-Type": "application/json"})
            if response.status_code != 200:
                code = "MODEL_AUTH_ERROR" if response.status_code in {401,403} else "MODEL_RATE_LIMIT" if response.status_code == 429 else "MODEL_UNAVAILABLE"
                raise ProviderError(code)
            if len(response.content) > 1_000_000:
                raise ProviderError("MODEL_INVALID_OUTPUT")
            try:
                body = strict_json(response.text)
            except Exception:
                raise ProviderError("MODEL_INVALID_OUTPUT") from None
            usage = body.get("usage") if isinstance(body, dict) else None
            normalized_usage = None
            if isinstance(usage, dict):
                p, c, h = usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("prompt_cache_hit_tokens", 0)
                if all(type(x) is int and x >= 0 for x in (p,c,h)) and h <= p and type(usage.get("total_tokens")) is int and usage.get("total_tokens") == p+c and usage.get("prompt_cache_miss_tokens",p-h) == p-h:
                    normalized_usage = {"prompt_tokens":p,"completion_tokens":c,"total_tokens":p+c,"prompt_cache_hit_tokens":h}
                    # Preserve known current-call usage even when settlement or
                    # a subsequent bound/model check fails before diagnostics.
                    self.last_response_metadata = {"call_id": call_id, "usage": normalized_usage}
                    try:
                        charged = self.ledger.settle(call_id, prompt_tokens=p, completion_tokens=c, cache_hit_tokens=h)
                        settled = True
                        if p > input_bound or c > limits.max_tokens:
                            self.ledger.freeze()
                            raise ProviderError("TOKEN_BOUND_EXCEEDED")
                    except BudgetError as error:
                        raise ProviderError(error.code) from None
            # Fixed allowlisted shape diagnostics only, never content/arguments,
            # raw IDs, arbitrary upstream keys, headers or raw exception text.
            choices = body.get("choices") if isinstance(body, dict) else None
            first = choices[0] if isinstance(choices,list) and choices and isinstance(choices[0],dict) else {}
            diagnostic_message = first.get("message") if isinstance(first.get("message"),dict) else {}
            diagnostic_calls = diagnostic_message.get("tool_calls")
            reported_model = body.get("model") if isinstance(body,dict) else None
            self.last_response_metadata = {
                "call_id": call_id,
                "reported_model": reported_model if isinstance(reported_model,str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",reported_model) else None,
                "usage": normalized_usage,
                "finish_reason": first.get("finish_reason") if first.get("finish_reason") in {"stop","tool_calls","length","content_filter","insufficient_system_resource","aborted"} else "unknown",
                "choice_count":len(choices) if isinstance(choices,list) else None,
                "message_known_fields":sorted(k for k in diagnostic_message if k in {"role","content","tool_calls","reasoning_content","name","refusal"}),
                "message_unknown_field_count":len(set(diagnostic_message)-{"role","content","tool_calls","reasoning_content","name","refusal"}),
                "content_type":type(diagnostic_message.get("content")).__name__,
                "reasoning_nonempty":bool(diagnostic_message.get("reasoning_content")),
                "tool_call_count":len(diagnostic_calls) if isinstance(diagnostic_calls,list) else None,
                "tool_call_shapes":[{"known_fields":sorted(k for k in c if k in {"id","type","function","index"}),"unknown_field_count":len(set(c)-{"id","type","function","index"}),"id_matches":isinstance(c.get("id"),str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}",c["id"])),"function_known_fields":sorted(k for k in c.get("function",{}) if k in {"name","arguments"}) if isinstance(c.get("function"),dict) else [],"function_unknown_field_count":len(set(c.get("function",{})) - {"name","arguments"}) if isinstance(c.get("function"),dict) else None} for c in diagnostic_calls if isinstance(c,dict)] if isinstance(diagnostic_calls,list) else []}
            if not isinstance(body, dict) or not isinstance(body.get("model"), str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", body["model"]) or not isinstance(body.get("choices"), list) or len(body["choices"]) != 1:
                raise ProviderError("MODEL_INVALID_OUTPUT")
            if body["model"] not in {"deepseek-flash", "deepseek-v4.1-flash", "DeepSeek-V4.1-Flash", "deepseek-v4.1-flash-1017", "DeepSeek-V4.1-Flash-1017"}:
                self.ledger.freeze()
                raise ProviderError("UNAPPROVED_REPORTED_MODEL")
            choice = body["choices"][0]
            if not isinstance(choice, dict) or choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise ProviderError("MODEL_INVALID_OUTPUT")
            message = choice.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant" or set(message) - {"role","content","tool_calls","reasoning_content"} or not (message.get("content") is None or isinstance(message.get("content"), str)) or message.get("reasoning_content"):
                raise ProviderError("MODEL_INVALID_OUTPUT")
            calls = _validate_calls(message.get("tool_calls", []), schemas)
            if bool(calls) != (choice["finish_reason"] == "tool_calls") or not calls and not message.get("content"):
                raise ProviderError("MODEL_INVALID_OUTPUT")
            if not settled:
                self.ledger.retain(call_id, "MISSING_USAGE")
                charged = cost_units(input_bound, limits.max_tokens)
            return ProviderResult(message.get("content"), calls, normalized_usage, "deepseek", self.config.model, body["model"], choice["finish_reason"], call_id, charged/1e9)
        except (TimeoutError, httpx.TimeoutException):
            self.ledger.retain(call_id, "MODEL_TIMEOUT")
            raise ProviderError("MODEL_TIMEOUT", call_id=call_id) from None
        except httpx.HTTPError:
            self.ledger.retain(call_id, "MODEL_UNAVAILABLE")
            raise ProviderError("MODEL_UNAVAILABLE", call_id=call_id) from None
        except ProviderError as error:
            if not settled:
                self.ledger.retain(call_id, error.code)
            raise ProviderError(error.code, call_id=call_id) from None
        except asyncio.CancelledError:
            self.ledger.retain(call_id, "INTERRUPTED_OR_INTERNAL")
            raise
        except Exception:
            self.ledger.retain(call_id, "INTERRUPTED_OR_INTERNAL")
            raise ProviderError("MODEL_UNAVAILABLE", call_id=call_id) from None


class MockProvider:
    """Scripted normalized provider responses; no usage or fake paid tokens."""
    def __init__(self, replies: list[ProviderResult | ProviderError]):
        self.replies, self.calls = list(replies), 0

    async def complete(self, messages, tools, limits=CallLimits(), *, scope="game", tool_choice="auto"):
        limits.validate()
        _validate_messages(messages, _validate_tools(tools))
        self.calls += 1
        if not self.replies:
            raise ProviderError("MOCK_REPLIES_EXHAUSTED")
        reply = self.replies.pop(0)
        if isinstance(reply, ProviderError):
            raise reply
        _validate_calls(list(reply.tool_calls), _validate_tools(tools))
        return reply
