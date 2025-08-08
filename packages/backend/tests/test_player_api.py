import pytest
import uuid
from sqlmodel import Session, select

from packages.shared.models import Player, Character, Campaign, CampaignPlayerLink


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


@pytest.fixture
def create_campaign(session: Session):
    def _create_campaign(server_id: str, campaign_name: str, owner_id: str) -> Campaign:
        campaign = Campaign(
            server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        return campaign

    return _create_campaign


# --- Test sections for each endpoint will go below ---


class TestPlayersCreate(BaseTestData):
    def test_create_player_success(self, client, session):
        resp = client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username

        # Check DB persistence
        player = session.get(Player, data["player_id"])
        assert player is not None
        assert player.username == self.username

    def test_create_player_duplicate(self, client, session):
        resp1 = client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        assert resp1.status_code == 200
        resp2 = client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username_2},
        )
        assert resp2.status_code == 200

        # Should not create duplicate, but update username
        player = session.get(Player, self.player_id)
        assert player is not None
        assert player.username == self.username_2

        statement = select(Player).where(Player.player_id == self.player_id)
        results = session.exec(statement).all()
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
    def test_create_player_validation_errors(self, client, payload, field):
        resp = client.post("/players/create", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestPlayersJoinCampaign(BaseTestData):
    def test_join_campaign_success(self, session, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
            "character_url": self.url,
        }
        resp = client.post("/players/join_campaign", json=payload)
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
        link = session.exec(statement).first()
        assert link is not None
        player = session.get(Player, link.player_id)
        assert player.player_status == "joined"

        statement = (
            select(Character)
            .where(Character.player_id == player.player_id)
            .where(Character.name == self.character_name)
        )
        character = session.exec(statement).first()
        assert character is not None
        assert character.character_url == self.url

    def test_join_campaign_nonexistent_campaign(self, client):
        player_id = client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        ).json()["player_id"]
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": player_id,
            "character_name": self.character_name,
        }
        resp = client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 404

    def test_join_campaign_already_joined(self, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        resp1 = client.post("/players/join_campaign", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/players/join_campaign", json=payload)
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
    def test_join_campaign_validation_errors(self, client, payload, field):
        resp = client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text

    def test_join_campaign_existing_character(self, client, create_campaign, session):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Pre-create character
        character = Character(
            player_id=self.player_id, name=self.character_name, character_url=self.url
        )
        session.add(character)
        session.commit()
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        resp = client.post("/players/join_campaign", json=payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["character_id"] is not None


class TestPlayersEndCampaign(BaseTestData):
    def test_end_campaign_success(self, session, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        client.post("/players/join_campaign", json=join_payload)
        # End campaign
        end_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = client.post("/players/end_campaign", json=end_payload)
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
        link = session.exec(statement).first()
        assert link is not None
        assert link.player_status == "cmd"

    def test_end_campaign_nonexistent_campaign(self, client):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": self.player_id,
        }
        resp = client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 404

    def test_end_campaign_no_last_active(self, client):
        client.post(
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
        resp = client.post("/players/end_campaign", json=payload)
        assert (
            resp.status_code == 422
            or resp.status_code == 404
            or "no last active" in resp.text.lower()
        )

    def test_end_campaign_player_never_joined(self, session, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Player never joined, should not error, but no update
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 404
        data = resp.json()
        assert data["message"] == "Campaign exited successfully."
        # DB: There should be no CampaignPlayers row for this player/campaign
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = session.exec(statement).first()
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
    def test_end_campaign_validation_errors(self, client, payload, field):
        resp = client.post("/players/end_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


@pytest.mark.skip(reason="continue_campaign endpoint is not implemented")
class TestPlayersContinueCampaign(BaseTestData):
    def test_continue_campaign_success(self, client, create_player, create_campaign):
        player = create_player(player_id=self.player_id, username=self.username)
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
            "character_name": self.character_name,
        }
        client.post("/players/join_campaign", json=join_payload)
        # End campaign to simulate a paused state
        end_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
        }
        client.post("/players/end_campaign", json=end_payload)
        # Continue campaign
        continue_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player.player_id,
        }
        resp = client.post("/players/continue_campaign", json=continue_payload)
        assert resp.status_code == 500
        assert "not implemented" in resp.text.lower()

    def test_continue_campaign_nonexistent_campaign(self, client, create_player):
        player = create_player(player_id=self.player_id, username=self.username)
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": player.player_id,
        }
        resp = client.post("/players/continue_campaign", json=payload)
        assert resp.status_code == 500
        assert "not implemented" in resp.text.lower()

    def test_continue_campaign_nonexistent_player(self, client, create_campaign):
        player_id = str(uuid.uuid4())
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": player_id,
        }
        resp = client.post("/players/continue_campaign", json=payload)
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
    def test_continue_campaign_validation_errors(self, client, payload, field):
        resp = client.post("/players/continue_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestPlayersRemoveCampaign(BaseTestData):
    def test_remove_campaign_success(self, session, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign first
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        client.post("/players/join_campaign", json=join_payload)
        # Leave campaign
        leave_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = client.post("/players/remove_campaign", json=leave_payload)
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
        link = session.exec(statement).first()
        assert link is None

        player = session.get(Player, self.player_id)
        assert player.last_active_campaign is None

    def test_remove_campaign_nonexistent_campaign(self, client):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": self.player_id,
        }
        resp = client.post("/players/remove_campaign", json=payload)
        assert resp.status_code == 404

    def test_remove_campaign_no_last_active(self, client):
        client.post(
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
        resp = client.post("/players/remove_campaign", json=payload)
        assert (
            resp.status_code == 422
            or resp.status_code == 404
            or "no last active" in resp.text.lower()
        )

    def test_remove_campaign_player_never_joined(
        self, session, client, create_campaign
    ):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Player never joined, should not error, but no update
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }
        resp = client.post("/players/remove_campaign", json=payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["campaign_name"] == self.campaign_name
        assert data["player_id"] == self.player_id
        assert data["status"] == "left"
        # DB: There should be no CampaignPlayers row for this player/campaign
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(Campaign.campaign_name == self.campaign_name)
        )
        link = session.exec(statement).first()
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
    def test_remove_campaign_validation_errors(self, client, payload, field):
        resp = client.post("/players/remove_campaign", json=payload)
        assert resp.status_code == 422
        assert field in resp.text


class TestGetPlayer(BaseTestData):
    def test_get_player_status_success(self, client, create_campaign):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, self.campaign_name, self.owner_id)
        # Join campaign and add character
        join_payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
            "character_url": self.url,
        }
        client.post("/players/join_campaign", json=join_payload)
        resp = client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert any(c["campaign_name"] == self.campaign_name for c in data["campaigns"])
        assert any(c["name"] == self.character_name for c in data["characters"])

    def test_get_player_status_no_campaigns_or_characters(self, client):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        resp = client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert data["campaigns"] == []
        assert data["characters"] == []

    def test_get_player_status_not_found(self, client):
        player_id = str(uuid.uuid4())
        resp = client.get(f"/players/status/{player_id}")
        assert resp.status_code == 404
        assert "not found" in resp.text

    def test_get_player_status_multiple_campaigns_and_characters(
        self, client, create_campaign, session
    ):
        client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )
        create_campaign(self.server_id, "EpicQuest", self.owner_id)
        create_campaign(self.server_id, "SideQuest", self.owner_id)
        # Add two characters
        char1 = Character(
            player_id=self.player_id, name=self.character_name, character_url="url1"
        )
        char2 = Character(
            player_id=self.player_id, name=self.character_name_2, character_url="url2"
        )
        session.add_all([char1, char2])
        session.commit()
        # Join EpicQuest
        join_payload1 = {
            "server_id": self.server_id,
            "campaign_name": "EpicQuest",
            "player_id": self.player_id,
            "character_name": self.character_name,
        }
        client.post("/players/join_campaign", json=join_payload1)
        # End EpicQuest
        client.post(
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
        client.post("/players/join_campaign", json=join_payload2)
        resp = client.get(f"/players/status/{self.player_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        assert data["player_status"] == "joined"
        assert data["last_active_campaign"] == "SideQuest"
        char_names = {c["name"] for c in data["characters"]}
        assert self.character_name in char_names
        assert self.character_name_2 in char_names
