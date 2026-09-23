from pydantic import BaseModel, ConfigDict, Field


class Operator(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    operator_id: str = Field(pattern=r"^OP\d{4}$")
    name: str
    home_site_id: str = Field(pattern=r"^S\d{2}$")
    experience_years: float = Field(ge=0)
    certifications: list[str] = Field(default_factory=list)
