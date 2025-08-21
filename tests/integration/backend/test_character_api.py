import uuid

import pytest
import pytest_asyncio

from packages.shared.errors import ErrorCode
from packages.shared.routes import ROUTES

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def player_id(client):
    test_player_id = str(uuid.uuid4())
    username = "TestPlayer"
    resp = await client.post(
        ROUTES.player_create(), json={"player_id": test_player_id, "username": username}
    )
    assert resp.status_code == 200
    return test_player_id


# --- Test sections for each endpoint will go below ---


async def test_add_character(client, player_id):
    resp = await client.post(
        ROUTES.character_add(),
        json={
            "player_id": player_id,
            "name": "TestPlayer",
            "character_url": "http://example.com",
        },
    )
    data = resp.json()
    assert resp.status_code == 200
    assert "character_id" in data


async def test_add_character_invalid_name(client, player_id):
    # Too short
    resp = await add_character(client, player_id, "")
    assert resp.status_code == 422
    # Too long
    resp = await add_character(client, player_id, "A" * 33)
    assert resp.status_code == 422
    # Invalid characters
    resp = await add_character(client, player_id, "Invalid!@#")
    assert resp.status_code == 422


async def test_add_character_missing_fields(client):
    resp = await client.post(ROUTES.character_add(), json={})
    assert resp.status_code == 422


async def test_add_character_not_found_player(client):
    resp = await add_character(client, "nonexistent", "Hero")
    assert resp.status_code == 404


async def test_update_character_not_found(client, player_id):
    resp = await client.post(
        ROUTES.character_update(), json={"character_id": 99999, "name": "NewName"}
    )
    error = ErrorCode.CHARACTER_NOT_FOUND
    assert resp.status_code == error.status_code
    print(error)
    assert error.error_code in resp.text


async def test_update_character_duplicate_name(client, player_id):
    # Add two characters
    await client.post(ROUTES.character_add(), json={"player_id": player_id, "name": "Char1"})
    resp2 = await client.post(
        ROUTES.character_add(), json={"player_id": player_id, "name": "Char2"}
    )
    char2_id = resp2.json()["character_id"]
    # Try to rename Char2 to Char1
    resp = await client.post(
        ROUTES.character_update(), json={"character_id": char2_id, "name": "Char1"}
    )
    error = ErrorCode.DUPLICATE_CHARACTER
    assert resp.status_code == error.status_code
    assert error.error_code in resp.text


async def test_add_duplicate_character(client, player_id):
    await client.post(
        ROUTES.character_add(), json={"player_id": player_id, "name": "DupChar"}
    )
    resp = await client.post(
        ROUTES.character_add(), json={"player_id": player_id, "name": "DupChar"}
    )
    error = ErrorCode.DUPLICATE_CHARACTER
    assert resp.status_code == error.status_code
    assert error.error_code in resp.text


async def test_list_characters(client, player_id):
    await client.post(
        ROUTES.character_add(), json={"player_id": player_id, "name": "ListChar"}
    )
    response = await client.post(ROUTES.character_list(), json={"player_id": player_id})
    assert response.status_code == 200
    data = response.json()
    assert "characters" in data
    assert any(c["name"] == "ListChar" for c in data["characters"])


async def test_update_character(client, player_id):
    add_resp = await add_character(client, player_id, "UpdatedChar")
    char_id = add_resp.json()["character_id"]
    response = await client.post(
        ROUTES.character_update(), json={"character_id": char_id, "name": "UpdatedChar"}
    )
    assert response.status_code == 200
    list_resp = await client.post(ROUTES.character_list(), json={"player_id": player_id})
    chars = list_resp.json()["characters"]
    assert any(c["name"] == "UpdatedChar" for c in chars)


async def test_remove_character(client, player_id):
    add_resp = await add_character(client, player_id, "RemovableChar")
    char_id = add_resp.json()["character_id"]
    response = await client.post(ROUTES.character_remove(), json={"character_id": char_id})
    assert response.status_code == 200
    list_resp = await client.post(ROUTES.character_list(), json={"player_id": player_id})
    chars = list_resp.json()["characters"]
    assert not any(c["character_id"] == char_id for c in chars)
    # TODO: Further update to assert not in any other command listing characters
    # TODO: Assert that when a character gets deleted, campaign char_id is null


async def test_remove_already_removed_character(client, player_id):
    add_resp = await add_character(client, player_id, "RemovableChar")
    char_id = add_resp.json()["character_id"]
    resp1 = await client.post(ROUTES.character_remove(), json={"character_id": char_id})
    assert resp1.status_code == 200
    list_resp = await client.post(ROUTES.character_list(), json={"player_id": player_id})
    chars = list_resp.json()["characters"]
    assert not any(c["character_id"] == char_id for c in chars)
    resp2 = await client.post(ROUTES.character_remove(), json={"character_id": char_id})
    assert resp2.status_code == 404


async def test_join_campaign_with_character(client, player_id):
    # Create Campaign
    await client.post(
        ROUTES.campaign_create(),
        json={
            "campaign_name": "Test Campaign",
            "server_id": "test-server",
            "owner_id": "owner_id",
        },
    )
    # Join campaign with character data
    join_payload = {
        "server_id": "test-server",
        "campaign_name": "Test Campaign",
        "player_id": player_id,
        "character_name": "Hero",
        "character_url": "http://dndbeyond.com/hero",
    }
    resp = await client.post(ROUTES.player_join_campaign(), json=join_payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["campaign_name"] == "Test Campaign"
    assert data["player_id"] == player_id
    assert data["character_id"] is not None
    assert data["status"] == "joined"


# --- Helper Functions --- #


async def add_character(client, player_id, name):
    response = await client.post(
        ROUTES.character_add(),
        json={
            "player_id": player_id,
            "name": name,
            "character_url": "http://dndbeyond.com/hero",
        },
    )
    return response
