"""
Core Database Models
SQLModel tables for the main entities in the system.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import SecretStr
from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped
from sqlmodel import Field as SQLField, Relationship, SQLModel


# Server Configuration Model
class Server(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = SQLField(primary_key=True)
    api_key: SecretStr = SQLField(sa_column=Column(String), default=None)
    dm_roll_visibility: str = SQLField(default="public")
    player_roll_mode: str = SQLField(default="digital")
    character_sheet_mode: str = SQLField(default="digital_sheet")

    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="server_api", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign-Player Link Table
class CampaignPlayerLink(SQLModel, table=True):
    __tablename__ = "campaign_players"
    campaign_id: int = SQLField(primary_key=True, foreign_key="campaigns.campaign_id")
    player_id: str = SQLField(primary_key=True, foreign_key="players.player_id")


# Player Model
class Player(SQLModel, table=True):
    __tablename__ = "players"
    player_id: str = SQLField(primary_key=True)
    username: Optional[str] = SQLField(default=None)
    player_status: str = SQLField(default="cmd")
    last_active_campaign: Optional[str] = SQLField(
        default=None, foreign_key="campaigns.campaign_name"
    )

    characters: Mapped[List["Character"]] = Relationship(
        back_populates="player", sa_relationship_kwargs={"lazy": "selectin"}
    )
    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="players",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


# Character Model
class Character(SQLModel, table=True):
    __tablename__ = "characters"
    character_id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(...)
    character_url: Optional[str] = SQLField(default=None)

    player_id: str = SQLField(foreign_key="players.player_id")
    player: Mapped["Player"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )

    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id"
    )
    campaign: Mapped["Campaign"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign Model
class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    campaign_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_name: str = SQLField(...)
    owner_id: str = SQLField(...)
    state: Optional[str] = SQLField(default=None)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    server_id: str = SQLField(foreign_key="keys.server_id")
    server_api: Mapped["Server"] = Relationship(
        back_populates="campaigns", sa_relationship_kwargs={"lazy": "selectin"}
    )

    players: Mapped[List["Player"]] = Relationship(
        back_populates="campaigns",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    characters: Mapped[List["Character"]] = Relationship(
        back_populates="campaign", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Memory State Model for Database Persistence
class MemoryStateModel(SQLModel, table=True):
    __tablename__ = "memory_states"
    memory_id: Optional[int] = SQLField(default=None, primary_key=True)
    session_id: str = SQLField(..., index=True, unique=True)
    user_id: Optional[str] = SQLField(default=None, index=True)
    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id", index=True
    )

    # JSON serialized memory data
    messages: str = SQLField(..., sa_column=Column(String))  # JSON serialized
    context: str = SQLField(..., sa_column=Column(String))  # JSON serialized
    scratchpad: str = SQLField(..., sa_column=Column(String))  # JSON serialized

    # Metadata
    turn_count: int = SQLField(default=0)
    total_messages: int = SQLField(default=0)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_activity: datetime = SQLField(default_factory=datetime.utcnow)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    # Relationships
    campaign: Mapped[Optional["Campaign"]] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Indexes for performance
    __table_args__ = ({"sqlite_autoincrement": True},)