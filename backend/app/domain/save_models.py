"""Additive manual archive arguments; gameplay/snapshot versions stay intact."""
from typing import Annotated

from pydantic import Field, field_validator

from .models import Identifier, StrictModel, VersionRequest


class CreateSaveRequest(VersionRequest):
    name: Annotated[str, Field(max_length=40)] = ''

    @field_validator('name')
    @classmethod
    def trim_name(cls, value):
        return value.strip()


class SelectedSave(StrictModel):
    save_id: Identifier
