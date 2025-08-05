import sqlite3
from fastapi import APIRouter
from pydantic import BaseModel, Field
from packages.backend.components.player_manager import PlayerManager
from packages.shared.error_handler import fastapi_error_handler


router = APIRouter(prefix="/players", tags=["players"])
player_manager = PlayerManager()


class CreatePlayerRequest(BaseModel):
    """
    Request model for creating a new player.

    Fields:
        user_id (str): Unique identifier for the player. Must be 3-64 characters, alphanumeric, dashes or underscores.
        username (str): Username for the player. Must be 3-32 characters, alphanumeric, dashes, underscores, or spaces.
    """

    user_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[\w\- ]+$")


class JoinCampaignRequest(BaseModel):
    """
    Request model for joining a campaign.

    Fields:
        server_id (str): Unique identifier for the server.
        campaign_name (str): Name of the campaign to join.
        player_id (str): Unique identifier for the player.
        character_name (str, optional): Name of the character to use or create.
        dnd_beyond_url (str, optional): D&D Beyond URL for the character.
    """

    server_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    campaign_name: str = Field(..., min_length=1, max_length=64)
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    character_name: str = Field(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    dnd_beyond_url: str = None


class ContinueCampaignRequest(BaseModel):
    """
    Request model for ending or continuing a campaign.

    Fields:
        server_id (str): Unique identifier for the server.
        campaign_name (str): Name of the campaign.
        player_id (str): Unique identifier for the player.
    """

    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")


class LeaveCampaignRequest(BaseModel):
    """
    Request model for leaving a campaign.

    Fields:
        server_id (str): Unique identifier for the server.
        campaign_name (str): Name of the campaign to leave.
        player_id (str): Unique identifier for the player.
    """

    server_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    campaign_name: str = Field(..., min_length=1, max_length=64)
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")


@router.post("/join_campaign", summary="Join an existing campaign")
@fastapi_error_handler
def join_campaign(req: JoinCampaignRequest):
    """
    Join an existing campaign as a player.

    Validates that the player and campaign exist, and that the player is not already joined to another campaign
    on the same server. Optionally creates a new character if character_name is provided and does not exist.

    Args:
        req (JoinCampaignRequest): Request body containing server_id, campaign_name, player_id, character_name, and dnd_beyond_url.

    Returns:
        dict: Success message and result details.

    Raises:
        ValidationError: If the player is already joined to a campaign or required fields are missing.
        NotFoundError: If the campaign or player does not exist.
    """
    print("inside API")
    result = player_manager.join_campaign(
        campaign_name=req.campaign_name,
        player_id=req.player_id,
        server_id=req.server_id,
        character_name=req.character_name,
        dnd_beyond_url=req.dnd_beyond_url,
    )
    print("after API", result)
    return {"message": "Campaign joined successfully.", "result": result}


@router.post(
    "/end_campaign", summary="Temporarily exit a campaign into the command state"
)
@fastapi_error_handler
def end_campaign(req: ContinueCampaignRequest):
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


@router.post("/create", summary="Used for internal testing only")
@fastapi_error_handler
def create_player(req: CreatePlayerRequest):
    """
    Create a new player in the database.

    Args:
        req (CreatePlayerRequest): Request body containing user_id and username.

    Returns:
        dict: The created player's user_id and username.

    Note:
        This endpoint is intended for internal testing only.
    """
    conn = sqlite3.connect(player_manager.db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO Players (user_id, username) VALUES (?, ?)",
            (req.user_id, req.username),
        )
        conn.commit()
        return {"user_id": req.user_id, "username": req.username}
    finally:
        conn.close()


@router.post("/continue_campaign", summary="Continue last active campaign")
@fastapi_error_handler
def continue_campaign(req: ContinueCampaignRequest):
    """
    (Not implemented) Continue the last active campaign for a player.

    Args:
        req (JoinCampaignRequest): Request body containing server_id, campaign_name, player_id, character_name, and dnd_beyond_url.

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
    "/leave_campaign", summary="Leave a campaign (removes player from campaign)"
)
@fastapi_error_handler
def leave_campaign(req: LeaveCampaignRequest):
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
    result = player_manager.leave_campaign(
        player_id=req.player_id,
        server_id=req.server_id,
        campaign_name=req.campaign_name,
    )
    return {"message": "Left campaign successfully.", "result": result}


@router.get(
    "/status/{player_id}", summary="Get player status, campaigns, and characters"
)
@fastapi_error_handler
def get_player_status(player_id: str):
    """
    Retrieve a summary of the player's campaigns, characters, and current status.

    Args:
        player_id (str): Unique identifier for the player (path parameter).

    Returns:
        dict: Player status, including username, last active campaign, campaigns, and characters.

    Raises:
        NotFoundError: If the player does not exist.
    """
    result = player_manager.get_player_status(player_id)
    return {"player_status": result}
