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

@router.post(
    "/players/end_campaign", summary="Temporarily exit a campaign into the command state"
)
@fastapi_error_handler
def end_campaign(req: CampaignContinueRequest):
    result = player_manager.end_campaign(
        player_discord_id=req.player_id,
        server_id=req.server_id,
        campaign_name=req.campaign_name,
    )
    return {
        "message": "Campaign exited successfully.",
        "narrative": result["narrative"],
    }

#! Not used yet
@router.post("/players/continue_campaign", summary="Continue last active campaign")
@fastapi_error_handler
def continue_campaign(req: CampaignContinueRequest):
    result = player_manager.resume_campaign(
        player_discord_id=req.player_id,
        campaign_name=req.campaign_name,
        server_id=req.server_id,
    )
    return {
        "message": "Campaign joined successfully.",
        "narrative": result["narrative"],
    }