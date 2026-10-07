"""Required, strict v3.2 puzzle state and manual login arguments."""
from typing import Annotated, Literal

from pydantic import Field

from .models import GameState, Identifier, StrictModel
from .upgrade_models import DeviceStates, TOOL_MODELS_UPGRADE


class PuzzleStates(StrictModel):
    microscope: Literal["EMPTY", "SLIDE_PLACED"]
    panel: Literal["EMPTY", "STRIP_INSERTED"]


class PuzzleState(GameState):
    level_version: Literal["3.2.0"]
    device_states: DeviceStates
    puzzle_states: PuzzleStates
    observed_object_ids: list[str]
    taken_item_ids: list[str]
    consumed_item_ids: list[str]


class LoginArgs(StrictModel):
    target_id: Identifier
    username: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
    password: Annotated[str, Field(min_length=1, max_length=16, pattern=r"^[0-9]+$")]


TOOL_MODELS_PUZZLE = {**TOOL_MODELS_UPGRADE, "submit_login": LoginArgs}
