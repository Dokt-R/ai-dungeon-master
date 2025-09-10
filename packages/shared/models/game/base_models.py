"""
Models used for inheritance
"""

from sqlmodel import Field, SQLModel


class BaseGameplayModel(SQLModel):
    """Base class for most D&D game elements"""

    # Common fields across most models
    index: str = Field(primary_key=True, description="Unique identifier")
    name: str = Field(description="Display name")
    url: str = Field(description="API endpoint URL")