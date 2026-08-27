"""
DTOs et Validation avec Pydantic V2.
Équivalent conceptuel des FormRequests (StoreTodoRequest, UpdateTodoRequest)
ET des API Resources (TodoResource) dans Laravel.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Titre de la tâche")
    description: str | None = Field(
        default=None, max_length=1000, description="Description détaillée optionnelle"
    )


class TodoCreate(TodoBase):
    """
    Payload reçu lors d'un POST /todos.
    Équivalent de StoreTodoRequest dans Laravel.
    """

    pass


class TodoUpdate(BaseModel):
    """
    Payload reçu lors d'un PATCH /todos/{id}.
    - Types 'str | None' et 'bool | None' pour satisfaire le typage statique de l'IDE.
    - @field_validator pour interdire 'null' si la clé est fournie.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_completed: bool | None = None

    @field_validator("title", "is_completed")
    @classmethod
    def prevent_explicit_none(cls, value: str | bool | None, info) -> str | bool:
        """
        Équivalent de la règle 'sometimes|required' de Laravel.
        Rejette la requête si le client envoie explicitement la clé avec la valeur null.
        """
        if value is None:
            raise ValueError(f"Le champ '{info.field_name}' ne peut pas être null s'il est fourni.")
        return value


class TodoResponse(TodoBase):
    """
    Payload sérialisé et retourné au client HTTP.
    Équivalent de TodoResource::make($todo) dans Laravel.
    """

    id: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    # from_attributes=True permet à Pydantic d'extraire automatiquement
    # les données depuis les attributs d'un objet SQLAlchemy (ex: todo.title)
    model_config = ConfigDict(from_attributes=True)
