from fastapi import APIRouter
from pydantic import BaseModel
from packages.backend.components.player_manager import PlayerManager
from packages.shared.error_handler import fastapi_error_handler

router = APIRouter()
player_manager = PlayerManager()