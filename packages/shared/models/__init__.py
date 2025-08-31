"""
Central import location
Import everything here so the rest of your code doesn't change
"""

# Base classes first
# from .audit import AuditLog, SystemLog, UserAction
# from .base import BaseModel, SoftDeleteMixin, TimestampMixin
# from .campaign import Campaign, CampaignMember, CampaignSettings
# from .character import Character, CharacterSheet, CharacterSkill, CharacterStats
# from .game import DiceRoll, GameEvent, GameLog, GameSession
# from .inventory import Equipment, Inventory, Item, ItemCategory

# # Domain models
# from .user import User, UserProfile, UserSession, UserSettings

################################################

from .advanced_voice_features_models import (
    AudioMixConfiguration,
    ConversationIntelligenceData,
    MultiUserConversation,
    SpeakerProfile,
    VoiceActivitySegment,
)
from .ai_action_models import ActionRequest, ActionResponse
from .ai_integration_models import AccuracyValidation, ToolCall, ToolResult
from .api_request_models import (
    AddCharacterRequest,
    CampaignCreateRequest,
    CampaignDeleteRequest,
    CampaignEndRequest,
    CampaignStateRequest,
    ContinueCampaignRequest,
    CreatePlayerRequest,
    JoinCampaignRequest,
    LeaveCampaignRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)
from .core_db_models import (
    Campaign,
    CampaignPlayerLink,
    Character,
    MemoryStateModel,
    Player,
    Server,
)
from .enum_models import CharacterSheetMode, DMVisibility, PlayerRollMode
from .langgraph_state_models import MemoryState
from .memory_management_models import (
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    MemoryContext,
    MemoryEvent,
    MemoryFact,
    MemoryOperation,
    UpdateMemoryEventRequest,
    UpdateMemoryFactRequest,
)
from .performance_models import (
    AudioQualityMetrics,
    PerformanceAlert,
    PerformanceReport,
    PrivacyComplianceRecord,
    VoiceLatencyMetrics,
    VoiceSessionConfig,
)
from .rules_engine_models import RulesQuery, RulesResponse
from .srd_compliance_models import (
    DataSource,
    Monster,
    Spell,
    SRDCompliance,
    Weapon,
)
from .stt_tts_models import (
    AudioProcessingConfig,
    AudioTranscriptionRequest,
    ProviderHealthStatus,
    SpeechSynthesisResult,
    STTServiceStatus,
    TextToSpeechRequest,
    TranscriptionResult,
    TTSServiceStatus,
)
from .voice_command_models import (
    CommandExecutionResult,
    CommandFeedback,
    CommandHistory,
    CommandPattern,
    VoiceCommandIntent,
)
from .voice_integration_models import (
    AudioStreamInfo,
    MemoryQueryRequest,
    VoiceChannelInfo,
    VoiceChannelResponse,
    VoiceCommandResponse,
    VoiceConnection,
    VoiceJoinRequest,
    VoiceLeaveRequest,
    VoicePermission,
    VoiceSession,
    VoiceStatusResponse,
)

# Re-export everything for backward compatibility
__all__ = [
    # Base
    # "BaseModel", "TimestampMixin", "SoftDeleteMixin",

    # # User models
    # "User", "UserProfile", "UserSettings", "UserSession",

    # # Campaign models
    # "Campaign", "CampaignSettings", "CampaignMember",

    # # Character models
    # "Character", "CharacterSheet", "CharacterStats", "CharacterSkill",

    # # Game models
    # "GameSession", "GameEvent", "DiceRoll", "GameLog",

    # # Inventory models
    # "Item", "Equipment", "Inventory", "ItemCategory",

    # # Audit models
    # "AuditLog", "SystemLog", "UserAction",

    # STT and TTS
    "AudioProcessingConfig",
    "AudioTranscriptionRequest",
    "ProviderHealthStatus",
    "SpeechSynthesisResult",
    "STTServiceStatus",
    "TextToSpeechRequest",
    "TranscriptionResult",
    "TTSServiceStatus",

    # Advanced Voice Features
    "AudioMixConfiguration",
    "ConversationIntelligenceData",
    "MultiUserConversation",
    "VoiceActivitySegment",
    "SpeakerProfile",

    # Core Database Models
    "Campaign",
    "CampaignPlayerLink",
    "Character",
    "MemoryStateModel",
    "Player",
    "Server",

    # API Request/Response Models
    "AddCharacterRequest",
    "CampaignCreateRequest",
    "CampaignDeleteRequest",
    "CampaignEndRequest",
    "CampaignStateRequest",
    "ContinueCampaignRequest",
    "CreatePlayerRequest",
    "JoinCampaignRequest",
    "LeaveCampaignRequest",
    "ListCharactersRequest",
    "RemoveCharacterRequest",
    "ServerConfigModel",
    "UpdateCharacterRequest",

    # AI Action Models
    "ActionRequest",
    "ActionResponse",

    # Enum Models
    "CharacterSheetMode",
    "DMVisibility",
    "PlayerRollMode",

    # LangGraph State Models
    "MemoryState",

    # SRD Compliance Models
    "DataSource",
    "Monster",
    "Spell",
    "SRDCompliance",
    "Weapon",

    # Memory Management Models
    "CreateMemoryEventRequest",
    "CreateMemoryFactRequest",
    "MemoryContext",
    "MemoryEvent",
    "MemoryFact",
    "MemoryOperation",
    "UpdateMemoryEventRequest",
    "UpdateMemoryFactRequest",

    # Voice Integration Models
    "AudioStreamInfo",
    "MemoryQueryRequest",
    "VoiceChannelInfo",
    "VoiceChannelResponse",
    "VoiceCommandResponse",
    "VoiceConnection",
    "VoiceJoinRequest",
    "VoiceLeaveRequest",
    "VoicePermission",
    "VoiceSession",
    "VoiceStatusResponse",

    # Performance Models
    "AudioQualityMetrics",
    "PerformanceAlert",
    "PerformanceReport",
    "PrivacyComplianceRecord",
    "VoiceLatencyMetrics",
    "VoiceSessionConfig",

    # Voice Command Models
    "CommandExecutionResult",
    "CommandFeedback",
    "CommandHistory",
    "CommandPattern",
    "VoiceCommandIntent",

    # Rules Engine Models
    "RulesQuery",
    "RulesResponse",

    # AI Integration Models
    "AccuracyValidation",
    "ToolCall",
    "ToolResult",
]

"""
Let’s build this out in four parts:

---

## 🏰 1. **Room Schema (SQLModel)**

Each room will store:

* A description
* Tactical data
* Connections to other rooms (by ID)
* Optional NPCs present

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict

class Room(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str
    exits: Dict[str, str] = Field(default_factory=dict, sa_column_kwargs={"nullable": True})
    is_visited: bool = False
    has_been_cleared: bool = False
```

Use `exits` like:

```json
{ "north": "hall_of_bones", "east": "goblin_den" }
```

---

## ⚔️ 2. **Combat Log Table**

Stores all key turn-by-turn events. You can later query this for replays, LLM prompts, or debugging.

```python
from datetime import datetime

class CombatLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    turn_count: int
    actor_id: str  # e.g. "goblin_1"
    action: str  # e.g. "attacked"
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## 🔁 3. **Integration Pattern (LangGraph Node → SQLModel)**

Here's an example LangGraph-style node that processes a combat action and updates the DB:

```python
from sqlmodel import Session, select
from models import Character, CombatLog, GameState

def process_combat_turn(state: GameState, session: Session) -> GameState:
    actor_id = state.combat_order[state.current_turn]
    actor = session.get(Character, actor_id)
    target_id = "player" if actor_id != state.player_id else "goblin_1"
    target = session.get(Character, target_id)

    damage = 5  # Normally determined by roll/logic
    target.hp = max(0, target.hp - damage)

    session.add(target)
    session.add(CombatLog(
        session_id=state.session_id,
        turn_count=state.turn_count,
        actor_id=actor_id,
        action="attack",
        target_id=target_id,
        details=f"{actor.name} hit {target.name} for {damage} damage"
    ))
    session.commit()

    state.recent_actions.append(f"{actor.name} attacked {target.name} for {damage} damage")
    state.turn_count += 1
    state.current_turn = (state.current_turn + 1) % len(state.combat_order)
    return state
```

---

## ⚡ 4. **Async Setup for SQLModel**

If you're using async (recommended for LangGraph with tool-based I/O), here's how to set it up:

### 📦 Requirements:

```bash
pip install sqlmodel aiosqlite sqlalchemy
```

### 🧪 Async Engine & Session

```python
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///game.db"

async_engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

### 🧠 Using in an async LangGraph node

```python
async def async_process_combat_turn(state: GameState) -> GameState:
    async with async_session_factory() as session:
        result = await session.get(Character, state.combat_order[state.current_turn])
        # ... similar logic as before ...
        await session.commit()
    return state
```

---

## ✅ Summary

You now have:

* `Room` model with exits and flags
* `CombatLog` to track all actions
* Integration pattern for LangGraph (sync + async)
* Async engine setup for better performance

---

Would you like:

* **Inventory** or **spell system modeling**?
* A working **LangGraph definition with these nodes**?
* FastAPI API scaffolding for a game master UI?

Just say the word.

"""