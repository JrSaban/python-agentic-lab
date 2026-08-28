from sqlalchemy import Column, ForeignKey, Table

from src.core.database import Base

todos_categories = Table(
    "todos_categories",
    Base.metadata,
    Column("todo_id", ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)
