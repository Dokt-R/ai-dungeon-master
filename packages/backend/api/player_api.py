from fastapi import APIRouter, Depends
from packages.backend.components.player_manager import PlayerManager
from packages.shared.error_handler import fastapi_error_handler
from packages.shared.models import (
    CampaignEndRequest,
    CreatePlayerRequest,
    JoinCampaignRequest,
    ContinueCampaignRequest,
    LeaveCampaignRequest,
)


router = APIRouter(prefix="/players", tags=["players"])


@router.post("/join_campaign", summary="Join an existing campaign")
@fastapi_error_handler
def join_campaign(
    req: JoinCampaignRequest, player_manager: PlayerManager = Depends(PlayerManager)
):
    """
    Join an existing campaign as a player.

    Validates that the player and campaign exist, and that the player is not already joined to another campaign
    on the same server. Optionally creates a new character if character_name is provided and does not exist.

    Args:
        req (JoinCampaignRequest): Request body containing server_id, campaign_name, player_id, character_name, and character_url.

    Returns:
        dict: Success message and result details.

    Raises:
        ValidationError: If the player is already joined to a campaign or required fields are missing.
        NotFoundError: If the campaign or player does not exist.
    """
    result = player_manager.join_campaign(
        campaign_name=req.campaign_name,
        player_id=req.player_id,
        server_id=req.server_id,
        character_name=req.character_name,
        character_url=req.character_url,
    )
    return {"message": "Campaign joined successfully.", "result": result}


@router.post(
    "/end_campaign", summary="Temporarily exit a campaign into the command state"
)
@fastapi_error_handler
def end_campaign(
    req: CampaignEndRequest, player_manager: PlayerManager = Depends(PlayerManager)
):
    """
    Temporarily exit a campaign, setting the player's status to 'cmd' (command state).

    Args:
        req (ContinueCampaignRequest): Request body containing server_id, campaign_name, and player_id.

    Returns:
        dict: Success message and optional narrative.

    Raises:
        ValidationError: If the campaign or player is not found or required fields are missing.
        NotFoundError: If the campaign does not exist.
    """
    result = player_manager.end_campaign(
        player_id=req.player_id,
        server_id=req.server_id,
        campaign_name=req.campaign_name,
    )
    return {
        "message": "Campaign exited successfully.",
        "narrative": result.get("narrative", None),
    }


@router.post("/create", summary="Creates a player for the server")
@fastapi_error_handler
def create_player(
    req: CreatePlayerRequest, player_manager: PlayerManager = Depends(PlayerManager)
):
    """
    Create a new player in the database.

    Args:
        req (CreatePlayerRequest): Request body containing player_id and username.

    Returns:
        dict: The created player's player_id and username.

    Note:
        This endpoint is intended for internal testing only.
    """
    player_data = player_manager.create_player(
        player_id=req.player_id, username=req.username
    )
    return player_data


@router.post("/continue_campaign", summary="Continue last active campaign")
@fastapi_error_handler
def continue_campaign(
    req: ContinueCampaignRequest, player_manager: PlayerManager = Depends(PlayerManager)
):
    """
    (Not implemented) Continue the last active campaign for a player.

    Args:
        req (JoinCampaignRequest): Request body containing server_id, campaign_name, player_id, character_name, and character_url.

    Returns:
        dict: Success message and result details.

    Raises:
        NotFoundError: If the campaign or player does not exist.
    """
    result = player_manager.continue_campaign(
        player_id=req.player_id,
    )
    return {"message": "Campaign joined successfully.", "result": result}


@router.post(
    "/remove_campaign", summary="Leave a campaign (removes player from campaign)"
)
@fastapi_error_handler
def remove_campaign(
    req: LeaveCampaignRequest, player_manager: PlayerManager = Depends(PlayerManager)
):
    """
    Remove a player from a campaign.

    Args:
        req (LeaveCampaignRequest): Request body containing server_id, campaign_name, and player_id.

    Returns:
        dict: Success message and result details.

    Raises:
        ValidationError: If the campaign or player is not found or required fields are missing.
        NotFoundError: If the campaign does not exist.
    """
    result = player_manager.remove_campaign(
        player_id=req.player_id,
        server_id=req.server_id,
        campaign_name=req.campaign_name,
    )
    return {"message": "Left campaign successfully.", "result": result}


@router.get(
    "/status/{player_id}", summary="Get player status, campaigns, and characters"
)
@fastapi_error_handler
def get_player(player_id: str, player_manager: PlayerManager = Depends(PlayerManager)):
    """
    Retrieve a summary of the player's campaigns, characters, and current status.

    Args:
        player_id (str): Unique identifier for the player (path parameter).

    Returns:
        dict: Player status, including username, last active campaign, campaigns, and characters.

    Raises:
        NotFoundError: If the player does not exist.
    """
    result = player_manager.get_player(player_id)
    return result
