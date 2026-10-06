"""Strict server state for the v3.1 device progression; no client state imports."""
from typing import Literal

from .models import GameState, Identifier, StrictModel, TOOL_MODELS


class DeviceStates(StrictModel):
    cabinet: Literal["LOCKED", "CODE_ACCEPTED", "OPEN", "ITEM_TAKEN"]
    powerbox: Literal["CLOSED", "OPEN", "MISSING_FUSE", "FUSE_INSTALLED", "CIRCUIT_READY", "POWER_ON"]
    computer: Literal["OFF", "BOOTING", "LOGIN_LOCKED", "UNLOCKED", "DATA_READ"]
    exit: Literal["LOCKED", "CARD_ACCEPTED", "FINAL_CHECK", "UNLOCKED", "OPEN"]


class UpgradeState(GameState):
    # Required marker prevents legacy database rows being silently upgraded.
    level_version: Literal["3.1.0"]
    device_states: DeviceStates
    observed_object_ids: list[str]
    taken_item_ids: list[str]
    consumed_item_ids: list[str]


class InteractArgs(StrictModel):
    target_id: Identifier


TOOL_MODELS_UPGRADE = {**TOOL_MODELS, "interact": InteractArgs}
