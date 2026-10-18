"""Public, store-independent AI runtime boundary. No private game state or auth."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RuntimeBoundaryError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Version:
    revision: int
    generation: str

    @classmethod
    def from_state(cls, state: dict) -> "Version":
        return cls(state["revision"], state["generation"])


@dataclass(frozen=True)
class TurnStart:
    turn_id: str
    message: str
    visible_state: dict
    history: tuple[dict, ...] = ()
    mode: str = "preset"


@dataclass(frozen=True)
class Snapshot:
    visible_state: dict


@dataclass(frozen=True)
class ReadResult:
    ok: bool
    visible_state: dict
    observation: str | None = None
    new_clue_ids: tuple[str, ...] = ()
    error_code: str | None = None


@dataclass(frozen=True)
class ProposalCandidate:
    tool: str
    arguments: dict
    clue_refs: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    error_code: str | None = None


@dataclass(frozen=True)
class TurnResult:
    # Only answer, clue_refs, status, stop_reason and usage. Backend adds truth.
    data: dict
    candidate: ProposalCandidate | None
    trace: tuple[dict, ...]
    expected_version: Version


class RuntimeCallbacks(Protocol):
    async def snapshot(self, expected: Version) -> Snapshot: ...
    async def read_tool(self, expected: Version, tool: str, arguments: dict) -> ReadResult: ...
    async def precheck_proposal(self, expected: Version, candidate: ProposalCandidate) -> CheckResult: ...
