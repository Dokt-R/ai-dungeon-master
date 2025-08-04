from fastapi import APIRouter
from pydantic import BaseModel
from packages.backend.components.player_manager import PlayerManager
from packages.shared.error_handler import fastapi_error_handler

router = APIRouter()
player_manager = PlayerManager()

class CampaignJoinRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str


@router.post("/players/join_campaign", summary="Join an existing campaign")
@fastapi_error_handler
def join_campaign(req: CampaignJoinRequest):
    result = player_manager.join_campaign(
        campaign_name=req.campaign_name,
        player_id=req.player_id,
    )
    return {"message": "Campaign joined successfully.", "result": result}