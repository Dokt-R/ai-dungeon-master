import uuid

import pytest
import pytest_asyncio
from sqlmodel import select

from packages.shared.models import Campaign, CampaignPlayerLink, Character, Player

pytestmark = pytest.mark.asyncio


class BaseTestData:
    state = "active"
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"
    username_2 = "roger_the_shrubber"
    character_name = "tim_the_enchanter"
    character_name_2 = "black_knight"
    url = "http://dndbeyond.com/tim_the_enchanter"
    url2 = "http://dndbeyond.com/black_knight"


@pytest_asyncio.fixture
async def create_campaign(session):
    async def _create_campaign(
        server_id: str, campaign_name: str, owner_id: str
    ) -> Campaign:
        campaign = Campaign(
            server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)
        return campaign

    return _create_campaign


# --- Test sections for each endpoint will go below ---


class TestPlayersCreate(BaseTestData):
    async def test_create_player_success(self, client, session):
        resp = await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username

        # Check DB persistence
        player = await session.get(Player, data["player_id"])
        assert player is not None
        assert player.username == self.username

    async def test_create_player_duplicate(self, client, session):
        resp1 = await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        assert resp1.status_code == 200
        resp2 = await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username_2},
        )
        assert resp2.status_code == 200

        # Should not create duplicate, but update username
        player = await session.get(Player, self.player_id)
        assert player is not None
        assert player.username == self.username_2

        statement = select(Player).where(Player.player_id == self.player_id)
        result = await session.execute(statement)
        results = result.scalars().all()
        assert len(results) == 1

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"username": "ValidName"}, "player_id"),
            ({"player_id": "abc"}, "username"),
            ({}, "player_id"),
            ({"player_id": "a", "username": "ValidName"}, "player_id"),
            ({"player_id": "validid", "username": "a"}, "username"),
            ({"player_id": "invalid id!", "username": "ValidName"}, "player_id"),
            ({"player_id": "validid", "username": "Invalid!@#"}, "username"),
        ],
    )
    async def test_create_player_validation_errors(self, client, payload, field):
        resp = await client.post("/players/create", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestPlayersJoinCampaign(BaseTestData):
    async def test_join_campaign_success(self, session, client, create_campaign):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
            "character_url": self.url,
        }
        resp = await client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["campaign_name"] == self.campaign_name
        assert data["player_id"] == self.player_id
        assert data["character_id"] is not None
        assert data["status"] == "joined"

        # DB checks
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = (await session.execute(statement)).scalars().first()
        assert link is not None
        player = await session.get(Player, link.player_id)
        assert player.player_status == "joined"

        statement = (
            select(Character)
            .where(Character.player_id == player.player_id)
            .where(Character.name == self.character_name)
        )
        character = (await session.execute(statement)).scalars().first()
        assert character is not None
        assert character.character_url == self.url

    async def test_join_campaign_nonexistent_campaign(self, client):
        player_resp = await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        player_id = player_resp.json()["player_id"]
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": player_id,
            "character_name": self.character_name,
        }
        resp = await client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 404

    async def test_join_campaign_already_joined(self, client, create_campaign):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        resp1 = await client.post("/players/join_campaign", json=payload)
        assert resp1.status_code == 200
        resp2 = await client.post("/players/join_campaign", json=payload)
        assert resp2.status_code in (400, 422)
        assert "already joined" in resp2.text or "already" in resp2.text

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
            ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
            ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
            (
                {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
                "server_id",
            ),
            (
                {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
                "campaign_name",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "p",
                },
                "player_id",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "pid",
                    "character_name": "",
                },
                "character_name",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "pid",
                    "character_name": "Invalid!@#",
                },
                "character_name",
            ),
        ],
    )
    async def test_join_campaign_validation_errors(self, client, payload, field):
        resp = await client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text

    async def test_join_campaign_existing_character(
        self, client, create_campaign, session
    ):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Pre-create character
        character = Character(
            player_id=self.player_id, name=self.character_name, character_url=self.url
        )
        session.add(character)
        await session.commit()
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        resp = await client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["character_id"] is not None


class TestPlayersEndCampaign(BaseTestData):
    async def test_end_campaign_success(self, session, client, create_campaign):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        await client.post("/players/join_campaign", json=join_payload)
        # End campaign
        end_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = await client.post("/players/end_campaign", json=end_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Campaign exited successfully."
        assert "narrative" in data

        # DB check: player_status should be 'cmd'
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = (await session.execute(statement)).scalars().first()
        assert link is not None

        statement = select(Player).where(Player.player_id == link.player_id)
        player = (await session.execute(statement)).scalars().first()
        assert player.player_status == "cmd"

    async def test_end_campaign_nonexistent_campaign(self, client):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": self.player_id,
        }
        resp = await client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 404

    async def test_end_campaign_no_last_active(self, client):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "",
            "player_id": self.player_id,
        }
        # Remove campaign_name to trigger last_active_campaign logic
        payload.pop("campaign_name")
        resp = await client.post("/players/end_campaign", json=payload)
        assert (
            resp.status_code == 422
            or resp.status_code == 404
            or "no last active" in resp.text.lower()
        )

    async def test_end_campaign_player_never_joined(
        self, session, client, create_campaign
    ):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Player never joined, should not error, but no update
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = await client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 404

        # DB: There should be no CampaignPlayers row for this player/campaign
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = (await session.execute(statement)).scalars().first()
        assert link is None

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
            ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
            ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
            (
                {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
                "server_id",
            ),
            (
                {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
                "campaign_name",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "p",
                },
                "player_id",
            ),
        ],
    )
    async def test_end_campaign_validation_errors(self, client, payload, field):
        resp = await client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


@pytest.mark.skip(reason="continue_campaign endpoint is not implemented yet")
class TestPlayersContinueCampaign(BaseTestData):
    async def test_continue_campaign_success(
        self, client, create_player, create_campaign
    ):
        player = await create_player(player_id=self.player_id, username=self.username)
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
            "character_name": self.character_name,
        }
        await client.post("/players/join_campaign", json=join_payload)
        # End campaign to simulate a paused state
        end_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
        }
        await client.post("/players/end_campaign", json=end_payload)
        # Continue campaign
        continue_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
        }
        resp = await client.post("/players/continue_campaign", json=continue_payload)
        assert resp.status_code == 500
        assert "not implemented" in resp.text.lower()

    async def test_continue_campaign_nonexistent_campaign(self, client, create_player):
        player = await create_player(player_id=self.player_id, username=self.username)
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": player.player_id,
        }
        resp = await client.post("/players/continue_campaign", json=payload)
        assert resp.status_code == 500
        assert "not implemented" in resp.text.lower()

    async def test_continue_campaign_nonexistent_player(self, client, create_campaign):
        player_id = str(uuid.uuid4())
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player_id,
        }
        resp = await client.post("/players/continue_campaign", json=payload)
        assert resp.status_code == 500
        assert "not implemented" in resp.text.lower()

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
            ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
            ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
            (
                {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
                "server_id",
            ),
            (
                {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
                "campaign_name",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "p",
                },
                "player_id",
            ),
        ],
    )
    async def test_continue_campaign_validation_errors(self, client, payload, field):
        resp = await client.post("/players/continue_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestPlayersRemoveCampaign(BaseTestData):
    async def test_remove_campaign_success(self, session, client, create_campaign):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        await client.post("/players/join_campaign", json=join_payload)
        # Leave campaign
        leave_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = await client.post("/players/remove_campaign", json=leave_payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["campaign_name"] == self.campaign_name
        assert data["player_id"] == self.player_id
        assert data["status"] == "left"
        # DB: player should be removed from CampaignPlayers, last_active_campaign should be NULL
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = (await session.execute(statement)).scalars().first()
        assert link is None

        player = await session.get(Player, self.player_id)
        assert player.last_active_campaign is None

    async def test_remove_campaign_nonexistent_campaign(self, client):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": self.player_id,
        }
        resp = await client.post("/players/remove_campaign", json=payload)
        assert resp.status_code == 404

    async def test_remove_campaign_no_last_active(self, client):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "",
            "player_id": self.player_id,
        }
        # Remove campaign_name to trigger last_active_campaign logic
        payload.pop("campaign_name")
        resp = await client.post("/players/remove_campaign", json=payload)
        assert (
            resp.status_code == 422
            or resp.status_code == 404
            or "no last active" in resp.text.lower()
        )

    async def test_remove_campaign_player_never_joined(
        self, session, client, create_campaign
    ):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Player never joined, should not error, but no update
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = await client.post("/players/remove_campaign", json=payload)
        # Player is not part of the specified campaign
        assert resp.status_code == 404

    @pytest.mark.parametrize(
        "payload,field",
        [
            ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
            ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
            ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
            (
                {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
                "server_id",
            ),
            (
                {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
                "campaign_name",
            ),
            (
                {
                    "server_id": "server1",
                    "campaign_name": "EpicQuest",
                    "player_id": "p",
                },
                "player_id",
            ),
        ],
    )
    async def test_remove_campaign_validation_errors(self, client, payload, field):
        resp = await client.post("/players/remove_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestGetPlayer(BaseTestData):
    async def test_get_player_status_success(self, client, create_campaign):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign and add character
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
            "character_url": self.url,
        }
        await client.post("/players/join_campaign", json=join_payload)
        resp = await client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert any(c["campaign_name"] == self.campaign_name for c in data["campaigns"])
        assert any(c["name"] == self.character_name for c in data["characters"])

    async def test_get_player_status_no_campaigns_or_characters(self, client):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        resp = await client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert data["campaigns"] == []
        assert data["characters"] == []

    async def test_get_player_status_not_found(self, client):
        player_id = str(uuid.uuid4())
        resp = await client.get(f"/players/status/{player_id}")
        assert resp.status_code == 404
        assert "not found" in resp.text

    async def test_get_player_status_multiple_campaigns_and_characters(
        self, client, create_campaign, session
    ):
        await client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        await create_campaign(self.server_id, "EpicQuest", self.owner_id)
        await create_campaign(self.server_id, "SideQuest", self.owner_id)
        # Add two characters
        char1 = Character(
            player_id=self.player_id, name=self.character_name, character_url="url1"
        )
        char2 = Character(
            player_id=self.player_id, name=self.character_name_2, character_url="url2"
        )
        session.add_all([char1, char2])
        await session.commit()
        # Join EpicQuest
        join_payload1 = {
            "server_id": self.server_id,
            "campaign_name": "EpicQuest",
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        await client.post("/players/join_campaign", json=join_payload1)
        # End EpicQuest
        await client.post(
            "/players/end_campaign",
            json={
                "server_id": self.server_id,
                "campaign_name": "EpicQuest",
                "player_id": self.player_id,
            },
        )
        # Join SideQuest
        join_payload2 = {
            "server_id": self.server_id,
            "campaign_name": "SideQuest",
            "player_id": self.player_id,
            "character_name": self.character_name_2,
        }
        await client.post("/players/join_campaign", json=join_payload2)
        resp = await client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert data["player_status"] == "joined"
        assert data["last_active_campaign"] == "SideQuest"
        char_names = {c["name"] for c in data["characters"]}
        assert self.character_name in char_names
        assert self.character_name_2 in char_names
