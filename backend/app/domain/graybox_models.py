"""Required run statistics and new-mode-only hint request arguments."""
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .mini_models import MiniState
from .models import AITurnRequest, StrictModel


class RunStatistics(StrictModel):
    started_at: str
    finished_at: str | None
    current_hint_level: Literal[1, 2, 3]
    hint_count: Annotated[int, Field(ge=0)]
    mistake_count: Annotated[int, Field(ge=0)]


class GrayboxState(MiniState):
    level_version: Literal['3.4.0']
    statistics: RunStatistics


class HintRequest(AITurnRequest):
    hint_level: Literal[1, 2, 3] = 1

    @field_validator('hint_level', mode='before')
    @classmethod
    def strict_level(cls, value):
        if type(value) is not int:
            raise ValueError('Hint level must be an integer')
        return value
