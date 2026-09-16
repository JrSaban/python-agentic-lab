"""DTOs et Validation avec Pydantic V2."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Payload reçu lors d'un POST /auth/login."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., max_length=255, description="Email de l'utilisateur")
    password: str = Field(
        ..., min_length=6, max_length=255, description="Mot de passe de l'utilisateur"
    )

    @field_validator("email")
    @classmethod
    def lower_case_email(cls, value: str) -> str:
        """Convertit l'email en minuscules."""
        return value.lower()


class TokenResponse(BaseModel):
    """Payload retourné lors d'un POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
