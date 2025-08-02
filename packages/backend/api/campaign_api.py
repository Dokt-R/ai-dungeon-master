from fastapi import APIRouter, HTTPException, Path, Body
from pydantic import BaseModel
import os
from packages.backend.components.campaign_manager import CampaignManager

router = APIRouter()
campaign_manager = CampaignManager()


class CampaignCreateRequest(BaseModel):
    server_id: str
    campaign_name: str
    owner_id: str


class CampaignJoinRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str


class CampaignContinueRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str


class CampaignEndRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str

@router.post("/campaigns/", summary="Create a new campaign")
def create_campaign(req: CampaignCreateRequest):
    try:
        campaign_manager.create_campaign(
            server_id=req.server_id,
            campaign_name=req.campaign_name,
            owner_id=req.owner_id,
        )
        return {"message": "Campaign created successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/join", summary="Join an existing campaign")
def join_campaign(req: CampaignJoinRequest):
    try:
        result = campaign_manager.join_campaign(
            server_id=req.server_id,
            campaign_name=req.campaign_name,
            player_id=req.player_id,
        )
        return {"message": "Joined campaign successfully.", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/end", summary="Exit a campaign")
def end_campaign(req: CampaignContinueRequest):
    try:
        result = campaign_manager.resume_campaign(
            player_discord_id=req.player_id,
            campaign_name=req.campaign_name,
            server_id=req.server_id,
        )
        return {
            "message": "Campaign exited successfully.",
            "narrative": result["narrative"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
