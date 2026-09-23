from pydantic import BaseModel, ConfigDict, Field
from enum import StrEnum


class MachineClass(StrEnum):
    EXCAVATOR = "excavator"
    MINI_EXCAVATOR = "mini_excavator"
    WHEEL_LOADER = "wheel_loader"
    DOZER = "dozer"
    BACKHOE_LOADER = "backhoe_loader"
    ELECTRIC_EXCAVATOR = "electric_excavator"
    ELECTRIC_MINI_EXCAVATOR = "electric_mini_excavator"


class Powertrain(StrEnum):
    DIESEL = "diesel"
    ELECTRIC = "electric"


class Machine(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    machine_id: str = Field(pattern=r"^[A-Z]{2,3}\d{3}$")
    machine_class: MachineClass
    powertrain: Powertrain
    site_id: str = Field(pattern=r"^S\d{2}$")
    primary_operator_id: str | None = Field(default=None, pattern=r"^OP\d{4}$")
