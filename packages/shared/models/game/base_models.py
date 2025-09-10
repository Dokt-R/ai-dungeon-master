"""
Models used for inheritance
"""

from typing import Optional

from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Column, Field, SQLModel


class BaseGameModel(SQLModel):
    """Base class for most D&D game elements"""

    # Common fields across most models
    index: str = Field(primary_key=True, description="Unique identifier")
    name: str = Field(description="Display name")
    url: str = Field(description="API endpoint URL")


class BaseGameModelWithDesc(BaseGameModel):
    """Base class for most D&D game elements"""

    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )
