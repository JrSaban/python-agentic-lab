from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

"""
DTOs et Validation avec Pydantic V2
"""


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la catégorie")
    color: str = Field(
        default="#FAFAFA", pattern=r"^#[a-fA-F0-9]{6}$", description="Couleur de la catégorie"
    )

    @field_validator("color")
    @classmethod
    def uppercase_color(cls, value: str) -> str:
        return value.upper()


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")

    @field_validator("name", "color")
    @classmethod
    def validate_and_normalize(cls, value: str | None, info):
        if value is None:
            raise ValueError(f"Le champ '{info.field_name}' ne peut pas être null s'il est fourni.")

        if info.field_name == "color":
            return value.upper()

        return value


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
