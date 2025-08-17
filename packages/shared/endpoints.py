"""
Centralized API endpoint definitions for AI Dungeon Master backend.
Auto-generated from docs/architecture/api-specification.md.
! COULD BE REPLACED OR NOT USED AT ALL !
"""

API_V1_PREFIX = "/api/v1"

# Server Config
SERVER_CONFIG = f"{API_V1_PREFIX}/servers/{{server_id}}/config"

# Campaigns
CAMPAIGN_BASE = f"{API_V1_PREFIX}/campaigns"
CAMPAIGN_CREATE = f"{CAMPAIGN_BASE}/new"
CAMPAIGN_DELETE = f"{CAMPAIGN_BASE}/delete"
CAMPAIGN_DETAILS = f"{CAMPAIGN_BASE}/{{server_id}}/{{campaign_name}}"
CAMPAIGN_PLAYERS = f"{CAMPAIGN_BASE}/{{campaign_id}}/players"
CAMPAIGN_STATE_UPDATE = f"{CAMPAIGN_BASE}/{{campaign_id}}/state"
CAMPAIGN_ACTION = f"{CAMPAIGN_BASE}/{{campaign_id}}/action"

# Characters
CHARACTER_BASE = f"{API_V1_PREFIX}/characters"
CHARACTER_INFO = f"{CHARACTER_BASE}/{{character_id}}"
CHARACTER_ADD = f"{CHARACTER_BASE}/add"
CHARACTER_UPDATE = f"{CHARACTER_BASE}/update"
CHARACTER_REMOVE = f"{CHARACTER_BASE}/remove"
CHARACTER_LIST = f"{CHARACTER_BASE}/list"

# Players
PLAYER__BASE = f"{API_V1_PREFIX}/players"
PLAYER_JOIN_CAMPAIGN = f"{PLAYER__BASE}/join_campaign"
PLAYER_END_CAMPAIGN = f"{PLAYER__BASE}/end_campaign"
PLAYER_REMOVE_CAMPAIGN = f"{PLAYER__BASE}/remove_campaign"
PLAYER_STATUS = f"{PLAYER__BASE}/status/{{player_id}}"
