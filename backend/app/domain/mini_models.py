"""Strict v3.3 state; all minigame operations are manual-only."""
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .models import StrictModel
from .puzzle_models import PuzzleState, TOOL_MODELS_PUZZLE

ModuleId = Literal['c00', 'c01', 'c02', 'c10', 'c11', 'c12', 'c20', 'c21', 'c22']
DeviceId = Literal['cooling', 'lighting', 'safety', 'ventilation']
Rotation = Annotated[int, Field(ge=0, le=3)]


class MiniState(PuzzleState):
    level_version: Literal['3.3.0']
    circuit_rotations: Annotated[list[Rotation], Field(min_length=9, max_length=9)]


class CircuitArgs(StrictModel):
    target_id: Literal['r2_powerbox']


class RotateArgs(CircuitArgs):
    module_id: ModuleId


class SequenceArgs(StrictModel):
    target_id: Literal['r3_panel']
    device_ids: Annotated[list[DeviceId], Field(min_length=4, max_length=4)]

    @field_validator('device_ids')
    @classmethod
    def unique_devices(cls, value):
        if len(set(value)) != 4:
            raise ValueError('Device identifiers must be unique')
        return value


TOOL_MODELS_MINI = {**TOOL_MODELS_PUZZLE, 'rotate_circuit': RotateArgs,
                    'submit_circuit': CircuitArgs, 'submit_sequence': SequenceArgs}
