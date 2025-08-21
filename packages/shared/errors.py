from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from typing import Dict


class ErrorCode(str, Enum):
    # Generic
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    AI_API_ERROR = "AI_API_ERROR"
    UNKNOWN = "UNKNOWN"
    INVALID_INPUT = "INVALID_INPUT"
    PERMISSION_DENIED_ERROR = "PERMISSION_DENIED_ERROR"

    # Server
    EMPTY_API_KEY = "EMPTY_API_KEY"

    # Campaign
    DUPLICATE_CAMPAIGN_NAME = "DUPLICATE_CAMPAIGN_NAME"
    CAMPAIGN_NOT_FOUND = "CAMPAIGN_NOT_FOUND"
    NO_LAST_ACTIVE_CAMPAIGN = "NO_LAST_ACTIVE_CAMPAIGN"

    # Character
    CHARACTER_NOT_FOUND = "CHARACTER_NOT_FOUND"
    ACTIVE_CHARACTERS = "ACTIVE_CHARACTERS"
    DUPLICATE_CHARACTER = "DUPLICATE_CHARACTER"
    CHARACTER_EMPTY_FIELDS = "CHARACTER_EMPTY_FIELDS"

    # Player
    PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"
    PLAYER_NOT_IN_CMD = "PLAYER_NOT_IN_CMD"
    PLAYER_ALREADY_IN_CMD = "PLAYER_ALREADY_IN_CMD"
    PLAYER_HAS_NO_CHARACTERS = "PLAYER_HAS_NO_CHARACTERS"

    # Admin/Member Sync
    NO_MEMBERS_FOUND = "NO_MEMBERS_FOUND"
    MEMBER_FETCH_ERROR = "MEMBER_FETCH_ERROR"
    PLAYER_HAS_MULTIPLE_CHARACTERS = "PLAYER_HAS_MULTIPLE_CHARACTERS"
    PLAYER_HAS_NO_CAMPAIGNS = "PLAYER_HAS_NO_CAMPAIGNS"
    PLAYER_NOT_IN_CAMPAIGN = "PLAYER_NOT_IN_CAMPAIGN"

    @property
    def message(self):
        return ERRORS[self].message

    @property
    def player_message(self):
        return PLAYER_ERRORS[self].message

    @property
    def status_code(self):
        return ERRORS[self].status_code

    @property
    def error_code(self):
        return ERRORS[self].error_code


@dataclass(frozen=True)
class ErrorDef:
    error_code: ErrorCode
    message: str
    status_code: int


@dataclass(frozen=True)
class PlayerErrorDef:
    code: str
    message: str


# System facing errors
ERRORS: Dict[str, ErrorDef] = {
    # Generic
    ErrorCode.INVALID_INPUT: ErrorDef(
        ErrorCode.INVALID_INPUT,
        "The provided input is invalid.",
        HTTPStatus.UNPROCESSABLE_ENTITY,
    ),
    ErrorCode.NOT_FOUND: ErrorDef(
        ErrorCode.NOT_FOUND, "Resource not found.", HTTPStatus.NOT_FOUND
    ),
    ErrorCode.VALIDATION_ERROR: ErrorDef(
        ErrorCode.VALIDATION_ERROR,
        "A validation error occurred.",
        HTTPStatus.BAD_REQUEST,
    ),
    ErrorCode.AI_API_ERROR: ErrorDef(
        ErrorCode.AI_API_ERROR,
        "A request to the AI service failed.",
        HTTPStatus.BAD_GATEWAY,
    ),
    ErrorCode.UNKNOWN: ErrorDef(
        ErrorCode.UNKNOWN, "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
    ),
    ErrorCode.PERMISSION_DENIED_ERROR: ErrorDef(
        ErrorCode.PERMISSION_DENIED_ERROR,
        "You do not have permission to perform this action.",
        HTTPStatus.FORBIDDEN,
    ),
    # Server
    ErrorCode.EMPTY_API_KEY: ErrorDef(
        ErrorCode.EMPTY_API_KEY,
        "API key is required and must be a non-empty string.",
        HTTPStatus.BAD_REQUEST,
    ),
    # Campaign
    ErrorCode.CAMPAIGN_NOT_FOUND: ErrorDef(
        ErrorCode.CAMPAIGN_NOT_FOUND,
        "Campaign named **{campaign}** not found.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.DUPLICATE_CAMPAIGN_NAME: ErrorDef(
        ErrorCode.DUPLICATE_CAMPAIGN_NAME,
        "A campaign with that name already exists",
        HTTPStatus.CONFLICT,
    ),
    ErrorCode.NO_LAST_ACTIVE_CAMPAIGN: ErrorDef(
        ErrorCode.NO_LAST_ACTIVE_CAMPAIGN,
        "No campaign specified and no last active campaign found.",
        HTTPStatus.NOT_FOUND,
    ),
    # Character
    ErrorCode.DUPLICATE_CHARACTER: ErrorDef(
        ErrorCode.DUPLICATE_CHARACTER,
        "Character '{name}' already exists for this player.",
        HTTPStatus.CONFLICT,
    ),
    ErrorCode.CHARACTER_EMPTY_FIELDS: ErrorDef(
        ErrorCode.CHARACTER_EMPTY_FIELDS,
        "Player did not provide any of the required fields",
        HTTPStatus.CONFLICT,
    ),
    ErrorCode.CHARACTER_NOT_FOUND: ErrorDef(
        ErrorCode.CHARACTER_NOT_FOUND,
        "Character not found.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.ACTIVE_CHARACTERS: ErrorDef(
        ErrorCode.ACTIVE_CHARACTERS,
        "Campaign has active characters and cannot be deleted.",
        HTTPStatus.BAD_REQUEST,
    ),
    # Player
    ErrorCode.PLAYER_NOT_FOUND: ErrorDef(
        ErrorCode.PLAYER_NOT_FOUND,
        "Player not found.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.PLAYER_HAS_NO_CHARACTERS: ErrorDef(
        ErrorCode.PLAYER_HAS_NO_CHARACTERS,
        "You have no characters to join with. Please create one.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS: ErrorDef(
        ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS,
        "You have multiple characters, please specify one to join with.",
        HTTPStatus.BAD_REQUEST,
    ),
    ErrorCode.PLAYER_HAS_NO_CAMPAIGNS: ErrorDef(
        ErrorCode.PLAYER_HAS_NO_CAMPAIGNS,
        "The player does not have any associated campaigns.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.PLAYER_NOT_IN_CAMPAIGN: ErrorDef(
        ErrorCode.PLAYER_NOT_IN_CAMPAIGN,
        "Player is not part of the specified campaign or has already been removed.",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.PLAYER_NOT_IN_CMD: ErrorDef(
        ErrorCode.PLAYER_NOT_IN_CMD,
        "Player is already in a campaign.\n"
        "Please use /campaign end to enter command mode\n"
        "or specify a different campaign to join",
        HTTPStatus.BAD_REQUEST,
    ),
    ErrorCode.PLAYER_ALREADY_IN_CMD: ErrorDef(
        ErrorCode.PLAYER_ALREADY_IN_CMD,
        "You are already in command mode",
        HTTPStatus.BAD_REQUEST,
    ),
    # Admin/Member Sync
    ErrorCode.NO_MEMBERS_FOUND: ErrorDef(
        ErrorCode.NO_MEMBERS_FOUND,
        "No non-bot members found in server",
        HTTPStatus.NOT_FOUND,
    ),
    ErrorCode.MEMBER_FETCH_ERROR: ErrorDef(
        ErrorCode.MEMBER_FETCH_ERROR,
        "Failed to fetch server members",
        HTTPStatus.INTERNAL_SERVER_ERROR,
    ),
}


# Player facing errors
PLAYER_ERRORS: Dict[str, PlayerErrorDef] = {
    # Generic
    ErrorCode.INVALID_INPUT: PlayerErrorDef(
        ErrorCode.INVALID_INPUT, "The provided input is invalid."
    ),
    ErrorCode.NOT_FOUND: PlayerErrorDef(ErrorCode.NOT_FOUND, "Resource not found."),
    ErrorCode.VALIDATION_ERROR: PlayerErrorDef(
        ErrorCode.VALIDATION_ERROR, "A validation error occurred."
    ),
    ErrorCode.AI_API_ERROR: PlayerErrorDef(
        ErrorCode.AI_API_ERROR, "A request to the AI service failed."
    ),
    ErrorCode.UNKNOWN: PlayerErrorDef(ErrorCode.UNKNOWN, "Something went wrong."),
    ErrorCode.PERMISSION_DENIED_ERROR: PlayerErrorDef(
        ErrorCode.PERMISSION_DENIED_ERROR,
        "You do not have permission to perform this action.",
    ),
    # Server
    ErrorCode.EMPTY_API_KEY: PlayerErrorDef(
        ErrorCode.EMPTY_API_KEY,
        "API key is required and must be a non-empty string.",
    ),
    # Campaign
    ErrorCode.CAMPAIGN_NOT_FOUND: PlayerErrorDef(
        ErrorCode.CAMPAIGN_NOT_FOUND, "Campaign named **{campaign_name}** not found."
    ),
    ErrorCode.DUPLICATE_CAMPAIGN_NAME: PlayerErrorDef(
        ErrorCode.DUPLICATE_CAMPAIGN_NAME,
        "A campaign named **{campaign_name}** already exists. Please use a different name to create the campaign.",
    ),
    ErrorCode.NO_LAST_ACTIVE_CAMPAIGN: PlayerErrorDef(
        ErrorCode.NO_LAST_ACTIVE_CAMPAIGN,
        "No campaign specified and no last active campaign found.",
    ),
    # Character
    ErrorCode.DUPLICATE_CHARACTER: PlayerErrorDef(
        ErrorCode.DUPLICATE_CHARACTER,
        "You already have a character named '{name}'.",
    ),
    ErrorCode.CHARACTER_EMPTY_FIELDS: PlayerErrorDef(
        ErrorCode.CHARACTER_EMPTY_FIELDS,
        "Please provide the required fields in order to proceed.",
    ),
    ErrorCode.CHARACTER_NOT_FOUND: PlayerErrorDef(
        ErrorCode.CHARACTER_NOT_FOUND,
        "You do not have any characters with that name. Please specify an existing character.",
    ),
    ErrorCode.ACTIVE_CHARACTERS: PlayerErrorDef(
        ErrorCode.ACTIVE_CHARACTERS,
        "Campaign has active characters and cannot be deleted.",
    ),
    # Player
    ErrorCode.PLAYER_NOT_FOUND: PlayerErrorDef(
        ErrorCode.PLAYER_NOT_FOUND, "Player not found."
    ),
    ErrorCode.PLAYER_HAS_NO_CHARACTERS: PlayerErrorDef(
        ErrorCode.PLAYER_HAS_NO_CHARACTERS,
        "You have no characters to join with. Please create one.",
    ),
    ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS: PlayerErrorDef(
        ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS,
        "You have multiple characters, please specify one to join with.",
    ),
    ErrorCode.PLAYER_HAS_NO_CAMPAIGNS: PlayerErrorDef(
        ErrorCode.PLAYER_HAS_NO_CAMPAIGNS, "You do are not in any campaigns yet. Join one to be able to perform this action."
    ),
    ErrorCode.PLAYER_NOT_IN_CAMPAIGN: PlayerErrorDef(
        ErrorCode.PLAYER_NOT_IN_CAMPAIGN,
        "Player is not part of the specified campaign or has already been removed.",
    ),
    ErrorCode.PLAYER_NOT_IN_CMD: PlayerErrorDef(
        ErrorCode.PLAYER_NOT_IN_CMD,
        "Player is already in a campaign. Use /campaign end to enter command mode or join a different campaign.",
    ),
    ErrorCode.PLAYER_ALREADY_IN_CMD: PlayerErrorDef(
        ErrorCode.PLAYER_ALREADY_IN_CMD, "You are already in command mode"
    ),
    # Admin/Member Sync
    ErrorCode.NO_MEMBERS_FOUND: PlayerErrorDef(
        ErrorCode.NO_MEMBERS_FOUND,
        "No non-bot members found in server. This might be due to:\n"
        "• Bot doesn't have 'Server Members Intent' enabled in Discord Developer Portal\n"
        "• Members haven't been loaded yet\n"
        "• Server has no human members"
    ),
    ErrorCode.MEMBER_FETCH_ERROR: PlayerErrorDef(
        ErrorCode.MEMBER_FETCH_ERROR,
        "Error fetching server members. Make sure the bot has 'Server Members Intent' enabled in Discord Developer Portal."
    ),
}
