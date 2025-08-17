"""
Thin async API client for AI Dungeon Master backend.
Uses centralized route definitions and shared models.
"""

from typing import Any, Dict, List

import httpx

from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    # Add other models as needed
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)
from packages.shared.routes import ROUTES


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def close(self):
        await self.client.aclose()

    # Server Config
    async def set_server_config(
        self, server_id: str, config: ServerConfigModel
    ) -> Dict[str, Any]:
        url = ROUTES.server_config(server_id)
        resp = await self.client.put(url, json=config.dict())
        resp.raise_for_status()
        return resp.json()

    # Campaigns
    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = ROUTES.campaign_create()
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def delete_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = ROUTES.campaign_delete()
        resp = await self.client.delete(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def get_campaign_details(
        self, server_id: str, campaign_name: str
    ) -> Dict[str, Any]:
        url = ROUTES.campaign_details(server_id, campaign_name)
        resp = await self.client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def get_campaign_players(self, campaign_id: int) -> List[Dict[str, Any]]:
        url = ROUTES.campaign_players(campaign_id)
        resp = await self.client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def update_campaign_state(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = ROUTES.campaign_state_update(campaign_id)
        resp = await self.client.put(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def submit_campaign_action(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = ROUTES.campaign_action(campaign_id)
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    # Characters
    async def get_character_info(self, character_id: str) -> Dict[str, Any]:
        url = ROUTES.character_info(character_id)
        resp = await self.client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def add_character(
        self, req: AddCharacterRequest, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = ROUTES.character_add()
        resp = await self.client.post(url, json=req.dict())
        resp.raise_for_status()
        return resp.json()

    async def update_character(self, req: UpdateCharacterRequest) -> Dict[str, Any]:
        url = ROUTES.character_update()
        resp = await self.client.post(url, json=req.dict())
        resp.raise_for_status()
        return resp.json()

    async def remove_character(self, req: RemoveCharacterRequest) -> Dict[str, Any]:
        url = ROUTES.character_remove()
        resp = await self.client.post(url, json=req.dict())
        resp.raise_for_status()
        return resp.json()

    async def list_characters(self, req: ListCharactersRequest) -> Dict[str, Any]:
        url = ROUTES.character_list()
        resp = await self.client.post(url, json=req.dict())
        resp.raise_for_status()
        return resp.json()

    # Players
    async def join_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = ROUTES.players_join_campaign()
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def end_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = ROUTES.players_end_campaign()
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def remove_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = ROUTES.players_remove_campaign()
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def get_player_status(self, player_id: str) -> Dict[str, Any]:
        url = ROUTES.players_status(player_id)
        resp = await self.client.get(url)
        resp.raise_for_status()
        return resp.json()


# Example usage:
# import asyncio
# from packages.shared.models import AddCharacterRequest
#
# async def main():
#     client = ApiClient(base_url="http://localhost:8000/api/v1")
#     req = AddCharacterRequest(player_id="123", name="Aragorn", character_url=None)
#     result = await client.add_character(req)
#     print(result)
#     await client.close()
#
# asyncio.run(main())
