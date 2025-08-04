from fastapi import APIRouter
from pydantic import BaseModel
from packages.backend.components.campaign_manager import CampaignManager
from packages.shared.error_handler import fastapi_error_handler

router = APIRouter()
campaign_manager = CampaignManager()


class CampaignCreateRequest(BaseModel):
    server_id: str
    campaign_name: str
    owner_id: str


class CampaignContinueRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str


class CampaignEndRequest(BaseModel):
    server_id: str
    campaign_name: str
    player_id: str


@router.post("/campaigns/new", summary="Create a new campaign")
@fastapi_error_handler
def create_campaign(req: CampaignCreateRequest):
    campaign_manager.create_campaign(
        server_id=req.server_id,
        campaign_name=req.campaign_name,
        owner_id=req.owner_id,
    )
    return {"message": "Campaign created successfully."}


#! ALL CODE BELOW THIS LINE IS A PLACEHOLDER AND SHOULD BE IGNORED UNLESS REQUESTED

# @router.post("/campaigns/kick", summary="Kick a player from the campaign")
# @fastapi_error_handler
# def kick_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/delete", summary="Delete a campaign")
# @fastapi_error_handler
# def delete_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign deleted successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/invite", summary="Invite a player to the campaign")
# @fastapi_error_handler
# def invite_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/leave", summary="Leave a campaign.")
# @fastapi_error_handler
# def leave_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Could return players, assets, NPCs, lore, plot threads, story arcs, quests, locations
# @router.post("/campaigns/list", summary="List campaign information")
# @fastapi_error_handler
# def list_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/summary", summary="Exit a campaign")
# @fastapi_error_handler
# def summary_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# @router.post("/campaigns/edit", summary="Exit a campaign")
# @fastapi_error_handler
# def edit_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Start, end session. Potential get current session.
# @router.post("/campaigns/session", summary="Exit a campaign")
# @fastapi_error_handler
# def session_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Park a campaign in case you want to hide it for the time being
# @router.post("/campaigns/archive", summary="Exit a campaign")
# @fastapi_error_handler
# def archive_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? States campaign name, players, permissions and important info
# @router.post(
#     "/campaigns/info",
#     summary="States campaign name, players, permissions and important info",
# )
# @fastapi_error_handler
# def info_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }


# # ? Opens a list of current players and their permissions.
# @router.post(
#     "/campaigns/permissions",
#     summary="Opens a list of current players and their permissions.",
# )
# @fastapi_error_handler
# def permissions_campaign(req: CampaignContinueRequest):
#     result = campaign_manager.resume_campaign(
#         player_discord_id=req.player_id,
#         campaign_name=req.campaign_name,
#         server_id=req.server_id,
#     )
#     return {
#         "message": "Campaign exited successfully.",
#         "narrative": result["narrative"],
#     }
