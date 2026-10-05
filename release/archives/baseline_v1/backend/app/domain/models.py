from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyRequest(StrictModel):
    pass


class VersionRequest(StrictModel):
    request_id: Identifier
    revision: Annotated[int, Field(ge=0)]
    generation: str


class ActionRequest(VersionRequest):
    tool: str
    arguments: dict


class AITurnRequest(VersionRequest):
    message: Annotated[str, Field(min_length=1, max_length=2000)]


class InspectArgs(StrictModel):
    object_id: Identifier


class InventoryArgs(StrictModel):
    pass


class TakeArgs(StrictModel):
    item_id: Identifier


class UseArgs(StrictModel):
    item_id: Identifier
    target_id: Identifier


class CodeArgs(StrictModel):
    target_id: Identifier
    code: Annotated[str, Field(min_length=1, max_length=16, pattern=r"^[0-9]+$")]


class MoveArgs(StrictModel):
    destination_id: Literal["R1", "R2", "R3", "EXIT"]


TOOL_MODELS = {
    "inspect": InspectArgs, "get_inventory": InventoryArgs, "take": TakeArgs,
    "use_item": UseArgs, "submit_code": CodeArgs, "move": MoveArgs,
}


def validate_generation(value: str) -> None:
    if str(UUID(value)) != value.lower():
        raise ValueError("Generation must use the UUID format")


class GameState(StrictModel):
    room_id: Literal["R1", "R2", "R3", "EXIT"] = "R1"
    inventory: list[str] = Field(default_factory=list)
    discovered_clue_ids: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=lambda: {
        "r2_unlocked": False, "power_on": False, "r3_unlocked": False, "check_done": False,
    })
    opened_containers: list[str] = Field(default_factory=list)
    status: Literal["playing", "won"] = "playing"
    revision: Annotated[int, Field(ge=0)] = 0
    generation: str = Field(default_factory=lambda: str(uuid4()))


class RuleError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

