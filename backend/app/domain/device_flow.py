"""Shared device stages for puzzle versions; presentation never advances state."""
from .models import RuleError
from .upgrade_models import DeviceStates

DEVICE_IDS = {"r1_cabinet": "cabinet", "r2_powerbox": "powerbox", "r2_monitor": "computer", "exit_door": "exit"}
INITIAL = {"cabinet": "LOCKED", "powerbox": "CLOSED", "computer": "OFF", "exit": "LOCKED"}
TRANSITIONS = {
    "powerbox": {"CLOSED": "OPEN", "OPEN": "MISSING_FUSE", "FUSE_INSTALLED": "CIRCUIT_READY", "CIRCUIT_READY": "POWER_ON"},
    "computer": {"OFF": "BOOTING", "BOOTING": "LOGIN_LOCKED", "UNLOCKED": "DATA_READ"},
    "exit": {"CARD_ACCEPTED": "FINAL_CHECK", "FINAL_CHECK": "UNLOCKED", "UNLOCKED": "OPEN"},
    "cabinet": {"CODE_ACCEPTED": "OPEN"},
}


def initial_devices():
    return DeviceStates(**INITIAL)


def advance(devices, field, transitions=None):
    stage = getattr(devices, field)
    mapping = TRANSITIONS[field] if transitions is None else transitions
    if stage not in mapping:
        raise RuleError("PRECONDITION_FAILED", "这件装置正在等待另一种操作。")
    setattr(devices, field, mapping[stage])


def validate_observed_devices(devices, observed_ids):
    for object_id, field in DEVICE_IDS.items():
        if getattr(devices, field) != INITIAL[field] and object_id not in observed_ids:
            raise ValueError("Device progression requires target observation")
